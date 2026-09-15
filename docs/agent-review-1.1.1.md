# Deck Fusion 1.1.1 review record

Date: 12 September 2026. Baseline: the supplied Deck-Fusion-1.1.0.zip and the user's two Steam Deck photographs. The named reviewers below are separate review passes by the same assistant, not independently running agents. Only the implementation pass edits the code. Review iterations count concrete rejection/correction cycles, not every command or harness attempt.

Scope: fix the clipped controls, replace the ineffective LSFG launch configuration with the documented compatibility route, and make the FSR diagnostic watermark optional without disabling INT8. A physical Steam Deck is not connected. Approval covers the inspectable implementation and release package, not an unmeasured 60 FPS result, native Decky focus, or game-rendering behavior. The original 1.1.0 review is preserved in `docs/agent-review-1.1.0.md`.

## Iteration 1: inspect the reported 1.1.0 defects

### Logic Inquisitor

**Verdict:** REJECTED

**Blocking findings:**

1. **Ineffective limiter integration.** Evidence: the shipped launch helper explicitly forces `ENABLE_GAMESCOPE_WSI=1` and sets the limiter-awareness flag to zero; the user reports that this does not cap LSFG. Upstream LSFG troubleshooting instead recommends `ENABLE_GAMESCOPE_WSI=0` for its VSync path under Gamescope/Steam Deck. Expected: implement the documented compatibility path, preserve the user's independent 33 base / 2x choices, and do not equate an environment flag with measured post-FG limiting. Required correction: replace the WSI-on route, retain FIFO, account for conflicting Mesa presentation overrides, and disclose the remaining pacing/HDR uncertainty. Severity: High.
2. **Watermark forced on repeatedly.** Evidence: DEFAULT_PROFILE sets `fsr4_watermark=true`, the INT8 preset helper sets it true again, and old applied profiles/session drafts retain it. Expected: diagnostics are optional and remain off when requested; FSR INT8 itself stays selected. Required correction: off-by-default migration for pre-schema-3 profiles/drafts, no preset reset, and an authoritative, visible watermark control. Severity: Medium.
3. **INI-only removal can be defeated.** Evidence: the maintainer's response in OptiScaler issue 1078 identifies inherited `PROTON_FSR4_INDICATOR` and `FSR4_WATERMARK` flags as another source of a persistent banner. Expected: watermark-off should clear known diagnostic overrides for the managed game, not disable upscaling. Required correction: unset those flags in the per-game wrapper only when OptiScaler is enabled and the watermark is off; disclose explicit conflicting launch assignments in the single Apply dialog. Severity: Medium.

**Non-blocking improvements:** Include the requested presentation environment and wrapper version in existing diagnostics, clearly labelled as launch information rather than measured FPS. Do not modify the LSFG binary or add a speculative custom Vulkan limiter.

**Verification performed:** Inspected the supplied ZIP, profile defaults, preset selection, profile load/build/plan/import paths, the persistent launch helper and Gamescope detection. Examined the user's FSR4-I8 photograph. Compared the implementation with the official LSFG troubleshooting/pacing/configuration pages, Mesa's presentation-mode documentation, Valve's WSI source, and the OptiScaler maintainer's response. No hardware execution was performed.

### Aesthetic Executioner

**Verdict:** REJECTED

**Blocking findings:**

1. **Actions hidden behind Steam's bottom bar.** Evidence: the user's photograph shows the bottom wizard button obscured by Steam's footer. The supplied Manager uses `height:100vh` without reserving space for that external overlay. Expected: the wizard's actions remain visible and independently reachable while content scrolls. Required correction: bound the entire route above the Steam footer, account for the route's top offset, prevent action-row shrinking, and keep settings in an inner scroll pane. Severity: High.
2. **Persistent debugging UI is the default experience.** Evidence: the INT8 selection re-enables an overlay, while the user expects normal gameplay without the banner. Expected: a discoverable diagnostic toggle, off by default, with no loss of INT8 and no surprise re-enabling by presets. Required correction: expose the control in the normal OptiScaler UI and INT8 wizard step, explain Apply/restart, and preserve explicit choices. Severity: Medium.

**Non-blocking improvements:** Recheck confirmation action placement, not just the wizard's bottom row. Avoid renaming unrelated controls or redesigning the working workflow.

**Verification performed:** Inspected both supplied photographs and the complete frontend layout/confirmation/wizard/selector implementation. Identified the difference between reserving room inside a scroller and reserving the outer route above an overlay. No approval relied on the older screenshots, which did not model Steam's external footer.

## Codeweaver correction checklist

- [x] Reserve 72 logical pixels below the manager; account for route offset, viewport size and scale, with resize/visual-viewport listeners and cleanup.
- [x] Keep wizard action rows non-shrinking; retain native Decky controls and independent content scrolling. Bound confirmation-body height.
- [x] Replace WSI-on with WSI-off and Mesa FIFO only for enabled LSFG plus the per-game opt-in in a detected Gamescope environment.
- [x] Preserve the existing 33 base / 2x configuration and global Steam settings; disclose that no independent post-FG cap is implemented or measured.
- [x] Migrate legacy profiles and session drafts to watermark-off without writing game files merely on load.
- [x] Keep new explicit diagnostic opt-ins; stop presets from re-enabling the watermark; make the primary control win over an advanced INI override.
- [x] Unset the two known inherited watermark-only flags and display launch-environment removals before acceptance.
- [x] Keep INT8 model/backend selection intact; preserve imported watermark choices and existing safety/backup/restore behavior.

## Iteration 2: review corrected implementation and rendered output

### Logic Inquisitor

**Verdict:** REJECTED

**Blocking findings:**

1. **Help and acceptance text still described the old behavior.** Evidence: README and docs/research.md still said the option enabled Gamescope WSI and enabled the watermark by default; docs/acceptance.md required the watermark to be enabled. Expected: installation instructions and limitations agree with the new implementation. Required correction: update all three documents, document one-time Apply/restart for installed games, and explicitly supersede the old route. Severity: Medium.
2. **Bypass could be misreported in diagnostics.** Evidence: launch_environment returns the inherited environment unchanged for `bypass`, but the new `limiter_route_requested` log field checked only LSFG, the opt-in, and a Gamescope variable. Expected: a bypassed launch reports the route as unchanged. Required correction: guard that diagnostic with `not cfg.get('bypass')` and check an actual wrapper subprocess. Severity: Low.

**Non-blocking improvements:** No further changes to working download, shader or transaction machinery were required. Preserve their existing tests rather than adding a new simulated graphics stack.

**Verification performed:** Read the full revised profile/migration/build/plan/import, launch/runtime, resolution-policy and frontend Apply/wizard paths, not only the latest edits. A 135-test backend run passed before the diagnostic correction. The self-contained frontend smoke test passed. The actual bundle completed wizard setup, Tools/resume, Cancel and Apply through real Python code in the browser host. Inspected generated fixture INI values and the saved schema-3 profile: INT8 still selected, watermark false, base 33 and multiplier 2 retained. No generated or displayed frames were measured.

### Aesthetic Executioner

**Verdict:** APPROVED

Approval scope: corrected source and observable browser-host UI, not native Decky/controller certification.

**Blocking findings:** None remaining in the inspected layout and interaction paths.

**Non-blocking improvements:** Native Steam UI scaling and the actual footer can still differ from the inspection host. The 72-pixel reserve includes extra clearance; do not claim to have measured the user's footer geometry from the photograph.

**Verification performed:**

- Ran `tests/browser/inspect_111.py` using the actual built plugin, real React 18, simulated Decky controls/Steam API/session storage, and the real Python backend with synthetic game/component files.
- Added a simulated 56-pixel Steam footer and a 40-pixel route top offset. Checked 1280x800, 1024x640 and 800x500. Wizard action bottoms were 714, 554 and 414 respectively, compared with footer tops 744, 584 and 444. Hit-testing at button centers found the buttons uncovered.
- Exercised all five wizard steps, completed setup, left for Tools and resumed, scrolled all six normal tabs to their final control, and inspected both confirmation actions at 800x500 and 1280x800.
- Opened and visually examined current screenshots: wizard-game-1280x800.png, wizard-game-1024x640.png, wizard-game-800x500.png, wizard-targets-800x500.png and confirmation-800x500.png in `evidence/1.1.1/`. Action rows, typography, spacing, labels, and overlay clearance were inspected. Partial text at the edge of a deliberately scrolled pane is scroll clipping, not an inaccessible action.
- Verified a legacy session draft does not re-enable the watermark. Explicit on/off survives re-selecting INT8. Cancel produces no saved-profile, game-file or simulated Steam launch writes. Apply completes and writes the expected configuration.
- Final host run recorded zero unhandled page errors and no horizontal document overflow.

Harness limitations encountered: about:blank cannot expose real sessionStorage in this environment. A routed test-origin navigation was also blocked by browser policy. The final host therefore stays on the in-memory page and provides simulated session storage explicitly. These were harness startup failures, not plugin failures. No browser policy, access restriction or TLS check was disabled, and no production code was changed to work around them.

## Iteration 3: complete final review

### Logic Inquisitor

**Verdict:** APPROVED

Approval scope: the complete 1.1.1 source/configuration implementation and package for device evaluation. The hardware FPS, frame-pacing, HDR and SDK behavior are still unverified limitations, not inferred successes.

**Blocking findings:** None remaining in the inspectable implementation. The obsolete documentation and bypass diagnostic were corrected. A separate guaranteed post-FG limiter is not claimed as implemented.

**Non-blocking improvements:** Use the existing per-game last-launch diagnostics when assessing the next device result. Do not infer working limiting from the requested values or infer failure/success solely from the location of an FPS counter in the Vulkan stack.

**Verification performed:**

- Re-examined the complete revised route, profile and launch data flow, authoritative watermark precedence, migration persistence, inherited-environment handling, single-dialog approval and unchanged transaction/restoration entry points. Compared the runtime diff against the supplied 1.1.0 archive and reviewed the full resulting relevant functions.
- Confirmed compatibility settings are opt-in, per-game, and inactive for bypass, desktop-without-Gamescope, disabled LSFG or a disabled option. Input dictionaries, unrelated environment settings, Steam launch text and the 33/2x configuration are retained.
- Confirmed the existing running-game, anti-cheat, stale approval, file conflict, path/symlink, rollback and launch-preservation checks still run. No root flag, system changes, new download dependency, third-party binary patch or hidden permanent permission was added.
- Final lightweight backend run: **136 passed in 7.78 seconds**. This includes 17 targeted 1.1.1 cases covering migration, INI precedence, diagnostic environment removal, opt-in/inactive paths, preserved base/multiplier, confirmation disclosures, disk import and a bypassed wrapper subprocess.
- The first inherited run had four assertions expecting schema 2, watermark-on or WSI-on. Those obsolete expectations were updated to the new requested behavior; the remaining inherited checks were retained. This is not represented as four newly discovered runtime faults.
- **1/1 Node frontend bundle smoke test passed**. Python compilation and JavaScript syntax checks passed. The frontend inspected in iteration 2 is byte-identical to the final frontend; subsequent corrections were documentation and the backend diagnostic bypass guard only.
- Reviewed `README.md`, `docs/research.md` and `docs/acceptance.md` for agreement with the final code, upgrade steps and explicit hardware boundaries. The exact runtime/code hashes are recorded in `evidence/reviewed-code-sha256.json` and checked by the packaging script.

### Aesthetic Executioner

**Verdict:** APPROVED

Approval scope: the final complete inspectable UI and workflow, with native Decky rendering and physical controller behavior still to be confirmed on the user's Deck.

**Blocking findings:** None remaining within this scope.

**Non-blocking improvements:** No additional cosmetic changes requested before the user's device evaluation.

**Verification performed:** Rechecked the complete final frontend and its unchanged rendered output, all normal tabs and wizard/confirmation states from iteration 2, and updated help/upgrade wording. The fixed actions remain above the simulated Steam bar; content can scroll without moving them; the banner control is explicitly optional and no longer reset by presets; status text does not promise a measured 60 FPS output. The final frontend is the same bundle used by `evidence/1.1.1/ui-inspection.json` and its screenshots. This was not an on-device inspection.

## Final accounting

Review cycles: 3. Logic Inquisitor rejections: 2. Aesthetic Executioner rejections: 1. All listed implementation/documentation corrections are complete. Both final scoped approvals refer to the same code hash manifest.

Important remaining limitations: this update replaces the incorrect launch arrangement with upstream's VSync troubleshooting path, but cannot certify that the Deck slider now caps LSFG or that 33 base FPS is retained while displaying 60. VSync back-pressure may reduce the base rate and disabling WSI may affect HDR. Actual native Decky CSS/focus, INT8 rendering and disappearance of the watermark in the game also need the user's device test. The existing downloader was not re-tested against live endpoints because this update does not alter it. Third-party tool binaries remain outside this ZIP. Reapply each affected profile and fully restart the game after upgrading.
