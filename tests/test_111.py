from pathlib import Path
"""Focused v1.1.1 regressions. No hardware/GPU performance assertions."""
import copy
import json
import pytest
from fusion_engine import migrate_profile
from fusion_launch import launch_environment
from fusion_util import atomic_json, ini_read
from test_110 import fsr_payload


def config():
    return {'api':'dx12','base_fps':33,'lsfg_config':'/saved/lsfg.toml',
            'lsfg':{'enabled':True,'respect_deck_limiter':True,'multiplier':2},
            'opti_enabled':True,'fsr4_watermark':False}


@pytest.mark.parametrize('display_key',['GAMESCOPE_WAYLAND_DISPLAY','GAMESCOPE_LIMITER_FILE'])
def test_fifo_compatibility_changes_only_game_environment(display_key):
    inherited={display_key:'/tmp/gamescope','ENABLE_GAMESCOPE_WSI':'1',
               'MESA_VK_WSI_PRESENT_MODE':'immediate','GAMESCOPE_WSI_FRAME_LIMITER_AWARE':'1',
               'OTHER':'kept','WINEDLLOVERRIDES':'other=n','LD_PRELOAD':'unrelated.so'}
    before=copy.deepcopy(inherited); c=config(); result=launch_environment(c,inherited)
    assert inherited==before
    assert result['ENABLE_GAMESCOPE_WSI']=='0' and result['DISABLE_GAMESCOPE_WSI']=='1'
    assert result['MESA_VK_WSI_PRESENT_MODE']=='fifo'
    assert 'GAMESCOPE_WSI_FRAME_LIMITER_AWARE' not in result
    assert result[display_key]==before[display_key]
    assert result['DXVK_FRAME_RATE']==result['VKD3D_FRAME_RATE']=='33'
    assert c['lsfg']['multiplier']==2 and c['base_fps']==33
    assert result['OTHER']=='kept' and result['LD_PRELOAD']=='unrelated.so'
    assert 'LSFG_OUTPUT_FPS' not in result


@pytest.mark.parametrize('disabled',['lsfg','option','desktop','bypass'])
def test_compatibility_does_not_leak_into_unselected_paths(disabled):
    c=config(); inherited={'ENABLE_GAMESCOPE_WSI':'1','MESA_VK_WSI_PRESENT_MODE':'mailbox',
                           'GAMESCOPE_WAYLAND_DISPLAY':'gamescope-0'}
    if disabled=='lsfg':c['lsfg']['enabled']=False
    elif disabled=='option':c['lsfg']['respect_deck_limiter']=False
    elif disabled=='desktop':del inherited['GAMESCOPE_WAYLAND_DISPLAY']
    else:c['bypass']=True
    result=launch_environment(c,inherited)
    assert result['ENABLE_GAMESCOPE_WSI']=='1'
    assert result['MESA_VK_WSI_PRESENT_MODE']=='mailbox'
    assert 'DISABLE_GAMESCOPE_WSI' not in result


@pytest.mark.parametrize('visible',[False,True])
def test_watermark_env_only_cleared_when_disabled(visible):
    c=config();c['fsr4_watermark']=visible
    inherited={'PROTON_FSR4_INDICATOR':'1','FSR4_WATERMARK':'1','PROTON_ENABLE_FSR4':'1'}
    result=launch_environment(c,inherited)
    # Explicit zero also prevents Proton user_settings/compat flags re-enabling it.
    assert result['PROTON_FSR4_INDICATOR']==('1' if visible else '0')
    assert ('FSR4_WATERMARK' in result)==visible
    assert result['PROTON_ENABLE_FSR4']=='1'
    c['opti_enabled']=False
    assert launch_environment(c,inherited)['FSR4_WATERMARK']=='1'


def test_legacy_profile_migration_is_once_and_read_only(packages):
    e,p,root,exe=packages;fsr_payload(e)
    p['schema']=2;p['api']='dx12';p['opti'].update(enabled=True,fsr_mode='fsr4_int8',fsr4_watermark=True)
    p['opti']['overrides']={'FSR':{'Fsr4EnableWatermark':'true'}}
    profile=e.store(p['appid'])/'profile.json';atomic_json(profile,p);before=profile.read_bytes()
    loaded=e.profile(p['appid'])
    assert loaded['schema']==4 and loaded['opti']['fsr4_watermark'] is False
    assert loaded['opti']['fsr_mode']=='fsr4_int8' and profile.read_bytes()==before
    plan=e.plan(loaded,'--skip-launcher');assert not plan['blockers'],plan
    assert any(f['id']=='ini-FSR-Fsr4EnableWatermark' for f in plan['resolutions'])
    assert profile.read_bytes()==before
    prepared=e.prepare_approved(loaded,'--skip-launcher',plan['approval_token'])
    e.finish(p['appid'],prepared['token'],prepared['launch_after'])
    ini=ini_read((exe.parent/'OptiScaler.ini').read_text())
    assert ini['FSR']['Fsr4EnableWatermark']=='auto'
    assert ini['FSR']['Fsr4ForceEnableInt8']=='true'
    saved=e.profile(p['appid']);assert saved['schema']==4
    saved['opti']['fsr4_watermark']=True
    assert migrate_profile(saved)['opti']['fsr4_watermark'] is True
    assert p['opti']['fsr4_watermark'] is True # input not mutated


@pytest.mark.parametrize('mode',['fsr4_int8','auto'])
@pytest.mark.parametrize('visible',[False,True])
def test_advanced_ini_cannot_override_watermark_control(packages,mode,visible):
    e,p,root,exe=packages;fsr_payload(e)
    p['api']='dx12';p['opti'].update(enabled=True,fsr_mode=mode,fsr4_watermark=visible)
    p['opti']['overrides']={'FSR':{'Fsr4EnableWatermark':str(not visible).lower()}}
    plan=e.plan(p,'');assert not plan['blockers'],plan
    desired,extras,runtime=e.build(plan['profile'])
    ini=ini_read(next(v.decode() for k,v in desired.items() if k.endswith('OptiScaler.ini')))
    assert ini['FSR']['Fsr4EnableWatermark']==('true' if visible else 'auto')
    assert runtime['fsr4_watermark']==visible
    assert runtime['opti_enabled'] is True
    assert any(x['id']=='ini-FSR-Fsr4EnableWatermark' for x in plan['resolutions'])


def test_dialog_discloses_removed_environment_and_preserves_launch_text(packages):
    e,p,root,exe=packages;fsr_payload(e)
    p['api']='dx12';p['opti'].update(enabled=True,fsr_mode='fsr4_int8')
    p['lsfg'].update(enabled=True,respect_deck_limiter=True);p['base_fps']=33
    text='PROTON_FSR4_INDICATOR=1 FSR4_WATERMARK=1 ENABLE_GAMESCOPE_WSI=1 MESA_VK_WSI_PRESENT_MODE=immediate %command% --skip-launcher'
    plan=e.plan(p,text);assert not plan['blockers'],plan
    fixes={x['id']:x for x in plan['resolutions']}
    assert fixes['env-PROTON_FSR4_INDICATOR']['after']=='0'
    assert fixes['env-FSR4_WATERMARK']['after']=='(unset)'
    assert fixes['env-ENABLE_GAMESCOPE_WSI']['after']=='0'
    assert fixes['env-MESA_VK_WSI_PRESENT_MODE']['after']=='fifo'
    assert plan['launch_after'].startswith('PROTON_FSR4_INDICATOR=1 FSR4_WATERMARK=1 ')
    assert '--skip-launcher' in plan['launch_after']


@pytest.mark.parametrize('visible',[False,True])
def test_import_reads_explicit_watermark_choice(packages,visible):
    e,p,root,exe=packages;atomic_json(e.store(p['appid'])/'profile.json',p)
    (exe.parent/'OptiScaler.ini').write_text('[FSR]\nFsr4EnableWatermark='+str(visible).lower()+'\n')
    imported=e.sync_from_disk(p['appid'])
    assert imported['opti']['fsr4_watermark']==visible


def test_bypass_diagnostics_do_not_claim_limiter_route(packages):
    import os, subprocess, sys
    e,p,root,exe=packages
    cfg=config();cfg['bypass']=True
    atomic_json(e.store(p['appid'])/'runtime.json',cfg)
    env={**os.environ,'GAMESCOPE_WAYLAND_DISPLAY':'gamescope-0','ENABLE_GAMESCOPE_WSI':'1'}
    result=subprocess.run([str(e.wrapper),p['appid'],'--',sys.executable,'-c',
                           'import os;print(os.environ["ENABLE_GAMESCOPE_WSI"])'],
                          capture_output=True,text=True,env=env,timeout=5)
    assert result.returncode==0 and result.stdout.strip()=='1'
    log=json.loads((e.store(p['appid'])/'last-launch.json').read_text())
    assert log['limiter_route_requested']=='unchanged'
    assert log['wrapper_version']==json.loads((Path(__file__).resolve().parents[1]/'package.json').read_text())['displayVersion']
