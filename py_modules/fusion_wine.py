"""Read-only Wine/loader inspection and conservative allocation of proxy names.

No DLL is force-loaded by this module. WINEDLLOVERRIDES chooses how Wine handles
an import/LoadLibrary request; an arbitrary DLL still needs a real loader.
"""
from __future__ import annotations
import copy
from collections import Counter
import re
from pathlib import Path
from fusion_launch import launch_assignments, parse_dll_overrides, override_name
from fusion_steam import libraries, pe_info
from fusion_util import FusionError, read_json
from fusion_api import bg3_renderer

OPTI_PROXIES = ('dxgi', 'winmm', 'version', 'winhttp', 'wininet', 'dbghelp', 'd3d12')
RESH_PROXIES = {'dx9': ('d3d9',), 'dx10': ('dxgi', 'd3d10'), 'dx11': ('dxgi', 'd3d11'),
                'dx12': ('dxgi', 'd3d12'), 'opengl': ('opengl32',)}


def module_basename(name: str) -> str:
    # Wine allows wildcard/path-specific inherited rules. Reserve conservatively
    # even if the exact requested path may differ at runtime.
    return override_name(name.replace('\\', '/').rsplit('/', 1)[-1]).lstrip('*')


def registry_entries(prefix: Path, exe: str) -> tuple[list, list]:
    found, warnings = [], []
    target = f'software\\wine\\appdefaults\\{exe}\\dlloverrides'.casefold()
    # HKCU takes precedence. HKLM entries are shown/reserved conservatively too.
    for filename in ('system.reg', 'user.reg'):
        f = prefix / filename
        if not f.is_file(): continue
        if f.stat().st_size > 24 * 1024 * 1024:
            warnings.append(f'{filename} exceeds the 24 MB read limit; not fully inspected.')
            continue
        scope = None
        try:
            with f.open(encoding='utf-8', errors='replace') as handle:
                for line in handle:
                    if line.startswith('['):
                        section = line[1:].split(']', 1)[0].replace('\\\\', '\\').casefold()
                        scope = 'game' if section == target else 'global' if section == 'software\\wine\\dlloverrides' else None
                    if not scope: continue
                    m = re.match(r'^"((?:[^"\\]|\\.)*)"="((?:[^"\\]|\\.)*)"', line)
                    if not m: continue
                    name, value = (re.sub(r'\\([\\"])', r'\1', x) for x in m.groups())
                    parsed = parse_dll_overrides(name + '=' + value)
                    for key, order in parsed.items():
                        found.append({'name': key, 'order': order, 'scope': scope,
                                      'source': f'{filename} · {scope}', 'prefix': str(prefix)})
        except (OSError, FusionError) as error:
            warnings.append(f'Cannot completely inspect {filename}: {error}')
    return found, warnings


def inspect_overrides(engine, raw: dict, launch: str) -> dict:
    game = engine.game(raw['appid']); root = Path(game['root']).resolve()
    exe = Path(raw.get('exe') or '').expanduser()
    if not exe.is_absolute(): exe = root / exe
    if not exe.is_file() or not exe.resolve().is_relative_to(root):
        raise FusionError('Select the actual game executable before inspecting its DLL overrides.')
    exe = exe.resolve(); parent = exe.parent
    assignments = launch_assignments(launch)
    text = assignments.get('WINEDLLOVERRIDES', '')
    inherited = parse_dll_overrides(text)
    wine = raw.get('wine') or {}
    if not isinstance(wine, dict): raise FusionError('Invalid custom Wine settings.')
    custom = parse_dll_overrides(wine.get('custom_overrides', ''), strict=True)
    reserved: dict[str, list[str]] = {}
    def reserve(name, reason):
        key = module_basename(name)
        reserved.setdefault(key, [])
        if reason not in reserved[key]: reserved[key].append(reason)
    for name in inherited: reserve(name, 'Steam launch override')
    for name in custom: reserve(name, 'Custom override')
    prefixes = []
    warnings = []
    libs = libraries(engine.home)
    explicit = assignments.get('WINEPREFIX') or assignments.get('STEAM_COMPAT_DATA_PATH')
    if explicit:
        candidate = Path(explicit).expanduser()
        if not assignments.get('WINEPREFIX'): candidate /= 'pfx'
        if ('$' in str(candidate) or not candidate.is_absolute() or
            not any(candidate.resolve().is_relative_to(base.resolve()) for base in [engine.home] + libs)):
            warnings.append('Custom Wine prefix is not a literal path under your home or Steam libraries; its registry was not inspected.')
        elif candidate.is_dir(): prefixes.append(candidate.resolve())
        else: warnings.append('The explicitly selected Wine prefix does not exist yet.')
    else:
        ordered = ([Path(game['library'])] if game.get('library') else []) + libs
        for lib in ordered:
            candidate = (lib / 'steamapps/compatdata' / str(raw['appid']) / 'pfx').resolve()
            if candidate.is_dir() and candidate not in prefixes: prefixes.append(candidate)
    registry = []
    for prefix in prefixes:
        entries, notes = registry_entries(prefix, exe.name)
        registry.extend(entries); warnings.extend(notes)
    if len(prefixes) > 1:
        warnings.append('Multiple matching Wine prefixes found. All their override names are protected; the active prefix cannot be proved from launch text alone.')
    for item in registry: reserve(item['name'], item['source'])
    manifest = read_json(engine.store(raw['appid']) / 'manifest.json', {'files': {}})
    managed = {rel.casefold(): meta for rel, meta in manifest.get('files', {}).items()}
    game_bits = pe_info(exe)['bits']
    imports = {override_name(name) for name in pe_info(exe)['imports']}
    files = []
    candidates = sorted((x for x in parent.iterdir() if x.suffix.casefold() == '.dll'), key=lambda x: x.name.casefold())
    counts = Counter(override_name(f.name) for f in candidates)
    ambiguous = {name for name, count in counts.items() if count > 1}
    if ambiguous:
        warnings.append('Ambiguous case-variant DLL files: ' + ', '.join(sorted(ambiguous)) + '. They are not offered as additional loaders.')
        if any(module_basename(name) in ambiguous for name in custom):
            raise FusionError('A custom override matches multiple case-variant DLL files. Resolve those duplicate files before adding its load override.')
    for f in candidates:
        rel = f.relative_to(root).as_posix(); meta = managed.get(rel.casefold())
        external = not meta or bool(meta.get('before'))
        if external: reserve(f.stem, 'Existing DLL / backed-up original')
        safe = f.is_file() and not f.is_symlink() and f.resolve().is_relative_to(root)
        info = pe_info(f) if safe else {'bits': 0, 'kind': 'unknown'}
        backed = bool(meta and meta.get('before'))
        if backed:
            backup = engine.store(raw['appid']) / 'originals' / meta['before']
            if backup.is_file(): info = pe_info(backup)
        stamp = f.lstat()
        files.append({'stat': {'size': stamp.st_size, 'mtime_ns': stamp.st_mtime_ns,
                               'ctime_ns': stamp.st_ctime_ns, 'inode': stamp.st_ino},
                      'name': f.name, 'module': override_name(f.name), 'relative': rel,
                      'bits': info['bits'], 'managed': bool(meta), 'original': backed,
                      'imported': override_name(f.name) in imports,
                      'selectable': override_name(f.name) not in ambiguous and external and safe and info['kind'] == 'pe' and info['bits'] == game_bits,
                      'description': 'Ambiguous case-variant DLL filename' if override_name(f.name) in ambiguous else
                                     'Backed-up original (restored when graphics loader moves)' if backed else
                                     'Managed by Deck Fusion' if meta else
                                     'Architecture mismatch / not a supported PE DLL' if not safe or info['bits'] != game_bits else
                                     'Imported by executable' if override_name(f.name) in imports else
                                     'Local DLL; a game/mod import is still required'})
    # Missing managed targets can still have an original restored during this apply.
    for rel, meta in manifest.get('files', {}).items():
        f = root / rel
        if f.parent == parent and f.suffix.casefold() == '.dll' and meta.get('before'):
            reserve(f.stem, 'Backed-up original restored on loader change')
    effective = {}
    for scope in ('global', 'game'):
        for item in registry:
            if item['scope'] == scope: effective[item['name']] = item['order']
    effective.update(inherited); effective.update(custom)
    return {'launch_value': text, 'launch_overrides': inherited, 'registry': registry,
            'custom': custom, 'effective_user': effective, 'reserved': reserved,
            'files': files, 'prefixes': [str(x) for x in prefixes], 'warnings': warnings,
            'exe': str(exe), 'kind': pe_info(exe)['kind'],
            'note': 'Read-only inspection. Overrides choose native/builtin loading when a module is requested; they do not force-load arbitrary DLLs.'}


def resolve_loaders(profile: dict, effective_api: str, context: dict, force_repair=False) -> tuple[dict, list]:
    p = copy.deepcopy(profile); o, r = p['opti'], p['reshade']; fixes = []
    reserved = context['reserved']
    def taken(name): return name in reserved or '' in reserved
    def fix(obj, key, value, title, detail):
        if obj[key] != value:
            fixes.append({'id': 'dll-' + key + '-' + value, 'title': title, 'detail': detail,
                          'before': obj[key], 'after': value})
            obj[key] = value
    manual = p.get('wine', {}).get('opti_proxy_manual', False)
    if o['enabled'] and not manual and o['proxy'] == 'dxgi' and bg3_renderer(p.get('exe', ''), p.get('root', ''), p.get('appid', '')):
        fix(o, 'proxy', 'winmm', 'Use winmm.dll for BG3',
            'BG3 on Proton uses the winmm loader by default. ReShade shares it through OptiScaler; DLL injection lets you choose another name.')
    opts = RESH_PROXIES.get(effective_api, ())
    desired_r = (opts[0] if r['proxy'] == 'auto' and opts else r['proxy'])
    if force_repair:
        # Only the selected graphics loaders are released for replacement. The
        # transaction still snapshots existing bytes and requires the exact plan.
        replace = ({o['proxy']} if o['enabled'] else set())
        if r['mode'] == 'standalone': replace.add(desired_r)
        if r['mode'] == 'opti': replace.add('reshade64')
        reserved = {name: reasons for name, reasons in reserved.items() if name not in replace}
    if r['mode'] == 'standalone':
        if desired_r not in opts:
            raise FusionError('The selected standalone ReShade loader is not supported for this graphics API. Choose Automatic in ReShade.')
        if p.get('wine', {}).get('reshade_proxy_manual') and taken(desired_r):
            raise FusionError(f'The selected {desired_r}.dll ReShade loader is occupied. Choose another DLL in DLL injection or use Force apply settings. Your explicit selection was not changed.')
        free = next((name for name in [desired_r] + list(opts) if not taken(name)), None)
        if free is None:
            if o['enabled'] and not taken('reshade64'):
                fix(r, 'mode', 'opti', 'Load ReShade through OptiScaler',
                    'All standalone ReShade proxy names are occupied by your existing overrides or DLLs. Keep those intact and use ReShade64.dll instead.')
            else:
                raise FusionError('All supported standalone ReShade DLL names are occupied. Keep the existing mod loader; use ReShade through OptiScaler (if enabled) or turn ReShade off. No existing DLL will be replaced.')
        elif free != desired_r:
            fix(r, 'proxy', free, f'Use {free}.dll for ReShade',
                f'{desired_r}.dll is reserved by an existing override or DLL. Keep it intact.')
    if r['mode'] == 'opti' and taken('reshade64'):
        raise FusionError('ReShade64.dll is occupied by an existing override or unmanaged file. No automatic replacement of that loader is safe.')
    if o['enabled']:
        r_used = (RESH_PROXIES.get(effective_api, ('dxgi',))[0] if r['proxy'] == 'auto' else r['proxy']) if r['mode'] == 'standalone' else None
        if manual and (taken(o['proxy']) or o['proxy'] == r_used):
            raise FusionError(f'The selected {o["proxy"]}.dll loader is occupied. Choose another DLL in DLL injection, or use Force apply settings to back up and replace it. Your explicit selection was not changed.')
        choices = [o['proxy']] + list(OPTI_PROXIES)
        free = next((name for name in choices if not taken(name) and name != r_used), None)
        if free is None and r_used and not taken('reshade64') and not taken(r_used):
            fix(r, 'mode', 'opti', 'Share OptiScaler’s ReShade loader',
                'Only one free graphics proxy remains. ReShade will use its documented companion loader instead.')
            free = r_used
        if free is None:
            raise FusionError('All supported OptiScaler proxy names are reserved by existing overrides or DLL files. No mod file was replaced. Resolve the conflict in DLLs or disable OptiScaler.')
        if free != o['proxy']:
            fix(o, 'proxy', free, f'Use {free}.dll for OptiScaler',
                f'{o["proxy"]}.dll is occupied by an existing override, mod DLL or ReShade. Your original loader and its load order stay intact. Verify the alternative loads in this game.')
    return p, fixes


def guard_payload(engine, p: dict, desired: dict, context: dict, force_repair=False) -> None:
    """Do not replace custom/prefix/Steam-loaded support DLLs from a package."""
    parent = Path(p['exe']).parent
    manifest = read_json(engine.store(p['appid']) / 'manifest.json', {'files': {}})
    user_names = {module_basename(name) for name in context['effective_user']}
    for rel in desired:
        f = Path(p['root']) / rel
        if f.parent != parent or f.suffix.casefold() != '.dll': continue
        if not force_repair and (module_basename(f.name) in user_names or '' in user_names):
            raise FusionError(f'{f.name} is reserved by an existing/custom Wine override. Refusing to replace its loader with a bundled component.')
    # A dropdown must not let an existing managed proxy be mistaken for a mod
    # and then silently disappear when a different OptiScaler proxy is chosen.
    for rel, meta in manifest.get('files', {}).items():
        f = Path(p['root']) / rel
        if f.parent != parent or f.suffix.casefold() != '.dll': continue
        if rel not in desired and not meta.get('before') and module_basename(f.name) in user_names:
            raise FusionError(f'{f.name} is currently a Deck Fusion graphics DLL, not a separate mod loader. Removing it would leave a requested override without that DLL. Remove that override or restore the actual mod first.')
