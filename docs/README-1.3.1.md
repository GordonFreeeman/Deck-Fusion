# Deck Fusion 1.3.1

A game-independent Decky toolkit for per-game LSFG, OptiScaler, ReShade, Wine DLL
load orders, optional Windows runtimes, diagnostics and tracked recovery.
Cyberpunk is one test case with optional extra diagnostics, not a restriction on
which games can use the core tools.

## Install this update

Install **Deck-Fusion-1.3.1.zip** through **Decky Settings → Developer → Install
Plugin from ZIP**, over the current version. No profile reset or uninstall is
needed. Profiles, downloaded components, Wine overrides, original-file backups,
runtime snapshots and manual FPS settings keep their existing paths. Reload Decky
or restart Steam if it retains the older frontend. This update does not reapply
graphics settings or install any runtime automatically.

## Windows runtimes for any selected Proton game

Select a game and its actual Windows executable in **Library**, then choose
**Open runtime setup**, or use the **Runtimes** tab. The same entry is available
from **DLLs**, and **Optional Windows runtime setup** is offered on the wizard's
Choose features step. **Resume wizard** retains the graphics draft and step.

Use **Check prefix and runtimes** first. It detects this game's existing prefix
and shows runtime-file and Winetricks-receipt evidence. Check **d3dcompiler_47**,
**vcrun2022**, or both only when the game/mod needs them, then choose **Install
selected runtimes → Back up & install**. Neither recipe is preselected. Switching
games or executables clears the selected recipes, prefix and inspection results;
previous snapshots/receipts remain saved under their original game.

`vcrun2022` is a Winetricks recipe for Microsoft's Visual C++ runtime, not a
filename to place in the game directory. These recipes install into the selected
game's Windows environment, its Proton prefix. No graphics feature needs to be
enabled and no graphics Apply is needed for the runtime operation.

There is no game-title, AppID or executable-basename allowlist. The target must
be a valid 32-bit or 64-bit Windows PE executable inside the selected installation,
with a safely resolved, initialized Proton prefix. Native Linux executables and
emulator programs show a not-applicable explanation instead of a runtime form.
Windows runtimes cannot improve a native Linux program.

Steam games and Steam-managed non-Steam Windows shortcuts use the same workflow.
For non-Steam shortcuts, enable **Include non-Steam games** in Library and launch
that shortcut once with its intended Proton version before inspecting its prefix.
The default Steam-only filter remains unchanged. Existing profiles/backups stay
accessible internally even after their library entries are filtered out.

When multiple matching prefixes exist, select one explicitly. A missing prefix
is never created, guessed, reset or replaced. A supported literal custom prefix
under the user's home or Steam libraries can be detected from launch settings;
Protontricks must still resolve the game's selected Steam compatibility tool.
Arbitrary standalone Lutris/Heroic/system-Wine folders and unresolved custom
runners are not silently modified. This is broad game support, not a claim that
every runtime, renderer, anti-cheat system or launcher is compatible.

## Prefix installation, backup and recovery

The existing safety workflow is retained. **Install Protontricks helper** is a
separate optional confirmation for the official Flathub helper and dependencies,
installed for the current user. Supported native/Flatpak installations are reused.
Runtime downloads require internet access; Microsoft installers are not bundled.
No sudo, SteamOS writable-system change, Winetricks --force or download-checksum
bypass is added. The compatibility tool selected in Steam is used, not system Wine.
Temporary Flatpak grants cover the detected libraries and selected prefix only
for the invocation; permanent permissions are not changed.

A runtime confirmation identifies the game, AppID, selected executable/prefix,
recipes and copy/free-space requirements. Approval is tied to that target and
its inspected state. Cancel changes nothing. A full checksum-verified pfx snapshot
is taken before installer execution. Running-game/prefix-process checks, unfinished
transaction checks and minimum free-space checks remain enabled. Close the game
and Protontricks windows, and do not launch or switch Proton during maintenance.

The game directory, mod-loader files, Steam launch text and graphics profile are
not rewritten. Winetricks intentionally changes runtime files and registry entries
inside the prefix. Existing VC components can conflict; inspect failure logs rather
than bypassing verification or automatically forcing replacements.

Snapshots are retained at
`<compatdata>/<appid>/.deck-fusion-runtime-backups/<operation-id>/pfx`
for normal layouts; receipts show exact paths. Links to external save folders are
preserved as links, not copied. This is not an independent external-save backup.
Copy space plus at least 256 MiB is checked; installers may need more workspace.
Snapshots are not automatically pruned.

**Cancel runtime operation** terminates only this operation's process group, not
other games or all Wine processes. Partial installer changes can remain; snapshots
and logs are retained. **Restore latest runtime snapshot** requires a separate
confirmation, verifies the saved copy and retains the displaced current prefix.
Restoring reverts prefix-local saves/settings; external linked folders are not
copied or reverted. Restore never silently deletes the displaced prefix.

The per-game maintenance lock blocks that game's Deck Fusion wrapper during the
operation. It cannot block unrelated launchers/shortcuts, especially ones manually
configured to share the same prefix. Do not start those during maintenance either.

Logs are retained under the game's profile runtime-jobs directory. The UI shows
the final 16 KB; installer output is bounded to about 4 MiB plus headers. Helper
setup has a separate log. Recipes have a 30-minute timeout; upstream installers
can still show Windows dialogs despite unattended mode, requiring Desktop Mode.
A successful command and receipts are evidence, not proof that the game launches.

## General diagnostics, optional game-specific extras

**DLLs → Check game files and logs** is available for every game. It reads the
selected executable's format/API hints, nearby graphics INIs, local DLL/ASI files,
plugin-folder entries and bounded OptiScaler/ReShade log tails. Both root-level
and nested executables are supported. It neither executes DLLs nor follows
external diagnostic symlinks. Missing optional configuration/log files are not
reported as proof of a missing dependency or failed injection.

Cyberpunk's separate CET/RED4ext/redscript inspector remains under **Optional
game-specific checks** only for that game's executable. It is not a prerequisite
for runtime installation, DLL overrides, general diagnostics or the wizard.

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

Manual polling bypasses missed window messages. It cannot block clicks from reaching the game underneath, so pause the game first and close other mod/ReShade menus before editing OptiScaler. Keeping external overlays enabled prevents OptiScaler from blocking Steam Input, but can reduce compatibility with some frame-generation paths. No Steam controller bindings are changed. Use an actual mouse/trackpad left-click binding; Tab, arrows and Space remain upstream's keyboard fallback. Settings can also be edited in the plugin without the in-game overlay. Mouse behavior on a physical Deck has not been verified here.

## Custom Wine DLL overrides

**DLLs** reads the selected game's current Steam launch options, relevant Wine-prefix global and executable-specific DLL overrides, and local DLL files beside its selected executable. Prefix registry files are read only, never rewritten. Ambiguous/custom prefix locations are reported rather than silently assumed to be inspected.

Existing names and load orders are retained. A launch option such as `WINEDLLOVERRIDES="version=n,b" %command% --skip-launcher` reserves `version` for that loader. Grouped names, case variants, `.dll` suffixes, wildcard-specific rules and disabled overrides are handled without dropping unrelated entries. Multiple literal shell assignments follow last-assignment semantics. Shell-expanded override lists require conversion to a literal list in the editable launch text; the plugin never evaluates shell expressions to guess their contents.

Under **DLLs → Add existing DLLs**, check several files (for example `dxgi.dll`, `version.dll`, `winmm.dll`), choose a load order, then use **Add selected DLLs (3)**. All checked entries are added together. Earlier custom entries and their load orders stay intact. Only Apply plus the confirmation commits them. Cancel is non-mutating.

Alternatively enter comma-separated basenames under **DLL module names**. Manual Add/update changes only explicitly named entries; all others are retained. The `.dll` suffix is optional. Native-first (`n,b`), native-only (`n`), builtin-first (`b,n`), builtin-only (`b`) and disabled are available. An existing custom entry can be edited or removed individually. Removing it returns to inherited behavior, not deletion of a DLL or a Steam/registry override.

Common proxy loaders are shown first. **Show all DLL files** expands the inventory; the filter searches every local DLL name regardless of that switch. The list only offers matching-architecture external DLLs or backed-up originals, never a managed graphics DLL masquerading as another mod. Unsafe links, wrong-architecture files and ambiguous case variants are excluded. Files are inspected beside the selected executable, not blindly through every subfolder. A selected file that disappears or becomes ineligible must be selected again after a refresh rather than silently dropped from a batch.

**Overrides are load-order rules, not a universal DLL injector.** The game or another loader must actually import/request the DLL. The plugin does not load every DLL in the directory, rename arbitrary mod files, install RED4ext/redscript/Cyber Engine Tweaks, or infer a specific mod from a filename. Follow that mod's own loader instructions.

## Optional Cyberpunk mod evidence

**DLLs → Optional game-specific checks → Check Cyberpunk mod files and logs** inspects the currently selected Cyberpunk executable, including an unsaved setup draft. It shows known CET, RED4ext and redscript paths, mod/script directory entries, and bounded log tails with timestamps and error-like lines. CET Lua mods are separate from RED4ext plugins and redscript scripts. A working CET overlay is not proof that those other frameworks loaded.

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

`agent-review.md` records actual findings, corrections and scoped final verdicts.
Historical notes in `docs/` describe prior versions, not the current restrictions.
Current scope: `docs/acceptance-1.3.1.md`; primary sources:
`docs/research-1.3.1.md`. Source plus tests and packaging scripts are included.

Build: `python3 scripts/build.py`. Lightweight automated checks:
`python3 -m pytest tests -q` and `node --test tests/*.test.mjs`.
Current rendered workflow: `python3 tests/browser/inspect_131.py`.
That development harness requires Playwright/Chromium and uses simulated Decky
widgets, Steam launch APIs and external installers with real React/Python logic.
It is not an on-device compatibility test. Evidence is in `evidence/1.3.1/`.

No physical Steam Deck, actual Microsoft/Protontricks installation, game launch,
GPU rendering or native-controller verification is claimed for this release.
