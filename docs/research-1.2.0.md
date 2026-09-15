# Primary-source notes for Deck Fusion 1.2.0

Sources inspected during this revision. All are upstream source code, not third-party installation sites. Local integration tests use synthetic binaries, not any claimed upstream binary build.

## Watermark

* OptiScaler `OptiScaler/dllmain.cpp`, DLL_PROCESS_ATTACH, FSR4 Watermark block: explicit false uses both `_wputenv_s` and `SetEnvironmentVariableW` to set `MLSR-WATERMARK` to `0`. Source read: https://github.com/optiscaler/OptiScaler/blob/master/OptiScaler/dllmain.cpp . Blob reported by connector: `f4522d9aa149a80b546a74168250af1b158ce97c`. Related Config.cpp reads the FSR section's Fsr4EnableWatermark boolean.
* GE-Proton `proton` script: `check_environment("PROTON_FSR4_INDICATOR", "fsr4hud")`; explicit zero discards the compatibility flag. Later `fsr4hud` enables `FSR_WATERMARK` and a separate FG watermark. User settings only supply variables missing from the environment. Source: https://raw.githubusercontent.com/GloriousEggroll/proton-ge-custom/master/proton . The fetched script identified its distribution as GE-Proton11-3. The plugin does not alter unrelated FG watermark choices.
* The previous plugin omitted the direct SDK variable and patched only the first duplicate INI key. Both failures were locally reproduced, independently of the user's hardware. This supports fixing those paths but cannot establish all possible causes of a banner in a particular game.

## Proxy names and other loaders

* ReShade official setup's GetModuleName mapping includes `d3d9`, `d3d10`, `d3d11`, `d3d12`, `dxgi` and `opengl32` for their corresponding API selections: https://raw.githubusercontent.com/crosire/reshade/main/setup/MainWindow.xaml.cs . In particular the D3D12 alternative is not an arbitrary rename invented by the plugin.
* OptiScaler CheckWorkingMode supports the exposed system-DLL proxies, and its companion ReShade path uses ReShade64.dll plus LoadReshade. Source: https://github.com/optiscaler/OptiScaler/blob/master/OptiScaler/dllmain.cpp . Previously documented integration research is retained in the historical docs.
* WINEDLLOVERRIDES selects native/builtin behavior for a requested Wine module, not an unconditional arbitrary-DLL injection mechanism. This distinction is reflected explicitly in the DLL page, file dropdown, README and review.

## Scope

Only already-visible literal Steam launch assignments, readable relevant prefix registry settings and files beside the chosen executable can be inspected before launch. Arbitrary scripts, launcher-internal environment changes and GPU state are not evaluated or guessed. The runtime preserves unknown inherited load-order entries when merging, but changes applied later by another launcher/Proton script remain outside this preflight inspection.
