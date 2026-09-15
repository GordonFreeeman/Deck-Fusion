"""Focused 1.1 configuration/consent checks. Synthetic payloads, no GPU claims."""
import copy
from pathlib import Path
import pytest
from conftest import pe_bytes
from fusion_launch import launch_environment
from fusion_transaction import Transaction
from fusion_util import FusionError, atomic_json, ini_read


def fsr_payload(e, modern=False):
    base=Path(e.package('opti')['path'])
    key='Fsr4ForceModel' if modern else 'Fsr4ForceEnableInt8'
    with (base/'OptiScaler.ini').open('a') as f:
        f.write(f'\n[FSR]\nFsr4Update=auto\n{key}=auto\nUpscalerIndex=auto\nFsr4EnableWatermark=auto\nFGIndex=auto\n')
    (base/'amd_fidelityfx_upscaler_dx12.dll').write_bytes(pe_bytes()+b'synthetic FFX')
    return base


def test_limiter_is_opt_in_and_keeps_base_separate():
    config={'api':'dx12','base_fps':33,'lsfg':{'enabled':True},'lsfg_config':'/profile.toml'}
    current={'GAMESCOPE_WAYLAND_DISPLAY':'gamescope-0','GAMESCOPE_WSI_FRAME_LIMITER_AWARE':'1','DISABLE_GAMESCOPE_WSI':'1'}
    off=launch_environment(config,current)
    assert off['GAMESCOPE_WSI_FRAME_LIMITER_AWARE']=='1'
    config['lsfg']['respect_deck_limiter']=True
    on=launch_environment(config,current)
    assert 'GAMESCOPE_WSI_FRAME_LIMITER_AWARE' not in on
    assert on['ENABLE_GAMESCOPE_WSI']=='0' and on['DISABLE_GAMESCOPE_WSI']=='1'
    assert on['MESA_VK_WSI_PRESENT_MODE']=='fifo'
    assert on['DXVK_FRAME_RATE']==on['VKD3D_FRAME_RATE']=='33'
    assert 'ENABLE_GAMESCOPE_WSI' not in launch_environment(config,{})
    assert current['DISABLE_GAMESCOPE_WSI']=='1'


def test_old_profile_defaults_preserved(installation):
    e,p,*_=installation;p.pop('schema');p['lsfg'].pop('respect_deck_limiter');p['opti'].pop('fsr_mode');p['opti'].pop('fsr4_watermark')
    atomic_json(e.store(p['appid'])/'profile.json',p)
    loaded=e.profile(p['appid'])
    assert loaded['schema']==4 and loaded['lsfg']['respect_deck_limiter'] is True
    assert loaded['opti']['fsr_mode']=='auto'


def test_plan_cancel_is_read_only_and_resolves_conflicts(packages):
    e,p,root,exe=packages;p['api']='dx12';p['lsfg']['enabled']=True;p['lsfg']['respect_deck_limiter']=True;p['lsfg']['override_present_mode']=False
    p['opti'].update(enabled=True,fg=True);p['reshade']['mode']='standalone'
    old=exe.parent/'dxgi.dll';old.write_bytes(b'existing third party mod')
    before={str(x):x.read_bytes() for x in root.rglob('*') if x.is_file()}
    plan=e.plan(p,'--skip-launcher')
    assert not plan['blockers'],plan
    assert {'double-fg','proxy-collision','fifo-pacing'}<=set(x['id'] for x in plan['resolutions'])
    # 1.2 protects occupied mod names instead of requesting replacement.
    assert not plan['conflicts'] and not plan['profile']['opti']['fg']
    assert plan['profile']['opti']['proxy'] != 'dxgi'
    assert before=={str(x):x.read_bytes() for x in root.rglob('*') if x.is_file()}
    assert not (e.store(p['appid'])/'profile.json').exists()
    assert not (e.store(p['appid'])/'pending.json').exists()


def test_approved_apply_and_restore(packages):
    e,p,root,exe=packages;p['opti']['enabled']=True;p['reshade']['mode']='standalone'
    conflict=exe.parent/'dxgi.dll';conflict.write_bytes(b'original graphics mod')
    plan=e.plan(p,'--skip-launcher');assert not plan['blockers'],plan
    prepared=e.prepare_approved(p,'--skip-launcher',plan['approval_token'])
    e.finish(p['appid'],prepared['token'],prepared['launch_after'])
    assert not e.profile(p['appid'])['backup_conflicts']
    restore=e.plan(e.profile(p['appid']),prepared['launch_after'],True)
    assert not restore['blockers'],restore
    restored=e.prepare_approved(e.profile(p['appid']),prepared['launch_after'],restore['approval_token'],True)
    e.finish(p['appid'],restored['token'],restored['launch_after'])
    assert restored['launch_after']=='--skip-launcher' and conflict.read_bytes()==b'original graphics mod'


@pytest.mark.parametrize('what',['game','package','profile'])
def test_changed_confirmation_rejected(packages,what):
    e,p,root,exe=packages;p['opti']['enabled']=True
    conflict=exe.parent/'dxgi.dll';conflict.write_bytes(b'original mod')
    plan=e.plan(p,'')
    if what=='game':conflict.write_bytes(b'changed independently')
    elif what=='package':(Path(e.package('opti')['path'])/'OptiScaler.dll').write_bytes(b'updated component')
    else:p['base_fps']=42
    with pytest.raises(FusionError,match='changed after confirmation'):
        e.prepare_approved(p,'',plan['approval_token'])
    assert not (e.store(p['appid'])/'pending.json').exists()
    assert not (exe.parent/'OptiScaler.ini').exists()


def test_final_transaction_checks_approved_state(tmp_path):
    root=tmp_path/'game';root.mkdir();(root/'mod.dll').write_bytes(b'old')
    tx=Transaction(root,tmp_path/'store');desired={'mod.dll':b'new'}
    reviewed=tx.inspect(desired)['file_state'];(root/'mod.dll').write_bytes(b'changed')
    with pytest.raises(FusionError,match='changed after confirmation'):
        tx.prepare(desired,{},'', '',True,expected_state=reviewed)
    assert (root/'mod.dll').read_bytes()==b'changed' and not tx.pending()


@pytest.mark.parametrize('modern',[False,True])
def test_fsr4_real_route_and_schema_keys(packages,modern):
    e,p,root,exe=packages;fsr_payload(e,modern)
    p['api']='dx12';p['opti'].update(enabled=True,fsr_mode='fsr4_int8',dx12='xess')
    plan=e.plan(p,'');assert not plan['blockers'],plan
    assert plan['profile']['opti']['dx12']=='fsr31'
    desired,extra,runtime=e.build(plan['profile'])
    raw=next(v for k,v in desired.items() if k.endswith('OptiScaler.ini')).decode()
    ini=ini_read(raw)
    assert ini['FSR']['Fsr4Update']=='auto'
    assert ini['FSR']['Fsr4EnableWatermark']=='auto'
    assert ini['FSR']['UpscalerIndex']=='0'
    assert ini['FSR']['Fsr4ForceModel' if modern else 'Fsr4ForceEnableInt8']==('2' if modern else 'true')
    assert ini['Upscalers']['Dx12Upscaler']=='fsr31'
    assert runtime['requested_fsr_mode']=='fsr4_int8'


def test_missing_int8_schema_is_blocker(packages):
    e,p,*_=packages;p['api']='dx12';p['opti'].update(enabled=True,fsr_mode='fsr4_int8')
    plan=e.plan(p,'');assert 'Update stable OptiScaler' in plan['blockers'][0]['detail']
    assert 'approval_token' not in plan


def test_no_native_dlss_on_amd(packages):
    e,p,*_=packages;e.hardware=lambda:{'known_non_nvidia':True}
    p['api']='dx12';p['opti'].update(enabled=True,dx12='dlss')
    plan=e.plan(p,'');assert not plan['blockers'],plan
    assert plan['profile']['opti']['dx12']=='fsr31'
    assert 'native-dlss' in [x['id'] for x in plan['resolutions']]


def test_imported_ini_has_precedence_over_old_preset(packages):
    e,p,root,exe=packages;p['opti'].update(enabled=True,fsr_mode='fsr4_int8')
    atomic_json(e.store(p['appid'])/'profile.json',p)
    (exe.parent/'OptiScaler.ini').write_text('[FSR]\nFsr4Update=false\nFsr4ForceEnableInt8=false\n[Upscalers]\nDx12Upscaler=xess\n')
    imported=e.sync_from_disk(p['appid'])
    assert imported['opti']['fsr_mode']=='auto'
    assert imported['opti']['dx12']=='xess'
    assert imported['opti']['overrides']['FSR']['Fsr4Update']=='false'


def test_fsr3_and_wine_override_resolutions(packages):
    e,p,*_=packages;p['api']='dx12';p['opti'].update(enabled=True,fsr_mode='fsr3',dx12='xess')
    plan=e.plan(p,"WINEDLLOVERRIDES='dxgi=b;other=n' %command% --skip-launcher")
    assert not plan['blockers'],plan
    assert plan['profile']['opti']['dx12']=='fsr31'
    fixes={f['id']:f for f in plan['resolutions']}
    assert fixes['env-dll-overrides']['after']=='dxgi=b;other=n;winmm=n,b'
    assert 'fsr3-route' in fixes
