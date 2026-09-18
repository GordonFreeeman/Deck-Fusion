# Changelog

## v0.3-beta6

- Repair stale Winetricks receipts after the prefix backup so they cannot skip or block the selected runtime installation. Keep unrelated receipts and verify the resulting runtime before applying graphics settings.
- Complete approved launch-option replacement after runtime repair, retaining the original launch text for rollback.
- Replace the current Steam navigation entry when opening and closing Deck Fusion. This prevents the closed app from reopening through the Home screen's Back action.
- Apply both fixes to the standard and full distributions. Full-bundle dependency versions are unchanged.

## v0.3-beta5

- Add the DLL filename troubleshooting note to guided setup.
- Rewrite the README for the public GitHub repository.
- Update application and package version labels to match the beta5 release.

## v0.3-beta4

- Add a DLL injection screen to guided setup, with per-game OptiScaler and standalone ReShade filename choices and matching Wine overrides.
- Keep manual DLL choices fixed. An occupied name requires a different choice or the existing backed-up force apply flow.
- Default BG3 OptiScaler injection to winmm.dll. Identify its DirectX 11 and Vulkan executables and provide a DirectX 11 selection button.
- Align recognized BG3 Steam/Proton launch commands with the reviewed renderer when graphics injection is enabled.
- Use a checksum-pinned upstream Winetricks recipe for vcrun2022. Recognize compatible native VC runtimes installed by Steam/Microsoft without a Winetricks receipt.
- Reject incomplete runtime evidence and preserve prefix backups and installer errors. Physical Deck/Proton verification remains outstanding.

## v0.3-beta3

- Hide the Expert Mode launch button; retain its implementation for later use.
- Use Steam's native scroll panel and browser scroll events for the effects popup. Scrolling no longer depends on pointer position or the removed raw controller API. Retain held-stick scrolling on older clients.
- Open a repair popup when managed files were deleted or changed. **Force apply settings** reinstalls selected files and configuration, with backups of overwritten files.
- Add a separate warning for old ReShade, OptiScaler and LSFG launch hooks. Replace approved entries with Deck Fusion's launcher while retaining unrelated arguments and DLL overrides.
- Preserve original launch text for rollback and recheck files, launch options and running-game state before Apply.

## v0.3-beta2

- Fix the legacy ReShade catalogue reference to use the upstream `legacy` branch.
- Keep available effects usable if an unselected optional shader pack cannot download; selected dependencies still block Apply when missing.
- Detect renderer imports through local engine DLLs, honor explicit Unity renderer flags, and add a scoped DirectX 11 default hint for Subnautica: Below Zero.
- Show the detected API in setup and resolve ambiguous selections before component downloads.
- Recover missing display/session environment fields from the same user's Steam process for runtime installers.
- Include actual installer output in runtime errors and expose retained logs from guided setup. Failed installs still retain snapshots and block graphics writes.

## v0.3-beta1

- Make guided setup the default launch entry; move the full interface to Expert Mode.
- Use five phases with separate Next screens for each setup stage.
- Preselect the running game and preserve per-game drafts.
- Add a searchable, scrollable popup with individual ReShade effect toggles.
- Always load ReShade through OptiScaler when OptiScaler is enabled.
- Prepare components automatically and install selected Windows runtimes on Apply.
- Default the Deck limiter option on in guided setup; preserve later opt-outs.
- Remove the duplicate Components screen and setup links from Expert Mode.
- Keep plain titles, compact pickers, native mouse input and Steam Home exit.
- Replace the earlier 2.0 beta release numbering with v0.3-beta1.

Earlier implementation and verification records remain in `docs/` and `evidence/`.
