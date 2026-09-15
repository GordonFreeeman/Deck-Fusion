# Deck Fusion 1.1.1 acceptance and boundaries

## Inspectable acceptance criteria

1. The manager/wizard ends above Steam's bottom controller bar rather than using the full unreserved viewport. Wizard Back/Next/Apply/exit buttons do not shrink or scroll behind it. Content, all six tabs and confirmation bodies remain scrollable. Inspect 1280x800, 1024x640 and 800x500 with an overlaid footer and route offset.
2. Replace 1.1.0's WSI-on setting with the upstream-recommended WSI-off/FIFO compatibility path when the existing opt-in is enabled in a Gamescope launch. Preserve the 33 FPS base cap, 2x multiplier, unrelated environment, original launch text and Steam's global settings. Turning the option off, disabling LSFG, or using bypass must not inject that path.
3. The FSR watermark defaults off in new and migrated profiles and old session drafts. Re-selecting INT8 cannot turn it on. Applying writes `Fsr4EnableWatermark=false` and removes inherited diagnostic-only environment overrides without disabling INT8. New explicit opt-ins and import-from-disk choices remain available. Display conflicts before Apply.
4. Preserve the one-confirmation Apply workflow, cancellation with no saved-profile/game/Steam writes, schema validation, backups, restoration, component reuse and game-running safety stops. Do not add root permissions, change global Steam settings, patch LSFG, or distribute new third-party payloads.
5. Deliver a versioned, self-contained Decky ZIP with source, updated documentation, exact-code hashes and a factual agent-review record.

## Verification achieved

The lightweight backend checks, bundle smoke test and actual-bundle browser inspection are recorded in `agent-review.md`. The browser host uses real React and Python but simulated Decky widgets, Steam APIs, session storage and bottom bar. Geometry and hit-testing prove visibility only in that host. It is not a Steam Deck emulator.

## Hardware acceptance still required

Actual Steam/Decky CSS and controller focus; the user's SteamOS/Proton/Mesa combinations; continued INT8 operation and disappearance of its SDK banner on the game; HDR behavior; displayed/generated FPS, frame pacing, slider changes and a retained 33 base / 60 displayed result. Source approval does not mark these as measured or satisfied. This release fixes the launch configuration but does not claim an independently implemented LSFG post-FG limiter.

## Upgrade use

Install over 1.1.0, open each affected profile, leave the watermark off, Apply once and fully restart the game. The UI can migrate a profile in memory without changing a currently installed INI. Set the Deck Performance limit to 60 separately for the requested 33x2 scenario.
