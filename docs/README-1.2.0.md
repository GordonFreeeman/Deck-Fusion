# Deck Fusion 1.2.0

A Decky Loader plugin for per-game LSFG, OptiScaler, ReShade and Wine DLL-loader configuration.

## Install over the previous version

Close the game and install **Deck-Fusion-1.2.0.zip** using Decky Settings → Developer → Install Plugin from ZIP. Keep the existing plugin name and data directory. Profiles, cached components, original-file backups and the Steam-only library preference remain in `~/.local/share/deck-fusion`.

Open the affected game's profile, leave **Show FSR 4 verification watermark** off, and choose **Apply settings → Accept all & apply**, then fully restart the game. This update changes the generated runtime and INI configuration, so reapplying is necessary. It is not enough to install the ZIP while the game continues running. If Steam keeps the previous frontend after installation, restart Steam or the Deck. No component redownload or profile reset is required for this update.

The manager's **DLLs** tab contains the new override controls. The setup wizard links to the same page; **Resume wizard** returns to the retained draft.

## Watermark correction

The old wrapper removed two diagnostic aliases but could leave AMD's direct `MLSR-WATERMARK=1` active. The old INI patcher also changed only the first occurrence of a setting. Both defects were reproduced in the 1.1.2 source.

When the watermark is off, the per-game wrapper now sets `MLSR-WATERMARK=0` and `PROTON_FSR4_INDICATOR=0`, and clears inherited `FSR4_WATERMARK` and `FSR_WATERMARK`. Explicit zero for the Proton indicator suppresses its `fsr4hud` compatibility option and prevents user-settings defaults from supplying that indicator again. The INI patcher writes `Fsr4EnableWatermark=false` to every matching assignment, including repeated sections/keys and case variants. The optional diagnostic toggle still works in both directions. Last-launch diagnostics record these environment values.

INT8 model selection and upscaling remain enabled. This does not modify the FSR binaries, system drivers, unrelated frame-generation watermark controls, or your chosen FPS cap. Primary-source evidence is recorded in `docs/research-1.2.0.md`. Actual visibility of the banner must still be checked in the game; no GPU access is available in the build environment.

## Custom Wine DLL overrides

**DLLs** reads the selected game's current Steam launch options, relevant Wine-prefix global and executable-specific DLL overrides, and local DLL files beside its selected executable. Prefix registry files are read only, never rewritten. Ambiguous/custom prefix locations are reported rather than silently assumed to be inspected.

Existing names and load orders are retained. A launch option such as `WINEDLLOVERRIDES="version=n,b" %command% --skip-launcher` reserves `version` for that loader. Grouped names, case variants, `.dll` suffixes, wildcard-specific rules and disabled overrides are handled without dropping unrelated entries. Multiple literal shell assignments follow last-assignment semantics. Shell-expanded override lists require conversion to a literal list in the editable launch text; the plugin never evaluates shell expressions to guess their contents.

To add a mod loader, select an eligible **Existing DLL beside the game** or enter a **DLL module name**, choose its load order and select **Add / update custom override**. The `.dll` suffix is optional. Native-first (`n,b`), native-only (`n`), builtin-first (`b,n`), builtin-only (`b`) and disabled are available. An existing custom entry can be edited or removed. Removing it returns to inherited behavior; it does not delete the DLL or remove an original Steam/registry override. Adding a custom entry is an explicit user choice to supersede an inherited entry with the same exact name.

The dropdown offers matching-architecture PE DLLs that are external files or backed-up originals. It excludes managed graphics DLLs, unsafe links, architecture mismatches and ambiguous case-variant duplicates. It scans beside the actual selected executable, not every DLL in a large installation tree. Additional module names can be entered manually.

**Overrides are load-order rules, not a universal DLL injector.** The game or another loader must actually import/request the DLL. The plugin does not load every DLL in the directory, rename arbitrary mod files, install RED4ext/redscript/Cyber Engine Tweaks, or infer a specific mod from a filename. Follow that mod's own loader instructions.

## Conflict-aware OptiScaler / ReShade installation

Existing override names, unmanaged local DLLs and backed-up originals reserve their names. Apply proposes another supported OptiScaler proxy if the chosen one is occupied. ReShade uses only API-appropriate proxy names: `dxgi` or the relevant `d3d10`, `d3d11`, `d3d12`; `d3d9` for DX9; `opengl32` for OpenGL. Where appropriate, it can propose `ReShade64.dll` through OptiScaler instead of standalone injection. A valid explicitly selected standalone proxy is retained when it does not conflict.

For example, `version=n,b` can remain the mod-loader override, OptiScaler can use a free `dxgi.dll`, and ReShade can use its OptiScaler companion path. Additional custom overrides are merged alongside the graphics entries at launch. The exact proposal depends on the files, API, existing overrides and selected mode. Supported proxy names are not guaranteed to be imported by every game; in-game activation still needs verification.

If no supported proxy is free, the plugin blocks instead of overwriting another loader. Its package-payload guard also prevents replacement of a DLL explicitly reserved by an existing/custom override. A graphics DLL managed by Deck Fusion is not falsely offered as a separate mod. When a previous release backed up a real mod under a now-conflicting proxy name, moving the graphics proxy restores that original through the existing transaction system.

One **Apply** confirmation displays proposed corrections, custom changes, preserved overrides and resulting graphics loaders. Cancel is non-mutating. Approval is tied to settings, managed-file state, component content and the inspected local DLL inventory. Independently changed files require a fresh approval. Original backups, rollback, launch-option readback and recovery stay enabled. “Accept all” does not bypass running-game or anti-cheat checks.

## Manual FPS settings

The fixed headroom preset has been removed from both the LSFG page and the wizard. Existing manually chosen base caps, multipliers and limiter opt-in are retained unchanged. Use the normal base-FPS and LSFG-multiplier controls.

The inherited Gamescope/FIFO compatibility option remains optional. It is not a separate, hardware-verified LSFG output limiter; VSync back-pressure can affect base FPS. This release does not change the limiter path or claim to fix/measure display pacing. Native Vulkan games need their own base limiter; the configured DXVK/VKD3D cap applies to the corresponding DirectX paths.

## Features and limitations retained

The five-step setup wizard, Steam-only library default with optional non-Steam games, executable selection, shader controls, strict TLS/CA fallback, per-component updates, game profiles and tracked restoration remain. The 1.1.2 cross-window measurement, error-recovery screen and footer clearance are retained.

FSR4 INT8 remains an explicit experimental output request on unsupported Steam Deck hardware. FSR3 fallback, game-specific compatibility, visual defects or performance regressions are possible. The plugin does not measure the active GPU upscaler. Native NVIDIA DLSS is not implemented on the Deck; a game's DLSS input can be translated by OptiScaler into FSR/XeSS output.

Third-party binaries/shaders are not included in this ZIP. Cached tools are reused, and the existing Tools/wizard download actions fetch missing components. LSFG needs the user's own Lossless Scaling installation. ReShade here targets Windows DirectX/OpenGL games through Proton, not native Linux or the separate Vulkan ReShade path. There is no root flag, telemetry, anti-cheat bypass or SteamOS read-only modification. Restore managed games before uninstalling.

## Verification and source

`agent-review.md` records actual findings, corrections and final scoped verdicts. The prior release's documentation/review is archived under `docs/`; it describes historical behavior, not the current feature set.

Build: `python3 scripts/build.py`. Checks: `python3 -m pytest tests -q` and `node --test tests/*.test.mjs`. The backend suite runs in seconds here. `tests/test_120.py` contains focused watermark, merge, file-protection, migration and transaction regressions with synthetic PE fixtures.

Rendered workflow inspection: `python3 tests/browser/inspect_120.py`. Requires Playwright with the React trace-viewer vendor used by this harness and Chromium at `/usr/bin/chromium`. It uses real React/browser rendering plus real Python RPC/jobs/transactions, with simulated Decky widgets and Steam launch APIs. A hidden module window and visible Steam-footer simulation cover the previous black-screen and overlap regressions. Screenshots/results are in `evidence/1.2.0`. Those test tools are not runtime dependencies and are not bundled.

No physical Steam Deck, live Wine injection, real FSR watermark display or GPU performance testing was performed. Source inspection and host checks establish the implemented configuration paths and workflow, not universal game compatibility.
