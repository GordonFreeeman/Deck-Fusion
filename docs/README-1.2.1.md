# Deck Fusion 1.2.1

A Decky Loader plugin for per-game LSFG, OptiScaler, ReShade and Wine DLL-loader configuration.

## Install over the previous version

Close the game and install **Deck-Fusion-1.2.1.zip** using Decky Settings → Developer → Install Plugin from ZIP. Keep the existing plugin name and data directory. Profiles, cached components, original-file backups and the Steam-only library preference remain in `~/.local/share/deck-fusion`.

## Repair a manually cleaned game directory

Close the game. Open its profile, keep the intended OptiScaler/ReShade components selected, then go to **Apply → Force repair / reinstall → Apply settings → Back up & repair**. Missing files are recreated from the cached component packages; no re-download or profile reset is necessary unless the component cache itself is missing.

Normal Apply still stops on unexpectedly deleted or replaced tracked binaries/shaders. Its dialog now has **Review force repair**, which opens the same explicit repair confirmation. This first action only reviews a plan; it does not authorize installation yet. The checkbox is off by default and is cleared after Apply succeeds, is cancelled, or fails, and when a game is selected/reloaded. It is not stored in the profile or session draft. Restore never uses force.

The confirmation lists each path and action separately, with individually focusable file rows. A missing selected component is reinstalled. An externally replaced selected file is snapshotted before replacement. An obsolete changed file is kept untouched and stops being tracked, not silently deleted. Keeping a DLL does not disable it: the game or a mod can still load it. An obsolete missing file stays absent unless a verified pre-installation original is available, in which case that original is restored. This preserves a backed-up mod loader when a graphics proxy must move to a different name.

Original backups under `~/.local/share/deck-fusion/profiles/<appid>/originals/` remain intact. Additional pre-repair snapshots and their filename mapping are retained under `transactions/<operation-id>/receipt.json` in the same profile directory. The completed repair shows the receipt path in Apply. **Restore this game** still restores the original pre-installation state, not the last externally edited replacement. Repair snapshots are retained separately for manual recovery. Interrupted/failed transactions use the existing recovery journal and return to the exact pre-attempt state, including files that were already absent.

Force repair only permits the explicitly reviewed managed-file repair. It does not bypass a running game, detected anti-cheat, a pending recovery operation, protected Wine/mod-loader conflicts, symlink/path/casing checks, missing/corrupt original backups or insufficient installation space. If files, component contents, settings or the ownership record change after approval, the repair must be reviewed again. Unrelated files and existing Wine DLL overrides are not wiped.

Install this ZIP over 1.2.0 without uninstalling or deleting the plugin data directory. Reload the plugin after installation; restart Steam or the Deck if Steam retains the old frontend. After an actual repair, fully restart the game. No changes to the LSFG limiter, INT8 controls or Wine override rules are introduced by this release.

## Retained watermark correction (1.2.0)

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

Build: `python3 scripts/build.py`. Checks: `python3 -m pytest tests -q` and `node --test tests/*.test.mjs`. The backend suite runs in seconds here. `tests/test_121.py` contains repair, approval, snapshot, rollback and mod-preservation regressions. The earlier focused checks are also retained. All use synthetic payloads.

Rendered workflow inspection: `python3 tests/browser/inspect_121.py`. Requires Playwright with the React trace-viewer vendor used by this harness and Chromium at `/usr/bin/chromium`. It uses real React/browser rendering plus real Python RPC/jobs/transactions, with simulated Decky widgets and Steam launch APIs. A hidden module window and visible Steam-footer simulation cover the previous black-screen and overlap regressions. Current screenshots/results are in `evidence/1.2.1`, with earlier evidence preserved in its original folders. Those test tools are not runtime dependencies and are not bundled.

No physical Steam Deck, live Wine injection, real FSR watermark display or GPU performance testing was performed. Source inspection and host checks establish the implemented configuration paths and workflow, not universal game compatibility.
