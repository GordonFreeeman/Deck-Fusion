"""Repair transactions with synthetic game/component payloads. No GPU assumptions."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from conftest import pe_bytes
from fusion_transaction import Transaction
from fusion_util import FusionError, atomic_json, sha256


def files(base):
    return {str(f.relative_to(base)): f.read_bytes() for f in base.rglob('*') if f.is_file()}


def apply(e, p, launch='--skip-launcher', force=False):
    plan = e.plan(p, launch, force_repair=force)
    assert not plan['blockers'], plan['blockers']
    stage = e.prepare_approved(p, launch, plan['approval_token'], force_repair=force)
    result = e.finish(p['appid'], stage['token'], stage['launch_after'])
    return stage, result


@pytest.fixture
def installed(packages):
    e, p, root, exe = packages
    p['opti']['enabled'] = True
    p['reshade']['mode'] = 'opti'
    p['wine']['custom_overrides'] = 'version=n,b'
    (exe.parent / 'version.dll').write_bytes(pe_bytes() + b'UNRELATED MOD')
    stage, _ = apply(e, p, 'WINEDLLOVERRIDES="version=n,b;keep=b" %command% --skip-launcher')
    return e, e.profile(p['appid']), root, exe, stage['launch_after']


def test_deleted_installation_repaired_without_profile_or_mod_reset(installed):
    e, p, root, exe, launch = installed
    tx = Transaction(root, e.store(p['appid']))
    tracked = tx.manifest()['files']
    expected = {rel: (root / rel).read_bytes() for rel in tracked}
    for rel in tracked: (root / rel).unlink()
    before = files(root)
    saved = (e.store(p['appid']) / 'profile.json').read_bytes()
    blocked = e.plan(p, launch)
    assert blocked['blockers'] and blocked['repair_available'] and 'approval_token' not in blocked
    plan = e.plan(p, launch, force_repair=True)
    assert not plan['blockers'], plan
    assert {x['path'] for x in plan['repairs']} == set(tracked)
    assert all(x['state'] == 'missing' for x in plan['repairs'])
    assert files(root) == before and (e.store(p['appid']) / 'profile.json').read_bytes() == saved
    assert not tx.pending()  # Preview/cancel is read-only.
    stage, result = apply(e, p, launch, True)
    for rel, value in expected.items(): assert (root / rel).read_bytes() == value
    assert (exe.parent / 'version.dll').read_bytes().endswith(b'UNRELATED MOD')
    profile = e.profile(p['appid'])
    assert 'force_repair' not in profile and not profile['backup_conflicts']
    assert profile['wine'] == p['wine']
    assert profile['base_fps'] == p['base_fps'] and profile['lsfg'] == p['lsfg']
    assert stage['launch_after'] == launch
    assert result['force_repair'] and Path(result['receipt']).is_file()
    assert not e.plan(profile, launch)['blockers']


def test_modified_binary_snapshot_and_originals_are_retained(installed):
    e, p, root, exe, launch = installed
    tx = Transaction(root, e.store(p['appid']))
    old = tx.manifest()
    proxy = exe.parent / (p['opti']['proxy'] + '.dll')
    replacement = pe_bytes() + b'EXTERNAL REPLACEMENT'
    proxy.write_bytes(replacement)
    _, result = apply(e, p, launch, True)
    receipt = json.loads(Path(result['receipt']).read_text())
    action = next(x for x in receipt['actions'] if x['area'] == 'game' and x['path'] == str(proxy.relative_to(root)))
    assert (Path(result['receipt']).parent / action['before']).read_bytes() == replacement
    assert receipt['force_repair'] and receipt['repairs'][0]['state'] == 'modified'
    assert proxy.read_bytes() != replacement
    assert tx.manifest()['original_launch'] == old['original_launch']
    for rel, meta in old['files'].items(): assert tx.manifest()['files'][rel]['before'] == meta['before']


def test_unapproved_force_and_repurposed_normal_token_are_blocked(installed):
    e, p, root, exe, launch = installed
    before = files(root)
    with pytest.raises(FusionError, match='confirmed repair plan'):
        e.prepare(p, launch, force_repair=True)
    normal = e.plan(p, launch)
    with pytest.raises(FusionError, match='changed after confirmation'):
        e.prepare_approved(p, launch, normal['approval_token'], force_repair=True)
    assert files(root) == before


@pytest.mark.parametrize('what', ['game', 'package', 'profile', 'manifest'])
def test_repair_approval_is_bound_to_exact_state(installed, what):
    e, p, root, exe, launch = installed
    proxy = exe.parent / (p['opti']['proxy'] + '.dll'); proxy.unlink()
    plan = e.plan(p, launch, force_repair=True); assert not plan['blockers']
    if what == 'game': proxy.write_bytes(pe_bytes() + b'changed after popup')
    elif what == 'package': (Path(e.package('opti')['path']) / 'OptiScaler.dll').write_bytes(pe_bytes() + b'package update')
    elif what == 'profile': p['base_fps'] = 41
    else:
        path = e.store(p['appid']) / 'manifest.json'
        data = json.loads(path.read_text()); data['external_note'] = 'changed after popup'; atomic_json(path, data)
    before = files(root)
    with pytest.raises(FusionError, match='changed after confirmation'):
        e.prepare_approved(p, launch, plan['approval_token'], force_repair=True)
    assert files(root) == before
    assert not (e.store(p['appid']) / 'pending.json').exists()


def test_failure_and_rollback_restore_the_manually_cleaned_state(installed):
    e, p, root, exe, launch = installed
    proxy = exe.parent / (p['opti']['proxy'] + '.dll'); proxy.unlink()
    (exe.parent / 'ReShade64.dll').write_bytes(b'EXTERNALLY CHANGED')
    before = files(root)
    store = e.store(p['appid'])
    saved = {key:(store/key).read_bytes() for key in ('profile.json','manifest.json','runtime.json')}
    plan = e.plan(p, launch, force_repair=True); assert not plan['blockers'], plan
    def interrupted(*_): raise OSError('simulated mid-write failure')
    with pytest.raises(OSError, match='mid-write'):
        e.prepare_approved(p, launch, plan['approval_token'], progress=interrupted, force_repair=True)
    assert files(root) == before and not (store/'pending.json').exists()
    assert all((store/key).read_bytes() == value for key,value in saved.items())
    # Lost/failed Steam write after all files were staged also has a working rollback.
    plan = e.plan(p, launch, force_repair=True)
    staged = e.prepare_approved(p, launch, plan['approval_token'], force_repair=True)
    assert e.plan(p, launch, force_repair=True)['blockers']  # Pending operation is not bypassed.
    e.rollback(p['appid'], staged['token'])
    assert files(root) == before and not (store/'pending.json').exists()
    assert all((store/key).read_bytes() == value for key,value in saved.items())


@pytest.mark.parametrize('deleted', [True, False])
def test_obsolete_drift_is_preserved_not_deleted_or_resurrected(installed, deleted):
    e, p, root, exe, launch = installed
    obsolete = exe.parent / 'ReShade64.dll'
    if deleted: obsolete.unlink()
    else: obsolete.write_bytes(b'MANUALLY REPLACED AND NOW DESELECTED')
    stamp = obsolete.stat() if not deleted else None
    p['reshade']['mode'] = 'off'
    plan = e.plan(p, launch, force_repair=True); assert not plan['blockers'],plan
    assert any(x['path'].endswith('ReShade64.dll') and x['action'] == ('leave-absent' if deleted else 'keep-and-untrack') for x in plan['repairs'])
    apply(e, p, launch, True)
    assert obsolete.exists() != deleted
    if not deleted:
        assert obsolete.read_bytes() == b'MANUALLY REPLACED AND NOW DESELECTED'
        assert obsolete.stat().st_ino == stamp.st_ino and obsolete.stat().st_mtime_ns == stamp.st_mtime_ns
    assert str(obsolete.relative_to(root)) not in Transaction(root,e.store(p['appid'])).manifest()['files']


def test_force_reinstalls_selected_loader_even_with_its_custom_override(installed):
    e, p, root, exe, launch = installed
    p['wine']['custom_overrides'] += ';' + p['opti']['proxy'] + '=n,b'
    plan = e.plan(p, launch, force_repair=True)
    assert not plan['blockers']
    assert plan['profile']['opti']['proxy'] == p['opti']['proxy']
    assert plan['profile']['wine']['custom_overrides'] == p['wine']['custom_overrides']


@pytest.mark.parametrize('reason', ['running','anti-cheat','symlink','full-disk'])
def test_force_keeps_safety_stops(installed, monkeypatch, reason):
    e, p, root, exe, launch = installed
    if reason == 'running':
        monkeypatch.setattr('fusion_engine.running_game', lambda *_:{'processes':[{'pid':4321}]})
    elif reason == 'anti-cheat':
        monkeypatch.setattr('fusion_engine.scan_game', lambda *_:{'anticheat':['synthetic-anti-cheat-marker']})
    elif reason == 'symlink':
        proxy=exe.parent/(p['opti']['proxy']+'.dll'); proxy.unlink()
        other=e.home/'outside.dll'; other.write_bytes(b'private'); proxy.symlink_to(other)
    if reason == 'full-disk':
        plan=e.plan(p,launch,force_repair=True);assert not plan['blockers']
        monkeypatch.setattr('fusion_transaction.shutil.disk_usage', lambda *_:SimpleNamespace(free=0))
        with pytest.raises(FusionError,match='free space'):
            e.prepare_approved(p,launch,plan['approval_token'],force_repair=True)
    else:
        plan=e.plan(p,launch,force_repair=True)
        assert plan['blockers'] and not plan['repair_available']
    assert not (e.store(p['appid'])/'pending.json').exists()


def test_force_preserves_pre_first_install_original_and_restore(tmp_path):
    root=tmp_path/'game';root.mkdir();tx=Transaction(root,tmp_path/'store')
    target=root/'dxgi.dll';target.write_bytes(b'ORIGINAL BEFORE FIRST INSTALL')
    init=tx.prepare({'dxgi.dll':b'OLD TOOL'},{},'original launch','installed launch',True)
    tx.finalize(init['token'],'installed launch');target.unlink()
    before=tx.manifest()['files']['dxgi.dll']['before']
    review=tx.inspect({'dxgi.dll':b'REPAIRED TOOL'},force_repair=True)
    stage=tx.prepare({'dxgi.dll':b'REPAIRED TOOL'},{},'installed launch','installed launch',True,
                     expected_state=review['file_state'],force_repair=True,expected_manifest=review['manifest_hash'])
    tx.finalize(stage['token'],'installed launch')
    assert tx.manifest()['files']['dxgi.dll']['before']==before
    restored=tx.prepare({}, {},'installed launch','original launch', reset_origin=True)
    tx.finalize(restored['token'],'original launch')
    assert target.read_bytes()==b'ORIGINAL BEFORE FIRST INSTALL'


def test_force_cannot_bypass_corrupt_original_backup(tmp_path):
    root=tmp_path/'game';root.mkdir();tx=Transaction(root,tmp_path/'store')
    target=root/'dxgi.dll';target.write_bytes(b'original')
    init=tx.prepare({'dxgi.dll':b'ours'},{},'','',True);tx.finalize(init['token'],'')
    original=tx.store/'originals'/tx.manifest()['files']['dxgi.dll']['before']
    original.write_bytes(b'corrupted');target.unlink()
    with pytest.raises(FusionError,match='backup is missing or damaged'):
        tx.inspect({'dxgi.dll':b'repair'},force_repair=True)
    assert not target.exists() and not tx.pending()


def test_force_is_not_a_restore_permission_and_requires_a_boolean(installed):
    e,p,root,exe,launch=installed
    assert e.plan(p,launch,True,force_repair=True)['blockers']
    for flag in ('true',1,None): assert e.plan(p,launch,force_repair=flag)['blockers']


def test_repair_restores_missing_original_mod_when_graphics_proxy_moves(packages):
    e,p,root,exe=packages
    p['opti'].update(enabled=True,proxy='version')
    original=pe_bytes()+b'ORIGINAL MOD LOADER'
    mod=exe.parent/'version.dll';mod.write_bytes(original)
    # Simulate the original/replaced-file record created by an older release.
    p=e.validate(p);desired,extras,_=e.build(p)
    tx=Transaction(root,e.store(p['appid']))
    launch='WINEDLLOVERRIDES=version=n,b %command% --skip-launcher'
    staged=tx.prepare(desired,extras,launch,launch,True);tx.finalize(staged['token'],launch)
    mod.unlink()
    p['opti']['proxy']='winmm'  # Explicitly move the selected graphics loader.
    plan=e.plan(p,launch,force_repair=True)
    assert not plan['blockers'],plan
    assert plan['profile']['opti']['proxy']!='version'
    assert any(x['path'].endswith('version.dll') and x['action']=='restore-original' for x in plan['repairs'])
    # Cancel leaves it absent; applying restores the actual mod, not the retired tool.
    assert not mod.exists()
    staged=e.prepare_approved(p,launch,plan['approval_token'],force_repair=True)
    e.finish(p['appid'],staged['token'],staged['launch_after'])
    assert mod.read_bytes()==original
    assert 'version=n,b' in staged['launch_after']
    assert str(mod.relative_to(root)) not in tx.manifest()['files']
