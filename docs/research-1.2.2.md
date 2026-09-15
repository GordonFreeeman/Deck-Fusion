# Source-backed integration decisions for 1.2.2

These are configuration/source findings, not a physical Steam Deck validation.

## Watermark

AMD FidelityFX SDK, current FSR3 upscaler implementation:
https://github.com/GPUOpen-LibrariesAndSDKs/FidelityFX-SDK/blob/main/Kits/FidelityFX/upscalers/fsr3/internal/ffx_fsr3upscaler.cpp
Blob consulted: 287e09baeed6cd01a444c3ed82bd1312e76a3eec.
The watermark creation guard uses the size/presence returned by the environment query. An existing string zero is not absence. This is published SDK evidence, not reverse engineering of Alex's exact FSR4 INT8 DLL.

OptiScaler v0.9.4, DLL attach path:
https://github.com/optiscaler/OptiScaler/blob/v0.9.4/OptiScaler/dllmain.cpp
Blob: 7580c65c77180cd0eb47f1ade6b75d58fd4e6ce8, examined around lines 2020-2105.
An explicitly configured false watermark value still causes both the C runtime and Win32 environment setter to write zero. The setter is guarded by optional-value presence. This is why removing the inherited variable alone was insufficient when Deck Fusion generated an explicit false.

OptiScaler INI and configuration reader:
https://github.com/optiscaler/OptiScaler/blob/v0.9.4/OptiScaler.ini
https://github.com/optiscaler/OptiScaler/blob/v0.9.4/OptiScaler/Config.cpp
INI blob: a9b7a88a9f5b210e399c5e6b5d7ae8052a9cea75.
Use the upstream unspecified `auto` value and remove the SDK variable. Leave INT8 selection unchanged. Keep the explicit diagnostic opt-in available. A game restart is required because the wrapper only prepares a process's launch environment.

Proton GE:
https://github.com/GloriousEggroll/proton-ge-custom/blob/master/proton
The FSR4 indicator is a separate Proton boolean/compatibility option that can populate FSR_WATERMARK. Set that indicator to zero while deleting the SDK/alias variables. Do not change FSR upgrades, model settings, or unrelated FG diagnostics.

## Mouse and Steam Input

The v0.9.4 INI documents `[Hotfix] ManualInputPolling` as a window-message-hook alternative. It explicitly warns that polling cannot prevent inputs reaching the game. `[Hotfix] DisableOverlays` can also block Steam Input. Offer manual polling plus keeping overlays enabled as an explicit compatibility action, not an unverified native input implementation.

https://github.com/optiscaler/OptiScaler/wiki/Known-Issues
Upstream notes pausing to unlock input and keyboard Tab/arrows/Space when mouse capture fails. Overlay preservation can conflict with some FG paths, so disclose the tradeoff and allow reverting to the prior input behavior. No automatic control remapping.

## Multiple DLLs and mod evidence

https://docs.red4ext.com/getting-started/installing-red4ext
https://docs.red4ext.com/getting-started/installing-a-plugin
https://docs.red4ext.com/getting-started/uninstalling
https://wiki.redmodding.org/cyber-engine-tweaks/first-steps/logs-debug
https://wiki.redmodding.org/redscript/getting-started/downloads
https://wiki.redmodding.org/redscript/help/troubleshooting
https://wiki.redmodding.org/cyberpunk-2077-modding/for-mod-creators/core-mods-explained

The frameworks have separate files, plugin/script directories and logs. Preserve an existing proxy, and use combined Wine overrides when the user selects several loaders. Overrides select native/builtin resolution when a module is requested; they do not cause every DLL to execute. A proxy name is not proof of the binary's identity or whether the game imports it.

Read known log paths with timestamped, bounded tails and a legacy redscript fallback. Do not infer all mods are running merely because CET works. Missing dependencies, runtime compatibility and script failures require their own evidence. The new report neither installs frameworks nor deletes caches.
