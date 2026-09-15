# Deck Fusion 1.1.2

A Decky Loader plugin for per-game LSFG, OptiScaler and ReShade configuration.

## Install or update

Close the game. In Decky Settings, enable Developer Mode, then use Developer → Install Plugin from ZIP and select **Deck-Fusion-1.1.2.zip**. Install over your existing Deck Fusion, including 1.1.1; do not delete your existing data directory. The plugin uses the same name and `~/.local/share/deck-fusion` storage. Existing profiles, component downloads, file backups and the Steam-only library preference are retained.

Open Deck Fusion in Quick Access and select **Set up a game**, or open the full manager and select **Setup wizard**. Its five steps are game/executable/API, features, FPS/upscaler targets, components, then apply. A draft is retained in the Steam UI session while visiting the normal controls. It becomes a durable profile only after Apply. No game is launched automatically.

## Changes in 1.1.2: black-screen hotfix

The 1.1.1 viewport measurement used the JavaScript module's global window. When React renders the page into another visible Steam document, that module window can report a height of zero. The resulting `height: 0px` hid all the controls. This failure was reproduced with both entry points, and was absent in 1.1.0 under the same conditions.

Sizing, resize events, animation scheduling and optional observers now use the rendered element's `ownerDocument.defaultView`. Hidden, detached or invalid measurements retain the last valid/CSS height, never zero. Focus scrolling stays inside the settings pane; advanced text editors focus their own DOM node rather than searching another window's document. The Steam footer reserve is retained.

Both routes have a recovery boundary. A component render/effect failure shows its message with Retry opening and Back to Steam controls instead of a blank route. The recovery view does not depend on Decky widgets or the measured-layout hook. It does not reset your saved configuration.

**This is a frontend-only hotfix.** The complete Python backend and launch runtime are byte-identical to 1.1.1. You do not need to reapply game settings or redownload tools just for this update. Restart Steam after installation to ensure that the old frontend is unloaded. Existing limitations of the experimental FPS-limiter integration remain unchanged; no new frame-limiting result is claimed here.

## Previous changes in 1.1.1

The full manager and wizard now reserve space above Steam's bottom controller bar. Wizard actions stay in a fixed, non-shrinking footer while the page scrolls independently. The available height accounts for the route offset and viewport size. Confirmation content scrolls without pushing its buttons behind the bar.

FSR4's diagnostic watermark is now off by default. Existing pre-1.1.1 profiles and session drafts migrate to watermark-off without changing the chosen upscaler. After saving the migrated profile, an explicit opt-in is remembered. Selecting the INT8 preset no longer turns the watermark on again.

**When first applying the older 1.1.1 watermark/limiter changes, open each affected game's profile, apply the settings once and fully restart the game. This is not required again solely for 1.1.2.** Updating the plugin or reopening its page does not rewrite an active game's INI. Leave **Show FSR 4 verification watermark** off to remove the banner. Cached tools and existing backups are retained; no component redownload is needed for these fixes.

## 33 → 66 with a Deck limit of 60

In LSFG choose **Headroom preset: 33 → 66, Deck limit 60**, or use the matching experimental preset in wizard step 3. This requests 33 base FPS, 2× LSFG, performance mode and Gamescope limiter integration. Set the Deck Performance FPS limit to **60** yourself, accept Apply, then restart the game. The plugin does not alter the global Performance setting.

**This is an experimental limiter-compatibility option, not a measured guarantee of 33 base / 60 displayed FPS.** The revised option follows LSFG's upstream VSync troubleshooting: disable the Gamescope Vulkan WSI layer for this game, keep the Gamescope compositor running, and force Mesa FIFO presentation. The previous 1.1.0 route forced that WSI layer on; it has been removed. Disabling the WSI layer can affect HDR. Depending on layer ordering and compositor behavior, presentation back-pressure may pull the base rate towards 30, or excess generated frames may be dropped. An exact 66-to-60 conversion is not intrinsically perfectly evenly paced. New profiles start with the option off. An existing opt-in is retained. Disable it and apply/restart to return to inherited behavior. Base caps remain independent DXVK/VKD3D settings; native Vulkan needs its own base limiter.

## A single Apply confirmation

All full Apply and Restore entry points open one native Decky confirmation. It lists proposed setting resolutions, existing mod files that need backups, Wine/environment overrides, warnings and any hard blockers. **Accept all & apply** accepts only that displayed operation. **Cancel** changes no game files, saved profile or Steam launch options.

Automatic resolutions include LSFG versus OptiScaler frame generation, competing ReShade/OptiScaler loaders, incompatible upscaler routes and conflicting advanced settings. Running games, anti-cheat markers, independently changed managed binaries, damaged backups and unsafe paths remain hard blockers. Approval is tied to the displayed configuration and file hashes. A later independent change requires a fresh confirmation. Multiplier/flow/performance live changes use a separate single confirmation limited to those three controls.

## FSR4 INT8 and DLSS

Choose **Use experimental FSR 4 INT8** in OptiScaler, or select that output in wizard step 3. The wizard checks for the upstream INT8 controls and FFX upscaler DLL. It provides an explicit update action when the cached OptiScaler build lacks them. No system driver replacement or driver downgrade is performed.

This is a real request to OptiScaler's FSR 3.x/4 backend, not a XeSS preset renamed FSR4. It selects `fsr31` for DX12 or `fsr31_12` for DX11/Vulkan interop, requests INT8 with the installed version's supported key and leaves the verification watermark off unless explicitly requested. It does not force `Fsr4Update=true` on unsupported hardware. The current stable key is `Fsr4ForceEnableInt8=true`; builds exposing the newer model selector use `Fsr4ForceModel=2`.

Steam Deck is outside official FSR4 hardware support. Compatible Proton/VKD3D/Mesa and game inputs are still required. FSR3 fallback, visual errors, initialization failures or worse performance remain possible. For a temporary diagnostic check, enable the verification watermark, apply and restart, then look for **FSR4-i8**. Turn the watermark off, apply and restart to hide it again. OptiScaler can also be inspected in game with **Insert**. **FSR3** means fallback. The plugin reports the requested mode, never claims to have measured the active shader. FSR 3.x and XeSS remain explicit alternatives. Vulkan-to-DX12 interop requires newer Proton support and remains experimental.

Native NVIDIA DLSS output requires compatible NVIDIA hardware. A game can nevertheless display “DLSS” when OptiScaler translates that input to FSR or XeSS. The native-DLSS choice is hidden on the Deck and unsupported saved DLSS output requests are resolved visibly. The plugin cannot determine what your previous installation actually ran.

When the watermark is off, the generated INI sets `Fsr4EnableWatermark=false`. The per-game wrapper also removes inherited `PROTON_FSR4_INDICATOR` and `FSR4_WATERMARK` diagnostic overrides, which can otherwise keep the banner visible. Other FSR/INT8 settings are unchanged. The original Steam launch text is preserved for restoration and any explicit conflicting assignments are shown in Apply's confirmation.

## Existing behavior retained

Steam-only listing by default, optional EmuDeck/non-Steam listing, deep executable discovery, useful empty-selector messages, strict TLS verification with a CA fallback, per-tool updates, shader configuration, per-game activation, tracked original files and recovery are preserved. No root flag, SteamOS read-only changes, telemetry or anti-cheat bypass is added. Restore managed games before uninstalling the plugin.

Third-party tools/shaders are not redistributed in this archive. Existing cached downloads are reused; Tools and the wizard fetch missing components from their upstream sources. LSFG still requires your own Lossless Scaling installation on its `lsfg-vk` branch. ReShade's current implementation supports Windows DirectX/OpenGL through Proton, not native Linux or the separate Windows Vulkan ReShade layer.

## Review and reproduction

`agent-review.md` records rejection/correction history and final scoped approvals. `docs/research.md` records primary-source evidence. The dependency-free frontend uses Decky's host React/UI; source is included in `src/index.js`, with the built entry point in `dist/index.js`.

Build: `python3 scripts/build.py`. Focused frontend checks: `node --test tests/*.test.mjs`. The unchanged inherited backend suite: `python3 -m pytest tests -q` (pytest required).

Optional rendered inspection: `python3 tests/browser/inspect_112.py`. It requires Python Playwright with the React 19.1.1 trace-viewer bundle used here, and Chromium at `/usr/bin/chromium`. It injects the host in memory; no browser policy is disabled and no external download is required. The bundled Playwright dependency is not included in this plugin. This harness is tied to those test-tool exports, not a production dependency. It simulates Decky widgets, Steam APIs, session storage, a bottom bar and backend read responses generated from synthetic Python fixtures. It uses two distinct browser windows to exercise the regression. It is not a Steam Deck emulator.

No hardware graphics tests or performance benchmarks were performed. The source reviews, small regression checks and desktop-browser inspection establish configuration and workflow behavior, not actual game compatibility or performance.
