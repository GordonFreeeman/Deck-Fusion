"""Lossless launch-option transformations and environment composition."""
from __future__ import annotations
import re
import shlex
from pathlib import Path
from fusion_util import FusionError

PLACEHOLDER = re.compile(r'%command%', re.I)
# Preserve original spelling, quoting and whitespace. Never eval launch options.
TOKEN = re.compile(r'''(?:[^\s'"\\]+|\\.|"(?:\\.|[^"\\])*"|'[^']*')+''')


def shell_tokens(text: str) -> list[tuple[str, int, int]]:
    try: shlex.split(text)
    except ValueError as e: raise FusionError(f'Launch options contain unbalanced quotes: {e}') from e
    return [(m.group(), m.start(), m.end()) for m in TOKEN.finditer(text)]


def command_template(text: str) -> str:
    text = text.strip()
    hits = list(PLACEHOLDER.finditer(text))
    if len(hits) > 1:
        raise FusionError('More than one %command% placeholder. Edit the launch options to contain exactly one.')
    if hits:
        hit = hits[0]
        # Quoting a whole command is not safe for arbitrary executable arguments.
        if (hit.start() and text[hit.start()-1] in "\"'"):
            raise FusionError('Remove quotes immediately around %command%; Steam expands it into a command and arguments.')
        return text[:hit.start()] + '%command%' + text[hit.end():]
    if not text: return '%command%'
    tokens = shell_tokens(text)
    pos = 0
    i = 0
    if tokens and tokens[0][0] == 'env':
        pos = tokens[0][2]
        i = 1
    for raw, start, end in tokens[i:]:
        parts = shlex.split(raw)
        if len(parts) == 1 and re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', parts[0]):
            pos = end
        else: break
    prefix = text[:pos].strip()
    tail = text[pos:].strip()
    if tail and not tail.startswith('-'):
        # Known command wrappers are distinguishable from game-only arguments.
        first = shlex.split(tail)[0]
        if first in ('gamemoderun', 'mangohud') and len(shlex.split(tail)) == 1:
            prefix = ' '.join(x for x in (prefix, tail) if x)
            tail = ''
        else:
            raise FusionError('Launch options without %command% contain an ambiguous command. Add %command% at its execution point in the editable preview. Game arguments such as --skip-launcher are handled automatically.')
    return ' '.join(x for x in (prefix, '%command%', tail) if x)


def launch_prefix(wrapper: Path, appid: str) -> str:
    if not re.fullmatch(r'[0-9]{1,20}', appid): raise FusionError('Invalid Steam app ID.')
    return f'{shlex.quote(str(wrapper))} {appid} -- '


def strip_wrapper(text: str, wrapper: Path, appid: str) -> str:
    prefix = launch_prefix(wrapper, appid)
    if prefix in text: return text.replace(prefix, '', 1)
    return text


def compose_launch(text: str, wrapper: Path, appid: str) -> str:
    plain = strip_wrapper(text, wrapper, appid)
    if 'deck-fusion/bin/launch' in plain:
        raise FusionError('A different Deck Fusion wrapper is already present. Restore that profile first.')
    templ = command_template(plain)
    return templ.replace('%command%', launch_prefix(wrapper, appid) + '%command%', 1)


def restore_launch(current: str, installed: str, original: str, wrapper: Path, appid: str) -> str:
    if current == installed: return original
    # Keep edits made after installation; remove only our own wrapper.
    return strip_wrapper(current, wrapper, appid)


def override_name(name: str) -> str:
    return name.strip().casefold().removesuffix('.dll')


def parse_dll_overrides(text: str, strict: bool = False) -> dict[str, str]:
    """Parse load orders without executing shell text. Last exact name wins.

    Existing path/wildcard rules are retained. New custom entries deliberately
    accept only module basenames and an optional leading Wine '*'.
    """
    if not isinstance(text, str) or len(text) > 16384 or any(c in text for c in '\0\r\n'):
        raise FusionError('DLL overrides must be a single line, maximum 16 KB.')
    aliases = {'native':'n', 'builtin':'b', 'n':'n', 'b':'b'}
    result = {}
    for group in text.split(';'):
        if not group.strip(): continue
        if '=' not in group:
            raise FusionError('Each DLL override needs a load order, for example version=n,b.')
        names, value = group.split('=', 1)
        modes = [item.strip().casefold() for item in value.split(',')] if value.strip() else []
        if any(item not in aliases for item in modes):
            raise FusionError('DLL load order must be n,b; b,n; n; b; or empty (disabled).')
        normalized = ','.join(dict.fromkeys(aliases[item] for item in modes))
        for name in names.split(','):
            key = override_name(name)
            if not key or (strict and not re.fullmatch(r'\*?[a-z0-9_][a-z0-9_.+-]{0,127}', key)):
                raise FusionError('Use a DLL basename such as version or winmm, not a path, wildcard pattern or shell command.')
            if strict and (key in ('.', '..') or '..' in key):
                raise FusionError('DLL override names cannot contain path traversal.')
            result[key] = normalized
    return result


def launch_assignments(text: str) -> dict[str, str]:
    """Read literal assignments before Steam's command; never eval shell code.

    Keep the shell's final assignment, rather than concatenating multiple values
    that the shell would actually replace. Expansion requires explicit user input.
    """
    head = text.split('%command%')[0]
    result = {}
    for raw, _, _ in shell_tokens(head):
        values = shlex.split(raw)
        if len(values) != 1: continue
        value = values[0]
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*|MLSR-WATERMARK)=(.*)$', value)
        if match:
            key, content = match.groups()
            if key == 'WINEDLLOVERRIDES' and any(c in content for c in '$`'):
                raise FusionError('WINEDLLOVERRIDES uses shell expansion. Use a literal override list in Steam or DLLs so existing mod names can be protected before applying.')
            result[key] = content
    return result


def merge_dll_overrides(existing: str, overrides: dict[str, str]) -> str:
    normalized = {override_name(k): v for k, v in overrides.items()}
    kept = []
    for group in existing.split(';'):
        if not group.strip(): continue
        if '=' not in group:
            kept.append(group)
            continue
        names, value = group.split('=', 1)
        left = [n.strip() for n in names.split(',') if override_name(n) not in normalized]
        if left: kept.append(','.join(left) + '=' + value)
    kept.extend(f'{k}={v}' for k, v in sorted(normalized.items()))
    return ';'.join(kept)


def launch_environment(config: dict, current: dict[str, str]) -> dict[str, str]:
    env = dict(current)
    if config.get('bypass'): return env
    overrides = {**config.get('custom_dll_overrides', {}), **config.get('dll_overrides', {})}
    if overrides:
        env['WINEDLLOVERRIDES'] = merge_dll_overrides(env.get('WINEDLLOVERRIDES', ''), overrides)
    lsfg = config.get('lsfg', {})
    if lsfg.get('enabled'):
        env['DECK_FUSION_LSFG'] = '1'
        env['LSFGVK_CONFIG'] = config['lsfg_config']
        # Reject legacy/global env overrides by replacing only keys that control this layer.
        for key in ('LSFGVK_ENV', 'LSFGVK_PROFILE', 'DISABLE_LSFGVK', 'LSFG_MULTIPLIER', 'LSFG_FLOW_SCALE', 'LSFG_PERFORMANCE_MODE'):
            env.pop(key, None)
        if lsfg.get('respect_deck_limiter') and (env.get('GAMESCOPE_WAYLAND_DISPLAY') or env.get('GAMESCOPE_LIMITER_FILE')):
            # lsfg-vk's VSync troubleshooting recommends ENABLE_GAMESCOPE_WSI=0
            # on Gamescope/Deck. Do NOT force the WSI Vulkan layer back on as 1.1
            # did: it can observe only the app's original present, not all FG output.
            # Disabling that layer does not disable the Gamescope compositor.
            env['ENABLE_GAMESCOPE_WSI'] = '0'
            env['DISABLE_GAMESCOPE_WSI'] = '1'
            env.pop('GAMESCOPE_WSI_FRAME_LIMITER_AWARE', None)
            # An inherited Mesa immediate/mailbox override beats a requested FIFO
            # swapchain. Keep the final driver presentation path VSync/FIFO too.
            env['MESA_VK_WSI_PRESENT_MODE'] = 'fifo'
    if config.get('opti_enabled') and isinstance(config.get('fsr4_watermark'), bool):
        show = config['fsr4_watermark']
        # FidelityFX has presence-based watermark checks: even a value of "0"
        # can enable the banner. Off MUST mean absent, not zero. The paired INI
        # setting uses upstream "auto" so OptiScaler does not recreate a zero
        # variable in DllMain (explicit false does precisely that in 0.9.4).
        if show:
            env['MLSR-WATERMARK'] = '1'
        else:
            env.pop('MLSR-WATERMARK', None)
        # Explicit 0 suppresses Proton's fsr4hud compatibility option. Merely
        # unsetting this variable lets a user_settings/compat setting re-enable it.
        env['PROTON_FSR4_INDICATOR'] = '1' if show else '0'
        if show:
            env['FSR4_WATERMARK'] = '1'
            env['FSR_WATERMARK'] = '1'
        else:
            env.pop('FSR4_WATERMARK', None)
            env.pop('FSR_WATERMARK', None)
        # Do not change FSR upgrades, INT8 model flags, FG or other diagnostic HUDs.
    if config.get('base_fps', 0) > 0 and config.get('api') in ('auto', 'dx9', 'dx10', 'dx11', 'dx12'):
        env['DXVK_FRAME_RATE'] = str(config['base_fps'])
        env['VKD3D_FRAME_RATE'] = str(config['base_fps'])
    if config.get('enable_nvapi'):
        env['PROTON_ENABLE_NVAPI'] = '1'
    return env
def bg3_command(config: dict, command: list[str]) -> tuple[list[str], str]:
    """Select the reviewed BG3 renderer inside Steam's existing Proton command.

    Only replace the executable operand of a recognized Proton invocation, never
    a game argument, another game's executable or the compatibility tool itself.
    """
    target = config.get('bg3_target')
    if config.get('bypass') or config.get('appid') != '1086940' or not isinstance(target, dict):
        return command, ''
    root, exe = Path(target['root']).resolve(), Path(target['exe']).resolve()
    if not exe.is_file() or not exe.is_relative_to(root): return command, 'BG3 target is unavailable; kept Steam command.'
    if exe.relative_to(root).as_posix().casefold() not in ('bin/bg3.exe', 'bin/bg3_dx11.exe'):
        return command, 'Unrecognized BG3 target; kept Steam command.'
    for i in range(2, len(command)):
        if command[i-1] not in ('run', 'waitforexitandrun') or Path(command[i-2]).name != 'proton': continue
        original = Path(command[i])
        if not original.is_absolute(): continue
        original = original.resolve()
        if not original.is_relative_to(root): continue
        if original.relative_to(root).as_posix().casefold() not in ('bin/bg3.exe', 'bin/bg3_dx11.exe', 'launcher/larilauncher.exe'): continue
        result = list(command); result[i] = str(exe)
        return result, 'Selected BG3 renderer: ' + exe.name
    return command, 'No recognized BG3 Proton launch operand; kept Steam command. Select the matching renderer in Steam.'
