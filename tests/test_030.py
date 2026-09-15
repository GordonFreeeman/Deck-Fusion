"""Guided setup persistence and startup hints. Synthetic processes and packages."""
import copy
import pytest
from fusion_engine import migrate_profile
from fusion_steam import running_appids
from fusion_util import FusionError, atomic_json
from test_110 import fsr_payload
from test_steam import makeproc
from test_120 import apply


def test_setup_defaults_and_explicit_limiter_optout_survive_migration(installation):
    e,p,*_=installation
    assert p['lsfg']['respect_deck_limiter'] is True
    assert p['setup']=={'version':0,'runtimes':[],'runtime_prefix':''}
    p['lsfg']['respect_deck_limiter']=False
    p['setup']={'version':1,'runtimes':['vcrun2022'],'runtime_prefix':'/example/pfx'}
    atomic_json(e.store('123')/'profile.json',p)
    saved=e.profile('123')
    assert saved['lsfg']['respect_deck_limiter'] is False
    assert saved['setup']==p['setup']


@pytest.mark.parametrize('bad',[
    {'version':4,'runtimes':[],'runtime_prefix':''},
    {'version':1,'runtimes':['arbitrary-command'],'runtime_prefix':''},
    {'version':1,'runtimes':'vcrun2022','runtime_prefix':''},
    {'version':1,'runtimes':[],'runtime_prefix':[]},
])
def test_setup_metadata_rejects_invalid_preferences(installation,bad):
    e,p,*_=installation;p['setup']=bad
    with pytest.raises(FusionError,match='setup preferences'):e.validate(p)


def test_running_selection_needs_exact_steam_id_and_game_path(tmp_path):
    proc=tmp_path/'proc';proc.mkdir();game=tmp_path/'Cyberpunk';game.mkdir()
    games=[{'appid':'123','root':str(game)},{'appid':'999','root':str(tmp_path/'Other')}]
    makeproc(proc,1,['steam',str(game/'game.exe')],['SteamAppId=123'])
    makeproc(proc,2,['wineserver'],['SteamAppId=123'])
    makeproc(proc,3,['game.exe'],['SteamAppId=123'])
    makeproc(proc,4,['wine64',str(game/'game.exe')],['SteamAppId=1234'])
    makeproc(proc,5,['wine64',str(tmp_path/'Cyberpunk-copy/game.exe')],['SteamAppId=123'])
    assert running_appids(games,proc)==[]
    makeproc(proc,6,['wine64','Z:'+str(game/'bin/game.exe')],['SteamAppId=123'])
    assert running_appids(games,proc)==['123']
    assert running_appids(games,tmp_path/'no-proc')==[]


def test_running_selection_can_use_direct_executable_link(tmp_path):
    proc=tmp_path/'proc';proc.mkdir();game=tmp_path/'Game';game.mkdir();exe=game/'play';exe.touch()
    entry=makeproc(proc,11,['./play'],['STEAM_APPID=456']);(entry/'exe').symlink_to(exe)
    assert running_appids([{'appid':'456','root':str(game)}],proc)==['456']


def test_cached_opti_must_support_selected_fsr4_output(packages):
    e,p,*_=packages;p['opti'].update(enabled=True,fsr_mode='fsr4_int8')
    assert not next(x for x in e.requirements(p)['items'] if x['id']=='opti')['ready']
    fsr_payload(e)
    assert next(x for x in e.requirements(p)['items'] if x['id']=='opti')['ready']


def test_reshade_always_uses_opti_loader_then_returns_to_standalone(packages):
    e,p,_,exe=packages;p['opti']['enabled']=True;p['reshade'].update(mode='standalone',proxy='d3d11')
    plan,prepared=apply(e,p)
    assert plan['profile']['reshade']['mode']=='opti'
    assert (exe.parent/'ReShade64.dll').exists()
    assert not (exe.parent/'d3d11.dll').exists()
    p=e.profile('123');p['opti']['enabled']=False
    plan,prepared=apply(e,p,prepared['launch_after'])
    assert plan['profile']['reshade']['mode']=='standalone'
    assert (exe.parent/'d3d11.dll').exists()
    assert not (exe.parent/'ReShade64.dll').exists()
