"""Beta3 launch migration and force-install tests, using synthetic game files."""
from pathlib import Path
import json
import shlex
import pytest

from fusion_cleanup import cleanup_launch
from fusion_launch import compose_launch, launch_assignments
from fusion_transaction import Transaction
from fusion_util import FusionError
from test_120 import apply

WRAPPER = Path('/home/deck/.local/share/deck-fusion/bin/launch')


@pytest.mark.parametrize('key', ['WINEDLLOVERRIDES', 'WINEDLLOVERIDES'])
def test_cleanup_dlls_and_legacy_wrapper_keeps_other_overrides_and_arguments(key):
    before = key + '="version,winmm=n,b;dinput8=n,b;d3dcompiler_47=n" ~/LSFG %command% --skip-launcher "a b"'
    result = cleanup_launch(before, WRAPPER, '1086940')
    assert result['before'] == before and result['removed'] and result['warnings']
    assert '~/LSFG' not in result['after'] and 'version,winmm' not in result['after']
    assert launch_assignments(result['cleaned'])[key] == 'dinput8=n,b;d3dcompiler_47=n'
    assert shlex.split(result['after'])[-2:] == ['--skip-launcher', 'a b']
    assert result['after'].endswith('--skip-launcher "a b"')
    assert result['after'].count('%command%') == 1
    assert result['after'].count(str(WRAPPER)) == 1


@pytest.mark.parametrize('old', ['~/LSFG', 'bash ~/LSFG/lsfg.sh', '"/home/deck/LSFG Tools/run.sh"', '$HOME/LSFG/lsfg-vk'])
def test_cleanup_known_wrapper_and_wrapper_options(old):
    result = cleanup_launch(old + ' --multiplier 2 -- %command% -dx11', WRAPPER, '123')
    assert result['removed'] and '--multiplier' not in result['after']
    assert shlex.split(result['after']) == [str(WRAPPER), '123', '--', '%command%', '-dx11']


def test_cleanup_injection_lists_keeps_other_layers_and_custom_environment():
    old = 'CUSTOM="two words" LSFGVK_CONFIG=/old/config.toml VK_INSTANCE_LAYERS=VkLayer_LS_frame_generation:VK_LAYER_MANGOHUD_overlay LD_PRELOAD="/x/liblsfg.so:/x/keep.so" %command% --foo'
    result = cleanup_launch(old, WRAPPER, '123')
    env = launch_assignments(result['cleaned'])
    assert env['CUSTOM'] == 'two words' and 'LSFGVK_CONFIG' not in env
    assert env['LD_PRELOAD'] == '/x/keep.so'
    assert env['VK_INSTANCE_LAYERS'] == 'VK_LAYER_MANGOHUD_overlay'


def test_cleanup_recognizes_lsfg_layer_name():
    # The LSFG layer can be named VkLayer_LS_frame_generation, without "lsfg".
    result = cleanup_launch('VK_INSTANCE_LAYERS=VK_LAYER_LS_frame_generation %command%', WRAPPER, '123')
    assert result['removed'] and 'VK_INSTANCE_LAYERS' not in result['cleaned']


@pytest.mark.parametrize('old', ['', '--skip-launcher', 'FOO="two words" %command% --message "ReShade is installed"',
                              'WINEDLLOVERRIDES="dinput8=n,b;d3dcompiler_47=n" mangohud %command%'])
def test_cleanup_no_false_hits_or_changes_to_unrelated_text(old):
    result = cleanup_launch(old, WRAPPER, '123')
    assert not result['removed'] and result['cleaned'] == old


def test_cleanup_is_idempotent_and_replaces_foreign_fusion_wrapper():
    initial = cleanup_launch('~/LSFG %command% --foo', WRAPPER, '123')
    second = cleanup_launch(initial['after'], WRAPPER, '123')
    assert second['after'] == initial['after'] and second['removed'] == []
    old = '/home/other/.local/share/deck-fusion/bin/launch 456 -- %command% --foo'
    replaced = cleanup_launch(old, WRAPPER, '123')
    assert replaced['removed'] and '456' not in replaced['after']
    assert replaced['after'] == compose_launch('%command% --foo', WRAPPER, '123')


@pytest.mark.parametrize('old', ['LSFGVK_CONFIG=x $(printf dangerous) %command%',
                              'LSFGVK_CONFIG=x %command%; touch /tmp/not-created',
                              'LSFGVK_CONFIG="unterminated', '~/LSFG %command% %command%'])
def test_cleanup_rejects_compound_or_malformed_shell_without_execution(old):
    with pytest.raises(FusionError): cleanup_launch(old, WRAPPER, '123')


def test_forced_reinstall_restores_deleted_and_modified_managed_files(packages):
    e, p, root, exe = packages
    p['opti']['enabled'] = True; p['reshade']['mode'] = 'opti'
    _, staged = apply(e, p)
    launch = staged['launch_after']; p = e.profile('123')
    old = Transaction(root, e.store('123')).manifest()
    expected = {rel: (root / rel).read_bytes() for rel in old['files']}
    dll = next(rel for rel in expected if rel.endswith('ReShade64.dll'))
    proxy = next(rel for rel in expected if rel.endswith(p['opti']['proxy'] + '.dll'))
    (root / dll).unlink(); (root / proxy).write_bytes(b'MANUALLY MODIFIED')
    assert e.plan(p, launch)['repair_available']
    plan = e.plan(p, launch, force_repair=True)
    assert not plan['blockers']
    fixed = e.prepare_approved(p, launch, plan['approval_token'], force_repair=True)
    e.finish('123', fixed['token'], fixed['launch_after'])
    assert all((root / rel).read_bytes() == data for rel, data in expected.items())
    receipt = json.loads((e.store('123') / 'transactions' / fixed['token'] / 'receipt.json').read_text())
    action = next(x for x in receipt['actions'] if x['path'] == proxy)
    assert (e.store('123') / 'transactions' / fixed['token'] / action['before']).read_bytes() == b'MANUALLY MODIFIED'


def test_force_selected_existing_proxy_is_backed_up_and_rollback_restores_old_launch(packages):
    e, p, root, exe = packages
    p['opti']['enabled'] = True; p['opti']['proxy'] = 'dxgi'
    proxy = exe.parent / 'dxgi.dll'; proxy.write_bytes(b'EXISTING OLD GRAPHICS LOADER')
    before = 'WINEDLLOVERRIDES="version,winmm=n,b" ~/LSFG %command% --foo'
    cleanup = e.launch_cleanup('123', before)
    plan = e.plan(p, cleanup['cleaned'], force_repair=True)
    assert not plan['blockers'] and plan['profile']['opti']['proxy'] == 'dxgi'
    assert str(proxy.relative_to(root)) in plan['conflicts']
    stage = e.prepare_approved(p, cleanup['cleaned'], plan['approval_token'], launch_actual=before, force_repair=True)
    assert stage['launch_before'] == before and stage['launch_after'] == cleanup['after']
    assert proxy.read_bytes() != b'EXISTING OLD GRAPHICS LOADER'
    Transaction(root, e.store('123')).rollback(stage['token'])
    assert proxy.read_bytes() == b'EXISTING OLD GRAPHICS LOADER'
    assert not (e.store('123') / 'pending.json').exists()
