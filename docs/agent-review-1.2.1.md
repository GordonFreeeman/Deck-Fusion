# Deck Fusion 1.2.1 agent review

## Scope and evidence boundary
This is a repair-installation update to the supplied `Deck-Fusion-1.2.0.zip`. The Codeweaver implementation, Logic Inquisitor review and Aesthetic Executioner review are separate role-based passes in this session, not externally spawned agents. Browser observations use real Chromium/React, the actual Python backend and transaction code, simulated Steam/Decky components, synthetic game/component files, a hidden module window and a simulated Steam footer. No Steam Deck, Proton injection or GPU operation is claimed.

Acceptance criteria: `docs/acceptance-1.2.1.md`.
Baseline: `evidence/1.2.1/baseline.json` reproduces installing and deleting tracked files, then receiving the old externally-changed-file refusal. No actual Cyberpunk binaries are used.

## Iteration 1
Codeweaver implemented operation-scoped force repair through UI, RPC, plan approval and journaled transaction paths. Repair reinstalls selected files, snapshots overwritten replacements, retains original backups, preserves/untracks independently changed obsolete files, and continues checking safety conditions. The flag is not saved in profiles or the launch runtime.

### Logic Inquisitor
**Verdict:** REJECTED

**Blocking findings:**
1. **Defect:** Repair permission is cleared too late during game selection.
   **Evidence/reproduction:** Code inspection of `Manager.load`: it awaited profile, scan and schema RPCs before calling `setForceRepair(false)`. Enable the repair toggle and start a load/reload whose RPC fails. The previous game's repair toggle remains armed. Successful selection resets it, but failure does not.
   **Expected behavior:** A one-shot permission must clear immediately when a game selection/reload starts, including when loading fails or the filtered library becomes empty.
   **Required correction:** Clear repair permission and the displayed repair receipt before the first await in `load`, and clear permission when no game remains selected.
   **Severity:** Medium.

**Non-blocking improvements:**
- Make clear that an obsolete externally changed DLL kept in place is not disabled by merely removing it from tracking.

**Verification performed:**
- Reviewed the full transaction inspect/prepare/finalize/rollback paths, Engine review/plan/approval/prepare paths, RPC forwarding, Wine-loader guards and UI consent/state flow.
- Executed 18 new repair-focused backend checks. All passed.
- Executed 52 existing transaction/approval/DLL-override regressions. All passed.
- Checked the backend/renderer integration evidence: plan is read-only, Cancel preserves files/profile/launch text, explicit repair applies with backup snapshots, and the checkbox resets after success/cancel.
- Did not execute a native Steam client, game, DLL or Vulkan layer.

### Aesthetic Executioner
**Verdict:** REJECTED

**Blocking findings:**
1. **Defect:** All repaired-file rows sit inside one potentially very tall focusable card.
   **Evidence/reproduction:** Inspected the actual 800x500 repair confirmation and 1280x800 file-list screenshot, plus the `Confirmation` rendering code. The list can exceed the scrolling viewport, but individual rows are not focus targets. A gamepad user can move to the list card and the following card without reaching each row in between.
   **Expected behavior:** Every affected path/action must be individually reachable within the scroll panel while Cancel and the explicit repair button remain above the Steam footer.
   **Required correction:** Render each path/action as a separate focusable item, move repair details ahead of general setting resolutions, and verify focused rows scroll within the constrained panel.
   **Severity:** Medium.

**Non-blocking improvements:**
- Include a short instruction that the repair list is scrollable rather than relying on a clipped next card as the only cue.

**Verification performed:**
- Ran the frontend with the actual Python backend at 1280x800, 1024x640 and 800x500.
- Used both the blocked-plan repair route and explicit toggle route; inspected confirmation, Cancel and success states.
- Measured primary-button clearance and horizontal overflow. Buttons cleared the simulated Steam footer and no horizontal overflow/page errors were found.
- Opened and visually inspected `repair-confirm-800x500.png` and `repair-files-1280x800.png` from iteration 1.
- No claim of native Decky rendering or physical controller testing.

### Returned to Codeweaver
- [ ] Clear one-shot repair state at the start of selection/reload and when the selection disappears.
- [ ] Make each repaired path individually focusable and scrollable; show repair details before unrelated resolutions.
- [ ] Explain kept/untracked DLLs are not disabled.
- [ ] Rebuild, rerun focused affected checks and return the complete revised implementation to both review passes.

**Rejection counters after iteration 1:** Logic Inquisitor 1; Aesthetic Executioner 1.

## Iteration 2
The Codeweaver moved permission reset before the first game-load await and into the empty-selection branches. Each repaired file now has a separate focusable card, appears before unrelated setting resolutions and has an explicit scroll cue. The UI explains that a kept/untracked DLL is not disabled.

### Logic Inquisitor
**Verdict:** REJECTED

**Blocking findings:**
1. **Defect:** Missing retired graphics proxies with backed-up original mod loaders were left absent rather than restoring the original.
   **Evidence/reproduction:** `evidence/1.2.1/original-loader-edge.json` records an executed synthetic reproduction: simulate an older release replacing an original `version.dll`, retain `version=n,b`, delete the installed proxy, and request repair. Loader allocation correctly moved OptiScaler to `dxgi.dll`, but repair left `version.dll` absent despite an intact original backup. The preserved override would no longer reach that local mod loader.
   **Expected behavior:** When retiring a missing managed path with an original backup, explicitly propose restoring that original. A path created only by Deck Fusion may stay absent. Independently replaced obsolete files must still remain untouched.
   **Required correction:** Distinguish `restore-original` from `leave-absent`, bind the restored content hash into file-state approval and staging verification, label it in the UI, and add an engine-level regression for the combined repair/loader-allocation path.
   **Severity:** High.

**Non-blocking improvements:** None.

**Verification performed:**
- Re-examined the complete revised transaction, approval, frontend state and existing DLL allocation/backup interactions.
- Executed the older-installation/original-loader reproduction recorded above.
- Reviewed the successful browser results for per-file focus/scrolling, cancellation, repaired installation, preserved overrides and failed-reload permission reset.

### Aesthetic Executioner
**Verdict:** APPROVED

**Blocking findings:** None remaining in the revised per-file interaction.

**Non-blocking improvements:** None required for this change.

**Verification performed:**
- Re-ran real-browser + actual-backend workflows at 1280x800, 1024x640 and 800x500.
- Focused all six affected binary/shader rows individually at each size and measured each focused row fully inside its scroll panel.
- Checked Cancel/repair actions clear the simulated Steam footer; no horizontal overflow or page errors.
- Opened and inspected the revised 800x500 file list and 1280x800 completed-repair screen.
- Tested a failed profile-reload RPC after arming repair: the toggle reset correctly. The failure is simulated and reported visibly, not a native Deck error.
- A test-harness return-value bug initially invoked the restored RPC binding with no argument. It was corrected in the harness, not in runtime plugin code; `harness-return-fix.txt` retains the failed harness trace. The complete run then passed.

### Returned to Codeweaver
- [x] Both iteration-1 corrections accepted by their respective reviewers.
- [ ] Restore verified original mod loaders when retiring a manually deleted graphics proxy.
- [ ] Verify the complete revised result again, including unchanged Wine/FPS/watermark behavior.

**Rejection counters after iteration 2:** Logic Inquisitor 2; Aesthetic Executioner 1.

## Iteration 3: final implementation
The Codeweaver added `restore-original` for a missing obsolete path with a verified original backup. Approval now also includes the actual restored-content hash, and staging checks that hash. Missing paths without originals remain absent; changed obsolete files stay untouched. The existing original-launch and original-file records are preserved. The confirmation explains the original-mod restoration explicitly. A new engine regression exercises the complete older-installation + manual deletion + automatic loader move + repair path.

### Logic Inquisitor
**Verdict:** APPROVED

**Blocking findings:** None remaining in the inspected implementation.

**Non-blocking improvements:** None required for this repair update.

**Verification performed:**
- Reviewed the complete final `fusion_transaction.py`, interacting Engine review/plan/prepare/finish/rollback logic, RPC operation flag, UI consent/reset flow and unchanged Wine allocation/payload guards.
- All **182 backend regression cases passed in 7.01 seconds**, including 19 new repair cases. These are host-side synthetic/local tests, not GPU tests.
- New checks cover deleted DLLs/shaders/configs, manually replaced binary snapshots, original-backup preservation, cancel/read-only preview, unapproved force requests, normal-token reuse rejection, changed game/package/profile/manifest approval rejection, interrupted writes, explicit rollback to absent/replaced files, pending journals, unchanged obsolete files, original mod restoration, protected mod overrides, running-process/anti-cheat guards, unsafe symlinks, insufficient installation space, corrupt backups and invalid flags.
- Final browser/RPC integration verifies repair through `start_job`/`plan`/`prepare`, simulated Steam readback, backend finalize, receipt creation and untouched `version=n,b` mod data.
- Python compilation, JavaScript syntax and eight bundle/viewport checks passed.
- Reviewed runtime-diff scope: only the transaction/orchestration/RPC/frontend paths and version labels changed. `fusion_launch.py`, `fusion_runtime.py`, `fusion_policy.py`, `fusion_wine.py`, component download code, Steam discovery and shader generation are byte-identical to 1.2.0.
- No claim of physical Steam Deck testing, DLL injection, FPS improvement or changed FSR/LSFG behavior.

### Aesthetic Executioner
**Verdict:** APPROVED

**Blocking findings:** None remaining in the final rendered/inspectable UI.

**Non-blocking improvements:** None required for this change.

**Verification performed:**
- Re-ran the complete focused browser workflow against the final built frontend and final Python backend at 1280x800, 1024x640 and 800x500. Evidence and the exact inspected bundle hash are in `evidence/1.2.1/ui-inspection.json`.
- Both access routes work: normal blocked Apply → Review force repair → explicit confirmation, and Apply-tab toggle → explicit confirmation.
- Confirmed visible repair/backup intent, per-file missing/changed labels, scroll/focus reachability, Cancel, successful completion and one-shot reset. The original-backup restoration label was examined in the final rendered UI code and its behavior verified by the backend regression.
- Each of six repair rows was individually focused and fully visible inside the scroll panel at all three sizes. Primary buttons clear the simulated Steam footer; the visible page has nonzero height despite a zero-height hidden module window.
- No horizontal overflow or unhandled browser errors. The unchanged global UI recovery/viewport checks also passed.
- Steam/Decky widgets and input APIs are simulated here, so this approval does not imply native Decky or physical-controller validation.

### Closure
- [x] Clear repair state even on a failed game selection/reload or empty selection.
- [x] Make every repaired-file row independently focusable/scrollable.
- [x] Preserve old original mod loaders when retiring a deleted graphics proxy.
- [x] Preserve backups, original launch options, user overrides and unrelated mod files.
- [x] Retain all hard safety stops; do not persist force authorization.
- [x] Both reviewers approve the same final runtime/source implementation.

**Final rejection counters:** Logic Inquisitor 2; Aesthetic Executioner 1.

## Release boundaries
Install the 1.2.1 ZIP over 1.2.0. Do not uninstall the plugin or delete `~/.local/share/deck-fusion`. Close the game before applying a repair. Repair does not download a missing tool cache, reset settings, change the FPS-limiter implementation, bypass protected mods or replace arbitrary untracked game files. Original backups and additional transaction snapshots remain available. Normal Restore uses the original pre-installation backups; per-repair snapshots are kept separately for manual recovery.

The exact archive CRC/path/hash checks and clean-extracted backend verification are recorded in the accompanying `Deck-Fusion-1.2.1-verification.json`. Native Steam Deck, real Cyberpunk, Proton injection and GPU behavior remain outside this environment's verification.
