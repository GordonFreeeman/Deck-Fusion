"""Beta6 runtime-repair and launch-replacement regression checks."""
from pathlib import Path
import shlex
import pytest
from conftest import vc_fixture
from fusion_util import FusionError
from test_130 import runtime_env, simulate_installer


@pytest.mark.parametrize('receipt', ['vcrun2022', 'vcrun2015', 'vcrun2017', 'vcrun2019'])
def test_stale_vc_receipt_repaired_after_snapshot_then_launch_options_replaced(runtime_env,monkeypatch,receipt):
    e,p,root,exe,prefix,m,payload=runtime_env
    vc_fixture(prefix,version=(14,29,0,0))
    original=b'dotnet48\r\n'+receipt.encode()+b'\r\n'+b'd3dcompiler_47\ncustom-setting\n'
    (prefix/'winetricks.log').write_bytes(original)
    payload={**payload,'runtimes':['vcrun2022']}
    cleanup=e.launch_cleanup(p['appid'],payload['launch'])
    assert 'version,winmm' not in cleanup['cleaned']
    def execute(cmd,env,log,progress,event=None):
        assert (Path(m.snapshot_record(m.target(payload))['snapshot'])/'winetricks.log').read_bytes()==original
        assert (prefix/'winetricks.log').read_bytes()==b'dotnet48\r\nd3dcompiler_47\ncustom-setting\n'
        assert '--force' not in shlex.split(cmd[-2])
        # Models Winetricks' skip/conflict logic: stale receipt must be gone.
        assert receipt not in (prefix/'winetricks.log').read_text().splitlines()
        vc_fixture(prefix)
        with (prefix/'winetricks.log').open('a') as f:f.write('vcrun2022\n')
    monkeypatch.setattr(m,'execute',execute)
    plan=m.plan(payload)
    assert (prefix/'winetricks.log').read_bytes()==original, 'Review must not repair anything'
    result=m.install({**payload,'approval':plan['approval']},lambda *_:None)
    assert result['state']=='completed' and result['receipt_repairs'][0]['removed']==[receipt]
    # Complete the real file/launcher transaction after repairing the runtime.
    plan=e.plan(p,cleanup['cleaned'],force_repair=True)
    assert not plan['blockers'],plan['blockers']
    stage=e.prepare_approved(p,cleanup['cleaned'],plan['approval_token'],launch_actual=payload['launch'],force_repair=True)
    assert stage['launch_before']==payload['launch']
    assert stage['launch_after']==cleanup['after']
    e.finish(p['appid'],stage['token'],stage['launch_after'])


def test_healthy_runtime_keeps_all_receipts_and_skips_installer(runtime_env,monkeypatch):
    *_,prefix,m,payload=runtime_env
    vc_fixture(prefix)
    receipt=b'dotnet48\nvcrun2019\nvcrun2022\n';(prefix/'winetricks.log').write_bytes(receipt)
    payload={**payload,'runtimes':['vcrun2022']}
    monkeypatch.setattr(m,'execute',lambda *_:pytest.fail('Healthy runtime was reinstalled'))
    plan=m.plan(payload);result=m.install({**payload,'approval':plan['approval']},lambda *_:None)
    assert result['state']=='completed' and not result.get('receipt_repairs')
    assert (prefix/'winetricks.log').read_bytes()==receipt


def test_failed_stale_receipt_repair_keeps_restorable_original(runtime_env,monkeypatch):
    *_,prefix,m,payload=runtime_env
    original=b'dotnet48\nvcrun2022\n';(prefix/'winetricks.log').write_bytes(original)
    payload={**payload,'runtimes':['vcrun2022']}
    monkeypatch.setattr(m,'execute',simulate_installer(prefix,fail=True))
    plan=m.plan(payload)
    with pytest.raises(FusionError,match='SIMULATED'):m.install({**payload,'approval':plan['approval']},lambda *_:None)
    record=m.snapshot_record(m.target(payload))
    assert record['snapshot_ready'] and (Path(record['snapshot'])/'winetricks.log').read_bytes()==original
    restore={**payload,'restore':True};plan=m.plan(restore)
    m.restore({**restore,'approval':plan['approval']},lambda *_:None)
    assert (prefix/'winetricks.log').read_bytes()==original


def test_repair_refuses_linked_receipt_and_preserves_external_file(runtime_env,monkeypatch,tmp_path):
    *_,prefix,m,payload=runtime_env
    outside=tmp_path/'outside';outside.write_bytes(b'vcrun2022\n')
    (prefix/'winetricks.log').symlink_to(outside)
    payload={**payload,'runtimes':['vcrun2022']}
    monkeypatch.setattr(m,'execute',lambda *_:pytest.fail('Unsafe receipt reached installer'))
    plan=m.plan(payload)
    with pytest.raises(FusionError,match='leaves|Symbolic links'):m.install({**payload,'approval':plan['approval']},lambda *_:None)
    assert outside.read_bytes()==b'vcrun2022\n'


def test_unselected_runtime_receipt_is_not_repaired(runtime_env,monkeypatch):
    *_,prefix,m,payload=runtime_env
    original=b'vcrun2022\ndotnet48\n';(prefix/'winetricks.log').write_bytes(original)
    payload={**payload,'runtimes':['d3dcompiler_47']}
    monkeypatch.setattr(m,'execute',simulate_installer(prefix))
    plan=m.plan(payload);result=m.install({**payload,'approval':plan['approval']},lambda *_:None)
    assert result['state']=='completed' and not result.get('receipt_repairs')
    assert (prefix/'winetricks.log').read_bytes().startswith(original)
