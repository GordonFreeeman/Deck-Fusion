"""Beta2 regressions. Synthetic PE files, session records and installer output."""
import os
from pathlib import Path
import struct
import sys
import zipfile

import pytest
from conftest import pe_bytes
from fusion_api import detect_graphics_api
from fusion_prereqs import installer_error, steam_session_environment
from fusion_util import FusionError, sha256
import fusion_downloads as downloads
from test_130 import runtime_env


def image(*imports, bits=64):
    data = bytearray(pe_bytes(bits, api=None))
    directory = 0x80 + 24 + (112 if bits == 64 else 96)
    struct.pack_into('<II', data, directory + 8, 0x1000, (len(imports) + 1) * 20)
    for n, name in enumerate(imports):
        struct.pack_into('<IIIII', data, 0x400 + n * 20, 0, 0, 0, 0x1200 + n * 128, 0)
        raw = name.encode() + b'\0'
        data[0x600 + n * 128:0x600 + n * 128 + len(raw)] = raw
    return bytes(data)


def unity_game(root, *imports):
    exe = root / 'SubnauticaZero.exe'
    exe.write_bytes(image('UnityPlayer.dll'))
    (root / 'UnityPlayer.dll').write_bytes(image(*imports))
    (root / 'SubnauticaZero_Data').mkdir(exist_ok=True)
    return exe


def test_engine_dll_imports_resolve_renderer(tmp_path):
    exe = unity_game(tmp_path, 'D3D11.dll')
    result = detect_graphics_api(exe, tmp_path)
    assert result['api'] == 'dx11' and result['source'] == 'imports'
    assert result['evidence'] == [{'api': 'dx11', 'file': 'UnityPlayer.dll', 'import': 'd3d11.dll'}]


@pytest.mark.parametrize('flag,api', [('-force-d3d11', 'dx11'), ('-force-d3d12', 'dx12'),
                                    ('-force-vulkan', 'vulkan'), ('-force-glcore', 'opengl')])
def test_unity_launch_flag_overrides_imports_and_title_default(tmp_path, flag, api):
    exe = unity_game(tmp_path, 'd3d11.dll', 'd3d12.dll')
    result = detect_graphics_api(exe, tmp_path, f'%command% {flag}', '848450')
    assert (result['api'], result['source']) == (api, 'launch-options')


def test_below_zero_default_is_scoped_and_explicit(tmp_path):
    exe = unity_game(tmp_path, 'd3d11.dll', 'd3d12.dll')
    hint = detect_graphics_api(exe, tmp_path, appid='848450')
    assert (hint['api'], hint['source']) == ('dx11', 'game-default')
    assert detect_graphics_api(exe, tmp_path, appid='999')['api'] == 'auto'
    renamed = exe.rename(tmp_path / 'OtherGame.exe')
    assert detect_graphics_api(renamed, tmp_path, appid='848450')['api'] == 'auto'


@pytest.mark.parametrize('launch', ['%command% -force-d3d11 -force-d3d12', '%command% -force-glcore45', '-force-d3d12-other'])
def test_conflicting_or_unrecognized_unity_flags_need_selection(tmp_path, launch):
    exe = unity_game(tmp_path, 'd3d11.dll')
    assert detect_graphics_api(exe, tmp_path, launch, '848450')['api'] == 'auto'


@pytest.mark.parametrize('launch', ['NOTE="-force-d3d12" %command%',
                                  'sh -c "%command% -force-d3d12"'])
def test_unrelated_strings_are_not_launch_flags(tmp_path, launch):
    exe = unity_game(tmp_path, 'd3d11.dll')
    assert detect_graphics_api(exe, tmp_path, launch)['api'] == 'dx11'


def test_dependency_cycle_wrong_arch_and_proxy_do_not_change_api(tmp_path):
    exe = tmp_path / 'game.exe'; exe.write_bytes(image('engine.dll', 'd3d11.dll', 'other.dll', 'dxgi.dll'))
    (tmp_path / 'engine.dll').write_bytes(image('engine.dll', 'd3d11.dll'))
    (tmp_path / 'other.dll').write_bytes(image('d3d12.dll', bits=32))
    (tmp_path / 'd3d11.dll').write_bytes(image('d3d12.dll'))
    (tmp_path / 'dxgi.dll').write_bytes(image('d3d12.dll'))
    assert detect_graphics_api(exe, tmp_path)['api'] == 'dx11'


def test_dependency_cannot_escape_root_or_follow_symlinks(tmp_path):
    root = tmp_path / 'game'; root.mkdir()
    exe = root / 'game.exe'; exe.write_bytes(image('engine.dll'))
    outside = tmp_path / 'engine.dll'; outside.write_bytes(image('d3d12.dll'))
    (root / 'engine.dll').symlink_to(outside)
    assert detect_graphics_api(exe, root)['api'] == 'auto'
    assert detect_graphics_api(outside, root)['api'] == 'auto'


def test_engine_scan_validate_context_and_plan_use_same_detector(packages):
    e, p, root, _ = packages
    exe = unity_game(root, 'd3d11.dll')
    p.update(exe=str(exe), api='auto')
    assert next(c for c in e.scan('123')['candidates'] if c['path'] == str(exe))['api'] == 'dx11'
    launch = '%command% -force-d3d12'
    assert e.detect_api(p, launch)['api'] == 'dx12'
    assert e.validate(p, launch)['api'] == 'dx12'
    plan = e.plan(p, launch)
    assert not plan['blockers'] and plan['profile']['api'] == 'dx12'
    assert not e.wine_context(p, launch)['blockers']
    p['api'] = 'dx11'
    assert e.validate(p, launch)['api'] == 'dx11'


def test_legacy_shader_pack_pins_actual_legacy_branch(packages, monkeypatch, tmp_path):
    e, *_ = packages
    calls = []; commit = 'a' * 40
    def metadata(url):
        calls.append(url)
        assert url.endswith('/commits/legacy')
        return {'sha': commit}
    def download(url, target, progress):
        assert url.endswith('/zip/' + commit)
        with zipfile.ZipFile(target, 'w') as archive:
            archive.writestr('shaders/Shaders/Legacy.fx', 'technique Legacy {}')
        return {'sha256': sha256(target)}
    monkeypatch.setattr(downloads, 'get_json', metadata)
    monkeypatch.setattr(downloads, 'download', download)
    installed = e.packages.install_shader_pack('legacy', lambda *_: None)
    assert installed['commit'] == commit and Path(installed['path']).is_dir()
    assert calls == ['https://api.github.com/repos/crosire/reshade-shaders/commits/legacy']


def session_proc(tmp_path, name='steam'):
    procroot = tmp_path / 'proc'; procroot.mkdir()
    proc = procroot / '12'; proc.mkdir()
    executable = tmp_path / name; executable.touch()
    (proc / 'exe').symlink_to(executable)
    (proc / 'environ').write_bytes(b'DISPLAY=:9\0XAUTHORITY=/session/auth\0XDG_RUNTIME_DIR=/run/user/123\0'
        b'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/123/bus\0WINEDLLOVERRIDES=bad\0SECRET=private\0')
    return procroot


def test_missing_session_environment_uses_same_user_steam_allowlist(tmp_path):
    proc = session_proc(tmp_path)
    original = {'PATH': '/usr/bin'}
    env = steam_session_environment(original, os.geteuid(), proc)
    assert env['DISPLAY'] == ':9' and env['XAUTHORITY'] == '/session/auth'
    assert env['DBUS_SESSION_BUS_ADDRESS'] == 'unix:path=/run/user/123/bus'
    assert 'SECRET' not in env and 'WINEDLLOVERRIDES' not in env
    assert original == {'PATH': '/usr/bin'}
    assert steam_session_environment(original, os.geteuid() + 1, proc) == original
    assert steam_session_environment({'DISPLAY': ':2'}, os.geteuid(), proc) == {'DISPLAY': ':2'}


def test_session_environment_ignores_other_processes(tmp_path):
    assert steam_session_environment({}, os.geteuid(), session_proc(tmp_path, 'other')) == {}


def test_runner_exposes_actual_stderr_and_keeps_final_output_after_limit(runtime_env, tmp_path, monkeypatch):
    *_, manager, _ = runtime_env
    import fusion_prereqs
    monkeypatch.setattr(fusion_prereqs, 'MAX_LOG', 128)
    log = tmp_path / 'installer.log'
    command = [sys.executable, '-c', 'import sys; print("x"*20000); print("SIMULATED checksum mismatch",file=sys.stderr); sys.exit(1)']
    # Python's buffered stdout can arrive after stderr; unbuffer it for a final marker.
    command.insert(1, '-u')
    with pytest.raises(FusionError, match='SIMULATED checksum mismatch') as caught:
        manager.execute(command, os.environ.copy(), log, lambda *_: None, timeout=3)
    assert 'do not bypass' in str(caught.value)
    assert 'SIMULATED checksum mismatch' in log.read_text()
    assert log.stat().st_size < 18000


def test_runtime_error_preserves_unknown_cause_and_strips_terminal_codes():
    result = installer_error(1, '\x1b[31mSIMULATED unknown failure\x1b[0m', '/example/log')
    assert 'SIMULATED unknown failure' in result and '\x1b' not in result
    assert 'display session' not in result and 'checksum' not in result
