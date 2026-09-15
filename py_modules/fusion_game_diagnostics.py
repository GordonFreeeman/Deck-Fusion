"""Game-independent, read-only evidence from a validated installation.

No game names/AppIDs or assumed mod frameworks. Only fixed graphics filenames
and a bounded non-recursive local inventory are read. No payload is executed.
"""
from __future__ import annotations
from pathlib import Path
import re

from fusion_steam import pe_info
from fusion_util import FusionError, read_json, safe_target


def game_diagnostics(root: Path, exe: Path, store: Path) -> dict:
    root = root.resolve()
    parent = exe.parent.relative_to(root)
    manifest = read_json(store / 'manifest.json', {}).get('files', {})
    tracked = {name.casefold() for name in manifest}
    launch = read_json(store / 'last-launch.json', {})
    launched = launch.get('time')
    if not isinstance(launched, (int, float)): launched = None
    notes = []

    def relative(name):
        return (parent / name).as_posix()

    def artifact(name):
        item = {'path': name, 'present': False, 'managed': name.casefold() in tracked}
        try:
            path = safe_target(root, name)
            item['present'] = path.is_file()
        except (OSError, FusionError) as error:
            item['note'] = str(error)
        return item

    def names(name):
        result = []
        try:
            # '.' means the authoritative, already resolved game root, not input traversal.
            folder = root if name == '.' else safe_target(root, name)
            if folder.is_dir():
                for index, item in enumerate(folder.iterdir()):
                    if index >= 4096:
                        notes.append(f'{name}: inventory limited to 4096 entries.')
                        break
                    if not item.is_symlink() and (item.is_file() or item.is_dir()):
                        result.append(item.name)
        except (OSError, FusionError) as error:
            notes.append(str(error))
        return sorted(result, key=str.casefold)

    local_dlls = [relative(name) for name in names(parent.as_posix())
                  if name.casefold().endswith(('.dll', '.asi'))]
    if len(local_dlls) > 64:
        notes.append('Local DLL/ASI evidence limited to 64 files. Use the DLLs filter for a specific loader.')
    image = pe_info(exe)
    reports = [
        {'name': 'Selected executable', 'files': [artifact(exe.relative_to(root).as_posix())],
         'children': [], 'note': f"{image['bits']}-bit {image['kind']} file. Detected rendering API: {image['api']}. Detection is a hint, not a runtime check."},
        {'name': 'Graphics configuration', 'files': [artifact(relative(name)) for name in
             ('OptiScaler.ini', 'ReShade.ini', 'DeckFusionPreset.ini')], 'children': [],
         'note': 'Optional configuration beside this executable. An absent file is not a missing game dependency.'},
        {'name': 'Local DLLs and plugins', 'files': [artifact(name) for name in local_dlls[:64]],
         'children': names(relative('plugins'))[:64],
         'note': 'File inventory only. A DLL filename does not identify a mod or prove that it loaded. Plugin entries are limited to 64.'},
    ]
    logs = []
    for label, name in (('OptiScaler', 'OptiScaler.log'), ('ReShade', 'ReShade.log')):
        name = relative(name)
        result = {'name': label, 'path': name, 'present': False, 'modified': None,
                  'current_launch': None, 'tail': '', 'error_lines': []}
        try:
            path = safe_target(root, name)
            if path.is_file():
                info = path.stat()
                start = max(0, info.st_size - 12288)
                with path.open('rb') as handle:
                    handle.seek(start)
                    lines = handle.read(12288).decode('utf-8', 'replace').splitlines()
                if start and lines: lines = lines[1:]
                result.update(present=True, modified=info.st_mtime, size=info.st_size,
                              current_launch=(info.st_mtime >= launched - 2) if launched else None,
                              tail='\n'.join(lines[-60:]),
                              error_lines=[line for line in lines if re.search(r'\berror\b|\bfatal\b|\bfailed\b', line, re.I)][-8:])
        except (OSError, FusionError) as error:
            result['note'] = str(error)
        logs.append(result)
    return {'title': 'Game files and logs', 'frameworks': reports, 'logs': logs,
            'last_launch_time': launched, 'notes': notes,
            'note': 'Read-only evidence from the selected executable’s folder. Logging may be disabled or use a custom path; missing logs do not prove a failure. Historical log messages are not a current game/mod verdict. No files, runtimes or settings were changed.'}
