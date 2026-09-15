"""Read-only renderer hints. Never load a DLL or execute launch options.

An engine may support several renderers. Imports prove availability, not which
backend is active. Ambiguous results require an explicit selection in setup.
"""
from pathlib import Path
import re
import shlex

from fusion_steam import pe_info

API_DLLS = {'d3d9.dll': 'dx9', 'd3d10.dll': 'dx10', 'd3d10_1.dll': 'dx10',
            'd3d11.dll': 'dx11', 'd3d12.dll': 'dx12',
            'vulkan-1.dll': 'vulkan', 'opengl32.dll': 'opengl'}
PROXY_DLLS = set(API_DLLS) | {'dxgi.dll', 'version.dll', 'winmm.dll', 'wininet.dll',
                            'dinput8.dll', 'dbghelp.dll', 'nvngx.dll', 'nvapi64.dll', 'reshade64.dll'}
UNITY_FLAGS = {'-force-d3d9': 'dx9', '-force-d3d11': 'dx11',
               '-force-d3d11-no-singlethreaded': 'dx11', '-force-d3d11-singlethreaded': 'dx11',
               '-force-d3d12': 'dx12', '-force-vulkan': 'vulkan',
               '-force-glcore': 'opengl', '-force-opengl': 'opengl'}


def bg3_renderer(exe, root, appid):
    if str(appid) != '1086940': return None
    try: relative = Path(exe).resolve().relative_to(Path(root).resolve()).as_posix().casefold()
    except ValueError: return None
    return {'bin/bg3_dx11.exe': 'dx11', 'bin/bg3.exe': 'vulkan'}.get(relative)


def detect_graphics_api(exe, root, launch='', appid=''):
    exe, root = Path(exe), Path(root).resolve()
    result = {'api': 'auto', 'source': 'unknown', 'evidence': [], 'candidates': [],
              'note': 'No renderer identified. Select the graphics API used by this game.'}
    if exe.is_symlink() or not exe.is_file() or not exe.resolve().is_relative_to(root):
        result['note'] = 'Choose an executable inside this game installation.'
        return result
    exe = exe.resolve()
    main = pe_info(exe)
    if main['kind'] != 'pe':
        result['note'] = 'This executable does not expose Windows renderer imports. Select its graphics API if needed.'
        return result

    renderer = bg3_renderer(exe, root, appid)
    if renderer:
        result.update(api=renderer, source='game-executable', candidates=[renderer],
                      note=f'BG3 renderer selected by executable: {renderer}. Use bg3_dx11.exe for ReShade.')
        return result

    # Only imported local modules are inspected; never every DLL in a mod folder.
    # Exclude graphics proxy names even if they have been installed beside the game.
    queue, visited, evidence = [(exe, main, 0)], set(), []
    unity = False
    while queue and len(visited) < 24:
        module, info, depth = queue.pop(0)
        if module in visited: continue
        visited.add(module)
        imports = info['imports']
        if 'unityplayer.dll' in imports or module.name.casefold() == 'unityplayer.dll': unity = True
        for dll in imports:
            if dll in API_DLLS:
                evidence.append({'api': API_DLLS[dll], 'file': str(module.relative_to(root)), 'import': dll})
        if depth >= 3: continue
        # Case-insensitive lookup matches Windows, with bounded directory reads.
        local = {}
        try:
            for n, child in enumerate(module.parent.iterdir()):
                if n >= 4096: break
                local.setdefault(child.name.casefold(), child)
        except OSError: continue
        for dll in imports:
            if dll in PROXY_DLLS or not re.fullmatch(r'[a-z0-9_.+ -]+\.dll', dll): continue
            child = local.get(dll)
            if not child or child.is_symlink() or not child.is_file(): continue
            child = child.resolve()
            if not child.is_relative_to(root) or child in visited: continue
            other = pe_info(child)
            if other['kind'] == 'pe' and other['bits'] == main['bits']:
                queue.append((child, other, depth + 1))
            if len(queue) + len(visited) >= 24: break

    candidates = sorted({item['api'] for item in evidence})
    result.update(evidence=evidence, candidates=candidates)
    if unity:
        # Exact standalone flags only. A flag inside an env assignment, quoted
        # shell script or unrelated executable's options is not renderer evidence.
        try:
            tokens = shlex.split(launch)
            if '%command%' in tokens: tokens = tokens[tokens.index('%command%') + 1:]
            elif tokens and not all(token.startswith('-') for token in tokens): tokens = []
            forced = {UNITY_FLAGS[token.casefold()] for token in tokens if token.casefold() in UNITY_FLAGS}
            unsupported = any(token.casefold().startswith('-force-') and
                              any(x in token.casefold() for x in ('d3d', 'vulkan', 'gl', 'metal')) and
                              token.casefold() not in UNITY_FLAGS for token in tokens)
        except ValueError:
            result['note'] = 'Launch options contain unbalanced quotes. Correct them before selecting a renderer.'
            return result
        if len(forced) > 1 or unsupported:
            result.update(source='ambiguous', note='Launch options request conflicting or unrecognized renderers. Check the flags and select the API explicitly.')
            return result
        if forced:
            api = next(iter(forced))
            result.update(api=api, source='launch-options', note=f'Renderer selected by the game’s Unity launch flag: {api}.')
            return result

    # Only this verified Steam title/default and executable identity are covered.
    # Its Unity engine can contain unused renderer backends. This is a default
    # inference (store requirements: DirectX 11), never a live rendering probe.
    if (unity and str(appid) == '848450' and exe.name.casefold() == 'subnauticazero.exe'
            and (exe.parent / 'SubnauticaZero_Data').is_dir()):
        result.update(api='dx11', source='game-default',
                      note='Subnautica: Below Zero uses a DirectX 11 default. This is a title-specific hint; an explicit Unity launch flag takes priority.')
        return result
    if len(candidates) == 1:
        api = candidates[0]
        files = list(dict.fromkeys(item['file'] for item in evidence))
        result.update(api=api, source='imports', note='Renderer imports found in ' + ', '.join(files[:3]) + '.')
    elif candidates:
        result.update(source='ambiguous', note='Several renderers are present (' + ', '.join(candidates) + '). Select the API the game uses.')
    return result
