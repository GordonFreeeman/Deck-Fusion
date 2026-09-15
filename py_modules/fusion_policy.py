"""Conservative feature resolution. No game, Steam, or GPU driver mutations."""
from __future__ import annotations
import copy
from pathlib import Path


# Explicit RDNA2 PCI IDs from the Linux amdgpu table; APU names cross-checked
# against pciutils/pciids. Unknown AMD devices are never classified by guesswork.
RDNA2_PCI = frozenset('73a0 73a1 73a2 73a3 73a5 73a8 73a9 73ab 73ac 73ad 73ae 73af 73bf 164d 1681 73c0 73c1 73c3 73da 73db 73dc 73dd 73de 73df 73e0 73e1 73e2 73e3 73e8 73e9 73ea 73eb 73ec 73ed 73ef 73ff 7420 7421 7422 7423 7424 743f 163f 1435 164e 1506'.split())


def hardware_info(sysfs=Path('/sys')) -> dict:
    """Read-only inventory. An architecture recommendation is not a renderer probe."""
    devices = []
    for card in sorted((sysfs / 'class/drm').glob('card[0-9]*')):
        if '-' in card.name:
            continue
        try:
            vendor = (card / 'device/vendor').read_text().strip().lower()
            device = (card / 'device/device').read_text().strip().lower()
            rdna2 = vendor == '0x1002' and device.removeprefix('0x') in RDNA2_PCI
            devices.append({'card': card.name, 'vendor': vendor, 'device': device,
                            'architecture': 'rdna2' if rdna2 else 'other_or_unknown'})
        except OSError:
            continue
    try:
        model = (sysfs / 'devices/virtual/dmi/id/product_name').read_text().strip()
    except OSError:
        model = ''
    deck = model.casefold() in ('jupiter', 'galileo', 'steam deck')
    # Mixed-GPU systems need an explicit choice: inventory cannot tell which GPU
    # renders this game, even when the chassis is a Deck with an external GPU.
    recommended = all(d['architecture'] == 'rdna2' for d in devices) if devices else deck
    reason = ('Detected Steam Deck / RDNA2 graphics.' if recommended else
              'Mixed graphics adapters detected; choose the fix manually for the rendering GPU.' if len(devices) > 1 else
              'RDNA2 was not positively identified; the community fix defaults off.')
    return {'devices': devices, 'model': model, 'steam_deck': deck,
            'has_nvidia': any(d['vendor'] == '0x10de' for d in devices),
            'known_non_nvidia': bool(devices) and all(d['vendor'] != '0x10de' for d in devices),
            'has_rdna2': any(d['architecture'] == 'rdna2' for d in devices) or (deck and not devices),
            'fsr4_rdna2_recommended': recommended, 'fsr4_rdna2_reason': reason,
            'note': 'PCI inventory only; actual rendering GPU and runtime upscaler are not verified.'}


def resolve_settings(profile: dict, effective_api: str, hardware: dict) -> tuple[dict, list, list]:
    """Propose deterministic fixes. The caller must display them before accepting."""
    p = copy.deepcopy(profile)
    l, o, r = p['lsfg'], p['opti'], p['reshade']
    fixes, warnings = [], []

    def fix(obj, key, value, identifier, title, detail):
        if obj[key] != value:
            fixes.append({'id': identifier, 'title': title, 'detail': detail,
                          'before': obj[key], 'after': value})
            obj[key] = value

    if o['fg'] and not o['enabled']:
        fix(o, 'fg', False, 'inactive-fg', 'Clear inactive OptiScaler frame generation',
            'OptiScaler is disabled. Its frame-generation switch will be off too.')
    if l['enabled'] and o['fg']:
        fix(o, 'fg', False, 'double-fg', 'Use LSFG as the only frame generator',
            'Keep LSFG enabled and disable OptiScaler FG. Upscaling can remain enabled.')
    if o['enabled'] and o['fg'] and effective_api != 'dx12':
        fix(o, 'fg', False, 'fg-api', 'Disable the DX12-only OptiScaler FG preset',
            'The selected renderer is not DirectX 12. Upscaling is not disabled.')
    if r['mode'] == 'opti' and not o['enabled']:
        fix(r, 'mode', 'standalone', 'reshade-loader', 'Load ReShade standalone',
            'OptiScaler is off. ReShade will use its own loader instead.')
    if r['mode'] == 'standalone' and o['enabled']:
        fix(r, 'mode', 'opti', 'proxy-collision', 'Load ReShade through OptiScaler',
            'OptiScaler is active. Use its ReShade64.dll companion loader, preserving backups.')
    if l['enabled'] and l['respect_deck_limiter']:
        fix(l, 'override_present_mode', True, 'fifo-pacing', 'Keep LSFG FIFO / VSync pacing enabled',
            'Gamescope limiter integration keeps LSFG\'s documented VSync pacing, not an immediate-mode override.')
        warnings.append('Deck limiter compatibility: use the Mesa FIFO path with Gamescope WSI disabled for this game. '
                        'The Gamescope compositor and Steam Performance menu stay active. Set your desired Deck limit yourself. '
                        'This is the upstream VSync compatibility path, not a separate LSFG output limiter. '
                        'VSync back-pressure may lower the base rate; displayed FPS still needs device verification. '
                        'Disabling the WSI layer can affect HDR. Restart required.')

    active = {'dx11': 'dx11', 'dx12': 'dx12', 'vulkan': 'vulkan'}.get(effective_api)
    if o['enabled'] and active and o[active] == 'dlss' and hardware.get('known_non_nvidia'):
        replacement = 'fsr31'
        fix(o, active, replacement, 'native-dlss', 'Replace unsupported native NVIDIA DLSS output',
            'This machine has no NVIDIA GPU. The game may still expose DLSS as INPUT; the actual OUTPUT will be FSR 3.x.')
    if o['enabled'] and active and o['fsr_mode'] == 'fsr3' and o[active] not in ('fsr31','fsr31_12'):
        fix(o, active, 'fsr31', 'fsr3-route', 'Use the selected FSR 3.x output preset',
            'The explicit FSR 3.x preset takes precedence over a conflicting per-API output. Choose upstream / advanced mode to keep custom outputs.')
    if o['enabled'] and o['fsr_mode'] == 'fsr4_int8':
        if active:
            output = 'fsr31' if effective_api == 'dx12' else 'fsr31_12'
            fix(o, active, output, 'fsr4-route', 'Route the selected API through the FSR 3.x/4 backend',
                'FSR 4 uses OptiScaler\'s fsr31 path for DX12, or fsr31_12 for DX11/Vulkan interop.')
        warnings.append('Experimental FSR 4 INT8: Steam Deck is not officially supported. '
                        'An up-to-date Proton/VKD3D and compatible Mesa are needed. FSR3 fallback, visual errors or slowdowns remain possible. '
                        'The diagnostic watermark is optional and off by default. Enable it temporarily to check FSR4-i8; '
                        'the game\'s DLSS menu label alone is not proof.')
        if effective_api in ('dx11', 'vulkan'):
            warnings.append('FSR 4 uses DX12 interop for this renderer. Vulkan interop requires Proton 11+ per upstream; it is not a native Vulkan FSR 4 implementation.')
    return p, fixes, warnings
