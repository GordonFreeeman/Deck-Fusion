"""Focused 1.2.2 regressions. Synthetic binaries, no rendering/GPU assertions."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest
from conftest import pe_bytes
from fusion_engine import migrate_profile
from fusion_launch import launch_environment, parse_dll_overrides
from fusion_transaction import Transaction
from fusion_util import FusionError, atomic_json, ini_read
from test_110 import fsr_payload
from test_120 import apply


def input_payload(e):
    base=fsr_payload(e)
    with (base/'OptiScaler.ini').open('a') as f:
        f.write('\n[Hotfix]\nManualInputPolling=auto\nDisableOverlays=auto\n')
    return base


def cyberpunk(packages):
    e,p,root,old=packages
    exe=root/'bin/x64/Cyberpunk2077.exe';exe.parent.mkdir(parents=True)
    exe.write_bytes(pe_bytes(api='dx12'));old.unlink()
    p['exe']=str(exe);p['api']='dx12'
    return e,p,root,exe


@pytest.mark.parametrize('inherited',[None,'','0','1','false'])
def test_watermark_off_means_absent_not_zero(inherited):
    original={'OTHER':'yes','FSR_WATERMARK':'1','FSR4_WATERMARK':'1','PROTON_FSR4_INDICATOR':'1','PROTON_FSR4_UPGRADE':'1','MLFI-WATERMARK':'1'}
    if inherited is not None:original['MLSR-WATERMARK']=inherited
    frozen=copy.deepcopy(original)
    result=launch_environment({'opti_enabled':True,'fsr4_watermark':False},original)
    assert 'MLSR-WATERMARK' not in result and 'FSR_WATERMARK' not in result and 'FSR4_WATERMARK' not in result
    assert result['PROTON_FSR4_INDICATOR']=='0'
    assert result['PROTON_FSR4_UPGRADE']=='1' and result['MLFI-WATERMARK']=='1' and original==frozen


def test_watermark_optin_bypass_and_disabled_opti():
    cfg={'opti_enabled':True,'fsr4_watermark':True}
    result=launch_environment(cfg,{})
    assert all(result[key]=='1' for key in ('MLSR-WATERMARK','FSR4_WATERMARK','FSR_WATERMARK','PROTON_FSR4_INDICATOR'))
    original={'MLSR-WATERMARK':'1','PROTON_FSR4_INDICATOR':'1'}
    assert launch_environment({**cfg,'bypass':True},original)==original
    assert launch_environment({**cfg,'opti_enabled':False},original)==original


def test_pair_prevents_optional_bool_recreating_sdk_variable(packages):
    e,p,root,exe=packages;input_payload(e)
    p['api']='dx12';p['opti'].update(enabled=True,fsr_mode='fsr4_int8')
    p['opti']['overrides']={'FSR':{'Fsr4EnableWatermark':'false'}}
    _,prepared=apply(e,p)
    config=ini_read((exe.parent/'OptiScaler.ini').read_text())
    assert config['FSR']['Fsr4EnableWatermark']=='auto'
    assert config['FSR']['Fsr4ForceEnableInt8']=='true'
    # Model only the published optional-bool + presence-check semantics, not AMD rendering.
    runtime=json.loads((e.store('123')/'runtime.json').read_text())
    env=launch_environment(runtime,{'MLSR-WATERMARK':'0'})
    value=config['FSR']['Fsr4EnableWatermark']
    if value in ('true','false'):env['MLSR-WATERMARK']='1' if value=='true' else '0'
    assert 'MLSR-WATERMARK' not in env
    output=subprocess.check_output([str(e.wrapper),'123','--',sys.executable,'-c','import os,json;print(json.dumps(dict(os.environ)))'],
        env={**os.environ,'MLSR-WATERMARK':'1'},text=True)
    assert 'MLSR-WATERMARK' not in json.loads(output)
    log=json.loads((e.store('123')/'last-launch.json').read_text())
    assert log['wrapper_version']==json.loads((Path(__file__).resolve().parents[1]/'package.json').read_text())['displayVersion'] and log['settings']['MLSR-WATERMARK'] is None and isinstance(log['time'],float)
    # Imported or in-game saved false must be repaired without changing the INT8 mode.
    ini=exe.parent/'OptiScaler.ini';ini.write_text(ini.read_text().replace('Fsr4EnableWatermark=auto','Fsr4EnableWatermark=false')+'\n[fsr]\nfsr4enablewatermark=true\n')
    saved=e.profile('123');plan=e.plan(saved,prepared['launch_after'],force_repair=True)
    assert not plan['blockers'],plan
    fixed=e.prepare_approved(saved,prepared['launch_after'],plan['approval_token'],force_repair=True)
    e.finish('123',fixed['token'],fixed['launch_after'])
    text=ini.read_text()
    assert 'Fsr4EnableWatermark=auto' in text and 'fsr4enablewatermark=auto' in text
    assert 'Fsr4ForceEnableInt8=true' in text


def test_input_compat_controls_and_preview_use_supported_keys(packages):
    e,p,root,exe=packages;input_payload(e)
    p['opti'].update(enabled=True,mouse_input='polling',steam_input='keep')
    p['opti']['overrides']={'Hotfix':{'ManualInputPolling':'false','DisableOverlays':'true'}}
    plan,pr=apply(e,p)
    fixes={x['id']:x for x in plan['resolutions']}
    assert fixes['ini-Hotfix-ManualInputPolling']['after']=='true'
    assert fixes['ini-Hotfix-DisableOverlays']['after']=='false'
    assert any('cannot block clicks' in x for x in plan['warnings'])
    ini=ini_read((exe.parent/'OptiScaler.ini').read_text())
    assert dict(ini['Hotfix'])=={'ManualInputPolling':'true','DisableOverlays':'false'}
    saved=e.profile('123');saved['opti'].update(mouse_input='window',steam_input='disable')
    apply(e,saved,pr['launch_after'])
    ini=ini_read((exe.parent/'OptiScaler.ini').read_text())
    assert dict(ini['Hotfix'])=={'ManualInputPolling':'false','DisableOverlays':'true'}


def test_auto_preserves_existing_advanced_and_imported_settings(packages):
    e,p,root,exe=packages;input_payload(e)
    p['opti']['enabled']=True;p['opti']['overrides']={'Hotfix':{'ManualInputPolling':'true','DisableOverlays':'false'}}
    apply(e,p)
    ini=ini_read((exe.parent/'OptiScaler.ini').read_text())
    assert ini['Hotfix']['ManualInputPolling']=='true' and ini['Hotfix']['DisableOverlays']=='false'
    imported=e.sync_from_disk('123')
    assert imported['opti']['mouse_input']=='polling' and imported['opti']['steam_input']=='keep'


@pytest.mark.parametrize('field,value,key',[('mouse_input','polling','ManualInputPolling'),('steam_input','keep','DisableOverlays')])
def test_unsupported_input_option_blocks_without_mutation(packages,field,value,key):
    e,p,root,exe=packages;p['opti'].update(enabled=True,**{field:value})
    plan=e.plan(p,'')
    assert plan['blockers'] and key in plan['blockers'][0]['detail']
    assert not (exe.parent/'OptiScaler.ini').exists()


def test_multiple_existing_dlls_apply_preserve_and_restore(packages):
    e,p,root,exe=cyberpunk(packages);input_payload(e)
    originals={name:pe_bytes()+b'EXISTING MOD '+name.encode() for name in ('dxgi.dll','version.dll','winmm.dll')}
    for name,data in originals.items():(exe.parent/name).write_bytes(data)
    p['opti']['enabled']=True;p['reshade']['mode']='opti'
    p['wine']['custom_overrides']='dxgi=n,b;version=n,b;winmm=n,b;dinput8='
    launch='WINEDLLOVERRIDES="*version=b;version=n,b;OTHER=b,n" %command% --skip-launcher'
    before={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    plan=e.plan(p,launch);assert not plan['blockers'],plan
    assert all(file['selectable'] for file in plan['dll_context']['files'] if file['name'] in originals)
    assert plan['profile']['opti']['proxy'] not in ('dxgi','version','winmm')
    assert before=={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    _,prepared=apply(e,p,launch)
    runtime=json.loads((e.store('123')/'runtime.json').read_text())
    result=parse_dll_overrides(launch_environment(runtime,{'WINEDLLOVERRIDES':'*version=b;version=n,b;OTHER=b,n'})['WINEDLLOVERRIDES'])
    assert all(result[name]=='n,b' for name in ('dxgi','version','winmm'))
    assert result['other']=='b,n' and result['*version']=='b' and result['dinput8']==''
    assert result[next(iter(runtime['dll_overrides']))]=='n,b'
    for name,data in originals.items():assert (exe.parent/name).read_bytes()==data
    restored=e.plan(e.profile('123'),prepared['launch_after'],True);assert not restored['blockers']
    reverse=e.prepare_approved(e.profile('123'),prepared['launch_after'],restored['approval_token'],True)
    e.finish('123',reverse['token'],reverse['launch_after'])
    assert reverse['launch_after']==launch
    for name,data in originals.items():assert (exe.parent/name).read_bytes()==data


def test_diagnostics_uses_unsaved_draft_and_is_bounded_readonly(packages):
    e,p,root,exe=cyberpunk(packages)
    assert e.profile('123')['exe']==''
    files={'bin/x64/version.dll':pe_bytes(),'bin/x64/winmm.dll':pe_bytes(),
           'bin/x64/plugins/cyber_engine_tweaks.asi':b'CET test file','red4ext/RED4ext.dll':b'RED4ext test file',
           'engine/tools/scc.exe':b'redscript test file','red4ext/logs/red4ext.log':b'info\n'*10000+b'ERROR old dependency\n',
           'r6/logs/redscript_r0001.log':b'failed to compile test script\n'}
    for rel,data in files.items():
        f=root/rel;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
    (root/'bin/x64/plugins/cyber_engine_tweaks/mods/TestLua').mkdir(parents=True)
    (root/'red4ext/plugins/TestPlugin').mkdir(parents=True)
    (root/'r6/scripts').mkdir();(root/'r6/scripts/test.reds').write_text('// fixture')
    atomic_json(e.store('123')/'last-launch.json',{'time':time.time()+100})
    before={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    result=e.mod_diagnostics('123',str(exe))
    assert result['selected_exe']==str(exe)
    assert [f['name'] for f in result['frameworks']]==['Cyber Engine Tweaks','RED4ext','redscript']
    assert 'TestLua' in result['frameworks'][0]['children']
    red=next(x for x in result['logs'] if x['name']=='RED4ext')
    assert red['current_launch'] is False and 'ERROR old dependency' in red['error_lines']
    assert len(red['tail'].encode())<=12288 and len(red['tail'].splitlines())<=60
    assert before=={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    assert not (e.store('123')/'profile.json').exists()


def test_diagnostic_scope_and_symlink_rejection(packages,tmp_path):
    e,p,root,exe=cyberpunk(packages)
    outside=tmp_path/'outside';outside.mkdir();secret=outside/'Cyberpunk2077.exe';secret.write_bytes(pe_bytes())
    with pytest.raises(FusionError):e.mod_diagnostics('123',str(secret))
    link=root/'linked';link.symlink_to(outside,target_is_directory=True)
    with pytest.raises(FusionError):e.mod_diagnostics('123',str(link/'Cyberpunk2077.exe'))
    (root/'red4ext').symlink_to(outside,target_is_directory=True)
    report=e.mod_diagnostics('123',str(exe))
    assert 'Symbolic links' in json.dumps(report) or 'Path leaves' in json.dumps(report)
    with pytest.raises(FusionError):e.mod_diagnostics('123','../../../../outside/Cyberpunk2077.exe')


def test_migration_retains_manual_fps_and_old_custom_entries(installation):
    _,p,*_=installation;p['base_fps']=33;p['lsfg']['multiplier']=2
    p['wine']['custom_overrides']='dxgi,version,winmm=n,b'
    p['opti'].pop('mouse_input');p['opti'].pop('steam_input')
    original=copy.deepcopy(p);merged=migrate_profile(p)
    assert merged['base_fps']==33 and merged['lsfg']['multiplier']==2 and merged['wine']==original['wine']
    assert merged['opti']['mouse_input']==merged['opti']['steam_input']=='auto' and p==original


def test_legacy_redscript_and_cet_script_log_paths(packages):
    e,p,root,exe=cyberpunk(packages)
    for rel in ('r6/cache/redscript.log','bin/x64/plugins/cyber_engine_tweaks/scripting.log'):
        f=root/rel;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('ERROR historical fixture\n')
    report=e.mod_diagnostics('123',str(exe))
    assert next(x for x in report['logs'] if x['name']=='redscript')['path']=='r6/cache/redscript.log'
    assert next(x for x in report['logs'] if x['name']=='CET scripts')['present']
    assert all(x['current_launch'] is None for x in report['logs'])
