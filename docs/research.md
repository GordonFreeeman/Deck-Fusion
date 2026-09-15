# Primary-source implementation notes

Reviewed 12 September 2026. These explain requested configuration, not measured results on the user's hardware.

## Gamescope and LSFG

Valve source: https://github.com/ValveSoftware/gamescope/blob/master/layer/VkLayer_FROG_gamescope_wsi.cpp

The 1.1.0 option set `ENABLE_GAMESCOPE_WSI=1` and `GAMESCOPE_WSI_FRAME_LIMITER_AWARE=0`. That flag controls limiter awareness; it is not an independent limiter for generated frames. The user reported that it did not cap LSFG. This route is superseded in 1.1.1.

Official LSFG troubleshooting: https://lsfg-vk.dev/docs/troubleshooting/basic-troubleshooting-steps/
Official pacing limitations: https://lsfg-vk.dev/docs/configuration/pacing-modes/
LSFG configuration reference: https://lsfg-vk.dev/docs/configuration/configuration-options/
Mesa presentation override: https://docs.mesa3d.org/envvars.html#envvar-MESA_VK_WSI_PRESENT_MODE

Upstream specifically recommends `ENABLE_GAMESCOPE_WSI=0` when using VSync pacing on Gamescope/Steam Deck. Version 1.1.1 follows that documented troubleshooting path only when the per-game option and LSFG are enabled and a Gamescope launch environment is present. It sets `DISABLE_GAMESCOPE_WSI=1`, removes the now-irrelevant limiter-awareness override, and sets `MESA_VK_WSI_PRESENT_MODE=fifo` to prevent an inherited immediate/mailbox mode from defeating FIFO. It does not disable Gamescope itself or change Steam's global Performance settings. Disabling its WSI layer can affect HDR; this tradeoff is disclosed before Apply.

The existing LSFG configuration retains `override_present_mode=true` and `pacing_mode="vsync"`. DXVK/VKD3D base caps remain separate, and the user's 33 base / 2x choice is not rewritten to 30. No binary patch, fabricated LSFG output-cap variable, limiter-file mutation, or system modification is used. The Gamescope limiter file represents a limiter state, not a numeric target FPS; it is used only as an environment-detection signal and left untouched.

Upstream documents only VSync pacing, without a separate pacing mode that establishes arbitrary 66-to-60 resampling. The change is therefore a corrected compatibility route, NOT verified independent post-FG limiting. VSync back-pressure, frame selection, output-rate changes and actual interaction with the Deck Performance slider remain hardware checks. `last-launch.json` labels its recorded values as requested launch environment, not measured FPS.

## FSR4 INT8

OptiScaler stable release notes: https://github.com/optiscaler/OptiScaler/releases/tag/v0.9.4
Exact stable template: https://github.com/optiscaler/OptiScaler/blob/v0.9.4/OptiScaler.ini
General API and input/output support: https://github.com/optiscaler/OptiScaler
Compatibility notes: https://github.com/optiscaler/OptiScaler/wiki/FSR4-Compatibility
Model-selector issue, firsthand Linux report rather than proof for Steam Deck: https://github.com/optiscaler/OptiScaler/issues/1059

The stable template selects FSR4 through the existing FSR3.x path. Stable 0.9.4 introduces `Fsr4ForceEnableInt8`, alongside `Fsr4Update`, `UpscalerIndex` and `Fsr4EnableWatermark`. The release notes warn against forcing Fsr4Update=true on unsupported GPUs and explain the FSR4/FSR4-i8/FSR3 watermark distinction. Newer schemas exposing `Fsr4ForceModel` use value 2 for INT8. Selection is based on the installed template; the plugin refuses the experimental preset if the required keys or upscaler DLL are absent. It does not download leaked payloads or alter GPU drivers.

Official FSR4 support listed by OptiScaler is RDNA4 and RDNA3 desktop GPUs, not the Steam Deck. An INT8 request is not proof that the SDK initialized that model. No assertion of acceptable performance, image quality, compatibility with every game, or elimination of fallback is made. Native Vulkan FSR4 is not being added; that route uses DX12 interop.

## Diagnostic watermark, not an INT8 requirement

OptiScaler template: https://github.com/optiscaler/OptiScaler/blob/master/OptiScaler.ini
Maintainer's matching issue response: https://github.com/optiscaler/OptiScaler/issues/1078#issuecomment-5023532964

The matching issue reports the watermark persisting with `Fsr4EnableWatermark=false`; a maintainer points to `PROTON_FSR4_INDICATOR=1` and `FSR4_WATERMARK=1`. Version 1.1.1 makes the main watermark control authoritative in preset and advanced modes, writes false by default, and unsets those two inherited diagnostic variables for the game process when OptiScaler is enabled and the watermark is off. It does not set them to the string `0`, since a consumer can test mere presence. It leaves the actual FSR4 model/backend controls unchanged. If the user explicitly opts in after schema-3 migration, the preference is retained.

The user's supplied photograph shows an FSR4-I8 diagnostic banner. The plugin did not independently inspect their shader, GPU, or frame-time output; no new runtime-success measurement is claimed.

## DLSS

NVIDIA hardware matrix: https://www.nvidia.com/en-eu/geforce/technologies/dlss/
OptiScaler's own explanation of inputs and outputs: https://github.com/optiscaler/OptiScaler

Native DLSS output and translating a game's DLSS input to FSR/XeSS are different. GPU spoofing can expose the input menu without providing NVIDIA DLSS execution on AMD. PCI inventory is only a hardware hint; it is not an active-renderer probe. No conclusion about the user's previous output is possible from a menu label alone.

## Native confirmation

Decky UI modal declarations: https://github.com/SteamDeckHomebrew/decky-frontend-lib/blob/main/src/components/Modal.ts

The integration uses showModal and ConfirmModal with onOK/onCancel/closeModal, bOKDisabled, bDisableBackgroundDismiss and explicit button labels. Native Decky supplies the actual focus/controller behavior. The browser host used for inspection substitutes these widgets and cannot certify native Steam Input interactions.
