#!/usr/bin/env python3
"""Persistent, fail-open launch wrapper. Runs as the game user, never as root."""
from __future__ import annotations
import fcntl
import json
import os
from pathlib import Path
import sys
import time
from fusion_launch import launch_environment, bg3_command


def main(argv: list[str]) -> int:
    if len(argv) < 4 or not argv[1].isdigit() or argv[2] != '--':
        print('Deck Fusion: expected <appid> -- <game command>', file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parent.parent
    command = argv[3:]
    env = dict(os.environ)
    # While maintenance owns this per-game lock, do not launch into a prefix
    # being modified. No global Steam setting or other game is affected.
    lock_path = root / 'profiles' / argv[1] / 'prefix-maintenance.lock'
    if lock_path.exists():
        try:
            with lock_path.open('r') as handle:
                try: fcntl.flock(handle.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                except BlockingIOError:
                    print('Deck Fusion: this game has a prefix runtime operation in progress. Wait or cancel it in Runtimes.', file=sys.stderr)
                    return 75
        except OSError as error:
            print(f'Deck Fusion: cannot verify the runtime maintenance lock: {error}', file=sys.stderr)
            return 75
    try:
        cfg = json.loads((root / 'profiles' / argv[1] / 'runtime.json').read_text())
        # A crash between file installation and Steam option commit is recoverable:
        # the wrapper still launches the game, and pending journals remain inspectable.
        env = launch_environment(cfg, env)
        command, renderer_note = bg3_command(cfg, command)
        log = root / 'profiles' / argv[1] / 'last-launch.json'
        summary = {'command_executable': command[0], 'settings': {k: env.get(k) for k in (
            'WINEDLLOVERRIDES', 'DECK_FUSION_LSFG', 'LSFGVK_CONFIG', 'DXVK_FRAME_RATE', 'VKD3D_FRAME_RATE', 'PROTON_ENABLE_NVAPI', 'ENABLE_GAMESCOPE_WSI', 'DISABLE_GAMESCOPE_WSI', 'GAMESCOPE_WSI_FRAME_LIMITER_AWARE', 'GAMESCOPE_WAYLAND_DISPLAY', 'GAMESCOPE_LIMITER_FILE', 'MESA_VK_WSI_PRESENT_MODE', 'PROTON_FSR4_INDICATOR', 'FSR4_WATERMARK', 'FSR_WATERMARK', 'MLSR-WATERMARK')}}
        summary['wrapper_version'] = '0.3-beta5'
        summary['time'] = time.time()
        summary['renderer'] = renderer_note
        if renderer_note: print('Deck Fusion: ' + renderer_note, file=sys.stderr)
        summary['watermark_strategy'] = 'SDK variable absent when off; paired OptiScaler INI uses auto'
        summary['limiter_route_requested'] = ('mesa-fifo-without-gamescope-wsi'
            if not cfg.get('bypass') and cfg.get('lsfg', {}).get('enabled') and cfg.get('lsfg', {}).get('respect_deck_limiter')
            and (env.get('GAMESCOPE_WAYLAND_DISPLAY') or env.get('GAMESCOPE_LIMITER_FILE')) else 'unchanged')
        summary['note'] = 'Launch environment only. Not a measurement of displayed or generated FPS.'
        try: log.write_text(json.dumps(summary, indent=2))
        except OSError: pass
    except Exception as e:
        print(f'Deck Fusion: configuration unavailable, launching without added environment: {e}', file=sys.stderr)
    try: os.execvpe(command[0], command, env)
    except OSError as e:
        print(f'Deck Fusion: cannot execute game command: {e}', file=sys.stderr)
        return 127
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
