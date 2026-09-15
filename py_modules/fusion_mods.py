"""Read-only Cyberpunk mod evidence. File presence is not a load/compatibility test.

Only fixed game-relative paths are inspected; nothing is executed, installed,
renamed, repaired or removed. Logs are bounded and shown with their timestamps.
"""
from __future__ import annotations
from pathlib import Path
import re
from fusion_util import FusionError, safe_target, read_json


def cyberpunk_diagnostics(root: Path, exe: str, store: Path) -> dict:
    root = root.resolve()
    if Path(exe).name.casefold() != 'cyberpunk2077.exe':
        raise FusionError('Select Cyberpunk2077.exe to inspect the Cyberpunk mod framework files.')
    manifest = read_json(store / 'manifest.json', {}).get('files', {})
    managed = {name.casefold(): value for name, value in manifest.items()}
    launch = read_json(store / 'last-launch.json', {})
    launched = launch.get('time')
    if not isinstance(launched, (float, int)): launched = None
    notes = []

    def artifact(relative):
        try:
            f = safe_target(root, relative)
            return {'path': relative, 'present': f.is_file(),
                    'managed': relative.casefold() in managed,
                    'note': 'Deck Fusion tracks this file; its name alone does not identify a mod loader.'
                            if relative.casefold() in managed else ''}
        except (OSError, FusionError) as error:
            return {'path': relative, 'present': False, 'managed': False, 'note': str(error)}

    def names(relative, folders_only=False):
        try:
            folder = safe_target(root, relative)
            if not folder.is_dir(): return []
            result = []
            for i, child in enumerate(folder.iterdir()):
                if i >= 4096:
                    notes.append(f'{relative}: directory scan stopped after 4096 entries.')
                    break
                if child.is_symlink() or (folders_only and not child.is_dir()): continue
                if child.is_dir() or child.is_file(): result.append(child.name)
            return sorted(result, key=str.casefold)
        except (OSError, FusionError) as error:
            notes.append(f'{relative}: {error}'); return []

    frameworks = [
        {'name':'Cyber Engine Tweaks', 'files':[artifact('bin/x64/version.dll'), artifact('bin/x64/plugins/cyber_engine_tweaks.asi')],
         'children':names('bin/x64/plugins/cyber_engine_tweaks/mods', True),
         'note':'CET loads its own Lua mods. A working CET overlay does not prove RED4ext or redscript is running.'},
        {'name':'RED4ext', 'files':[artifact('bin/x64/winmm.dll'), artifact('red4ext/RED4ext.dll')],
         'children':names('red4ext/plugins'),
         'note':'The normal loader is winmm.dll; native plugins go under red4ext/plugins. They are not extra Wine proxy DLLs.'},
        {'name':'redscript', 'files':[artifact('engine/tools/scc.exe'), artifact('engine/config/base/scripts.ini')],
         'children':names('r6/scripts'),
         'note':'Compiler and script inventory only. Overrides cannot fix script compilation errors, missing dependencies or mismatched game/mod versions.'},
    ]
    log_paths = [('CET','bin/x64/plugins/cyber_engine_tweaks/cyber_engine_tweaks.log'),
                 ('CET scripts','bin/x64/plugins/cyber_engine_tweaks/scripting.log'),
                 ('RED4ext','red4ext/logs/red4ext.log')]
    # Select the most recently modified redscript log, without following symlinks.
    redlogs = []
    for name in names('r6/logs'):
        if name.casefold().startswith('redscript') and name.casefold().endswith('.log'):
            try:
                f = safe_target(root, 'r6/logs/' + name)
                if f.is_file(): redlogs.append((f.stat().st_mtime, 'r6/logs/' + name))
            except (OSError, FusionError) as error:
                notes.append(f'r6/logs/{name}: {error}')
    if redlogs: log_paths.append(('redscript', max(redlogs)[1]))
    else:
        # Older redscript installations use this documented cache log path.
        legacy = artifact('r6/cache/redscript.log')
        log_paths.append(('redscript', 'r6/cache/redscript.log' if legacy['present'] else 'r6/logs/redscript_rCURRENT.log'))
    logs = []
    for label, relative in log_paths:
        result = {'name':label, 'path':relative, 'present':False, 'modified':None,
                  'current_launch':None, 'tail':'', 'error_lines':[]}
        try:
            f = safe_target(root, relative)
            if f.is_file():
                stat = f.stat()
                with f.open('rb') as handle:
                    start = max(0, stat.st_size - 12288)
                    handle.seek(start); data = handle.read(12288)
                # Drop a potentially partial first line when taking a tail.
                lines = data.decode('utf-8', errors='replace').splitlines()
                if start and lines: lines = lines[1:]
                tail = '\n'.join(lines[-60:])
                result.update(present=True, modified=stat.st_mtime, size=stat.st_size,
                              current_launch=(stat.st_mtime >= launched - 2) if launched else None,
                              tail=tail,
                              error_lines=[line for line in lines if re.search(r'\berror\b|\bfatal\b|\bfailed\b', line, re.I)][-8:])
        except (OSError, FusionError) as error:
            result['note'] = str(error)
        logs.append(result)
    return {'frameworks':frameworks, 'logs':logs, 'last_launch_time':launched, 'notes':notes,
            'note':'Read-only evidence, not a running-mod verdict. Log messages may be historical; timestamps are shown. No mods, runtimes, scripts or overrides were changed.'}
