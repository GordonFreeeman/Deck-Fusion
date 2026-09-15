# Deck Fusion 1.1.0 review record

Scope: source/configuration integrity and desktop-browser UI inspection. The three named roles are separate review passes by the same assistant, not independently running agents. No Steam Deck is connected. Graphics injection, frame pacing, actual hardware FSR4 support, native Decky focus/navigation and performance cannot be certified here. The previous release's review is preserved in docs/agent-review-1.0.0.md.

## Iteration 1

### Logic Inquisitor
**Verdict:** REJECTED

**Blocking findings:**
1. Approved file snapshots were checked in Engine.prepare, but Transaction.prepare took a new snapshot without comparing it to the approved one. Evidence: the call passed no expected_state; a file change between those functions could become a newly accepted conflict. Expected: approval binds the exact before/after contents until staging. Required correction: pass and validate the approved state inside the transaction before staging. Severity: High.
2. Importing an in-game INI retained the previous first-class FSR mode, which could override the freshly imported choices. Switching away from experimental FSR4 also risked retaining forced FSR values from the managed on-disk INI. Expected: explicit preset selection and overlay import have predictable precedence. Required correction: imports return FSR control to upstream/advanced mode; choosing a preset clears the incompatible managed values and FSR3 selection selects its actual output. Severity: Medium.

**Non-blocking improvements:** Keep hard blockers for running games, anti-cheat and modified managed binaries. Do not treat generic acknowledgement as permission to bypass them.

**Verification performed:** Read fusion_policy.py, fusion_launch.py, fusion_engine.py plan/prepare/build/import paths, fusion_transaction.py inspect/stage/apply/recovery and frontend apply/live-apply entry points. Existing 105 regression tests passed prior to this review. No hardware or browser claim for this iteration.

### Aesthetic Executioner
**Verdict:** REJECTED

**Blocking findings:**
1. Wizard component readiness could remain stale after exiting to Tools and resuming the same step, leaving Next disabled after a successful registration. Evidence: requirements state was only refreshed by selected wizard actions, not on resume. Expected: resumed status can be refreshed and reflects current components. Required correction: refresh on resume and provide an always-available refresh action. Severity: Medium.
2. The wizard offered a selectable "Keep current / advanced choices" item that did nothing when selected from a preset. Evidence: its onChange intentionally skipped the custom value. Expected: every selectable option works. Required correction: show the current custom choice only when active; use explicit presets and an advanced-controls route. Severity: Medium.
3. FSR 3.x backend selection could leave XeSS selected as output while the wizard displayed an FSR3 selection. Evidence: the mode dropdown only changed fsr_mode, unlike the preset buttons. Expected: selection and summary agree with the generated output. Required correction: route explicit FSR3 selections through the preset helper and reflect actual output in the wizard. Severity: Medium.

**Non-blocking improvements:** Label draft exit as "Keep draft & exit", since it retains a session draft, not a durable applied profile.

**Verification performed:** Inspected the implemented source for all five wizard steps, component-status flow, output selector, summary, confirmation dialog and fixed footer. Rendered inspection follows after correction. No approval based solely on a screenshot from the old release.

## Correction checklist
- [x] Bind the final transaction to the approved file snapshot.
- [x] Make FSR preset changes and overlay imports preserve the selected output honestly.
- [x] Refresh wizard readiness on resume and on demand.
- [x] Remove the no-op custom choice; clarify session-draft exit.
- [x] Review the corrected complete implementation and inspect the rendered UI.

## Iteration 2

### Logic Inquisitor
**Verdict:** REJECTED

**Blocking findings:**
1. The confirmation listed environment conflicts except WINEDLLOVERRIDES, although this is a critical injection setting. Expected: show the actual merged loader settings while preserving unrelated overrides. Correction: add a loader-override resolution to the single dialog. Severity: Medium.
2. A manually contradictory FSR3 preset plus XeSS per-API output could still pass planning. Expected: the explicit preset wins visibly, or custom mode retains manual choices. Correction: resolve the FSR3 route as explicitly as the FSR4 route. Severity: Medium.

**Verification performed:** Full corrected source reread of consent propagation, plan fingerprint, import precedence, restore and frame-generation policies. Ran 13 focused checks including old profile migration, read-only planning, accepted apply/restore, changed files/components/profiles, final transaction snapshot, both upstream FSR4 key generations and native-DLSS rejection on simulated AMD. All 13 passed before the additional findings above. The real backend also completed the short browser-host wizard and cancel/apply flow.

### Aesthetic Executioner
**Verdict:** REJECTED

**Blocking findings:**
1. The LSFG note said "Gamescope handles the output limit" and the wizard preset said "capped by the Deck at 60", despite that hardware behavior being unverified. Expected: labels distinguish a requested experimental compatibility path from measured output. Correction: qualify the note and preset button without hiding the actual goal. Severity: Medium.

**Verification performed:** Inspected current screenshots wizard-targets-1280.png, wizard-targets-800.png and confirm-800.png, rendered from the actual 1.1 frontend with real React 18 in Chromium and simulated Decky widgets. Footer and dialog actions remain visible at both 1280×800 and 800×500; long content scrolls inside the wizard/dialog. The five-step workflow, Tools/resume, effect selection, Cancel without writes and accepted Apply completed with the real Python backend and synthetic payloads. Zero unhandled browser errors. Native Decky typography/focus engine and physical controller behavior are not established by this host.

**Non-blocking improvements:** None additional within the current scope. Do not replace remaining hardware uncertainties with further synthetic benchmarks.


## Iteration 3: final review

### Logic Inquisitor
**Verdict:** APPROVED

Approval scope: the 1.1.0 implementation and package for the user's device evaluation. This is not approval of unmeasured Gamescope output pacing or FSR4 performance/compatibility.

**Blocking findings:** None remaining within the inspected implementation scope. The limiter and INT8 runtime outcomes remain explicitly unverified hardware limitations, not claimed successes.

**Non-blocking improvements:** Future hardware feedback may identify a more appropriate Gamescope layer arrangement for particular Proton versions. Do not promise that the requested base/output targets are achieved merely because the environment and INI are generated correctly.

**Verification performed:**
- Re-read the complete changed main.py, fusion_policy.py, fusion_catalog.py, fusion_engine.py, fusion_launch.py, fusion_runtime.py and transaction paths, plus frontend apply, restore, live-update, component readiness and wizard data flow. Compared the API assumptions with upstream Gamescope, OptiScaler and Decky declarations recorded in docs/research.md.
- Confirmed the approval fingerprint is revalidated against the same raw request; a final expected-state comparison now exists inside Transaction.prepare; snapshot staging and before-write comparison remain enabled. Consent is not saved as a reusable permission.
- Confirmed running-game, anti-cheat, file-modification, casing/symlink, rollback and launch-option safeguards were retained; no root permission or driver modification was introduced.
- All 119 backend checks passed in 4.20 seconds, including 14 focused new checks. These cover legacy profile defaults, limiter environment opt-in, no-write planning/cancellation, accepted apply/restore, stale game/package/profile rejection, final snapshot verification, supported FSR forcing keys, missing-key blockers, overlay import precedence and FSR3/Wine-override resolutions. These are synthetic file/configuration checks, not GPU tests.
- One Node bundle smoke check passed. Python compilation and JavaScript syntax checks passed.
- The real backend completed the short browser-host wizard/apply workflow. Cancel left the game, saved profile and simulated Steam launch state unchanged. Accept deployed the inspected fixture configuration and completed its transaction; the applied profile recorded 33 base, Gamescope integration requested, and FSR4 requested via fsr31. That record is NOT proof those frame rates/upscaling modes run on hardware.

### Aesthetic Executioner
**Verdict:** APPROVED

Approval scope: rendered layout and workflow in the desktop inspection host, plus the native Decky API usage visible in source. Native Steam Deck rendering and controller focus must still be checked on the device.

**Blocking findings:** None remaining within the inspectable layout/workflow. Earlier false-certainty wording, no-op selection and stale resume issues have been corrected.

**Non-blocking improvements:** No speculative UI churn requested before user device feedback.

**Verification performed:**
- Examined the complete corrected frontend including normal Library/LSFG/OptiScaler/ReShade/Apply/Tools paths, both quick-access entry routes, all five wizard steps, success state, live confirmation and full confirmation.
- Ran the actual final runtime bundle with React 18.2 in Chromium, simulated Decky widgets and Steam API, the real Python backend and synthetic component fixtures. This is an inspection host, not a Deck emulator. The host's first attempts hit an environment localhost-navigation restriction and a bridge argument-serialization issue; the final harness uses in-memory local scripts and a single-object bridge. Neither workaround changes production code or disables TLS.
- Inspected screenshots at 1280×800 and 800×500. Inspected current wizard targets, single confirmation, completion screen and the retained library view. Fixed wizard footer and dialog buttons remain reachable; long settings and warnings scroll inside their content area; no horizontal document overflow was observed.
- Followed game → features → 33/2× and experimental INT8 → components → Tools/resume → effects → Cancel → Apply → complete. Component status refreshed on resume, choices remained in the draft, and Cancel did not apply them. Zero unhandled browser errors occurred in the final run.
- Confirmed in source that custom output choices are no longer offered as a no-op action; explicit FSR3/FSR4 choices route through actual backend selection; the user-facing text reports requested/experimental behavior and explains how the watermark distinguishes fallback.

## Final accounting and limitations

Review iterations: 3. Logic Inquisitor rejections: 2. Aesthetic Executioner rejections: 2. All listed implementation corrections were completed. Both final approvals refer to the same runtime source hashes in evidence/reviewed-code-sha256.json.

Remaining limitations are genuine: no physical Steam Deck, actual Decky native focus/controller navigation, GPU graphics injection or performance benchmark was available. The 33→66→60 behavior may incur back-pressure or dropped-frame cadence and is not guaranteed by the setting. FSR4 INT8 remains unsupported/experimental on the Deck and may fall back to FSR3 or perform poorly. Native NVIDIA DLSS is not implemented on AMD. External component download behavior was not re-tested against the network in this update; the working 1.0.0 downloader/TLS implementation is unchanged. Windows Vulkan/native Linux ReShade remain outside the implemented installation path. The archive contains no third-party graphics tool binaries.
