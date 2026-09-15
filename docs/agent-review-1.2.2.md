# Deck Fusion 1.2.2: agent review record

## Scope and acceptance criteria

This record describes separate, emulated implementation, logic-review and visual-review passes, not independent external agents or physical Steam Deck sessions. Base: the supplied 1.2.1 ZIP. No remote repository commits or CI builds.

1. Watermark off must remove the SDK environment variable, not assign zero; pair this with an unspecified (`auto`) OptiScaler watermark option so v0.9.4 does not recreate zero. Preserve INT8 flags and other unrelated environment values. Keep explicit opt-in usable.
2. Select several existing DLLs cumulatively; add them together, without replacing previous custom entries. Preserve original Steam/prefix overrides and mod binaries. Retain existing approval, backup, conflict and one-shot force-repair safeguards.
3. Provide supported OptiScaler manual polling and Steam Input controls, with explicit warnings and Apply/restart semantics. Do not silently change the controller layout or claim physical mouse validation.
4. Offer bounded, read-only Cyberpunk framework/log evidence; do not imply that file presence proves successful loading or dependency compatibility.
5. Preserve the hidden-module-window/visible-window sizing fix, footer clearance, manual FPS settings and removed headroom preset. Deliver a rebuilt self-contained developer-install ZIP.

## Iteration 1: initial implementation inspection

### Logic Inquisitor
**Verdict:** REJECTED

**Blocking findings:**
1. Diagnostic RPC uses only the last saved executable while the button is enabled for the current selected draft. Evidence: `Engine.mod_diagnostics(appid)` read `self.profile(appid)`; the frontend sent only `appid`. On a fresh setup the saved exe is empty even when Cyberpunk2077.exe is selected. Expected: inspect the selected draft executable without requiring Apply. Required correction: pass the selected exe, validate it against the authoritative installation root, and keep reads bounded. **Severity: Medium.**
2. The redscript newest-log selection can raise on a concurrent removal between directory enumeration and stat. Evidence: `safe_target`/`stat` were outside per-file error handling. Expected: diagnostic report remains available with a note about a vanished/unreadable log. Required correction: catch each candidate failure before choosing the newest log. **Severity: Low.**

**Non-blocking improvements:** Keep an explicit timestamp and unknown/stale labels instead of a green "loaded" status inferred from files.

**Verification performed:** Inspected the current engine/RPC/frontend diagnostic data flow, guarded file-reader implementation, shared INI override map, launch environment merger, and upstream v0.9.4 watermark/polling configuration paths. No running-game or GPU test.

Codeweaver correction: the RPC now receives the current selected executable, enforces game-root confinement and no symlinks, and reports per-log races instead of discarding the whole report. A targeted regression check is required before approval.

### Aesthetic Executioner
**Verdict:** REJECTED

**Blocking findings:**
1. The new read-only framework and log cards had no individual focus targets. Evidence: current rendered mod-evidence screenshots at 1280x800 and 800x500, plus their DOM (`div` without tabindex/Focusable). Mouse scrolling reached the evidence, but controller focus could skip it to the final Show log text toggle. Expected: each card can receive focus and expose long evidence without moving the whole route. Required correction: use the existing Decky Focusable pattern, visible focus feedback, bounded overflow and keyboard scrolling within the focused card. **Severity: Medium.**
2. ManualInputPolling and DisableOverlays remained editable in the advanced INI section when explicit main controls owned those values. Evidence: rendered control mapping and `managed` condition in the frontend. The approval reconciler correctly overrode them, but the editor invited an ineffective edit. Expected: indicate that main controls own these two values whenever not in Keep upstream/advanced mode. Required correction: make the advanced rows informational in that case. **Severity: Low.**

**Non-blocking improvements:** No visual redesign requested; retain familiar navigation and the fixed footer-safe content area.

**Verification performed:** Opened the new batch-picker, mouse-control and mod-evidence screenshots; inspected rendered controls and frontend focus/advanced-setting ownership. The browser workflow already passed at 1280x800 and 800x500 in the hidden-module-window host. This is not native Decky/gamepad validation.

Codeweaver correction: added focusable, highlighted, bounded framework/log cards with keyboard scrolling, and marked explicitly controlled input settings as main-control-owned in the advanced editor. Returned the entire revised build to both review passes.


## Iteration 2: complete revised implementation

The complete rebuilt frontend and backend were re-examined, not only the latest patch. The published SDK presence guard and OptiScaler v0.9.4 optional-bool setter were considered together. The output strategy is a configuration workaround supported by those sources, not a claim to have exercised the proprietary INT8 DLL.

### Logic Inquisitor
**Verdict:** APPROVED

**Blocking findings:** None remaining in the inspectable implementation.

**Non-blocking improvements:** None required for this release. On-device banner/mouse/mod verification is a genuine environment limitation, not a completed test.

**Verification performed:**
- Inspected the complete current launch environment builder, persistent runtime, profile migration, OptiScaler schema matching/INI patching, main-control/advanced reconciliation, RPC routing and diagnostic reader. Verified the off path removes the SDK flag while its INI optional value remains unspecified; opt-in, bypass and unrelated FSR/FG values stay distinct.
- Checked batch selector helpers against the existing parser/merger and conflict-aware proxy planner. The three existing sample mod DLLs survive plan/cancel/apply/restore unchanged. Custom entries and inherited wildcard/disabled/other entries remain represented. No arbitrary DLL force-loading is claimed.
- Confirmed the repair/transaction, Wine-prefix/loader, library discovery, network safety and path-safety modules are byte-for-byte unchanged from supplied 1.2.1.
- Ran 131 focused backend cases (5.38 seconds), including absence-vs-zero semantics, generated INI auto, explicit/advanced mouse settings, supported-key rejection, wrapper execution with a synthetic child process, multi-DLL apply/restore, original mod bytes, draft-selected diagnostics, bounded/stale logs, symlink rejection, legacy redscript log fallback and one-shot force repair.
- Ran 13 Node checks for cumulative DLL helpers, validation, self-contained route registration, owner-window sizing and focus scrolling.
- Clean ZIP extraction: verified CRC, path safety, no font/symlink entries or root flag, reviewed code hashes, identical src/dist, JavaScript syntax, and isolated Python startup/state/diagnostics/shutdown.

Accepted corrections from iteration 1: the draft-selected diagnostic regression is covered; each candidate log error is handled without abandoning the report. Additional source cross-checking added the documented old redscript cache-log fallback and CET scripting log, rather than presenting absent modern logs as a universal result.

### Aesthetic Executioner
**Verdict:** APPROVED

**Blocking findings:** None remaining in the inspected rendered workflow.

**Non-blocking improvements:** No redesign required. Keep the existing familiar native-component structure. The simulated host cannot verify native Steam controller-event translation.

**Verification performed:**
- Inspected the actual current bundle in Chromium with real React, Python RPC/jobs/transactions and simulated Decky widgets/Steam launch APIs. Both 1280x800 and 800x500 were exercised with a zero-height hidden module window and a separate visible window.
- Viewed current screenshots of three checked DLL files, persistent batch count, the mouse-input controls, framework/log cards, focused card outline, watermark help, and the confirmation dialog. Selected all three DLLs, filtered a non-common name without losing custom entries, staged the mouse workaround, cancelled a plan, then applied it.
- Verified all seven framework/log cards can receive focus and remain within the scroll pane. The smaller viewport exercised local PageDown scrolling on a long card. Advanced rows owned by the main input controls now say so rather than inviting an ineffective edit.
- The 1280x800 frame ends at y=728 with the simulated footer starting at y=744. At 800x500 it ends at y=428 with the footer at y=444. Neither case has outer-page scrolling, horizontal overflow or unhandled page errors. Confirmation buttons stay above the footer.
- After the complete workflow, verified real generated INI mouse keys, watermark auto and preserved INT8 selection, merged Wine entries and unchanged synthetic mod files.

Accepted corrections from iteration 1: focus targets and visible focus feedback are present; bounded cards do not push controls behind the footer; directly owned advanced fields no longer accept conflicting edits.

## Verification record and limitations

Current evidence lives in `evidence/1.2.2/`; earlier folders are historical and are not presented as current results. `evidence/reviewed-code-sha256.json` identifies the exact runtime sources and bundle reviewed. The package script checks those hashes before delivery.

Two initial focused runs caught stale expectations in the old test file: first the old hard-coded wrapper version, then a missing Path import while making that assertion read the release metadata. Both test-harness issues were corrected. The final recorded run has 131 passes. No failed check is represented as a pass.

Rejection counters: Logic Inquisitor = 1; Aesthetic Executioner = 1. All four blocking findings from iteration 1 have been corrected and accepted. No hardware verification is claimed: actual INT8 banner visibility, Wine loading of the user's installed binaries, CET/RED4ext/redscript compatibility, and native Steam Deck mouse/gamepad events remain for on-device testing. No new LSFG limiter implementation or GPU performance result is included.

