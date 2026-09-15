# Deck Fusion 1.3.0

A Decky Loader plugin for per-game LSFG, OptiScaler, ReShade and custom Wine DLL
configuration. This update adds optional Cyberpunk Proton-prefix runtime setup.

## Install this plugin update

Close the game and install **Deck-Fusion-1.3.0.zip** through **Decky Settings →
Developer → Install Plugin from ZIP** over the current version. Keep the existing
plugin name and data folder. Profiles, cached components, original backups,
custom overrides and manual FPS settings remain in `~/.local/share/deck-fusion`.
Reload Decky or restart Steam if it retains the older frontend. Installing this
ZIP does not install any Windows runtime or silently alter a game prefix.

## New: Cyberpunk prefix runtimes

These dependencies are installed in Cyberpunk's emulated Windows environment,
called the Proton prefix. They are not expected as two files in the game's bin
folder. In particular, `vcrun2022` is the installer recipe name, not a DLL filename.
A typical Steam prefix is `steamapps/compatdata/1091500/pfx`, but locations can
vary with library and launch settings. The plugin detects candidates instead of
hard-coding a home directory or copying runtime files next to Cyberpunk2077.exe.

1. Close Cyberpunk and any other Protontricks operation for that prefix.
2. Select the game and its real **bin/x64/Cyberpunk2077.exe** in Library.
3. Open **Runtimes → Check prefix and runtimes**. Confirm the detected existing
   prefix; select one explicitly if more than one is found.
4. If needed, choose **Install Protontricks helper** and accept its separate
   confirmation. It installs the official Flathub app for your user, not a system
   package. Existing native Protontricks + Winetricks or Flatpak installs are used.
5. Leave **d3dcompiler_47** and **vcrun2022** selected (or select only the one you
   intend to install), then **Install selected runtimes → Back up & install**.
6. Wait for completion and inspect the result/log before restarting the game.
   No additional graphics **Apply settings** is required for this operation.

An initialized Proton prefix is required. No prefix found means the workflow
stops; it never deletes or recreates compatdata. Runtime installation follows the
compatibility tool chosen in Steam through Protontricks, with an explicit target
prefix and an additional checked WINEPREFIX inside the command. Custom runner
overrides that cannot be resolved safely are rejected rather than ignored.

### What the confirmation authorizes

The plugin inventories and copies the whole selected pfx, checks the copy hashes,
then runs only the selected upstream Winetricks recipes in unattended mode. It
requests neither sudo nor a SteamOS read-only filesystem change. Runtime downloads
require an internet connection; Microsoft installers are not bundled in this ZIP.
When using Flatpak, the confirmation lists the detected library/prefix folders
made accessible for this invocation so Protontricks can see manifests, Proton and
Steam Runtime, including separate SD-card libraries. Permissions are not changed
permanently.

The game directory, mod-loader DLLs, Steam launch text and graphics configuration
are not rewritten. Winetricks can modify **the prefix's runtime files and registry**,
which is the intended purpose. An installed native runtime can conflict with
existing VC components or behave differently in a particular Proton version;
this is not an automatic fix for every CET/RED4ext initialization error.

### Snapshots, cancellation and restore

Prefix snapshots are stored on the same filesystem at
`<compatdata>/<appid>/.deck-fusion-runtime-backups/<operation-id>/pfx` for ordinary
Steam layouts. The exact path appears in the receipt. The free-space check uses
the actual copy size plus at least 256 MiB workspace; installers/caches may require
more than that minimum. Snapshots are retained, not automatically pruned.

Wine links (including dosdevices and linked user folders) are preserved as links,
not recursively followed. Therefore a snapshot is **not a separate backup of
external save folders**. Preserve an independent save backup as usual.

**Cancel runtime operation** stops this operation's child process group, not all
Wine processes or other games. Already-made installer changes can remain. The
snapshot and failure/cancellation receipt stay available; no automatic rollback
silently replaces a prefix that might now contain newer saves.

**Restore latest runtime snapshot** requires a separate confirmation. It verifies
the snapshot, stages a new copy and atomically exchanges it with the current pfx.
It retains the entire displaced current pfx at the receipt's **displaced_prefix**
path. Prefix-local saves/settings revert to the snapshot version, while external
linked folders are not copied or changed by the restore. No existing snapshot
or displaced prefix is deleted by this recovery action. Unsupported filesystems
or damaged backups fail closed without replacing pfx.

A per-game maintenance lock prevents launches through Deck Fusion's wrapper while
that maintenance job is active. Launching through unrelated shortcuts/tools is
not globally blocked, so do not start Cyberpunk or switch Proton during the job.

### Logs and failure modes

**Show runtime file details** distinguishes file presence from Winetricks receipts.
Neither proves that the game or mods can load. The result only says completed
when both the subprocess exit status and selected Winetricks receipts support
that status; missing receipts are reported as unverified.

**Show runtime installation log** displays the final 16 KB of the operation's
installer log. The full log is bounded to approximately 4 MiB plus command/status
headers under `~/.local/share/deck-fusion/profiles/<appid>/runtime-jobs/<id>/`.
Optional helper setup has its own **Show Protontricks helper log**. Paths and exit
codes are retained. Error output is never substituted with a success message.

The child-process timeout is 30 minutes per recipe. Some combinations can still
open a Windows installer dialog despite unattended mode. An unresolved dialog,
blocked download, outdated helper or conflicting VC package reports a failure
with the snapshot retained; Desktop Mode may be necessary for that upstream issue.

This update deliberately does not pass Winetricks **--force**: upstream uses it
not only for conflicting runtimes but also to continue after checksum mismatches.
Deck Fusion's existing **graphics Force repair** remains a different, unchanged
operation. Use the log rather than overriding runtime download verification.

### About the current Cyberpunk launch failure

Re-extracting mods can replace proxy DLLs used by other injectors. Missing prefix
runtimes are a separate possibility, not proof of the cause. The existing **DLLs →
Check Cyberpunk mod files and logs** remains the place for CET/RED4ext/redscript
file inventories and recent logs. Do not use graphics Force repair to overwrite
a loader blindly after refreshing your mod archives.

## Verification and boundaries of this release

See `agent-review.md`, `evidence/1.3.0/verification.json` and the source hashes in
`evidence/reviewed-code-sha256.json`. The new runtime work is exercised through
synthetic prefixes and explicitly simulated installers, plus real filesystem
snapshot/restore, bounded subprocesses, cancellation and Chromium UI inspection.
The Steam/Decky UI components in the browser harness are simulated. No Microsoft
installer, actual Proton/Flatpak invocation, physical Steam Deck control or game
renderer was available for end-to-end verification. Neither reviewer approves an
unmeasured claim that this necessarily fixes the user's current game failure.

Primary-source details are in `docs/research-1.3.0.md`. The archived 1.2.2 README
is in `docs/README-1.2.2.md`; the existing graphics features are described below.

## Repair a manually cleaned game directory

Close the game. Open its profile, keep the intended OptiScaler/ReShade components selected, then go to **Apply → Force repair / reinstall → Apply settings → Back up & repair**. Missing files are recreated from the cached component packages; no re-download or profile reset is necessary unless the component cache itself is missing.

Normal Apply still stops on unexpectedly deleted or replaced tracked binaries/shaders. Its dialog now has **Review force repair**, which opens the same explicit repair confirmation. This first action only reviews a plan; it does not authorize installation yet. The checkbox is off by default and is cleared after Apply succeeds, is cancelled, or fails, and when a game is selected/reloaded. It is not stored in the profile or session draft. Restore never uses force.

The confirmation lists each path and action separately, with individually focusable file rows. A missing selected component is reinstalled. An externally replaced selected file is snapshotted before replacement. An obsolete changed file is kept untouched and stops being tracked, not silently deleted. Keeping a DLL does not disable it: the game or a mod can still load it. An obsolete missing file stays absent unless a verified pre-installation original is available, in which case that original is restored. This preserves a backed-up mod loader when a graphics proxy must move to a different name.

Original backups under `~/.local/share/deck-fusion/profiles/<appid>/originals/` remain intact. Additional pre-repair snapshots and their filename mapping are retained under `transactions/<operation-id>/receipt.json` in the same profile directory. The completed repair shows the receipt path in Apply. **Restore this game** still restores the original pre-installation state, not the last externally edited replacement. Repair snapshots are retained separately for manual recovery. Interrupted/failed transactions use the existing recovery journal and return to the exact pre-attempt state, including files that were already absent.

Force repair only permits the explicitly reviewed managed-file repair. It does not bypass a running game, detected anti-cheat, a pending recovery operation, protected Wine/mod-loader conflicts, symlink/path/casing checks, missing/corrupt original backups or insufficient installation space. If files, component contents, settings or the ownership record change after approval, the repair must be reviewed again. Unrelated files and existing Wine DLL overrides are not wiped.

The repair behavior was introduced in 1.2.1; install this ZIP over your existing version without uninstalling or deleting the plugin data directory. Reload the plugin after installation; restart Steam or the Deck if Steam retains the old frontend. After an actual repair, fully restart the game. The one-shot repair behavior and original backup rules are retained. This release does not change the LSFG limiter or your manual FPS settings.

## Persistent INT8 watermark: corrected off semantics

Earlier Deck Fusion releases incorrectly used `MLSR-WATERMARK=0` and `Fsr4EnableWatermark=false`. AMD's published FidelityFX code can check the environment variable's **existence**, not its numeric value. OptiScaler v0.9.4 writes a zero-valued variable when its optional bool is explicitly false, recreating the problem.

With the toggle off, this release **removes `MLSR-WATERMARK`**, clears `FSR4_WATERMARK` and `FSR_WATERMARK`, and writes **`Fsr4EnableWatermark=auto`** to all matching INI occurrences. The upstream optional bool then stays unspecified, so its DllMain does not recreate a zero value. The separate Proton indicator is set to `PROTON_FSR4_INDICATOR=0`, since Proton does parse that option as a boolean. An explicit opt-in still sets the diagnostic flag and INI true.

After upgrading, leave the watermark off, **Apply settings and fully restart the game**. Updating the plugin alone does not rewrite the game's installed INI. Reapply after an in-game Save that explicitly restores false/true. The INT8 model flags remain enabled and the upscaler binary is not patched, replaced or silently switched to XeSS/FSR3. Last-launch diagnostics show null for an absent variable, plus a timestamp and wrapper version.

This corrects the source-level configuration error. It is not a hardware-tested claim about every proprietary FSR4 build or about an additional third-party diagnostic overlay. The exact on-device INT8 binary was not available for GPU validation. See `docs/research-1.2.2.md` for primary sources.

## OptiScaler in-game mouse input

Open **OptiScaler → Use mouse-input compatibility settings**. This stages `ManualInputPolling=true` and `DisableOverlays=false` using keys found in the downloaded upstream INI. **Apply and fully restart the game**. The two direct selectors also permit standard window-message input or the existing upstream/advanced settings. An unsupported component format is blocked instead of inventing keys.

Manual polling bypasses missed window messages. It cannot block clicks from reaching the game underneath, so pause the game first and close the CET/ReShade menus before editing OptiScaler. Keeping external overlays enabled prevents OptiScaler from blocking Steam Input, but can reduce compatibility with some frame-generation paths. No Steam controller bindings are changed. Use an actual mouse/trackpad left-click binding; Tab, arrows and Space remain upstream's keyboard fallback. Settings can also be edited in the plugin without the in-game overlay. Mouse behavior on a physical Deck has not been verified here.

## Custom Wine DLL overrides

**DLLs** reads the selected game's current Steam launch options, relevant Wine-prefix global and executable-specific DLL overrides, and local DLL files beside its selected executable. Prefix registry files are read only, never rewritten. Ambiguous/custom prefix locations are reported rather than silently assumed to be inspected.

Existing names and load orders are retained. A launch option such as `WINEDLLOVERRIDES="version=n,b" %command% --skip-launcher` reserves `version` for that loader. Grouped names, case variants, `.dll` suffixes, wildcard-specific rules and disabled overrides are handled without dropping unrelated entries. Multiple literal shell assignments follow last-assignment semantics. Shell-expanded override lists require conversion to a literal list in the editable launch text; the plugin never evaluates shell expressions to guess their contents.

Under **DLLs → Add existing DLLs**, check several files (for example `dxgi.dll`, `version.dll`, `winmm.dll`), choose a load order, then use **Add selected DLLs (3)**. All checked entries are added together. Earlier custom entries and their load orders stay intact. Only Apply plus the confirmation commits them. Cancel is non-mutating.

Alternatively enter comma-separated basenames under **DLL module names**. Manual Add/update changes only explicitly named entries; all others are retained. The `.dll` suffix is optional. Native-first (`n,b`), native-only (`n`), builtin-first (`b,n`), builtin-only (`b`) and disabled are available. An existing custom entry can be edited or removed individually. Removing it returns to inherited behavior, not deletion of a DLL or a Steam/registry override.

Common proxy loaders are shown first. **Show all DLL files** expands the inventory; the filter searches every local DLL name regardless of that switch. The list only offers matching-architecture external DLLs or backed-up originals, never a managed graphics DLL masquerading as another mod. Unsafe links, wrong-architecture files and ambiguous case variants are excluded. Files are inspected beside the selected executable, not blindly through every subfolder. A selected file that disappears or becomes ineligible must be selected again after a refresh rather than silently dropped from a batch.

**Overrides are load-order rules, not a universal DLL injector.** The game or another loader must actually import/request the DLL. The plugin does not load every DLL in the directory, rename arbitrary mod files, install RED4ext/redscript/Cyber Engine Tweaks, or infer a specific mod from a filename. Follow that mod's own loader instructions.

## Cyberpunk mod evidence

**DLLs → Check Cyberpunk mod files and logs** inspects the currently selected Cyberpunk executable, including an unsaved setup draft. It shows known CET, RED4ext and redscript paths, mod/script directory entries, and bounded log tails with timestamps and error-like lines. CET Lua mods are separate from RED4ext plugins and redscript scripts. A working CET overlay is not proof that those other frameworks loaded.

Logs include CET's main/scripting logs, RED4ext's main log, and the newest redscript log (with its older cache-path fallback). Up to 12 KB / 60 lines per file are read. Each framework/log card is focusable; long cards scroll locally and support keyboard Page Up/Down. Errors may be historical. Freshness is unknown until the new wrapper has recorded a launch timestamp. File presence is never marked as proof of successful injection. The report is read-only; it does not download runtimes, delete script caches, install missing dependencies or try to execute arbitrary DLLs.

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

Build: `python3 scripts/build.py`. Checks: `python3 -m pytest tests -q` and `node --test tests/*.test.mjs`. The backend suite runs in seconds here. `tests/test_122.py` covers the absence-based watermark pair, mouse settings, multiple DLL preservation and read-only diagnostics. `tests/test_121.py` retains the repair/rollback checks. The earlier focused checks are also retained. All use synthetic payloads.

Rendered workflow inspection: `python3 tests/browser/inspect_122.py`. Requires Playwright with the React trace-viewer vendor used by this harness and Chromium at `/usr/bin/chromium`. It uses real React/browser rendering plus real Python RPC/jobs/transactions, with simulated Decky widgets and Steam launch APIs. A hidden module window and visible Steam-footer simulation cover the previous black-screen and overlap regressions. Current screenshots/results are in `evidence/1.2.2`, with earlier evidence preserved in its original folders. Those test tools are not runtime dependencies and are not bundled.

No physical Steam Deck, live Wine injection, real FSR watermark display or GPU performance testing was performed. Source inspection and host checks establish the implemented configuration paths and workflow, not universal game compatibility.
