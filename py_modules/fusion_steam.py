from __future__ import annotations
import os
import re
import shlex
import struct
from pathlib import Path
from typing import Any
from fusion_util import FusionError


def parse_vdf(text: str) -> dict:
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|//[^\n]*|[{}]|[^\s{}"]+', text)
    tokens = [t for t in tokens if not t.startswith('//')]
    index = 0
    def decode(s: str) -> str:
        if s.startswith('"'):
            return re.sub(r'\\([\\"])', r'\1', s[1:-1])
        return s
    def obj(nested: bool = False) -> dict:
        nonlocal index
        out = {}
        while index < len(tokens):
            key = tokens[index]; index += 1
            if key == '}':
                if not nested: raise FusionError('Unexpected closing brace in Steam manifest')
                return out
            if index >= len(tokens): raise FusionError('Truncated Steam manifest')
            value = tokens[index]; index += 1
            out[decode(key)] = obj(True) if value == '{' else decode(value)
        if nested: raise FusionError('Unclosed Steam manifest')
        return out
    return obj()


def binary_vdf(data: bytes) -> dict:
    pos = 0
    def cstr() -> str:
        nonlocal pos
        end = data.find(b'\0', pos)
        if end < 0: raise FusionError('Truncated shortcuts file')
        s = data[pos:end].decode('utf-8', 'replace'); pos = end + 1
        return s
    def obj(depth: int = 0) -> dict:
        nonlocal pos
        if depth > 24: raise FusionError('Shortcuts file nesting is too deep')
        out = {}
        while pos < len(data):
            typ = data[pos]; pos += 1
            if typ in (8, 11): return out
            key = cstr()
            if typ == 0: value = obj(depth + 1)
            elif typ == 1: value = cstr()
            elif typ in (2, 3, 4, 6):
                if pos + 4 > len(data): raise FusionError('Truncated shortcut value')
                value = struct.unpack_from('<I', data, pos)[0]; pos += 4
            elif typ == 7:
                value = struct.unpack_from('<Q', data, pos)[0]; pos += 8
            else: raise FusionError(f'Unsupported shortcut field type {typ}')
            out[key] = value
        return out
    return obj()


def steam_roots(home: Path) -> list[Path]:
    roots = []
    for p in (home / '.steam/steam', home / '.local/share/Steam', home / '.steam/root'):
        if p.is_dir() and p.resolve() not in roots: roots.append(p.resolve())
    return roots


def libraries(home: Path) -> list[Path]:
    result = list(steam_roots(home))
    for root in list(result):
        f = root / 'steamapps/libraryfolders.vdf'
        if not f.exists(): continue
        try:
            data = parse_vdf(f.read_text('utf-8')).get('libraryfolders', {})
            for key, value in data.items():
                if not str(key).isdigit(): continue
                value = value.get('path') if isinstance(value, dict) else value
                if value:
                    p = Path(value).resolve()
                    if p.is_dir() and p not in result: result.append(p)
        except (OSError, FusionError): continue
    return result


def installed_games(home: Path, include_shortcuts: bool = False) -> list[dict]:
    result = {}
    for library in libraries(home):
        for manifest in (library / 'steamapps').glob('appmanifest_*.acf'):
            try:
                d = parse_vdf(manifest.read_text('utf-8'))['AppState']
                appid = str(d['appid'])
                root = library / 'steamapps/common' / d['installdir']
                if not appid.isdigit() or not root.is_dir(): continue
                result[appid] = {'appid': appid, 'name': d['name'], 'root': str(root.resolve()),
                                  'library': str(library), 'kind': 'steam', 'manifest': str(manifest)}
            except (OSError, KeyError, FusionError): continue
    for root in steam_roots(home) if include_shortcuts else ():
        for f in (root / 'userdata').glob('*/config/shortcuts.vdf'):
            try:
                if f.stat().st_size > 32 * 1024 * 1024: continue
                shortcuts = binary_vdf(f.read_bytes()).get('shortcuts', {})
                for d in shortcuts.values():
                    if not isinstance(d, dict) or 'appid' not in d: continue
                    d = {k.lower(): v for k, v in d.items()}
                    appid = str(int(d['appid']) & 0xffffffff)
                    exe = str(d.get('exe', '')).strip('"')
                    if not Path(exe).is_file(): continue
                    result.setdefault(appid, {'appid': appid, 'name': d.get('appname', Path(exe).stem),
                        'root': str(Path(exe).resolve().parent), 'exe': str(Path(exe).resolve()), 'kind': 'shortcut'})
            except (OSError, FusionError, ValueError, struct.error): continue
    return sorted(result.values(), key=lambda x: x['name'].casefold())


def pe_info(path: Path) -> dict:
    """Read PE headers and imports by bounded seek, not a truncated image copy.

    Large game images commonly put the import table far beyond 4 MB. Even an
    unavailable/malformed import directory must not erase valid PE architecture.
    """
    unknown = {'kind': 'unknown', 'bits': 0, 'imports': [], 'api': 'auto'}
    try:
        with path.open('rb') as f:
            size = os.fstat(f.fileno()).st_size
            def read_at(offset, length):
                if offset < 0 or length < 0 or length > 65536 or offset + length > size:
                    raise ValueError('Header or import data lies outside the file')
                f.seek(offset)
                value = f.read(length)
                if len(value) != length: raise ValueError('Truncated executable')
                return value
            header = read_at(0, min(size, 64))
            if header[:4] == b'\x7fELF' and len(header) >= 16 and header[4] in (1, 2):
                return {'kind': 'elf', 'bits': 64 if header[4] == 2 else 32, 'imports': [], 'api': 'auto'}
            if header[:2] != b'MZ' or len(header) < 64: return unknown
            off = struct.unpack_from('<I', header, 0x3c)[0]
            coff = read_at(off, 24)
            if coff[:4] != b'PE\0\0': return unknown
            machine, sections = struct.unpack_from('<HH', coff, 4)
            optional_size = struct.unpack_from('<H', coff, 20)[0]
            if not 96 <= optional_size <= 4096 or not 1 <= sections <= 96: return unknown
            optional = read_at(off + 24, optional_size)
            magic = struct.unpack_from('<H', optional)[0]
            bits = 64 if machine == 0x8664 and magic == 0x20b else (32 if machine == 0x14c and magic == 0x10b else 0)
            if not bits: return unknown
            result = {'kind': 'pe', 'bits': bits, 'imports': [], 'api': 'auto'}
            try:
                mappings = []
                for n in range(sections):
                    section = read_at(off + 24 + optional_size + n * 40, 40)
                    virtual_size, address, raw_size, raw_offset = struct.unpack_from('<IIII', section, 8)
                    mappings.append((address, raw_size, raw_offset))
                header_size = struct.unpack_from('<I', optional, 60)[0]
                def rva(value, length=1):
                    for address, raw_size, raw_offset in mappings:
                        if address <= value and value + length <= address + raw_size:
                            return raw_offset + value - address
                    if value + length <= header_size: return value
                    raise ValueError('Unmapped import RVA')
                directories = 112 if bits == 64 else 96
                for directory_index, delay in ((1, False), (13, True)):
                    at = directories + directory_index * 8
                    if at + 8 > len(optional): continue
                    address, table_size = struct.unpack_from('<II', optional, at)
                    if not address: continue
                    row_size = 32 if delay else 20
                    # Some linkers omit directory size. Bound iteration in either case.
                    rows = min(256, table_size // row_size if table_size else 256)
                    for n in range(rows):
                        row = struct.unpack('<' + 'I' * (row_size // 4), read_at(rva(address + n * row_size, row_size), row_size))
                        if not any(row): break
                        if delay:
                            if not row[0] & 1: continue  # Old VA-based delay imports: no unsafe guess.
                            name_rva = row[1]
                        else: name_rva = row[3]
                        pos = rva(name_rva)
                        f.seek(pos); name = f.read(min(256, max(0, size - pos))).split(b'\0', 1)[0]
                        if not name or len(name) >= 256: continue
                        dll = name.decode('ascii', 'strict').lower()
                        if dll not in result['imports']: result['imports'].append(dll)
            except (OSError, ValueError, struct.error, UnicodeError):
                result['imports_incomplete'] = True
            result['api'] = next((api for dll, api in (
                ('d3d12.dll', 'dx12'), ('d3d11.dll', 'dx11'), ('d3d10.dll', 'dx10'),
                ('d3d9.dll', 'dx9'), ('vulkan-1.dll', 'vulkan'), ('opengl32.dll', 'opengl'))
                if dll in result['imports']), 'auto')
            return result
    except (OSError, ValueError, struct.error):
        return unknown

ANTI = ('easyanticheat', 'easyanticheat_eos', 'battleye', 'beservice', 'eac_launcher', 'start_protected_game', 'vgk.sys', 'vgc.exe')
SKIP = {'_commonredist', 'redist', 'redistributables', 'crashreporter', '.git', 'node_modules', 'deck-fusion-shaders', '.deck-fusion'}
SUPPORT_NAMES = ('errorreporter', 'crashreporter', 'crashreportclient', 'unitycrashhandler',
                 'cefsubprocess', 'vcredist', 'vc_redist', 'dxsetup', 'unins')
PRIORITY_DIRS = {'bin': 0, 'binaries': 0, 'x64': 0, 'win64': 0, 'win32': 1, 'x86': 1,
                 'retail': 1, 'game': 2, 'engine': 8, 'content': 9, 'archive': 10, 'data': 10}


def scan_game(root: Path) -> dict:
    root = root.resolve()
    candidates, anticheat, oldmods, warnings = [], [], [], []
    count = 0
    truncated = False
    def walk_error(error):
        warnings.append(f'Could not read {error.filename}: {error.strerror}')
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        relative = Path(directory).relative_to(root)
        dirs[:] = [d for d in dirs if not (Path(directory) / d).is_symlink()]
        for name in dirs + files:
            low = name.lower()
            if any(low.startswith(x) or low == x for x in ANTI): anticheat.append(str(relative / name))
        if len(relative.parts) >= 12:
            if dirs: truncated = True
            dirs[:] = []
        dirs[:] = sorted((d for d in dirs if d.lower() not in SKIP),
                         key=lambda d: (PRIORITY_DIRS.get(d.casefold(), 5), d.casefold()))
        for name in sorted(files, key=lambda n: (not n.lower().endswith('.exe'), n.casefold())):
            count += 1
            if count > 150000:
                truncated = True; break
            p = Path(directory) / name
            if p.is_symlink(): continue
            low = name.lower()
            if low in ('dxgi.dll', 'winmm.dll', 'version.dll', 'nvapi64.dll', 'nvngx.dll', 'reshade64.dll'):
                oldmods.append(str(relative / name))
            if not low.endswith('.exe') and not (os.access(p, os.X_OK) and '.' not in name): continue
            info = pe_info(p)
            if info['kind'] == 'unknown': continue
            support = any(x in low for x in SUPPORT_NAMES) or low in ('setup.exe', 'install.exe', 'uninstall.exe')
            launcher = 'launcher' in low
            score = 10 + (60 if 'shipping' in low else 0) + (20 if info['bits'] == 64 else 0)
            if info['api'] != 'auto': score += 15
            if launcher: score -= 80
            if support: score -= 200
            if any(x.casefold() in {'win64','x64'} for x in relative.parts): score += 25
            if not relative.parts: score += 10
            candidates.append({'path': str(p), 'relative': str(p.relative_to(root)), 'score': score,
                               'support': support, 'launcher': launcher, **info})
        if count > 150000: break
    return {'candidates': sorted(candidates, key=lambda x: (-x['score'], x['relative'].casefold())),
            'anticheat': sorted(set(anticheat)), 'existing_mods': oldmods[:100],
            'truncated': truncated, 'warnings': warnings[:20]}


def running_game(exe: Path, appid: str, procroot: Path = Path('/proc')) -> dict:
    target = str(exe.resolve()).replace('\\', '/').casefold()
    basename = exe.name.casefold()
    found, denied = [], 0
    ignored = {'wineserver', 'wineserver64', 'steam', 'steamwebhelper', 'pressure-vessel-wrap', 'pv-bwrap',
               'bash', 'sh', 'python', 'python3', 'reaper', 'steam-runtime-launch-client'}
    for proc in procroot.iterdir():
        if not proc.name.isdigit(): continue
        try:
            raw = (proc / 'cmdline').read_bytes()
            args = [s.decode('utf-8', 'replace') for s in raw.split(b'\0') if s]
            if not args: continue
            first = Path(args[0].replace('\\', '/')).name.casefold()
            if first in ignored: continue
            try:
                environment = (proc / 'environ').read_bytes().split(b'\0')
                own_id = any(s in (f'SteamAppId={appid}'.encode(), f'SteamGameId={appid}'.encode()) for s in environment)
            except (PermissionError, FileNotFoundError): own_id = False
            normalized = [s.replace('\\', '/').casefold().strip('"') for s in args]
            exact = any(s == target or s == 'z:' + target for s in normalized)
            named = own_id and any(s.rsplit('/', 1)[-1] == basename for s in normalized)
            try: direct = str((proc / 'exe').resolve()).casefold() == target
            except OSError: direct = False
            if exact or named or direct:
                found.append({'pid': int(proc.name), 'process': first, 'evidence': 'executable path' if exact or direct else 'executable name + exact Steam app ID'})
        except PermissionError: denied += 1
        except (FileNotFoundError, ProcessLookupError, OSError): continue
    return {'running': bool(found), 'processes': found, 'unreadable_processes': denied,
            'note': 'Only a matching executable counts. Steam, Proton helpers and wineserver alone do not.'}


def running_appids(games, procroot=Path('/proc')):
    """A startup selection hint, never authorization to mutate a running game."""
    roots = {str(g['appid']): Path(g['root']).resolve() for g in games}
    found = set()
    ignored = {'steam', 'steamwebhelper', 'wineserver', 'wineserver64', 'proton',
               'bash', 'sh', 'python', 'python3', 'reaper', 'pressure-vessel-wrap',
               'pv-bwrap', 'steam-runtime-launch-client'}
    try: processes = list(procroot.iterdir())
    except OSError: return []
    for proc in processes:
        if not proc.name.isdigit(): continue
        try:
            args = [a.decode('utf-8', 'replace') for a in (proc/'cmdline').read_bytes().split(b'\0') if a]
            if not args or Path(args[0].replace('\\', '/')).name.casefold() in ignored: continue
            env = dict(field.split(b'=', 1) for field in (proc/'environ').read_bytes().split(b'\0') if b'=' in field)
            ids = {env.get(key, b'').decode('ascii', 'ignore') for key in (b'SteamAppId', b'SteamGameId', b'STEAM_APPID')}
            for appid in ids & roots.keys():
                paths = [a.replace('\\', '/').strip('"') for a in args]
                try: paths.append(str((proc/'exe').resolve(strict=True)))
                except OSError: pass
                if any(Path(a[2:] if a.lower().startswith('z:/') else a).is_relative_to(roots[appid]) for a in paths):
                    found.add(appid)
        except (OSError, ValueError): continue
    return sorted(found)
