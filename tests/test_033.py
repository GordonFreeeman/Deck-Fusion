"""Beta4 regression checks with synthetic DLLs and mocked Steam/Proton."""
import copy
import json
import shlex
from pathlib import Path
import pytest
from conftest import pe_bytes, vc_fixture
from fusion_api import detect_graphics_api
from fusion_launch import bg3_command, launch_environment
from fusion_prereqs import vc_runtime_evidence, WINETRICKS_SHA256
from fusion_util import FusionError, sha256
from test_120 import apply
from test_130 import runtime_env


def bg3_game(packages):
    e, _, root, _ = packages
    apps = root.parent.parent
    (apps/'appmanifest_1086940.acf').write_text('"AppState" {"appid" "1086940" "name" "Baldur\'s Gate 3" "installdir" "Test Game"}')
    (root/'bin').mkdir(exist_ok=True)
    (root/'bin/bg3_dx11.exe').write_bytes(pe_bytes(api=None))
    (root/'bin/bg3.exe').write_bytes(pe_bytes(api=None))
    p = e.profile('1086940'); p['exe'] = str(root/'bin/bg3_dx11.exe')
    p['opti']['enabled'] = True; p['reshade']['mode'] = 'opti'
    return e, p, root


def test_bg3_default_apply_deploys_winmm_and_shared_reshade(packages):
    e, p, root = bg3_game(packages)
    assert e.scan('1086940')['candidates'][0]['path'] == p['exe']
    plan, stage = apply(e, p)
    assert plan['profile']['opti']['proxy'] == 'winmm'
    assert (root/'bin/winmm.dll').is_file() and (root/'bin/ReShade64.dll').is_file()
    assert 'LoadReshade=true' in (root/'bin/OptiScaler.ini').read_text()
    assert not (root/'bin/dxgi.dll').exists()
    runtime = json.loads((e.store('1086940')/'runtime.json').read_text())
    assert launch_environment(runtime, {})['WINEDLLOVERRIDES'] == 'winmm=n,b'
    assert runtime['bg3_target']['exe'] == p['exe']
    assert stage['launch_after'].count('%command%') == 1


@pytest.mark.parametrize('proxy', ['winmm','version','dxgi','wininet','winhttp','dbghelp','d3d12'])
def test_manual_dll_choice_is_deployed_and_used_in_launch_environment(packages, proxy):
    e, p, root, exe = packages
    p['opti'].update(enabled=True, proxy=proxy)
    p['wine']['opti_proxy_manual'] = True; p['reshade']['mode'] = 'opti'
    _, stage = apply(e, p)
    assert (exe.parent/(proxy+'.dll')).is_file()
    runtime = json.loads((e.store('123')/'runtime.json').read_text())
    assert launch_environment(runtime, {})['WINEDLLOVERRIDES'] == proxy+'=n,b'
    assert e.profile('123')['wine']['opti_proxy_manual']
    assert stage['launch_after']


def test_manual_collision_blocks_instead_of_silently_changing_name(packages):
    e, p, _, exe = packages
    p['opti'].update(enabled=True, proxy='version'); p['wine']['opti_proxy_manual'] = True
    original = pe_bytes()+b'old mod'; (exe.parent/'version.dll').write_bytes(original)
    plan = e.plan(p, '')
    assert plan['blockers'] and 'explicit selection' in str(plan['blockers'])
    assert (exe.parent/'version.dll').read_bytes() == original
    force = e.plan(p, '', force_repair=True)
    assert not force['blockers'] and force['profile']['opti']['proxy'] == 'version'


def test_proxy_change_retires_old_dll_and_override(packages):
    e,p,root,exe = packages
    p['opti']['enabled'] = True; _, stage = apply(e,p)
    p = e.profile('123');p['opti']['proxy']='version';p['wine']['opti_proxy_manual']=True
    apply(e,p,stage['launch_after'])
    assert not (exe.parent/'dxgi.dll').exists() and (exe.parent/'version.dll').is_file()
    cfg=json.loads((e.store('123')/'runtime.json').read_text())
    assert cfg['dll_overrides']=={'version':'n,b'}


def test_bg3_renderer_identity_and_wrong_api(packages):
    e,p,root=bg3_game(packages)
    assert detect_graphics_api(root/'bin/bg3.exe',root,appid='1086940')['api']=='vulkan'
    assert detect_graphics_api(root/'bin/bg3_dx11.exe',root,appid='1086940')['api']=='dx11'
    assert detect_graphics_api(root/'bin/bg3_dx11.exe',root,appid='123')['api']=='auto'
    p['api']='vulkan'
    assert 'does not match' in str(e.plan(p,'')['blockers'])


@pytest.mark.parametrize('operand', ['bin/bg3.exe','bin/bg3_dx11.exe','Launcher/LariLauncher.exe'])
def test_bg3_renderer_command_keeps_proton_and_game_arguments(packages,operand):
    _,p,root=bg3_game(packages)
    cfg={'appid':'1086940','bg3_target':{'root':str(root),'exe':p['exe']}}
    cmd=['/steam/reaper','--','/steam/Proton/proton','waitforexitandrun',str(root/operand),'--skip-launcher','argument with spaces']
    after,note=bg3_command(cfg,cmd)
    assert after[:4]==cmd[:4] and after[4]==p['exe'] and after[5:]==cmd[5:]
    assert 'bg3_dx11.exe' in note
    assert bg3_command({**cfg,'bypass':True},cmd)==(cmd,'')
    assert bg3_command({**cfg,'appid':'123'},cmd)==(cmd,'')
    unrelated=['/some/proton','run','/other/game.exe','--file',str(root/operand)]
    assert bg3_command(cfg,unrelated)[0]==unrelated


@pytest.mark.parametrize('bits',[32,64])
def test_steam_vc_runtime_is_detected_without_winetricks_receipt(runtime_env,bits):
    *_,prefix,m,_=runtime_env
    folder=vc_fixture(prefix,bits)
    assert not (prefix/'winetricks.log').exists()
    evidence=vc_runtime_evidence(prefix,bits)
    assert evidence['satisfied'] and evidence['registered']
    assert not vc_runtime_evidence(prefix,32 if bits==64 else 64)['satisfied']
    (folder/'msvcp140.dll').unlink()
    assert not vc_runtime_evidence(prefix,bits)['satisfied']


@pytest.mark.parametrize('damage',['old','builtin','placeholder','wrong-bits','symlink','missing-publisher','registry-only'])
def test_incomplete_or_builtin_runtime_is_not_accepted(runtime_env,damage,tmp_path):
    *_,prefix,m,_=runtime_env
    folder=vc_fixture(prefix,version=(14,29,0,0) if damage=='old' else (14,44,35211,0))
    dll=folder/'msvcp140.dll'
    if damage in ('builtin','placeholder'):
        data=bytearray(dll.read_bytes());marker=b'Wine builtin DLL' if damage=='builtin' else b'Wine placeholder DLL';data[0x40:0x40+len(marker)]=marker;dll.write_bytes(data)
    elif damage=='wrong-bits': dll.write_bytes(pe_bytes(32))
    elif damage=='symlink':
        outside=tmp_path/'outside.dll';dll.rename(outside);dll.symlink_to(outside)
    elif damage=='missing-publisher':dll.write_bytes(dll.read_bytes().replace('Microsoft Corporation'.encode('utf-16le'),bytes(42)))
    elif damage=='registry-only':dll.unlink()
    (prefix/'winetricks.log').write_text('vcrun2022\n')
    evidence=next(x for x in m.evidence(prefix) if x['name']=='vcrun2022')
    assert evidence['recorded'] and not evidence['satisfied']


def test_existing_vc_skips_installer_without_inventing_receipt(runtime_env,monkeypatch):
    _,_,_,_,prefix,m,payload=runtime_env
    vc_fixture(prefix);payload={**payload,'runtimes':['vcrun2022']}
    monkeypatch.setattr(m,'execute',lambda *_:pytest.fail('existing compatible runtime must not be installed again'))
    plan=m.plan(payload)
    result=m.install({**payload,'approval':plan['approval']},lambda *_:None)
    assert result['state']=='completed' and not (prefix/'winetricks.log').exists()


def test_vcrun_uses_verified_pinned_recipe_in_protontricks(runtime_env,monkeypatch,tmp_path):
    e,_,_,_,_,m,payload=runtime_env
    target=m.target(payload)
    cmd,_=m.command(target,{'kind':'flatpak','executable':'flatpak'},['vcrun2022'])
    assert str(e.source/'vendor/winetricks/winetricks') in shlex.split(cmd[-2])
    assert '--filesystem='+str(e.source/'vendor/winetricks')+':ro' in cmd
    assert '--force' not in cmd[-2] and 'WINEPREFIX' in cmd[-2]
    assert sha256(e.source/'vendor/winetricks/winetricks')==WINETRICKS_SHA256
    fake=tmp_path/'bad-source';(fake/'vendor/winetricks').mkdir(parents=True)
    (fake/'vendor/winetricks/winetricks').write_text('bad recipe')
    monkeypatch.setattr(e,'source',fake)
    with pytest.raises(FusionError,match='integrity'):m.command(target,{'kind':'native','executable':'protontricks'},['vcrun2022'])
