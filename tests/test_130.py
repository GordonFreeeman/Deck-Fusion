"""Focused runtime boundary checks. No Microsoft payload, Proton, or Deck emulated.

All installer fixtures say SIMULATED; real subprocess checks use /bin/sh to
exercise allowlisting, quoting, logging, cancellation and prefix guarding only.
"""
import copy
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import threading
import time

import pytest
from fusion_prereqs import PrefixRuntimes, prefix_inventory, content_index, prefix_processes
from fusion_util import FusionError, atomic_json, read_json
from test_122 import cyberpunk
from conftest import pe_bytes, vc_fixture


def setup_prefix(e, p):
    lib=Path(e.game(p['appid'])['library'])
    prefix=lib/'steamapps/compatdata'/p['appid']/'pfx'
    (prefix/'drive_c/windows/system32').mkdir(parents=True)
    (prefix/'drive_c/windows/syswow64').mkdir()
    (prefix/'system.reg').write_text('WINE REGISTRY Version 2\n#arch=win64\n')
    (prefix/'user.reg').write_text('WINE REGISTRY Version 2\n[Software\\\\Wine\\\\DllOverrides]\n"version"="native,builtin"\n')
    (prefix.parent/'pfx.lock').touch()
    (prefix/'dosdevices').mkdir(); (prefix/'dosdevices/z:').symlink_to('/')
    (prefix/'drive_c/users/steamuser').mkdir(parents=True)
    (prefix/'drive_c/users/steamuser/save.dat').write_text('SAVE BEFORE RUNTIME')
    return prefix


@pytest.fixture
def runtime_env(packages, monkeypatch):
    e,p,root,exe=cyberpunk(packages); prefix=setup_prefix(e,p)
    manager=e.prereqs
    # The production user guard is separately tested. Fixtures run in a root-owned container.
    monkeypatch.setattr(manager,'user_check',lambda:None)
    monkeypatch.setattr(manager,'helper',lambda:{'kind':'native','executable':'/fixture/protontricks','winetricks':'/fixture/winetricks','available':True})
    payload={'appid':p['appid'],'exe':str(exe),'launch':'WINEDLLOVERRIDES="version,winmm=n,b" %command% --skip-launcher','runtimes':['d3dcompiler_47','vcrun2022']}
    return e,p,root,exe,prefix,manager,payload


def simulate_installer(prefix, fail=False):
    def execute(command, env, log, progress, event=None, **kwargs):
        assert command[-1]=='123' and 'STEAM_COMPAT_DATA_PATH' in env
        assert ' --force' not in shlex.join(command)
        verb='vcrun2022' if command[-2].endswith('vcrun2022') else 'd3dcompiler_47'
        assert env['STEAM_COMPAT_DATA_PATH']==str(prefix.parent)
        assert (prefix.parent/'.deck-fusion-runtime-backups').is_dir()
        log.parent.mkdir(parents=True,exist_ok=True);log.write_text('SIMULATED installer '+verb+'\n')
        (prefix/'drive_c/windows/system32'/f'{verb}.test-marker').write_text('SIMULATED, NOT A DLL')
        if fail:raise FusionError('SIMULATED installer failed')
        if verb == 'vcrun2022': vc_fixture(prefix)
        else: (prefix/'drive_c/windows/system32/d3dcompiler_47.dll').write_bytes(pe_bytes())
        with (prefix/'winetricks.log').open('a') as f:f.write(verb+'\n')
    return execute


def install(env, monkeypatch):
    e,p,root,exe,prefix,m,payload=env
    monkeypatch.setattr(m,'execute',simulate_installer(prefix))
    plan=m.plan(payload)
    return m.install({**payload,'approval':plan['approval']},lambda *_:None)


def test_status_reads_prefix_not_bin_without_mutations(runtime_env):
    e,p,root,exe,prefix,m,payload=runtime_env
    original=prefix_inventory(prefix,hashes=True)
    result=m.status(payload)
    assert result['prefix']==str(prefix) and result['prefixes']==[str(prefix)]
    assert all(not x['recorded'] for x in result['runtimes'])
    assert prefix_inventory(prefix,hashes=True)==original
    assert not (e.store('123')/'runtime-last.json').exists()
    (prefix/'drive_c/windows/system32/d3dcompiler_47.dll').write_text('placeholder file evidence')
    result=m.status(payload)
    assert result['runtimes'][0]['files'][0]['present'] and not result['runtimes'][0]['recorded']


def test_install_snapshots_preserves_mods_saves_and_no_force(runtime_env,monkeypatch):
    e,p,root,exe,prefix,m,payload=runtime_env
    before={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    record=install(runtime_env,monkeypatch)
    assert record['state']=='completed' and record['snapshot_ready']
    snapshot=Path(record['snapshot'])
    assert not (snapshot/'winetricks.log').exists()
    assert (snapshot/'dosdevices/z:').is_symlink()
    assert (prefix/'drive_c/users/steamuser/save.dat').read_text()=='SAVE BEFORE RUNTIME'
    assert before=={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    assert not (e.store('123')/'profile.json').exists()
    assert read_json(e.store('123')/'runtime-snapshots.json')[str(prefix)]['id']==record['id']
    assert '--skip-launcher' in payload['launch']


def test_failure_retains_partial_prefix_and_snapshot_then_atomic_restore(runtime_env,monkeypatch):
    e,p,root,exe,prefix,m,payload=runtime_env
    monkeypatch.setattr(m,'execute',simulate_installer(prefix,fail=True))
    plan=m.plan(payload)
    with pytest.raises(FusionError,match='SIMULATED'):m.install({**payload,'approval':plan['approval']},lambda *_:None)
    record=m.status(payload)['last']; assert record['snapshot_ready'] and record['state']=='failed'
    marker=prefix/'drive_c/windows/system32/d3dcompiler_47.test-marker';assert marker.exists()
    (prefix/'drive_c/users/steamuser/save.dat').write_text('NEWER SAVE, RETAIN ME')
    restore=m.plan({**payload,'restore':True})
    result=m.restore({**payload,'approval':restore['approval']},lambda *_:None)
    assert result['state']=='restored' and not marker.exists()
    old=Path(result['displaced_prefix'])
    assert (old/'drive_c/users/steamuser/save.dat').read_text()=='NEWER SAVE, RETAIN ME'
    assert (prefix/'drive_c/users/steamuser/save.dat').read_text()=='SAVE BEFORE RUNTIME'
    assert (old/'drive_c/windows/system32/d3dcompiler_47.test-marker').exists()


def test_stale_approval_components_prefix_changes_and_cancel_are_safe(runtime_env,monkeypatch):
    *_,prefix,m,payload=runtime_env
    plan=m.plan(payload)
    with pytest.raises(FusionError,match='changed since'):m.install({**payload,'runtimes':['d3dcompiler_47'],'approval':plan['approval']},lambda *_:None)
    (prefix/'user.reg').write_text('changed independently')
    with pytest.raises(FusionError,match='changed since'):m.install({**payload,'approval':plan['approval']},lambda *_:None)
    plan=m.plan(payload);event=threading.Event();event.set()
    with pytest.raises(FusionError,match='cancelled'):m.install({**payload,'approval':plan['approval']},lambda *_:None,event)
    assert not (prefix.parent/'.deck-fusion-runtime-backups').exists()


def test_allowlist_rejects_arbitrary_verbs_and_force(runtime_env):
    *_,m,payload=runtime_env
    for verbs in ([],['dotnet48'],['vcrun2022;touch /tmp/oops'],'vcrun2022'):
        with pytest.raises(FusionError):m.plan({**payload,'runtimes':verbs})
    with pytest.raises(FusionError,match='checksum'):m.plan({**payload,'force_vc':True})
    with pytest.raises(FusionError):m.target({**payload,'launch':'PROTON_VERSION="Some other Proton" %command%'})


def test_unknown_ambiguous_and_explicit_prefixes(runtime_env):
    e,p,root,exe,prefix,m,payload=runtime_env
    with pytest.raises(FusionError,match='not among'):m.target({**payload,'prefix':'/tmp/unrelated/pfx'})
    with pytest.raises(FusionError):m.target({**payload,'exe':'../../Cyberpunk2077.exe'})
    extra=e.home/'SD Library';extra.mkdir()
    lib=Path(e.game('123')['library'])
    (lib/'steamapps/libraryfolders.vdf').write_text('"libraryfolders" { "0" { "path" "'+str(lib)+'" } "1" { "path" "'+str(extra)+'" } }')
    other=extra/'steamapps/compatdata/123/pfx';other.mkdir(parents=True)
    result=m.target(payload);assert result['prefix'] is None and len(result['prefixes'])==2
    with pytest.raises(FusionError,match='Select one'):m.plan(payload)
    assert m.plan({**payload,'prefix':str(prefix)})['target']['prefix']==str(prefix)
    explicit={**payload,'launch':'STEAM_COMPAT_DATA_PATH='+shlex.quote(str(prefix.parent))+' %command%'}
    assert m.target(explicit)['prefixes']==[str(prefix)]


def test_symlink_backup_escape_blocked_and_damaged_backup_refused(runtime_env,monkeypatch,tmp_path):
    e,p,root,exe,prefix,m,payload=runtime_env
    outside=tmp_path/'outside';outside.mkdir()
    alias=prefix.parent/'.deck-fusion-runtime-backups';alias.symlink_to(outside,target_is_directory=True)
    plan=m.plan(payload)
    with pytest.raises(FusionError):m.install({**payload,'approval':plan['approval']},lambda *_:None)
    assert list(outside.iterdir())==[]
    alias.unlink();record=install(runtime_env,monkeypatch)
    (Path(record['snapshot'])/'user.reg').write_text('corrupt backup')
    plan=m.plan({**payload,'restore':True})
    with pytest.raises(FusionError,match='integrity'):m.restore({**payload,'approval':plan['approval']},lambda *_:None)


def test_busy_pending_and_low_space_block_before_install(runtime_env,monkeypatch):
    e,p,root,exe,prefix,m,payload=runtime_env
    atomic_json(e.store('123')/'pending.json',{'test':True})
    with pytest.raises(FusionError,match='pending'):m.plan(payload)
    (e.store('123')/'pending.json').unlink()
    monkeypatch.setattr('fusion_prereqs.prefix_processes',lambda *_:[{'pid':456}])
    with pytest.raises(FusionError,match='456'):m.plan(payload)
    monkeypatch.setattr('fusion_prereqs.prefix_processes',lambda *_:[])
    monkeypatch.setattr('fusion_prereqs.shutil.disk_usage',lambda *_:type('Space',(),{'free':1})())
    with pytest.raises(FusionError,match='free space'):m.plan(payload)


def test_approval_ignores_unrelated_disk_usage(runtime_env,monkeypatch):
    *_,m,payload=runtime_env
    monkeypatch.setattr('fusion_prereqs.shutil.disk_usage',lambda *_:type('Space',(),{'free':10**10})())
    first=m.plan(payload)
    monkeypatch.setattr('fusion_prereqs.shutil.disk_usage',lambda *_:type('Space',(),{'free':10**10-777})())
    second=m.plan(payload)
    assert first['approval']==second['approval'] and first['free_bytes']!=second['free_bytes']


def test_guarded_shell_only_executes_for_approved_prefix(runtime_env,tmp_path):
    e,p,root,exe,prefix,m,payload=runtime_env
    fake=tmp_path/'fake winetricks';fake.write_text('#!/bin/sh\nprintf "SIMULATED verbs=%s\\n" "$*"\n');fake.chmod(0o755)
    helper={'kind':'native','executable':'/fixture/protontricks','winetricks':str(fake),'available':True}
    target=m.target(payload)
    cmd,env=m.command(target,helper,['d3dcompiler_47'])
    assert cmd[-4:-2]==['--no-background-wineserver','-c']
    result=subprocess.run(['/bin/sh','-c',cmd[-2]],env={**env,'WINEPREFIX':str(prefix)},capture_output=True,text=True)
    assert result.returncode==0 and 'SIMULATED verbs=-q d3dcompiler_47' in result.stdout
    result=subprocess.run(['/bin/sh','-c',cmd[-2]],env={**env,'WINEPREFIX':'/tmp/wrong'},capture_output=True,text=True)
    assert result.returncode==73 and 'SIMULATED' not in result.stdout
    flat,env=m.command(target,{'kind':'flatpak','executable':'/usr/bin/flatpak'},['vcrun2022'])
    assert '--filesystem='+str(prefix.parent) in flat and '--env=STEAM_COMPAT_DATA_PATH='+str(prefix.parent) in flat
    assert 'com.github.Matoking.protontricks' in flat and '--force' not in cmd[-2]


def test_process_runner_exit_status_logs_and_cancellation(runtime_env,tmp_path):
    *_,m,payload=runtime_env;events=[];log=tmp_path/'run.log'
    m.execute(['/bin/sh','-c','printf "SIMULATED output\\n"'],os.environ.copy(),log,lambda *args:events.append(args),timeout=2)
    assert 'Exit status: 0' in log.read_text() and events
    with pytest.raises(FusionError,match='status 7'):m.execute(['/bin/sh','-c','exit 7'],os.environ.copy(),log,lambda *_:None,timeout=2)
    cancel=threading.Event();threading.Timer(.15,cancel.set).start()
    with pytest.raises(FusionError,match='cancelled'):m.execute(['/bin/sh','-c','sleep 20'],os.environ.copy(),log,lambda *_:None,cancel,timeout=2)


def test_user_guard_and_helper_untrusted_remote(runtime_env,monkeypatch):
    e,p,root,exe,prefix,m,payload=runtime_env
    other=PrefixRuntimes(e)
    monkeypatch.setattr('fusion_prereqs.os.geteuid',lambda:0)
    with pytest.raises(FusionError,match='root'):other.user_check()
    monkeypatch.setattr(m,'helper',lambda:{'available':False,'flatpak':'/usr/bin/flatpak'})
    monkeypatch.setattr(m,'_probe',lambda cmd,*_:(0,'flathub\thttps://untrusted.example/repo'))
    with pytest.raises(FusionError,match='official HTTPS'):m.helper_plan()
    monkeypatch.setattr(m,'_probe',lambda cmd,*_:(0,''))
    plan=m.helper_plan()
    assert len(plan['commands'])==2 and all('--user' in command for command in plan['commands'])
    assert 'https://dl.flathub.org/repo/flathub.flatpakrepo' in plan['commands'][0]


def test_prior_completed_snapshot_survives_failed_new_backup(runtime_env,monkeypatch):
    e,p,root,exe,prefix,m,payload=runtime_env
    good=install(runtime_env,monkeypatch)
    monkeypatch.setattr(m,'_copy_snapshot',lambda *args:(_ for _ in ()).throw(FusionError('disk unavailable')))
    plan=m.plan(payload)
    with pytest.raises(FusionError):m.install({**payload,'approval':plan['approval']},lambda *_:None)
    status=m.status(payload)
    assert not status['last']['snapshot_ready'] and status['restore_snapshot']['id']==good['id']


def test_managed_launch_waits_for_prefix_maintenance(runtime_env):
    e,p,root,exe,prefix,m,payload=runtime_env
    with m.maintenance_lock('123'):
        result=subprocess.run([str(e.wrapper),'123','--',sys.executable,'-c','print("SHOULD NOT START")'],capture_output=True,text=True)
        assert result.returncode==75 and 'SHOULD NOT START' not in result.stdout
    result=subprocess.run([str(e.wrapper),'123','--',sys.executable,'-c','print("CAN START")'],capture_output=True,text=True)
    assert result.returncode==0 and 'CAN START' in result.stdout


def test_flatpak_grants_include_separate_library_and_binding(runtime_env,monkeypatch):
    e,p,root,exe,prefix,m,payload=runtime_env
    library=Path(e.game('123')['library'])
    sd=e.home/'SD Steam Library';(sd/'steamapps').mkdir(parents=True)
    (library/'steamapps/libraryfolders.vdf').write_text('"libraryfolders" { "0" { "path" "'+str(library)+'" } "1" { "path" "'+str(sd)+'" } }')
    helper={'kind':'flatpak','executable':'/usr/bin/flatpak','available':True}
    monkeypatch.setattr(m,'helper',lambda:helper)
    plan=m.plan(payload)
    cmd,_=m.command(plan['target'],helper,['d3dcompiler_47'])
    for path in (sd,library,prefix.parent,root):
        assert str(path) in plan['filesystem_grants'] and '--filesystem='+str(path) in cmd
    assert '--filesystem=host' not in cmd and 'override' not in cmd
    # A later-discovered tool library must be shown in a fresh confirmation.
    (library/'steamapps/libraryfolders.vdf').write_text('"libraryfolders" {}')
    with pytest.raises(FusionError,match='changed since'):m.install({**payload,'approval':plan['approval']},lambda *_:None)


def test_restore_space_uses_saved_prefix_size_and_index_is_bound(runtime_env,monkeypatch):
    e,p,root,exe,prefix,m,payload=runtime_env
    big=prefix/'drive_c/large-fixture';big.write_bytes(b'a'*(2*1024*1024))
    record=install(runtime_env,monkeypatch);big.unlink()
    plan=m.plan({**payload,'restore':True})
    assert plan['copy_bytes']>plan['prefix_bytes']+1000000
    free=plan['required_space_bytes']-1
    monkeypatch.setattr('fusion_prereqs.shutil.disk_usage',lambda *_:type('Space',(),{'free':free})())
    with pytest.raises(FusionError,match='free space'):m.plan({**payload,'restore':True})
    monkeypatch.setattr('fusion_prereqs.shutil.disk_usage',lambda *_:type('Space',(),{'free':10**10})())
    index=Path(record['snapshot']).parent/'index.json';data=read_json(index)
    data['system.reg']['size']+=1;atomic_json(index,data)
    with pytest.raises(FusionError,match='target changed'):m.restore({**payload,'approval':plan['approval']},lambda *_:None)


def test_tampered_receipt_log_and_snapshot_paths_do_not_escape(runtime_env,monkeypatch,tmp_path):
    e,p,root,exe,prefix,m,payload=runtime_env
    store=e.store('123')
    atomic_json(store/'runtime-last.json',{'id':'../outside','appid':'123','prefix':str(prefix)})
    status=m.status(payload)
    assert status['last'] is None and any('receipt' in b for b in status['blockers'])
    good=install(runtime_env,monkeypatch)
    log=store/'runtime-jobs'/good['id']/'installer.log';log.unlink()
    target=tmp_path/'private';target.write_text('DO NOT EXPOSE')
    log.symlink_to(target)
    status=m.status(payload)
    assert 'DO NOT EXPOSE' not in json.dumps(status) and status['blockers']
    log.unlink()
    index=read_json(store/'runtime-snapshots.json');index[str(prefix)]['prefix']='/other/pfx';atomic_json(store/'runtime-snapshots.json',index)
    with pytest.raises(FusionError,match='receipt'):m.plan({**payload,'restore':True})


def test_restore_staging_failure_cleans_only_partial_copy(runtime_env,monkeypatch):
    e,p,root,exe,prefix,m,payload=runtime_env
    record=install(runtime_env,monkeypatch)
    before=prefix_inventory(prefix,hashes=True)
    plan=m.plan({**payload,'restore':True})
    original=__import__('shutil').copy2
    def failing_copy(src,dst,**kwargs):
        original(src,dst,**kwargs)
        raise FusionError('SIMULATED cancelled copy')
    monkeypatch.setattr('fusion_prereqs.shutil.copy2',failing_copy)
    with pytest.raises(FusionError,match='cancelled copy'):m.restore({**payload,'approval':plan['approval']},lambda *_:None)
    assert not list(prefix.parent.glob('.df-before-restore-*'))
    assert prefix_inventory(prefix,hashes=True)==before and Path(record['snapshot']).is_dir()


def test_helper_failure_output_exposed_and_success_is_reprobed(runtime_env,monkeypatch):
    e,p,root,exe,prefix,m,payload=runtime_env
    monkeypatch.setattr(m,'helper',lambda:{'available':False,'flatpak':'/fixture/flatpak'})
    monkeypatch.setattr(m,'_probe',lambda *args:(0,'flathub https://dl.flathub.org/repo'))
    plan=m.helper_plan()
    def failure(command,env,log,progress,event=None,**kwargs):
        log.write_text('SIMULATED no network access')
        raise FusionError('SIMULATED Flatpak failure')
    monkeypatch.setattr(m,'execute',failure)
    with pytest.raises(FusionError,match='Flatpak failure'):m.install_helper({'approval':plan['approval']},lambda *_:None)
    assert m.status(payload)['helper_log']['text']=='SIMULATED no network access'


def test_restore_does_not_require_any_runtime_checkbox(runtime_env,monkeypatch):
    e,p,root,exe,prefix,m,payload=runtime_env
    install(runtime_env,monkeypatch)
    payload={**payload,'runtimes':[],'restore':True}
    plan=m.plan(payload)
    assert plan['restoring'] and not plan['runtimes']
    result=m.restore({**payload,'approval':plan['approval']},lambda *_:None)
    assert result['state']=='restored'


def test_mutation_during_backup_blocks_installer(runtime_env,monkeypatch):
    e,p,root,exe,prefix,m,payload=runtime_env
    original=m._copy_snapshot
    def modified(*args,**kwargs):
        original(*args,**kwargs)
        (prefix/'user.reg').write_text('independent change after snapshot')
    monkeypatch.setattr(m,'_copy_snapshot',modified)
    monkeypatch.setattr(m,'execute',lambda *args,**kwargs:pytest.fail('installer must not start'))
    plan=m.plan(payload)
    with pytest.raises(FusionError,match='approved prefix changed'):m.install({**payload,'approval':plan['approval']},lambda *_:None)
    assert m.status(payload)['last']['snapshot_ready']
