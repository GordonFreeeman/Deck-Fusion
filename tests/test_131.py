"""Game-independent scope checks; all executables/installers are synthetic."""
import copy
import json
from pathlib import Path
import shlex
import struct
import pytest
from conftest import pe_bytes
from fusion_util import FusionError, atomic_json
from fusion_prereqs import prefix_inventory
from test_130 import setup_prefix


def configure(e, monkeypatch):
    m = e.prereqs
    monkeypatch.setattr(m, 'user_check', lambda: None)
    monkeypatch.setattr(m, 'helper', lambda: {'kind':'native','executable':'/fixture/protontricks','winetricks':'/fixture/winetricks','available':True})
    return m


def request(p, exe):
    return {'appid':p['appid'], 'exe':str(exe), 'launch':'WINEDLLOVERRIDES="version,winmm=n,b" %command% --skip-launcher',
            'runtimes':['d3dcompiler_47','vcrun2022']}


def add_game(e, appid, name):
    lib=e.home/'.local/share/Steam';root=lib/'steamapps/common'/name
    exe=root/'Game.exe';root.mkdir(parents=True);exe.write_bytes(pe_bytes())
    (lib/f'steamapps/appmanifest_{appid}.acf').write_text(f'"AppState" {{"appid" "{appid}" "name" "{name}" "installdir" "{name}"}}')
    p=e.profile(appid);p['exe']=str(exe)
    return p, root, exe


def fake_execute(target, calls):
    def execute(command, env, log, progress, event=None, **kwargs):
        assert command[-1] == target['appid']
        assert env['STEAM_COMPAT_DATA_PATH'] == str(Path(target['prefix']).parent)
        assert (Path(target['prefix']).parent/'.deck-fusion-runtime-backups').is_dir()
        assert '--force' not in shlex.join(command)
        verb = 'vcrun2022' if command[-2].endswith('vcrun2022') else 'd3dcompiler_47'
        from conftest import vc_fixture
        from fusion_steam import pe_info
        prefix = Path(target['prefix'])
        if verb == 'vcrun2022': vc_fixture(prefix, pe_info(Path(target['exe']))['bits'])
        else: (prefix/'drive_c/windows/system32/d3dcompiler_47.dll').write_bytes(pe_bytes())
        with (Path(target['prefix'])/'winetricks.log').open('a') as handle: handle.write(verb+'\n')
        log.parent.mkdir(parents=True,exist_ok=True);log.write_text('SIMULATED installer; no Microsoft binary executed\n')
        calls.append(verb)
    return execute


@pytest.mark.parametrize('name,bits,api', [('Unrelated-Win64-Shipping.exe',64,'dx12'),('LegacyGame.EXE',32,'dx9'),('unusual-name',64,'vulkan')])
def test_any_windows_game_uses_own_prefix_and_keeps_install_optional(installation,monkeypatch,name,bits,api):
    e,p,root,old=installation;exe=old.with_name(name);old.unlink();exe.write_bytes(pe_bytes(bits,api));p['exe']=str(exe)
    prefix=setup_prefix(e,p);m=configure(e,monkeypatch);payload=request(p,exe)
    original=prefix_inventory(prefix,hashes=True);status=m.status(payload)
    assert status['game']=='Test Game' and status['prefix']==str(prefix) and not status['blockers']
    assert prefix_inventory(prefix,hashes=True)==original
    assert not (e.store(p['appid'])/'runtime-last.json').exists()
    calls=[];monkeypatch.setattr(m,'execute',fake_execute(m.target(payload),calls))
    before={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    plan=m.plan(payload)
    record=m.install({**payload,'approval':plan['approval']},lambda *_:None)
    assert calls==['d3dcompiler_47','vcrun2022'] and record['state']=='completed'
    assert before=={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    assert not (e.store(p['appid'])/'profile.json').exists()
    restore=m.plan({**payload,'restore':True})
    result=m.restore({**payload,'approval':restore['approval']},lambda *_:None)
    assert result['state']=='restored'
    assert prefix_inventory(prefix,hashes=True)==original


def test_two_games_cannot_reuse_target_prefix_or_approval(installation,monkeypatch):
    e,p,root,exe=installation;m=configure(e,monkeypatch);prefix=setup_prefix(e,p)
    other,_,other_exe=add_game(e,'456','Second Game');other_prefix=setup_prefix(e,other)
    first=request(p,exe);second=request(other,other_exe)
    assert m.status(first)['prefix']==str(prefix)
    assert m.status(second)['prefix']==str(other_prefix)
    with pytest.raises(FusionError,match='not among'):m.status({**second,'prefix':str(prefix)})
    plan=m.plan(first)
    with pytest.raises(FusionError,match='changed since'):m.install({**second,'approval':plan['approval']},lambda *_:None)
    with pytest.raises(FusionError,match='outside'):m.status({**first,'exe':str(other_exe)})
    assert not (prefix.parent/'.deck-fusion-runtime-backups').exists()
    assert not (other_prefix.parent/'.deck-fusion-runtime-backups').exists()


def test_non_steam_windows_shortcut_uses_its_own_prefix(installation,monkeypatch):
    e,*_=installation;m=configure(e,monkeypatch)
    exe=e.home/'Games/External game/Game.exe';exe.parent.mkdir(parents=True);exe.write_bytes(pe_bytes(32,'dx9'))
    appid=0xf1234567
    def text(key,value):return b'\1'+key.encode()+b'\0'+value.encode()+b'\0'
    data=b'\0shortcuts\0\x000\0\2appid\0'+struct.pack('<I',appid)+text('AppName','External Windows Game')+text('Exe',f'"{exe}"')+b'\x08\x08\x08'
    shortcuts=e.home/'.local/share/Steam/userdata/123/config/shortcuts.vdf';shortcuts.parent.mkdir(parents=True);shortcuts.write_bytes(data)
    assert str(appid) not in [game['appid'] for game in e.games()]
    e.set_settings({'include_shortcuts':True})
    p=e.profile(str(appid));assert p['exe']==str(exe)
    prefix=e.home/'.local/share/Steam/steamapps/compatdata'/str(appid)/'pfx'
    (prefix/'drive_c/windows/system32').mkdir(parents=True)
    (prefix/'system.reg').write_text('WINE REGISTRY Version 2\n#arch=win64\n');(prefix/'user.reg').write_text('WINE REGISTRY Version 2\n');(prefix.parent/'pfx.lock').touch()
    payload=request(p,exe);status=m.status(payload)
    assert status['prefix']==str(prefix) and not status['blockers']
    plan=m.plan(payload);calls=[];monkeypatch.setattr(m,'execute',fake_execute(plan['target'],calls))
    assert m.install({**payload,'approval':plan['approval']},lambda *_:None)['state']=='completed'
    e.set_settings({'include_shortcuts':False})
    assert m.status(payload)['restore_snapshot']['snapshot_ready']


@pytest.mark.parametrize('data',[b'\x7fELF\x02'+b'\0'*100,b'#!/bin/sh\n',b'not an executable'])
def test_native_linux_emulator_and_invalid_files_are_rejected_without_mutation(installation,monkeypatch,data):
    e,p,root,exe=installation;exe.write_bytes(data);m=configure(e,monkeypatch)
    with pytest.raises(FusionError,match='Windows runtime setup needs'):m.status(request(p,exe))
    assert not (e.home/'.local/share/Steam/steamapps/compatdata').exists()


def test_no_prefix_never_falls_back_to_another_games_prefix(installation,monkeypatch):
    e,p,root,exe=installation;m=configure(e,monkeypatch)
    other,_,_=add_game(e,'456','Other Game');setup_prefix(e,other)
    status=m.status(request(p,exe));assert status['prefix'] is None and status['blockers']
    with pytest.raises(FusionError,match='Select one'):m.plan(request(p,exe))


def test_general_diagnostics_are_available_readonly_and_bounded(installation):
    e,p,root,exe=installation
    log=exe.parent/'OptiScaler.log';log.write_text('info\n'*20000+'ERROR synthetic old message\n')
    (exe.parent/'ReShade.ini').write_text('[GENERAL]\n')
    (exe.parent/'winmm.dll').write_bytes(pe_bytes());(exe.parent/'plugins').mkdir()
    (exe.parent/'plugins/example.asi').write_text('fixture')
    before={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    result=e.game_diagnostics(p['appid'],str(exe))
    assert result['game']=='Test Game' and result['selected_exe']==str(exe)
    assert 'Cyberpunk' not in json.dumps(result)
    log=next(log for log in result['logs'] if log['name']=='OptiScaler')
    assert log['present'] and len(log['tail'].splitlines())<=60 and len(log['tail'])<=12288
    assert log['error_lines']==['ERROR synthetic old message']
    assert before=={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    assert not (e.store(p['appid'])/'profile.json').exists()


def test_general_diagnostics_do_not_follow_external_links(installation,tmp_path):
    e,p,root,exe=installation
    secret=tmp_path/'secret';secret.write_text('PRIVATE CONTENT')
    (exe.parent/'OptiScaler.log').symlink_to(secret)
    result=e.game_diagnostics(p['appid'],str(exe))
    assert 'PRIVATE CONTENT' not in json.dumps(result)
    assert not result['logs'][0]['present']
    with pytest.raises(FusionError):e.game_diagnostics(p['appid'],str(secret))


def test_root_folder_game_diagnostics_do_not_omit_dlls(installation):
    e,p,root,old=installation;exe=root/'Game.exe';exe.write_bytes(pe_bytes());old.unlink()
    (root/'winmm.dll').write_bytes(pe_bytes())
    report=e.game_diagnostics(p['appid'],str(exe))
    assert not report['notes']
    assert report['frameworks'][2]['files'][0]['path']=='winmm.dll'
    assert report['frameworks'][2]['files'][0]['present']
