import json
from pathlib import Path
import pytest
from fusion_transaction import Transaction
from fusion_util import FusionError

@pytest.fixture
def tx(tmp_path):
    root=tmp_path/'game';root.mkdir()
    return Transaction(root,tmp_path/'state')


def test_conflict_requires_consent(tx):
    (tx.root/'dxgi.dll').write_bytes(b'old mod')
    assert tx.inspect({'dxgi.dll':b'new'})['needs_consent']
    with pytest.raises(FusionError):tx.prepare({'dxgi.dll':b'new'}, {},'old','new')
    assert (tx.root/'dxgi.dll').read_bytes()==b'old mod'


def test_install_update_remove_restore(tx):
    (tx.root/'dxgi.dll').write_bytes(b'old mod')
    prep=tx.prepare({'dxgi.dll':b'new','ReShade.ini':b'config'}, {'runtime.json':b'{}'},'old args','new args',True)
    assert (tx.root/'dxgi.dll').read_bytes()==b'new'
    tx.finalize(prep['token'],'new args')
    second=tx.prepare({'dxgi.dll':b'newer'}, {},'new args','latest args')
    tx.finalize(second['token'],'latest args')
    assert not (tx.root/'ReShade.ini').exists()
    restore=tx.prepare({}, {},'latest args','old args',reset_origin=True)
    tx.finalize(restore['token'],'old args')
    assert (tx.root/'dxgi.dll').read_bytes()==b'old mod'
    assert tx.manifest()['files']=={} and tx.manifest()['original_launch'] is None


def test_explicit_rollback(tx):
    (tx.root/'game.ini').write_bytes(b'original')
    prep=tx.prepare({'game.ini':b'new','brandnew.dll':b'new'}, {},'before','after',True)
    restored=tx.rollback(prep['token'])
    assert restored['launch_options']=='before'
    assert (tx.root/'game.ini').read_bytes()==b'original' and not (tx.root/'brandnew.dll').exists()
    assert tx.pending() is None


def test_failure_mid_install_rolls_back(tx):
    (tx.root/'a.dll').write_bytes(b'original')
    def fail(text,fraction):raise OSError('simulated interrupted write')
    with pytest.raises(OSError):tx.prepare({'a.dll':b'new','b.dll':b'new'}, {},'before','after',True,fail)
    assert (tx.root/'a.dll').read_bytes()==b'original' and not (tx.root/'b.dll').exists()
    assert tx.pending() is None


def test_external_modification_not_destroyed(tx):
    prep=tx.prepare({'dxgi.dll':b'ours'}, {},'before','after');tx.finalize(prep['token'],'after')
    (tx.root/'dxgi.dll').write_bytes(b'new external mod')
    with pytest.raises(FusionError,match='changed outside'):tx.inspect({})
    assert (tx.root/'dxgi.dll').read_bytes()==b'new external mod'


def test_recovery_stops_on_independent_edit(tx):
    prep=tx.prepare({'dxgi.dll':b'ours'}, {},'before','after')
    (tx.root/'dxgi.dll').write_bytes(b'external change')
    with pytest.raises(FusionError,match='changed independently'):tx.rollback(prep['token'])
    assert tx.pending() is not None


def test_finalize_requires_verified_launch(tx):
    prep=tx.prepare({'dxgi.dll':b'ours'}, {},'before','after')
    with pytest.raises(FusionError):tx.finalize(prep['token'],'wrong')
    assert tx.pending() is not None
    tx.rollback(prep['token'])


def test_pending_blocks_second_install(tx):
    prep=tx.prepare({'a':b'a'}, {},'before','after')
    with pytest.raises(FusionError,match='interrupted'):tx.prepare({'a':b'b'}, {},'before','after')
    tx.rollback(prep['token'])


def test_casing_collision(tx):
    (tx.root/'DXGI.DLL').write_bytes(b'old')
    with pytest.raises(FusionError,match='casing conflict'):tx.inspect({'dxgi.dll':b'new'})


def test_edited_ini_snapshot_preserved(tx):
    prep=tx.prepare({'ReShade.ini':b'first'}, {},'before','after');tx.finalize(prep['token'],'after')
    (tx.root/'ReShade.ini').write_bytes(b'user edit')
    prep=tx.prepare({'ReShade.ini':b'next'}, {},'after','after');tx.finalize(prep['token'],'after')
    snapshots=list((tx.store/'transactions'/prep['token']).glob('*.before'))
    assert any(p.read_bytes()==b'user edit' for p in snapshots)


def test_game_symlink_not_touched(tx,tmp_path):
    outside=tmp_path/'outside';outside.write_bytes(b'private')
    (tx.root/'dxgi.dll').symlink_to(outside)
    with pytest.raises(FusionError):tx.prepare({'dxgi.dll':b'bad'}, {},'before','after',True)
    assert outside.read_bytes()==b'private'
