"""Focused 1.2 regression checks. Synthetic PE payloads, never GPU validation."""
import copy, json, os, subprocess, sys
from pathlib import Path
import pytest
from conftest import pe_bytes
from fusion_launch import launch_environment, parse_dll_overrides, merge_dll_overrides, launch_assignments
from fusion_engine import migrate_profile
from fusion_util import ini_patch, atomic_json, FusionError
from fusion_wine import OPTI_PROXIES, registry_entries
from test_110 import fsr_payload


def apply(e, p, launch=''):
    plan=e.plan(p,launch)
    assert not plan['blockers'],plan
    prepared=e.prepare_approved(p,launch,plan['approval_token'])
    e.finish(p['appid'],prepared['token'],prepared['launch_after'])
    return plan, prepared


def test_watermark_direct_and_proton_switches():
    env={'MLSR-WATERMARK':'1','PROTON_FSR4_INDICATOR':'1','FSR4_WATERMARK':'1',
         'FSR_WATERMARK':'1','PROTON_FSR4_UPGRADE':'4.1.1','MLFI-WATERMARK':'1','KEEP':'yes'}
    result=launch_environment({'opti_enabled':True,'fsr4_watermark':False},env)
    assert 'MLSR-WATERMARK' not in result and result['PROTON_FSR4_INDICATOR']=='0'
    assert 'FSR4_WATERMARK' not in result and 'FSR_WATERMARK' not in result
    assert result['PROTON_FSR4_UPGRADE']=='4.1.1' and result['MLFI-WATERMARK']=='1'
    assert env['MLSR-WATERMARK']=='1'


def test_all_duplicate_case_variant_ini_keys_are_patched():
    text='; keep comments\n[FSR]\nFsr4EnableWatermark=true\nFsr4EnableWatermark=true\nOther=42\n[fsr]\nfsr4enablewatermark=true\n'
    result=ini_patch(text,{'FSR':{'Fsr4EnableWatermark':'false'}})
    assert 'true' not in result and result.count('=false')==3
    assert '; keep comments' in result and 'Other=42' in result


def test_int8_flags_survive_watermark_change(packages):
    e,p,root,exe=packages;fsr_payload(e)
    p['api']='dx12';p['opti'].update(enabled=True,fsr_mode='fsr4_int8')
    plan,prepared=apply(e,p)
    ini=(exe.parent/'OptiScaler.ini').read_text()
    assert 'Fsr4EnableWatermark=auto' in ini
    assert 'Fsr4ForceModel=2' in ini or 'Fsr4ForceEnableInt8=true' in ini
    cfg=json.loads((e.store(p['appid'])/'runtime.json').read_text())
    env={**os.environ,'MLSR-WATERMARK':'1'}
    output=subprocess.check_output([str(e.wrapper),p['appid'],'--',sys.executable,'-c',
        'import os,json;print(json.dumps(dict(os.environ)))'],env=env,text=True)
    assert 'MLSR-WATERMARK' not in json.loads(output)
    log=json.loads((e.store(p['appid'])/'last-launch.json').read_text())
    assert log['settings']['MLSR-WATERMARK'] is None
    assert cfg['requested_fsr_mode']=='fsr4_int8'


@pytest.mark.parametrize('value',['../version=n,b','version=oops','version','a=b;nonsense',
    'a=nn','version=n,,b','bad/name=n','$(touch foo)=n','a\nb=n'])
def test_invalid_custom_entries(value):
    with pytest.raises(FusionError): parse_dll_overrides(value,strict=True)


def test_group_alias_wildcard_disabled_and_last_assignment_preserved():
    env='*version=b;version,winmm=n,b;dinput8=;keep=b,n'
    merged=merge_dll_overrides(env,{'winmm':'n','dxgi':'n,b'})
    assert parse_dll_overrides(merged)=={'*version':'b','version':'n,b','dinput8':'','keep':'b,n','winmm':'n','dxgi':'n,b'}
    assert parse_dll_overrides('VERSION.DLL=native,builtin;version=b')=={'version':'b'}
    text='WINEDLLOVERRIDES="old=n" env WINEDLLOVERRIDES="version=n,b" %command% --skip-launcher'
    assert launch_assignments(text)['WINEDLLOVERRIDES']=='version=n,b'
    with pytest.raises(FusionError,match='shell expansion'):launch_assignments('WINEDLLOVERRIDES="$WINEDLLOVERRIDES;version=n,b" %command%')


def test_detect_preserve_version_and_add_winmm_mod(packages):
    e,p,root,exe=packages;p['opti'].update(enabled=True,proxy='version')
    p['reshade']['mode']='standalone'
    mods={name:pe_bytes()+name.encode() for name in ['Version.dll','winmm.dll']}
    for name,data in mods.items():(exe.parent/name).write_bytes(data)
    p['wine']['custom_overrides']='winmm=n,b'
    launch='WINEDLLOVERRIDES="version=n,b;dinput8=" %command% --skip-launcher'
    context=e.wine_context(p,launch)
    assert {f['name'] for f in context['files'] if f['selectable']}==set(mods)
    before={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    plan=e.plan(p,launch)
    assert not plan['blockers'],plan
    assert plan['profile']['opti']['proxy'] not in ('version','winmm')
    assert 'version=n,b' in plan['dll_summary']['effective']
    assert before=={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()} # Cancel
    _,prepared=apply(e,p,launch)
    for name,data in mods.items():assert (exe.parent/name).read_bytes()==data
    assert launch.split('%command%')[0] in prepared['launch_after']
    cfg=json.loads((e.store(p['appid'])/'runtime.json').read_text())
    result=parse_dll_overrides(launch_environment(cfg,{'WINEDLLOVERRIDES':'version=n,b;dinput8='})['WINEDLLOVERRIDES'])
    assert result['version']=='n,b' and result['winmm']=='n,b' and result['dinput8']==''
    assert result[cfg['dll_overrides'].keys().__iter__().__next__()]=='n,b'
    restored=e.prepare_approved(p,prepared['launch_after'],e.plan(p,prepared['launch_after'],True)['approval_token'],True)
    e.finish(p['appid'],restored['token'],restored['launch_after'])
    assert restored['launch_after']==launch
    for name,data in mods.items():assert (exe.parent/name).read_bytes()==data


def test_custom_only_apply_no_graphics_tool_required(installation):
    e,p,root,exe=installation;p['wine']['custom_overrides']='version=n,b;dinput8='
    plan,prep=apply(e,p,'--skip-launcher')
    assert not plan['changes'] and any(f['id']=='custom-dinput8' for f in plan['resolutions'])
    cfg=json.loads((e.store(p['appid'])/'runtime.json').read_text())
    assert launch_environment(cfg,{'WINEDLLOVERRIDES':'keep=b,n'})['WINEDLLOVERRIDES']=='keep=b,n;dinput8=;version=n,b'
    p=e.profile(p['appid']);p['wine']['custom_overrides']=''
    apply(e,p,prep['launch_after'])
    cfg=json.loads((e.store(p['appid'])/'runtime.json').read_text())
    assert launch_environment(cfg,{'WINEDLLOVERRIDES':'version=b'})['WINEDLLOVERRIDES']=='version=b'


def test_registry_global_per_app_and_unrelated_keys(packages):
    e,p,root,exe=packages;p['opti'].update(enabled=True,proxy='version')
    lib=Path(e.game(p['appid'])['library']);prefix=lib/'steamapps/compatdata/123/pfx';prefix.mkdir(parents=True)
    text='WINE REGISTRY Version 2\n[Software\\\\Wine\\\\DllOverrides]\n"*version"="native,builtin"\n"winmm"="builtin"\n' \
         '[Software\\\\Wine\\\\AppDefaults\\\\'+exe.name+'\\\\DllOverrides]\n"winhttp"="native"\n' \
         '[Software\\\\Wine\\\\AppDefaults\\\\Other.exe\\\\DllOverrides]\n"dxgi"="native"\n'
    (prefix/'user.reg').write_text(text)
    context=e.wine_context(p,'')
    assert set(context['reserved'])>={'version','winmm','winhttp'} and 'dxgi' not in context['reserved']
    plan,prep=apply(e,p)
    assert plan['profile']['opti']['proxy']=='dxgi'
    assert (prefix/'user.reg').read_text()==text
    runtime=json.loads((e.store(p['appid'])/'runtime.json').read_text())
    assert runtime['dll_overrides']=={'dxgi':'n,b'} # Registry not flattened into environment


@pytest.mark.parametrize('api,expected',[('dx10','d3d10'),('dx11','d3d11'),('dx12','d3d12')])
def test_reshade_supported_alternative_preserves_dxgi(packages,api,expected):
    e,p,root,exe=packages;p['api']=api;p['reshade']['mode']='standalone'
    mod=exe.parent/'dxgi.dll';mod.write_bytes(pe_bytes()+b'existing mod')
    plan=e.plan(p,'WINEDLLOVERRIDES=dxgi=n,b %command%')
    assert not plan['blockers'],plan
    assert plan['profile']['reshade']['proxy']==expected
    assert mod.read_bytes().endswith(b'existing mod')


def test_occupied_reshade_names_route_through_opti(packages):
    e,p,root,exe=packages;p['api']='dx12';p['opti'].update(enabled=True,proxy='winmm');p['reshade']['mode']='standalone'
    plan=e.plan(p,'WINEDLLOVERRIDES="dxgi=n,b;d3d12=n,b" %command%')
    assert not plan['blockers'],plan
    assert plan['profile']['reshade']['mode']=='opti' and plan['profile']['opti']['proxy']=='winmm'


def test_all_occupied_and_wildcard_block_cleanly(packages):
    e,p,root,exe=packages;p['opti']['enabled']=True
    for launch in ['WINEDLLOVERRIDES="'+ ';'.join(name+'=n,b' for name in OPTI_PROXIES)+'" %command%',
                   'WINEDLLOVERRIDES="*=b" %command%']:
        plan=e.plan(p,launch);assert plan['blockers']
        assert not (e.store(p['appid'])/'pending.json').exists()


def test_managed_proxy_not_presented_as_mod(packages):
    e,p,root,exe=packages;p['opti']['enabled']=True
    plan,prepared=apply(e,p)
    context=e.wine_context(e.profile(p['appid']),prepared['launch_after'])
    dxgi=next(f for f in context['files'] if f['name']=='dxgi.dll')
    assert dxgi['managed'] and not dxgi['selectable']
    nextp=e.profile(p['appid']);nextp['wine']['custom_overrides']='dxgi=n,b'
    plan=e.plan(nextp,prepared['launch_after']);assert plan['blockers']


def test_old_backed_up_mod_restored_when_proxy_moves(packages):
    e,p,root,exe=packages;p['opti'].update(enabled=True,proxy='version')
    original=pe_bytes()+b'original mod';(exe.parent/'version.dll').write_bytes(original)
    # Simulate an older Deck Fusion installation, which used replacement consent.
    from fusion_transaction import Transaction
    p=e.validate(p);desired,extras,_=e.build(p)
    tx=Transaction(root,e.store(p['appid']))
    prepared=tx.prepare(desired,extras,'WINEDLLOVERRIDES=version=n,b %command%',
                       'WINEDLLOVERRIDES=version=n,b '+str(e.wrapper)+' 123 -- %command%',True)
    tx.finalize(prepared['token'],prepared['launch_after'])
    current=e.profile(p['appid']);plan,_=apply(e,current,prepared['launch_after'])
    assert plan['profile']['opti']['proxy']!='version'
    assert (exe.parent/'version.dll').read_bytes()==original


def test_rollback_restores_custom_runtime_and_files(packages):
    e,p,root,exe=packages;p['wine']['custom_overrides']='version=n,b';p['opti']['enabled']=True
    plan,prepared=apply(e,p)
    old=(e.store(p['appid'])/'runtime.json').read_bytes();current=e.profile(p['appid'])
    current['wine']['custom_overrides']='version=n,b;winmm=n'
    plan=e.plan(current,prepared['launch_after']);assert not plan['blockers'],plan
    stage=e.prepare_approved(current,prepared['launch_after'],plan['approval_token']);e.rollback(p['appid'],stage['token'])
    assert (e.store(p['appid'])/'runtime.json').read_bytes()==old


def test_removed_preset_does_not_change_manual_rates(packages):
    e,p,*_=packages;p['schema']=3;p['base_fps']=33;p['lsfg']['multiplier']=2
    updated=migrate_profile(p)
    assert updated['base_fps']==33 and updated['lsfg']['multiplier']==2 and updated['schema']==4
    source=(e.source/'src/index.js').read_text()
    assert '33 → 66' not in source and '33 × 2 preset' not in source


def test_active_opti_routes_reshade_through_companion_even_without_collision(packages):
    e,p,root,exe=packages;p['api']='dx12';p['opti'].update(enabled=True,proxy='dxgi')
    p['reshade'].update(mode='standalone',proxy='d3d12')
    plan=e.plan(p,'')
    assert not plan['blockers']
    assert plan['profile']['reshade']['mode']=='opti'
    assert plan['dll_summary']['reshade']=='ReShade64.dll via OptiScaler'
    assert any(x['id']=='proxy-collision' for x in plan['resolutions'])


def test_ambiguous_case_variant_dlls_not_offered(packages):
    e,p,root,exe=packages
    for name in ('Version.dll','version.dll'):(exe.parent/name).write_bytes(pe_bytes())
    context=e.wine_context(p,'')
    assert not any(f['selectable'] for f in context['files'])
    assert context['warnings']
    p['wine']['custom_overrides']='version=n,b'
    assert e.plan(p,'')['blockers']
