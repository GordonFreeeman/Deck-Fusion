LSFG_VERSION = '2.0.0'
LSFG_INDEX = 'https://builds.lsfg-vk.dev/'
OPTI_API = 'https://api.github.com/repos/optiscaler/OptiScaler/releases/latest'
FSR4FIX = {
    'version': '4.1.1b',
    'url': 'https://github.com/the3rdparty1917/fsr4xyz/releases/download/4.1.1b/FSR_4.1.1b_INT8_with_RDNA2_fix.7z',
    'sha256': '66e9a818e0c914def7712c8dac06b08e64a64dbcfe77f3162d43ea6de93869ff',
    'dll': 'amd_fidelityfx_upscaler_dx12.dll',
}
RESH_SITE = 'https://reshade.me/'
SHADER_PACKS = [
    {'id': 'standard', 'name': 'ReShade standard headers', 'repo': 'crosire/reshade-shaders', 'branch': 'slim', 'description': 'Required shared headers and basic shaders.'},
    {'id': 'sweetfx', 'name': 'SweetFX', 'repo': 'CeeJayDK/SweetFX', 'branch': 'master', 'description': 'Curves, DPX, Vibrance, Tonemap, SMAA and LumaSharpen.'},
    {'id': 'fxshaders', 'name': 'FXShaders', 'repo': 'luluco250/FXShaders', 'branch': 'master', 'description': 'CAS and other sharpening / post-processing effects.'},
    {'id': 'quint', 'name': 'qUINT', 'repo': 'martymcmodding/qUINT', 'branch': 'master', 'description': 'MXAO, bloom, depth of field and Lightroom. Depth effects are expensive.'},
    {'id': 'prod80', 'name': 'prod80', 'repo': 'prod80/prod80-ReShade-Repository', 'branch': 'master', 'description': 'Extensive colour correction, contrast, bloom and film effects.'},
    {'id': 'fubax', 'name': 'Fubax shaders', 'repo': 'fubaxiusz/fubax-shaders', 'branch': 'master', 'description': 'Film effects, AA, sharpening and miscellaneous filters.'},
    {'id': 'legacy', 'name': 'Legacy ReShade shaders', 'repo': 'crosire/reshade-shaders', 'branch': 'legacy', 'description': 'Original reference shader repository.'},
]
DEFAULT_PROFILE = {
    'schema': 4, 'appid': '', 'name': '', 'root': '', 'exe': '', 'api': 'auto',
    'lsfg': {'enabled': False, 'multiplier': 2, 'flow_scale': 0.75, 'performance_mode': True,
             'allow_fp16': True, 'respect_deck_limiter': True, 'override_present_mode': True, 'preserve_swapchain_image_count': False},
    'base_fps': 0,
    'opti': {'enabled': False, 'proxy': 'dxgi', 'dx11': 'fsr31', 'dx12': 'fsr31', 'vulkan': 'fsr31',
             'fsr_mode': 'auto', 'fsr4_rdna2_fix': False, 'fsr4_watermark': False, 'mouse_input': 'auto', 'steam_input': 'auto', 'fg': False, 'enable_nvapi': False, 'spoof': 'auto', 'overrides': {}},
    'reshade': {'mode': 'off', 'proxy': 'auto', 'performance': True, 'techniques': [], 'uniforms': {},
                'packs': ['standard', 'sweetfx', 'fxshaders'], 'raw_preset': '', 'raw_config': '', 'overlay_key': 36},
    'wine': {'custom_overrides': '', 'opti_proxy_manual': False, 'reshade_proxy_manual': False},
    'setup': {'version': 0, 'runtimes': [], 'runtime_prefix': ''},
    'backup_conflicts': False,
}
