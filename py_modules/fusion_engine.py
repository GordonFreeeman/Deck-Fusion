"""Per-game orchestration. All mutations are user-scoped and explicitly requested."""
from __future__ import annotations
import copy
import hashlib
import json
import math
import os
import re
import shlex
import time
from pathlib import Path
from fusion_catalog import DEFAULT_PROFILE, SHADER_PACKS, FSR4FIX
from fusion_downloads import Packages
from fusion_network import tls_context
from fusion_launch import compose_launch, restore_launch, launch_environment, shell_tokens, merge_dll_overrides, parse_dll_overrides, launch_assignments
from fusion_policy import hardware_info, resolve_settings
from fusion_mods import cyberpunk_diagnostics
from fusion_game_diagnostics import game_diagnostics
from fusion_prereqs import PrefixRuntimes
from fusion_wine import inspect_overrides, resolve_loaders, guard_payload, RESH_PROXIES
from fusion_shaders import opti_schema, pack_files, preset_text
from fusion_steam import installed_games, pe_info, running_game, scan_game
from fusion_api import detect_graphics_api, bg3_renderer
from fusion_cleanup import cleanup_launch
from fusion_transaction import ManagedFilesChanged, Transaction, copy_atomic
from fusion_util import FusionError, atomic_bytes, atomic_json, ini_patch, ini_read, ini_set, ini_write, read_json, safe_target, sha256

PROXIES = {'dxgi', 'winmm', 'version', 'wininet', 'winhttp', 'dbghelp', 'd3d12'}
APIS = {'auto', 'dx9', 'dx10', 'dx11', 'dx12', 'vulkan', 'opengl'}


def encoded(value) -> bytes: return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def merge_defaults(value, template):
    if isinstance(template, dict):
        if not isinstance(value, dict): value = {}
        return {**copy.deepcopy(value), **{k: merge_defaults(value.get(k), v) for k, v in template.items()}}
    return copy.deepcopy(template if value is None else value)


def migrate_profile(raw):
    """Merge new defaults without writing anything. v1.1 enabled a debug watermark
    by default, so pre-schema-3 profiles start with that diagnostic switched off.
    Once saved as schema 3, an explicit user's opt-in is preserved.
    """
    p = merge_defaults(raw, DEFAULT_PROFILE)
    version = raw.get('schema', 1) if isinstance(raw, dict) else 1
    if not isinstance(version, int) or version < 3:
        p['opti']['fsr4_watermark'] = False
    if not isinstance(version, int) or version < 4:
        p['reshade']['proxy'] = 'auto'  # This field was ignored by pre-1.2 installers.
    p['schema'] = 4
    return p


def opti_compat_keys(o):
    """One source of truth for the installer AND its approval preview.

    Fsr4EnableWatermark=false makes OptiScaler 0.9.4 set MLSR-WATERMARK=0.
    FidelityFX presence checks treat that as on. Upstream auto + absent env
    leaves its optional setting unset and avoids that setter entirely.
    """
    result = {'Fsr4EnableWatermark': 'true' if o['fsr4_watermark'] else 'auto'}
    if o['mouse_input'] != 'auto':
        result['ManualInputPolling'] = 'true' if o['mouse_input'] == 'polling' else 'false'
    if o['steam_input'] != 'auto':
        result['DisableOverlays'] = 'false' if o['steam_input'] == 'keep' else 'true'
    return result


def boolean(value):
    if not isinstance(value, bool): raise FusionError('A toggle setting must be true or false.')
    return value


def number(value, low, high, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise FusionError(f'Numeric setting must be between {low} and {high}.')
    if integer and int(value) != value: raise FusionError('This setting requires a whole number.')
    return int(value) if integer else value


class Engine:
    def __init__(self, home: Path, source: Path, data: Path | None = None):
        self.home = home.resolve(); self.source = source.resolve()
        self.data = (data or self.home / '.local/share/deck-fusion').resolve()
        self.data.mkdir(parents=True, exist_ok=True)
        self.packages = Packages(self.data, self.source / 'bundled')
        self.wrapper = self.data / 'bin/launch'
        self.layer_file = self.home / '.local/share/vulkan/implicit_layer.d/DeckFusion.LSFG.json'
        self.install_runtime()
        self.prereqs = PrefixRuntimes(self)

    def install_runtime(self):
        for name in ('fusion_runtime.py', 'fusion_launch.py', 'fusion_util.py'):
            dest = self.data / 'bin' / name
            src = self.source / 'py_modules' / name
            if not dest.exists() or sha256(dest) != sha256(src): copy_atomic(src, dest, 0o644)
        launcher = f'#!/bin/sh\nexec /usr/bin/python3 {shlex.quote(str(self.data / "bin/fusion_runtime.py"))} "$@"\n'
        if not self.wrapper.exists() or self.wrapper.read_text() != launcher:
            atomic_bytes(self.wrapper, launcher.encode(), 0o755)

    def hardware(self):
        return hardware_info()

    def settings(self):
        value = read_json(self.data / 'settings.json', {})
        if not isinstance(value, dict): raise FusionError('The saved plugin settings are invalid. The original file was not overwritten.')
        return {'include_shortcuts': value.get('include_shortcuts') is True}

    def set_settings(self, value):
        if not isinstance(value, dict) or set(value) != {'include_shortcuts'}:
            raise FusionError('Only the non-Steam library toggle can be changed here.')
        boolean(value['include_shortcuts'])
        atomic_json(self.data / 'settings.json', value)
        return self.settings()

    def games(self, include_shortcuts=None):
        if include_shortcuts is None: include_shortcuts = self.settings()['include_shortcuts']
        entries = installed_games(self.home, include_shortcuts=include_shortcuts)
        # These are Steam runtime/software entries, not a blacklist of games.
        utility = re.compile(r'^(?:Steam Linux Runtime(?: .*)?|Steamworks Common Redistributables|Proton (?:Experimental|Hotfix|Next|[0-9].*))$', re.I)
        return [g for g in entries if g['appid'] not in ('993090', '228980') and not utility.fullmatch(g['name'])]

    def game(self, appid):
        appid = str(appid)
        if not re.fullmatch(r'\d{1,20}', appid): raise FusionError('Invalid game ID.')
        # A display filter must never make existing profiles/backups inaccessible.
        entries = installed_games(self.home)
        game = next((g for g in entries if g['appid'] == appid), None)
        if game is None:
            game = next((g for g in installed_games(self.home, include_shortcuts=True) if g['appid'] == appid), None)
        if not game: raise FusionError('Game installation was not found. Mount the SD card / library and refresh Library.')
        return game

    def store(self, appid):
        if not re.fullmatch(r'\d{1,20}', str(appid)): raise FusionError('Invalid game ID.')
        return self.data / 'profiles' / str(appid)

    def profile(self, appid):
        game = self.game(appid)
        raw = read_json(self.store(appid) / 'profile.json', {})
        p = migrate_profile(raw)
        explicit = raw.get('opti', {}) if isinstance(raw, dict) else {}
        if not isinstance(explicit, dict) or 'fsr4_rdna2_fix' not in explicit:
            p['opti']['fsr4_rdna2_fix'] = self.hardware().get('fsr4_rdna2_recommended', False)
        p.update({k: game[k] for k in ('appid', 'name', 'root')})
        if not p['exe'] and game.get('exe'): p['exe'] = game['exe']
        p['schema'] = 4
        return p

    def scan(self, appid):
        game = self.game(appid); result = scan_game(Path(game['root']))
        if str(appid) == '1086940':
            result['candidates'].sort(key=lambda c: (bg3_renderer(c['path'], game['root'], appid) != 'dx11', -c['score'], c['relative']))
        for candidate in result['candidates'][:30]:
            hint = detect_graphics_api(candidate['path'], game['root'], appid=appid)
            candidate.update(api=hint['api'], api_detection=hint)
        result['game'] = game
        return result

    def detect_api(self, raw, launch=''):
        p = migrate_profile(raw)
        game = self.game(p['appid'])
        exe = Path(p['exe']).expanduser()
        if not exe.is_absolute(): exe = Path(game['root']) / exe
        return detect_graphics_api(exe, game['root'], launch, p['appid'])

    def launch_cleanup(self, appid, launch):
        self.game(appid)
        return cleanup_launch(launch, self.wrapper, appid)

    def wine_context(self, raw, launch):
        p = migrate_profile(raw)
        context = inspect_overrides(self, p, launch)
        actual = self.detect_api(p, launch)['api'] if p['api'] == 'auto' else p['api']
        context['blockers'] = []
        try:
            proposed, policy, _ = resolve_settings(p, actual, self.hardware())
            proposed, fixes = resolve_loaders(proposed, actual, context)
            context['resolutions'] = policy + fixes
            context['proposed'] = {'opti_proxy': proposed['opti']['proxy'], 'reshade_mode': proposed['reshade']['mode'],
                'reshade_proxy': (RESH_PROXIES.get(actual, ('dxgi',))[0] if proposed['reshade']['proxy'] == 'auto' else proposed['reshade']['proxy'])}
        except FusionError as error:
            context['resolutions'] = []
            context['blockers'] = [str(error)]
        return context

    def package(self, component):
        info = self.packages.status().get(component)
        if not info or not Path(info['path']).is_dir():
            raise FusionError(f'Install {component} in the Tools tab first.')
        return info

    def fsr4fix_binary(self):
        pkg = self.package('fsr4fix')
        if pkg.get('version') != FSR4FIX['version'] or pkg.get('sha256') != FSR4FIX['sha256']:
            raise FusionError('Reinstall the pinned FSR 4.1.1b RDNA2 fix in Tools.')
        payload = pkg.get('payload', {})
        dll = safe_target(Path(pkg['path']), payload.get('dll', ''))
        if dll.is_symlink() or not dll.is_file() or sha256(dll) != payload.get('dll_sha256'):
            raise FusionError('The cached RDNA2 fix DLL changed or is missing. Reinstall it in Tools.')
        return dll

    def old_layers(self):
        results = []
        for base in (self.home / '.local/share/vulkan', self.home / '.config/vulkan', Path('/usr/share/vulkan'), Path('/etc/vulkan')):
            for kind in ('implicit_layer.d', 'explicit_layer.d'):
                for f in (base / kind).glob('*.json'):
                    if f == self.layer_file: continue
                    try:
                        data = json.loads(f.read_text())
                        if 'lsfg' not in json.dumps(data).lower(): continue
                        results.append({'path': str(f), 'user_owned': f.is_relative_to(self.home) and not f.is_symlink(),
                                        'name': data.get('layer', {}).get('name', '')})
                    except (OSError, ValueError): pass
        return results

    def disable_old_layers(self):
        # This operation requires its own clearly-labelled UI button. System files are untouched.
        changes = []
        for entry in self.old_layers():
            if not entry['user_owned']: continue
            f = Path(entry['path']); target = f.with_name(f.name + '.disabled-by-deck-fusion')
            if target.exists(): raise FusionError(f'Backup already exists: {target}. Nothing was overwritten.')
            os.replace(f, target); changes.append({'from': str(f), 'to': str(target)})
        return {'disabled': changes, 'remaining': self.old_layers()}

    def lsfg_dll(self, custom=''):
        if custom:
            p = Path(custom).expanduser().resolve()
            allowed = p.is_relative_to(self.home) or any(p.is_relative_to(Path(g['root'])) for g in installed_games(self.home, include_shortcuts=True))
            if not allowed or p.name.lower() != 'lsfg-vk.dll':
                raise FusionError('Select your own lsfg-vk.dll from Lossless Scaling, inside your home or Steam library.')
            choices = [p]
        else:
            games = [g for g in installed_games(self.home) if g['appid'] == '993090']
            choices = [p for g in games for p in Path(g['root']).rglob('*') if p.name.lower() == 'lsfg-vk.dll' and p.is_file()]
        if not choices:
            raise FusionError('Install your purchased Lossless Scaling app (993090), select its lsfg-vk beta branch in Steam, then retry. Version 2 does not use the old Lossless.dll.')
        p = choices[0]
        if not p.is_file() or p.stat().st_size > 256 * 1024 * 1024 or p.read_bytes()[:2] != b'MZ':
            raise FusionError('The selected Lossless Scaling DLL is missing or invalid.')
        return p

    def setup_lsfg(self, custom=''):
        info = self.package('lsfg')
        conflicts = self.old_layers()
        if conflicts:
            raise FusionError('Another LSFG Vulkan manifest was found. Disable its plugin, then use the explicit legacy-manifest action in Tools. System installations must be removed by their original installer.')
        src = self.lsfg_dll(custom)
        dll = self.data / 'dlls' / sha256(src) / 'lsfg-vk.dll'
        if not dll.exists(): copy_atomic(src, dll, 0o644)
        manifest = json.loads((Path(info['path']) / info['payload']['manifest']).read_text())
        layer = manifest['layer']
        layer['library_path'] = str(Path(info['path']) / info['payload']['library'])
        layer['enable_environment'] = {'DECK_FUSION_LSFG': '1'}
        layer['disable_environment'] = {'DISABLE_LSFGVK': '1'}
        # A private gate is essential: merely installing this plugin never enables FG globally.
        atomic_json(self.layer_file, manifest)
        atomic_json(self.data / 'lsfg-install.json', {'dll': str(dll), 'library': layer['library_path'],
                                                    'manifest': str(self.layer_file), 'version': info['version']})
        return {'version': info['version'], 'dll': str(dll), 'manifest': str(self.layer_file)}

    def schema(self, appid=''):
        result = {'opti': [], 'shaders': [], 'packs': SHADER_PACKS, 'opti_version': None, 'fsr4_int8': False}
        status = self.packages.status()
        if 'opti' in status:
            info = status['opti']; base = Path(info['path']) / info['payload']['directory']
            result['opti'] = opti_schema((base / info['payload']['ini']).read_text('utf-8-sig'))
            result['opti_version'] = info['version']
            keys = {item['key'] for item in result['opti']}
            result['fsr4_int8'] = bool({'Fsr4ForceModel', 'Fsr4ForceEnableInt8'} & keys) and 'Fsr4EnableWatermark' in keys
            result['fsr4_sdk'] = any(f.is_file() for f in base.rglob('amd_fidelityfx_upscaler_dx12.dll'))
        for key, pack in status.get('shaders', {}).items():
            _, shaders = pack_files(pack)
            for s in shaders: s['pack'] = key
            result['shaders'].extend(shaders)
        if appid:
            p = self.profile(appid)
            if p['exe']:
                folder = Path(p['exe']).parent
                for filename, key in [('OptiScaler.ini', 'opti_current'), ('DeckFusionPreset.ini', 'preset_current'), ('ReShade.ini', 'reshade_current')]:
                    f = folder / filename
                    if f.is_file() and f.stat().st_size < 1024 * 1024: result[key] = f.read_text('utf-8-sig', errors='replace')
        return result

    def validate(self, raw, launch=''):
        p = migrate_profile(raw)
        p['schema'] = 4
        game = self.game(p['appid']); root = Path(game['root']).resolve()
        p.update({k: game[k] for k in ('name', 'root', 'appid')})
        exe = Path(p['exe']).expanduser()
        if not exe.is_absolute(): exe = root / exe
        if exe.is_symlink() or not exe.is_file() or not exe.resolve().is_relative_to(root):
            raise FusionError('Choose the actual game executable inside this Steam installation, not a launcher outside the library.')
        p['exe'] = str(exe.resolve()); info = pe_info(exe)
        if info['kind'] not in ('pe', 'elf') or info['bits'] not in (32, 64): raise FusionError('The selected file is not a supported Windows or Linux executable.')
        if p['api'] not in APIS: raise FusionError('Unknown rendering API.')
        if p['api'] == 'auto': p['api'] = self.detect_api(p, launch)['api']
        renderer = bg3_renderer(exe, root, p['appid'])
        if renderer and p['api'] != renderer:
            raise FusionError('BG3 graphics API does not match the executable. Select bin/bg3_dx11.exe for DirectX 11 or bin/bg3.exe for Vulkan.')
        p['base_fps'] = number(p['base_fps'], 0, 240, True)
        p['backup_conflicts'] = boolean(p['backup_conflicts'])
        if not isinstance(p.get('wine'), dict): raise FusionError('Invalid Wine override settings.')
        boolean(p['wine']['opti_proxy_manual'])
        boolean(p['wine']['reshade_proxy_manual'])
        custom = parse_dll_overrides(p['wine']['custom_overrides'], strict=True)
        p['wine']['custom_overrides'] = ';'.join(f'{name}={order}' for name, order in custom.items())
        setup = p['setup']
        if (not isinstance(setup.get('version'), int) or setup['version'] not in (0, 1) or
                not isinstance(setup.get('runtimes'), list) or any(v not in ('d3dcompiler_47', 'vcrun2022') for v in setup['runtimes']) or
                not isinstance(setup.get('runtime_prefix'), str) or len(setup['runtime_prefix']) > 4096):
            raise FusionError('Invalid setup preferences.')
        l, o, r = p['lsfg'], p['opti'], p['reshade']
        for key in ('enabled', 'performance_mode', 'allow_fp16', 'override_present_mode', 'preserve_swapchain_image_count', 'respect_deck_limiter'): boolean(l[key])
        number(l['multiplier'], 1, 8, True); number(l['flow_scale'], .1, 1)
        for key in ('enabled', 'fg', 'enable_nvapi', 'fsr4_watermark', 'fsr4_rdna2_fix'): boolean(o[key])
        if o['fsr_mode'] not in ('auto', 'fsr3', 'fsr4_int8'): raise FusionError('Unknown FSR backend mode.')
        if o['mouse_input'] not in ('auto', 'polling', 'window'): raise FusionError('Unknown OptiScaler mouse-input mode.')
        if o['steam_input'] not in ('auto', 'keep', 'disable'): raise FusionError('Unknown OptiScaler overlay compatibility mode.')
        if o['proxy'] not in PROXIES: raise FusionError('Unsupported OptiScaler proxy DLL name.')
        if o['spoof'] not in ('auto', 'true', 'false'): raise FusionError('Invalid GPU-spoofing value.')
        for key in ('dx11', 'dx12', 'vulkan'):
            if o[key] not in ('auto','fsr21','fsr22','fsr31','xess','xess_12','fsr21_12','fsr22_12','fsr31_12','dlss'):
                raise FusionError('Invalid upscaler selection.')
        if r['mode'] not in ('off', 'standalone', 'opti'): raise FusionError('Invalid ReShade loading mode.')
        if r['proxy'] not in ('auto','dxgi','d3d9','d3d10','d3d11','d3d12','opengl32'): raise FusionError('Unsupported ReShade proxy name.')
        if custom and info['kind'] != 'pe': raise FusionError('Wine DLL overrides apply to Windows games through Proton, not native Linux executables.')
        boolean(r['performance']); number(r['overlay_key'], 1, 255, True)
        if o['enabled'] and (info['kind'] != 'pe' or info['bits'] != 64 or p['api'] not in ('dx11','dx12','vulkan')):
            raise FusionError('OptiScaler here requires a 64-bit Windows DX11/DX12/Vulkan game with a compatible DLSS/FSR/XeSS input. Choose its rendering API explicitly if auto-detection is inconclusive.')
        if o['enabled'] and o['fg'] and l['enabled']: raise FusionError('Do not stack two frame generators. Disable OptiScaler frame generation or LSFG.')
        if o['enabled'] and o['fg'] and p['api'] != 'dx12': raise FusionError('The provided OptiScaler FG preset is for DX12. Other FG paths require game-specific setup.')
        if r['mode'] == 'opti' and not o['enabled']: raise FusionError('ReShade-through-OptiScaler requires OptiScaler to be enabled.')
        if r['mode'] != 'off' and (info['kind'] != 'pe' or p['api'] not in ('dx9','dx10','dx11','dx12','opengl')):
            raise FusionError('This build supports ReShade in Windows DirectX/OpenGL games through Proton. Native Linux and Windows Vulkan ReShade require a different layer path and are not offered as a false working option.')
        if r['mode'] == 'standalone' and o['enabled'] and o['proxy'] == self.reshade_proxy(p):
            raise FusionError('OptiScaler and standalone ReShade cannot use the same proxy DLL. Select ReShade-through-OptiScaler, or choose winmm for OptiScaler.')
        if l['enabled'] and (info['bits'] != 64 or p['api'] == 'opengl'):
            raise FusionError('The LSFG layer installed by this build is 64-bit Vulkan. DirectX through DXVK/VKD3D is supported; direct OpenGL and 32-bit processes are not.')
        if l['enabled'] and info['kind'] == 'elf' and p['api'] != 'vulkan':
            raise FusionError('For a native Linux game, explicitly select Vulkan and use its Vulkan renderer. A Linux executable alone does not prove Vulkan support.')
        active = {'dx11':'dx11', 'dx12':'dx12', 'vulkan':'vulkan'}.get(p['api'])
        if o['enabled'] and active and o[active] == 'dlss' and self.hardware()['known_non_nvidia']:
            raise FusionError('Native NVIDIA DLSS output is not supported on this GPU. Select FSR or XeSS output; DLSS can still be the game input.')
        if o['enabled'] and o['fsr_mode'] == 'fsr4_int8':
            required_output = 'fsr31' if p['api'] == 'dx12' else 'fsr31_12'
            if not active or o[active] != required_output:
                raise FusionError('Experimental FSR4 requires the FSR 3.x/4 output route. Use Apply settings to resolve this choice automatically.')
        if l['enabled'] and l['respect_deck_limiter'] and not l['override_present_mode']:
            raise FusionError('The Deck limiter preset requires LSFG VSync/FIFO pacing. Use Apply settings to resolve this conflict.')
        if l['enabled']: self.package('lsfg')
        if o['enabled']:
            self.package('opti')
            if o['fsr_mode'] == 'fsr4_int8' and o['fsr4_rdna2_fix']:
                self.fsr4fix_binary()
        if r['mode'] != 'off': self.package('reshade')
        p['architecture'] = info
        return p

    def reshade_proxy(self, p):
        if p['reshade']['proxy'] != 'auto': return p['reshade']['proxy']
        return RESH_PROXIES.get(p['api'], ('dxgi',))[0]

    def safety(self, p):
        running = running_game(Path(p['exe']), p['appid'])
        if running['processes']:
            raise FusionError('The selected game process is running: ' + ', '.join(str(x['pid']) for x in running['processes']) + '. Exit it before installing or changing files.')
        scan = scan_game(Path(p['root']))
        if scan['anticheat'] and (p['opti']['enabled'] or p['lsfg']['enabled'] or p['reshade']['mode'] != 'off' or p.get('wine', {}).get('custom_overrides')):
            raise FusionError('Anti-cheat markers detected. Injection is blocked for this installation: ' + ', '.join(scan['anticheat'][:5]))
        return running

    def config_lsfg(self, p):
        install = read_json(self.data / 'lsfg-install.json', {})
        if not install or not Path(install.get('dll','')).is_file() or not self.layer_file.is_file():
            raise FusionError('LSFG is downloaded but not registered. Use Tools → Register LSFG and detect my DLL.')
        l = p['lsfg']
        text = 'version = 2\n\n[global]\n'
        text += 'dll = ' + json.dumps(install['dll']) + '\n'
        text += f'allow_fp16 = {str(l["allow_fp16"]).lower()}\n'
        text += 'log_level = "info"\nlog_file = ' + json.dumps(str(self.store(p['appid']) / 'lsfg.log')) + '\n'
        text += '\n[[profile]]\nname = ' + json.dumps('Deck Fusion ' + p['appid']) + '\n'
        text += 'active_in = [' + json.dumps(Path(p['exe']).name) + ']\n'
        for key in ('multiplier','flow_scale','performance_mode','override_present_mode','preserve_swapchain_image_count'):
            text += key + ' = ' + str(l[key]).lower() + '\n'
        text += 'pacing_mode = "vsync"\n'
        return text

    def build(self, p):
        root = Path(p['root']); parent = Path(p['exe']).parent
        prefix = parent.relative_to(root).as_posix()
        def rel(name): return name if prefix == '.' else prefix + '/' + name
        desired, overrides = {}, {}
        o, r = p['opti'], p['reshade']
        if o['enabled']:
            pkg = self.package('opti'); base = Path(pkg['path']) / pkg['payload']['directory']
            template = (base / pkg['payload']['ini']).read_text('utf-8-sig')
            schema = opti_schema(template); valid = {(s['section'], s['key']) for s in schema}
            for required in [('Upscalers','Dx11Upscaler'),('Upscalers','Dx12Upscaler'),('Upscalers','VulkanUpscaler'),('FrameGen','Enabled')]:
                if required not in valid:
                    raise FusionError('The installed OptiScaler configuration format changed. Review its upstream options before integrating this version.')
            changes = {}
            for section, values in o['overrides'].items():
                if not isinstance(values, dict): raise FusionError('Invalid advanced OptiScaler settings.')
                for key, value in values.items():
                    if (section,key) not in valid: raise FusionError(f'Unknown key in the installed OptiScaler version: {section}.{key}')
                    if not isinstance(value, (str,int,float,bool)) or any(c in str(value) for c in '\n\r\0'):
                        raise FusionError('Invalid OptiScaler INI value.')
                    changes.setdefault(section,{})[key] = str(value)
            changes.setdefault('Upscalers',{}).update({'Dx11Upscaler':o['dx11'],'Dx12Upscaler':o['dx12'],'VulkanUpscaler':o['vulkan']})
            changes.setdefault('FrameGen',{})['Enabled'] = str(o['fg']).lower()
            if o['fg']: changes['FrameGen'].update({'FGInput':'upscaler','FGOutput':'fsrfg'})
            def known_key(key, value, required=False):
                matches = [s for s in schema if s['key'].casefold() == key.casefold()]
                if not matches and required: raise FusionError(f'This OptiScaler version does not expose {key}; refusing an unverified configuration.')
                for s in matches: changes.setdefault(s['section'],{})[s['key']] = value
            if o['fsr_mode'] != 'auto':
                experimental = o['fsr_mode'] == 'fsr4_int8'
                keys = {item['key'] for item in schema}
                if experimental:
                    if not ({'Fsr4ForceModel', 'Fsr4ForceEnableInt8'} & keys):
                        raise FusionError('This OptiScaler version cannot force the FSR4 INT8 model. Update stable OptiScaler in Tools first.')
                    if not any(f.is_file() for f in base.rglob('amd_fidelityfx_upscaler_dx12.dll')):
                        raise FusionError('The installed OptiScaler package has no FFX upscaler DLL. Repair/update OptiScaler before selecting experimental FSR4.')
                # Do not force Fsr4Update=true on unsupported GPUs: upstream documents
                # that this can trigger the SDK's FSR3 fallback. Prefer its INT8 selector.
                known_key('Fsr4Update', 'auto' if experimental else 'false', experimental)
                if 'Fsr4ForceModel' in keys:
                    known_key('Fsr4ForceModel', '2' if experimental else 'auto', experimental)
                else:
                    known_key('Fsr4ForceEnableInt8', str(experimental).lower(), experimental)
                known_key('UpscalerIndex', '0' if experimental else '1', experimental)
                if o['fg']: known_key('FGIndex', '1')  # This UI offers FSR3 FG, not unsupported ML-FG.
            for key, value in opti_compat_keys(o).items():
                known_key(key, value, key != 'Fsr4EnableWatermark' or o['fsr_mode']=='fsr4_int8')
            known_key('LoadReshade', str(r['mode']=='opti').lower(), r['mode']=='opti')
            if o['spoof'] != 'auto':
                matches = [s for s in schema if s['key'] == 'Dxgi' and 'spoof' in s['section'].lower()]
                if not matches: raise FusionError('Could not find the GPU spoofing key in this OptiScaler version.')
                for s in matches: changes.setdefault(s['section'],{})[s['key']] = o['spoof']
            # Retain existing OptiScaler choices if managed by us; explicit UI values win.
            current = parent / 'OptiScaler.ini'
            tx = Transaction(root, self.store(p['appid']))
            if rel('OptiScaler.ini') in tx.manifest()['files'] and current.is_file():
                template = current.read_text('utf-8-sig', errors='replace')
            for file in base.rglob('*'):
                if not file.is_file() or file.is_symlink(): continue
                relative = file.relative_to(base).as_posix()
                if file.suffix.lower() not in ('.dll','.ini','.json','.bin','.dat'):
                    continue  # Never execute or deploy batch / setup scripts.
                if file.name.lower() == pkg['payload']['dll'].lower():
                    relative = o['proxy'] + '.dll'
                if file.name.lower() == 'optiscaler.ini': continue
                desired[rel(relative)] = file
            if o['fsr_mode'] == 'fsr4_int8' and o['fsr4_rdna2_fix']:
                targets = [name for name in desired if Path(name).name.lower() == FSR4FIX['dll']]
                if len(targets) != 1:
                    raise FusionError('Cannot identify a unique OptiScaler FidelityFX DLL target for the RDNA2 fix.')
                desired[targets[0]] = self.fsr4fix_binary()
            desired[rel('OptiScaler.ini')] = ini_patch(template, changes).encode('utf-8')
            overrides[o['proxy']] = 'n,b'
            if o['enable_nvapi'] and rel('nvapi64.dll') in desired: overrides['nvapi64'] = 'n,b'
        if r['mode'] != 'off':
            pkg = self.package('reshade'); key = 'reshade64.dll' if p['architecture']['bits'] == 64 else 'reshade32.dll'
            binary = pkg['payload']['binaries'].get(key)
            if not binary: raise FusionError('The downloaded ReShade installer does not contain the required architecture.')
            proxy = self.reshade_proxy(p)
            target = 'ReShade64.dll' if r['mode'] == 'opti' else proxy + '.dll'
            desired[rel(target)] = Path(pkg['path']) / binary
            if r['mode'] == 'standalone': overrides[proxy] = 'n,b'
            effects, textures, found_names = [], [], {}
            packs = self.packages.status().get('shaders', {})
            for pack_id in dict.fromkeys(['standard'] + r['packs']):
                if pack_id not in packs: raise FusionError(f'Install the selected shader pack in Tools first: {pack_id}')
                files, shaders = pack_files(packs[pack_id])
                for file, source in files.items(): desired[rel('deck-fusion-shaders/' + pack_id + '/' + file)] = source
                # Root plus recursive search supports repositories with or without Shaders/Textures folders.
                effects.append('.\\deck-fusion-shaders\\' + pack_id + '\\**')
                textures.append('.\\deck-fusion-shaders\\' + pack_id + '\\**')
                for s in shaders:
                    if s['file'].casefold() in found_names:
                        raise FusionError(f'Duplicate shader filename {s["file"]} in {pack_id} and {found_names[s["file"].casefold()]}. Deselect one pack to avoid ambiguous presets.')
                    found_names[s['file'].casefold()] = pack_id
            for technique in r['techniques']:
                if technique.rsplit('@',1)[-1].casefold() not in found_names:
                    raise FusionError(f'A selected effect belongs to an unselected shader pack: {technique}')
            # Explicit raw editor values are retained, but loader and managed path keys are authoritative.
            raw = r.get('raw_config','')
            current = parent / 'ReShade.ini'
            if not raw and current.is_file(): raw = current.read_text('utf-8-sig', errors='replace')
            config = ini_read(raw)
            for key, value in {'EffectSearchPaths':','.join(effects), 'TextureSearchPaths':','.join(textures),
                               'PresetPath':'.\\DeckFusionPreset.ini', 'PerformanceMode':str(int(r['performance'])),
                               'SkipLoadingDisabledEffects':'1'}.items(): ini_set(config,'GENERAL',key,value)
            ini_set(config,'INPUT','KeyOverlay',f'{r["overlay_key"]},0,0,0')
            ini_set(config,'PROXY','EnableProxyLibrary','0')
            ini_set(config,'OVERLAY','TutorialProgress','4')
            desired[rel('ReShade.ini')] = ini_write(config).encode('utf-8')
            desired[rel('DeckFusionPreset.ini')] = preset_text(r).encode('utf-8')
        runtime = {'schema':1, 'appid':p['appid'], 'api':p['api'], 'lsfg':p['lsfg'],
                   'lsfg_config':str(self.store(p['appid'])/'lsfg.toml'), 'dll_overrides':overrides,
                   'custom_dll_overrides':parse_dll_overrides(p['wine']['custom_overrides'], strict=True),
                   'requested_fsr_mode':o['fsr_mode'], 'opti_enabled':o['enabled'],
                   'fsr4_watermark':o['fsr4_watermark'], 'watermark_strategy':'absent-sdk-variable', 'base_fps':p['base_fps'], 'enable_nvapi':o['enabled'] and o['enable_nvapi']}
        if bg3_renderer(p['exe'], p['root'], p['appid']) and (o['enabled'] or r['mode'] != 'off'):
            runtime['bg3_target'] = {'root': p['root'], 'exe': p['exe']}
        saved_profile = copy.deepcopy(p); saved_profile['backup_conflicts'] = False
        extras = {'profile.json':encoded(saved_profile), 'runtime.json':encoded(runtime)}
        if p['lsfg']['enabled']: extras['lsfg.toml'] = self.config_lsfg(p).encode('utf-8')
        return desired, extras, runtime

    def review(self, raw, launch: str, remove=False, force_repair=False):
        boolean(force_repair)
        if remove and force_repair: raise FusionError("Force repair is for installation, not Restore.")
        if remove:
            raw = self.profile(raw['appid'])
            raw['lsfg']['enabled'] = False; raw['opti']['enabled'] = False
            raw['opti']['fg'] = False; raw['reshade']['mode'] = 'off'; raw['base_fps'] = 0
            raw['wine']['custom_overrides'] = ''
        p = self.validate(raw, launch)
        self.safety(p)
        tx = Transaction(Path(p['root']), self.store(p['appid']))
        if tx.pending(): raise FusionError('Recover the unfinished operation before applying another configuration.')
        if remove:
            desired, extras, runtime = {}, {}, {}
            old = tx.manifest()
            new_launch = restore_launch(launch, old.get('installed_launch') or '', old.get('original_launch') or '', self.wrapper, p['appid'])
        else:
            context = inspect_overrides(self, p, launch)
            allocated, fixes = resolve_loaders(p, p['api'], context, force_repair)
            if fixes:
                raise FusionError('An existing DLL/override occupies a graphics loader. Use Apply settings to review the proposed free loader names.')
            desired, extras, runtime = self.build(p)
            guard_payload(self, p, desired, context, force_repair)
            new_launch = compose_launch(launch, self.wrapper, p['appid'])
        result = tx.inspect(desired, p['backup_conflicts'], force_repair)
        result.update({'profile':p, 'launch_before':launch, 'launch_after':new_launch,
                       'effective_runtime':runtime,
                       'configuration_hash': hashlib.sha256(b''.join(encoded(k) + extras[k] for k in sorted(extras))).hexdigest(), 'warnings':[
                           'A clean anti-cheat scan is not proof of safety. Use only games whose rules permit injection.',
                           'Restart the game after applying. This is not a live game-memory editor.',
                           'Only DXVK/VKD3D use this base FPS cap. Native Vulkan uses the game limiter.'
                       ]})
        return result

    def requirements(self, raw):
        """Read-only dependency list for the wizard. Never downloads implicitly."""
        p = migrate_profile(raw)
        status = self.packages.status()
        required = []
        for component, enabled in [('lsfg', p['lsfg']['enabled']), ('opti', p['opti']['enabled']),
                                   ('reshade', p['reshade']['mode'] != 'off')]:
            if enabled:
                info = status.get(component, {})
                ready = bool(info.get('path') and Path(info['path']).is_dir())
                if component == 'opti' and ready and p['opti']['fsr_mode'] == 'fsr4_int8':
                    shape = self.schema()
                    ready = bool(shape.get('fsr4_int8') and shape.get('fsr4_sdk'))
                required.append({'kind': 'component', 'id': component, 'ready': ready,
                                 'version': info.get('version', '')})
        if p['opti']['enabled'] and p['opti']['fsr_mode'] == 'fsr4_int8' and p['opti']['fsr4_rdna2_fix']:
            try:
                self.fsr4fix_binary(); ready = True
            except (FusionError, OSError):
                ready = False
            required.append({'kind': 'component', 'id': 'fsr4fix', 'ready': ready,
                             'version': FSR4FIX['version'], 'label': 'Community FSR 4.1.1b RDNA2 fix'})
        if p['reshade']['mode'] != 'off':
            for key in dict.fromkeys(['standard'] + p['reshade']['packs']):
                info = status.get('shaders', {}).get(key, {})
                required.append({'kind': 'shader', 'id': key,
                                 'ready': bool(info.get('path') and Path(info['path']).is_dir()),
                                 'version': info.get('commit', '')[:8]})
        registered = read_json(self.data / 'lsfg-install.json', {})
        ready_lsfg = bool(registered.get('dll') and Path(registered['dll']).is_file() and self.layer_file.is_file())
        return {'items': required, 'needs_registration': p['lsfg']['enabled'] and not ready_lsfg}

    def plan(self, raw, launch: str, remove=False, force_repair=False):
        """Resolve settings and collect one confirmation; hard safety stops stay hard."""
        p = migrate_profile(raw)
        p['backup_conflicts'] = False  # Approval is per operation, never a sticky permission.
        result = {'profile': p, 'resolutions': [], 'blockers': [], 'warnings': [],
                  'conflicts': [], 'changes': [], 'file_count': 0, 'remove': remove,
                  'force_repair': force_repair, 'repairs': [], 'repair_available': False}
        try:
            boolean(force_repair)
            if remove and force_repair: raise FusionError('Force repair is for installation, not Restore.')
            game = self.game(p['appid'])
            candidate = Path(p['exe']).expanduser()
            if not candidate.is_absolute(): candidate = Path(game['root']) / candidate
            if not candidate.is_file() or not candidate.resolve().is_relative_to(Path(game['root']).resolve()):
                raise FusionError('Choose the actual executable in Library or in step 1 of the wizard.')
            effective = self.detect_api(p, launch)['api'] if p['api'] == 'auto' else p['api']
            if not remove:
                p, fixes, warnings = resolve_settings(p, effective, self.hardware())
                context = inspect_overrides(self, p, launch)
                p, loader_fixes = resolve_loaders(p, effective, context, force_repair)
                fixes.extend(loader_fixes)
                warnings.extend(context['warnings'])
                result.update(profile=p, resolutions=fixes, warnings=warnings, dll_context=context)
            # Main controls are authoritative. Make overwritten advanced values visible.
            if not remove and p['opti']['enabled']:
                shape = self.schema(p['appid'])['opti']
                expected = {('Upscalers','Dx11Upscaler'):p['opti']['dx11'],
                            ('Upscalers','Dx12Upscaler'):p['opti']['dx12'],
                            ('Upscalers','VulkanUpscaler'):p['opti']['vulkan'],
                            ('FrameGen','Enabled'):str(p['opti']['fg']).lower()}
                if p['opti']['fg']:
                    expected.update({('FrameGen','FGInput'):'upscaler', ('FrameGen','FGOutput'):'fsrfg'})
                for item in shape:
                    key, section = item['key'], item['section']
                    for compat_key, value in opti_compat_keys(p['opti']).items():
                        if key.casefold() == compat_key.casefold(): expected[(section,key)] = value
                    if key == 'LoadReshade': expected[(section,key)] = str(p['reshade']['mode']=='opti').lower()
                    if key == 'Dxgi' and 'spoof' in section.lower() and p['opti']['spoof'] != 'auto': expected[(section,key)] = p['opti']['spoof']
                    if p['opti']['fsr_mode'] != 'auto':
                        exp = p['opti']['fsr_mode'] == 'fsr4_int8'
                        fsr_values = {'Fsr4Update':'auto' if exp else 'false',
                                      'Fsr4ForceEnableInt8':str(exp).lower(), 'Fsr4ForceModel':'2' if exp else 'auto',
                                      'UpscalerIndex':'0' if exp else '1',
                                      'Fsr4EnableWatermark':'true' if p['opti']['fsr4_watermark'] else 'auto'}
                        if key in fsr_values: expected[(section,key)] = fsr_values[key]
                for (section,key), value in expected.items():
                    values = p['opti']['overrides'].get(section, {})
                    if key in values and str(values[key]).lower() != str(value).lower():
                        result['resolutions'].append({'id':f'ini-{section}-{key}', 'title':f'Align advanced {section}.{key}',
                            'detail':'Use the main control instead of this conflicting advanced value.', 'before':values[key], 'after':value})
                        del values[key]
            if not remove and p['opti']['enabled']:
                if p['opti']['fsr_mode'] == 'fsr4_int8' and p['opti']['fsr4_rdna2_fix']:
                    warnings.append('Selected community FSR 4.1.1b INT8 RDNA2 ghosting fix from the3rdparty1917/fsr4xyz. Replace the OptiScaler FidelityFX upscaler DLL using tracked backups. This is a community Windows build used through Proton; Steam Deck rendering is not verified.')
                if not p['opti']['fsr4_watermark']:
                    warnings.append('Watermark off: remove MLSR-WATERMARK entirely and use upstream auto in OptiScaler.ini. A zero-valued variable can still enable FidelityFX banners. Apply and fully restart; this does not disable INT8.')
                if p['opti']['mouse_input'] == 'polling':
                    warnings.append('OptiScaler manual mouse polling is enabled. Pause the game first: polling cannot block clicks from also reaching the game. Close CET and ReShade menus while using OptiScaler.')
                if p['opti']['steam_input'] == 'keep':
                    warnings.append('Keep Steam Input: OptiScaler will not disable external overlays. This can help Steam controller mappings, but may conflict with some frame-generation paths.')
            review = self.review(p, launch, remove, force_repair)
            result.update(review)
            result['warnings'] = list(dict.fromkeys(warnings + review['warnings'])) if not remove else review['warnings']
            # Display simple inherited launch-env conflicts, without evaluating shell code.
            inherited = {'GAMESCOPE_WAYLAND_DISPLAY':'gamescope-0'}
            assignments = launch_assignments(launch)
            inherited.update(assignments)
            env = launch_environment(review['effective_runtime'], inherited)
            for key, value in assignments.items():
                if key == 'WINEDLLOVERRIDES':
                    merged = env.get('WINEDLLOVERRIDES', value)
                    if value != merged:
                        result['resolutions'].append({'id':'env-dll-overrides', 'title':'Merge Wine DLL loader settings',
                            'detail':'Keep existing mod load orders; merge your explicit custom entries and the separately allocated graphics loaders.',
                            'before':value, 'after':merged})
                elif key not in env:
                    result['resolutions'].append({'id':f'env-{key}', 'title':f'Clear inherited {key}',
                        'detail':'Unset this conflicting override in the game process only. The original Steam launch text is retained for restoration.',
                        'before':value, 'after':'(unset)'})
                elif env[key] != value:
                    result['resolutions'].append({'id':f'env-{key}', 'title':f'Use the profile value for {key}',
                        'detail':'The wrapper overrides this inherited value for this game only. The original launch text is retained for restoration.',
                        'before':value, 'after':env[key]})
            if not remove:
                old_custom = parse_dll_overrides(self.profile(p['appid'])['wine']['custom_overrides'], strict=True)
                new_custom = parse_dll_overrides(p['wine']['custom_overrides'], strict=True)
                for name in sorted(set(old_custom) | set(new_custom)):
                    if old_custom.get(name) != new_custom.get(name) or (name in old_custom) != (name in new_custom):
                        result['resolutions'].append({'id': 'custom-' + name, 'title': f'Custom Wine override: {name}',
                            'detail': 'Explicit profile edit. Removing it returns to inherited Steam/Wine settings; no DLL or registry entry is deleted.',
                            'before': old_custom.get(name, '(inherit)') or '(disabled)',
                            'after': new_custom.get(name, '(inherit)') or '(disabled)'})
                combined = {**context['effective_user'], **review['effective_runtime'].get('dll_overrides', {})}
                result['dll_summary'] = {'effective': ';'.join(f'{name}={order}' for name, order in combined.items()),
                    'opti': (p['opti']['proxy'] + '.dll') if p['opti']['enabled'] else 'off',
                    'reshade': 'ReShade64.dll via OptiScaler' if p['reshade']['mode'] == 'opti' else
                        self.reshade_proxy(p) + '.dll' if p['reshade']['mode'] == 'standalone' else 'off',
                    'note': 'Prefix defaults are displayed, not copied into launch options. Runtime also merges inherited environment overrides.'}
            result['approval_token'] = hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        except ManagedFilesChanged as error:
            result['repairs'] = error.repairs
            result['repair_available'] = not remove
            result['blockers'].append({'title':'Tracked files are missing or changed', 'detail':str(error)})
        except FusionError as error:
            result['blockers'].append({'title':'Needs attention before applying', 'detail':str(error)})
        return result

    def prepare_approved(self, raw, launch, approval, remove=False, progress=lambda *_: None, launch_actual=None, force_repair=False):
        fresh = self.plan(raw, launch, remove, force_repair)
        if fresh['blockers']:
            raise FusionError('Cannot apply: ' + '; '.join(x['detail'] for x in fresh['blockers']))
        if not isinstance(approval, str) or approval != fresh.get('approval_token'):
            raise FusionError('Settings, components or game files changed after confirmation. Click Apply settings again to review the updated changes. Nothing was installed.')
        accepted = copy.deepcopy(fresh['profile'])
        accepted['backup_conflicts'] = True
        return self.prepare(accepted, launch, remove, progress, launch_actual,
                            expected_state=fresh['file_state'], expected_configuration=fresh['configuration_hash'],
                            force_repair=force_repair, expected_manifest=fresh['manifest_hash'])

    def prepare(self, raw, launch: str, remove=False, progress=lambda *_: None, launch_actual=None, expected_state=None, expected_configuration=None, force_repair=False, expected_manifest=None):
        boolean(force_repair)
        if force_repair and (expected_state is None or expected_configuration is None):
            raise FusionError('Force repair requires a confirmed repair plan. Click Apply to review it first.')
        review = self.review(raw, launch, remove, force_repair)
        if force_repair and review['manifest_hash'] != expected_manifest:
            raise FusionError('The managed-file record changed after confirmation. Review the repair again.')
        p = review['profile']
        if expected_state is not None and (review['file_state'] != expected_state or review['configuration_hash'] != expected_configuration):
            # The configuration hash excludes consent, see review() below.
            raise FusionError('Files or configuration changed during approval. Click Apply again; no files were changed.')
        consent = p['backup_conflicts']
        p['backup_conflicts'] = False
        if remove:
            desired = {}
            disabled = copy.deepcopy(p)
            disabled['lsfg']['enabled'] = False; disabled['opti']['enabled'] = False
            disabled['reshade']['mode'] = 'off'; disabled['base_fps'] = 0
            extras = {'profile.json':encoded(disabled), 'runtime.json':encoded({'bypass':True})}
        else: desired, extras, _ = self.build(p)
        tx = Transaction(Path(p['root']), self.store(p['appid']))
        self.safety(p)  # Recheck immediately before filesystem changes, not just during preview.
        return tx.prepare(desired, extras, launch if launch_actual is None else launch_actual, review['launch_after'], consent, progress, reset_origin=remove, expected_state=expected_state,
                          force_repair=force_repair, expected_manifest=expected_manifest)

    def finish(self, appid, token, verified):
        game = self.game(appid); tx = Transaction(Path(game['root']), self.store(appid))
        return tx.finalize(token, verified)

    def rollback(self, appid, token):
        game = self.game(appid); p = self.profile(appid)
        pending = read_json(self.store(appid) / 'pending.json', None)
        if p['exe'] and Path(p['exe']).is_file(): self.safety({**p,'opti':{'enabled':False},'lsfg':{'enabled':False},'reshade':{'mode':'off'}})
        tx = Transaction(Path(pending['root'] if pending else game['root']), self.store(appid))
        return tx.rollback(token)

    def hot_lsfg(self, appid, changes):
        p = self.profile(appid)
        if not p['lsfg']['enabled']: raise FusionError('Apply an LSFG-enabled profile first.')
        for key, value in changes.items():
            if key not in ('multiplier','flow_scale','performance_mode'): raise FusionError('This LSFG setting requires restart.')
            p['lsfg'][key] = value
        p = self.validate(p)
        if (self.store(appid)/'pending.json').exists(): raise FusionError('Finish or recover the pending operation first.')
        atomic_bytes(self.store(appid)/'lsfg.toml',self.config_lsfg(p).encode())
        atomic_json(self.store(appid)/'profile.json',p)
        return p

    def sync_from_disk(self, appid):
        p = self.profile(appid)
        if not p['exe']: raise FusionError('Select and apply a game executable first.')
        parent = Path(p['exe']).parent
        opt = parent/'OptiScaler.ini'
        if opt.is_file():
            ini = ini_read(opt.read_text('utf-8-sig',errors='replace'))
            p['opti']['overrides'] = {s:dict(ini[s]) for s in ini.sections() if s != '__ROOT__'}
            for src,dst in [('Dx11Upscaler','dx11'),('Dx12Upscaler','dx12'),('VulkanUpscaler','vulkan')]:
                p['opti'][dst] = ini.get('Upscalers',src,fallback=p['opti'][dst])
            p['opti']['fg'] = ini.get('FrameGen','Enabled',fallback='false').lower() == 'true'
            # Imported overlay values, not a previous preset, become authoritative.
            p['opti']['fsr_mode'] = 'auto'
            p['opti']['fsr4_watermark'] = any(
                str(value).lower() == 'true' for section in ini.sections()
                for key, value in ini[section].items() if key.casefold() == 'fsr4enablewatermark')
            # Preserve explicitly imported in-game choices for the new direct controls.
            values = {key.casefold(): str(value).lower() for section in ini.sections()
                      for key, value in ini[section].items()}
            p['opti']['mouse_input'] = {'true':'polling','false':'window'}.get(values.get('manualinputpolling'), 'auto')
            p['opti']['steam_input'] = {'false':'keep','true':'disable'}.get(values.get('disableoverlays'), 'auto')
        preset = parent/'DeckFusionPreset.ini'
        if preset.is_file():
            text = preset.read_text('utf-8-sig',errors='replace'); ini = ini_read(text)
            p['reshade']['raw_preset'] = text
            p['reshade']['techniques'] = [x.strip() for x in ini.get('__ROOT__','Techniques',fallback='').split(',') if x.strip()]
            p['reshade']['uniforms'] = {s:dict(ini[s]) for s in ini.sections() if s.lower().endswith('.fx')}
        cfg = parent/'ReShade.ini'
        if cfg.is_file():
            text = cfg.read_text('utf-8-sig',errors='replace'); ini = ini_read(text)
            p['reshade']['raw_config'] = text
            p['reshade']['performance'] = ini.get('GENERAL','PerformanceMode',fallback='1') == '1'
        return p

    def _diagnostic_target(self, appid, selected_exe=None):
        # Inspect the current draft, not only the last applied profile. Keep the
        # installation root authoritative and reject symlinks/paths outside it.
        game = self.game(appid)
        root = Path(game['root']).resolve()
        value = selected_exe if selected_exe is not None else self.profile(appid).get('exe', '')
        if not isinstance(value, str) or not value:
            raise FusionError('Select a game executable in Library before inspecting its files.')
        candidate = Path(value).expanduser()
        if not candidate.is_absolute(): candidate = root / candidate
        if not candidate.is_relative_to(root):
            raise FusionError('The diagnostic executable must be inside this game installation.')
        candidate = safe_target(root, candidate.relative_to(root).as_posix())
        if not candidate.is_file(): raise FusionError('The selected game executable no longer exists.')
        return root, candidate

    def game_diagnostics(self, appid, selected_exe=None):
        root, candidate = self._diagnostic_target(appid, selected_exe)
        result = game_diagnostics(root, candidate, self.store(appid))
        result.update(game=self.game(appid)['name'], selected_exe=str(candidate))
        return result

    def mod_diagnostics(self, appid, selected_exe=None):
        # Optional adapter for this game's known frameworks, not a core-tool gate.
        root, candidate = self._diagnostic_target(appid, selected_exe)
        result = cyberpunk_diagnostics(root, str(candidate), self.store(appid))
        result.update(title='Optional Cyberpunk mod evidence', selected_exe=str(candidate))
        return result

    def diagnostics(self, appid=''):
        status = self.packages.status()
        result = {'version':'0.3-beta6','data':str(self.data),'home':str(self.home),
                  'packages':status,'legacy_layers':self.old_layers(),
                  'settings':self.settings(), 'bundled':self.packages.bundle_status(),
                  'https':tls_context()[1], 'last_error':read_json(self.data/'last-error.json',None),
                  'lsfg_install':read_json(self.data/'lsfg-install.json',None),
                  'hardware': self.hardware(), 'hardware_validated':False}
        if appid:
            p = self.profile(appid); store = self.store(appid)
            result['profile'] = p; result['manifest'] = read_json(store/'manifest.json',{}); result['pending'] = read_json(store/'pending.json',None)
            result['last_launch'] = read_json(store/'last-launch.json',None)
            if p['exe'] and Path(p['exe']).is_file():
                result['running'] = running_game(Path(p['exe']), p['appid'])
                folder = Path(p['exe']).parent
                for name in ('ReShade.log','OptiScaler.log'):
                    f = folder/name
                    if f.is_file():
                        with f.open('rb') as handle:
                            handle.seek(max(0,f.stat().st_size-18000)); result[name] = handle.read().decode('utf-8',errors='replace')
        return result
