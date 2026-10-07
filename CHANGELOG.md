# Changelog

## v0.3-beta8

- Add Advanced OptiScaler settings to the guided Upscaling output screen, with a complete INI editor, installed-file import and a return to guided settings.
- Save manual settings per game as a draft. Apply uses those values instead of the guided INI presets and keeps the existing file backup and recovery process.
- Keep ReShade chaining controlled by the feature toggle, derive runtime-sensitive settings from the manual INI, and reject invalid INIs and incompatible frame-generation choices.
- Show manual configuration in the final review. Keep the full bundle's dependency versions unchanged.

## v0.3-beta7

- Add removal of existing OptiScaler and ReShade setups from the game selection screen, with a file-by-file review and Undo.
- Identify external injector DLLs by verified cached hashes or structured version resources. Keep unknown DLLs, edited files, untracked presets, shared shader folders and untracked SDK libraries.
- Restore verified originals for unchanged managed files and keep snapshots of every removal change. Refuse stale reviews, running games, unsafe prefix overrides and Undo over later edits.
- Keep LSFG, frame caps and Windows runtimes when removing OptiScaler / ReShade; only remove launch overrides for identified loaders that are now absent.
- Split guided setup into six phases. L1/R1 change phases; L2/R2 change tabs within a phase. Preserve validation and block trigger-generated mouse clicks from confirming actions.
- Keep the full bundle's dependency versions unchanged.

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
