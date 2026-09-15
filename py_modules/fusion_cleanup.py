"""Preview removal of old graphics launch hooks. Never execute launch text."""
import re
import shlex
from pathlib import PurePosixPath

from fusion_launch import compose_launch, shell_tokens, strip_wrapper, override_name
from fusion_util import FusionError

GRAPHICS_DLLS = frozenset(('dxgi', 'd3d9', 'd3d10', 'd3d10_1', 'd3d11', 'd3d12',
    'opengl32', 'version', 'winmm', 'winhttp', 'wininet', 'dbghelp', 'nvngx', 'reshade64'))
WRAPPERS = frozenset(('lsfg', 'lsfg.sh', 'lsfg-vk', 'lsfg-vk.sh', 'lsfg-vk-run',
    'lossless-scaling', 'lossless-scaling.sh', 'optiscaler', 'optiscaler.sh', 'reshade', 'reshade.sh'))
INJECTOR = re.compile(r'lsfg|vk_?layer_ls_frame_generation|lossless[-_ ]?scaling|optiscaler|reshade', re.I)


def cleanup_launch(launch, wrapper, appid):
    if not isinstance(launch, str) or len(launch) > 32768:
        raise FusionError('Launch options must be text under 32 KB.')
    plain = strip_wrapper(launch, wrapper, appid)
    tokens = [(raw, shlex.split(raw)[0]) for raw, *_ in shell_tokens(plain)]
    commands = [n for n, (_, value) in enumerate(tokens) if value.lower() == '%command%']
    if len(commands) > 1: raise FusionError('Multiple %command% placeholders. Keep one game command before applying.')
    boundary = commands[0] if commands else len(tokens)
    head, tail = tokens[:boundary], tokens[boundary:]
    # Shell scripts/pipelines cannot be rewritten as a flat argument vector.
    # Ordinary quoted values may contain these characters and are left intact.
    lexer = shlex.shlex(plain, posix=True, punctuation_chars=';&|<>')
    lexer.whitespace_split = True; lexer.commenters = ''
    complex_shell = any(t and all(c in ';&|<>' for c in t) for t in lexer)
    removed, kept = [], []
    i = 0
    while i < len(head):
        raw, value = head[i]
        match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*|MLSR-WATERMARK)=(.*)', value, re.S)
        if match:
            key, content = match.groups()
            if key in ('WINEDLLOVERRIDES', 'WINEDLLOVERIDES'):
                groups = []; changed = False
                for group in content.split(';'):
                    names, sep, order = group.partition('=')
                    if not sep:
                        if group.strip(): groups.append(group)
                        continue
                    names = names.split(',')
                    drop = [name for name in names if override_name(name).lstrip('*') in GRAPHICS_DLLS]
                    remain = [name for name in names if name not in drop]
                    if drop: removed.append(key + ': ' + ','.join(drop) + '=' + order); changed = True
                    if remain: groups.append(','.join(remain) + '=' + order)
                if groups: kept.append((key + '=' + shlex.quote(';'.join(groups))) if changed else raw)
            elif (key.startswith(('LSFG', 'OPTISCALER_', 'RESHADE_')) or
                  key in ('ENABLE_LSFG', 'DISABLE_LSFGVK', 'DECK_FUSION_LSFG')):
                removed.append(raw)
            elif key in ('VK_INSTANCE_LAYERS', 'VK_LAYER_PATH', 'VK_ADD_LAYER_PATH', 'LD_PRELOAD'):
                parts = re.split(r'[:\s]+' if key == 'LD_PRELOAD' else ':', content)
                old = [part for part in parts if INJECTOR.search(part)]
                if old:
                    removed.extend(key + ': ' + part for part in old)
                    remain = [part for part in parts if part not in old]
                    if remain: kept.append(key + '=' + shlex.quote(':'.join(remain)))
                else: kept.append(raw)
            else: kept.append(raw)
            i += 1; continue
        path = value.replace('\\', '/')
        name = PurePosixPath(path).name.casefold()
        interpreter = name in ('bash', 'sh') and i + 1 < len(head)
        script = head[i + 1][1].replace('\\', '/') if interpreter else path
        script_name = PurePosixPath(script).name.casefold()
        legacy = script_name in WRAPPERS or (script_name in ('launch', 'run', 'run.sh') and INJECTOR.search(str(PurePosixPath(script).parent)))
        fusion = script.endswith('/deck-fusion/bin/launch')
        if legacy or fusion:
            start = i; i += 2 if interpreter else 1
            if fusion:
                if i < len(head) and head[i][1].isdigit(): i += 1
                if i < len(head) and head[i][1] == '--': i += 1
            elif commands:
                # Options before the game placeholder belong to the old launcher.
                # Keep common independent wrappers encountered after its options.
                while i < len(head) and head[i][1] not in ('gamemoderun', 'mangohud', 'env'):
                    if '=' in head[i][1]: break
                    i += 1
            removed.append(' '.join(item[0] for item in head[start:i])); continue
        kept.append(raw); i += 1
    if removed and (complex_shell or any('$(' in value or '`' in value for _, value in head)):
        raise FusionError('Old graphics settings are inside a compound shell command. Edit its launch text to one %command% invocation before replacing the graphics hooks; no command was executed or changed.')
    if kept == ['env']: kept = []
    cleaned = ' '.join(kept + [raw for raw, _ in tail]) if removed else launch
    return {'before': launch, 'cleaned': cleaned,
            'after': compose_launch(cleaned, wrapper, appid), 'removed': removed,
            'warnings': ['DLL overrides such as version and winmm can also load other mods. The listed entries will be removed from Steam launch options. Unrelated arguments and overrides are retained.'] if removed else []}
