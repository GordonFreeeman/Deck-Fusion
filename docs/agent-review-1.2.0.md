# Deck Fusion 1.2.0: implementation and review record

Baseline: the uploaded `Deck-Fusion-1.1.2.zip`. Output: developer-installable `Deck-Fusion-1.2.0.zip`.

These are separately scoped review passes performed by the assistant under the Codeweaver, Logic Inquisitor and Aesthetic Executioner roles. They are not independent spawned models or a substitute for testing on the user's Steam Deck. Only the Codeweaver implementation pass changed code. Findings below report observable code, executed checks and browser output, not hidden deliberation.

## Scope and acceptance criteria

The requested changes are: correct the persistent INT8 diagnostic banner with the toggle off; detect/preserve existing Wine overrides and mod DLLs; add manual and detected-file override controls; propose compatible, unoccupied graphics-loader names; remove the fixed FPS preset without changing manual values. `docs/acceptance-1.2.0.md` records the complete acceptance criteria. Previous release reviews and behavior are archived in `docs/agent-review-1.1.2.md` and `docs/README-1.1.2.md`.

### Codeweaver inspection and implementation

Inspected the extracted runtime, launch wrapper, INI writer, profile migration, transaction/confirmation flow, Decky RPC handling, frontend controls and cross-window viewport code before editing. Inspected upstream OptiScaler DLL initialization, GE-Proton's indicator handling and ReShade's official API-to-module mapping. See `docs/research-1.2.0.md`.

Reproduced two defects in the original 1.1.2 code: the disabled watermark left `MLSR-WATERMARK=1` in the environment, and duplicate INI keys could retain a later `true` after the first key became `false`.

Implemented direct SDK/Proton diagnostic control, case-insensitive all-occurrence INI patching, a read-only Wine/prefix/DLL inspector and conservative loader allocator, per-profile custom overrides, merge and payload protection, a DLLs tab and wizard link, explicit apply disclosures, and removal of both preset buttons. Retained the existing 1.1.2 owner-window sizing, footer reserve, recovery boundary, transaction and TLS behavior.

## Iteration 1

### Logic Inquisitor

**Verdict:** REJECTED

**Blocking findings:**

1. **The newer Proton watermark alias was still retained.**
   * Evidence/reproduction: `tests/test_120.py::test_watermark_direct_and_proton_switches` failed with inherited `FSR_WATERMARK=1`; the first implementation cleared only the older `FSR4_WATERMARK`. Upstream Proton's `fsr4hud` branch uses the newer alias.
   * Expected behavior: disable the direct SDK flag and all identified upscaling-indicator aliases when the user disables the toggle, without changing INT8 selection or unrelated FG diagnostics.
   * Required correction: clear the newer alias as well, keep explicit zero for `PROTON_FSR4_INDICATOR`, and include the alias in last-launch diagnostics.
   * Severity: High.

2. **The supported standalone DX12 ReShade alternative was omitted.**
   * Evidence/reproduction: `test_reshade_supported_alternative_preserves_dxgi[dx12-d3d12]` failed. ReShade's official installer maps its D3D12 selection to `d3d12.dll`.
   * Expected behavior: when `dxgi.dll` is reserved, offer/allocate an API-supported free name rather than unnecessarily block or force companion mode.
   * Required correction: add `d3d12` to the DX12 backend/UI choices and validator. The original broad dxgi collision policy also needs to respect an explicit, noncolliding standalone choice.
   * Severity: Medium.

3. **External mod-file changes did not invalidate an existing confirmation.**
   * Evidence/reproduction: inherited `test_changed_confirmation_rejected[game]` failed after collision avoidance stopped putting the external mod in the managed write set. The mod changed between plan and acceptance, but its unchanged name/architecture did not alter the plan token.
   * Expected behavior: require fresh confirmation when the inspected local DLL inventory changes.
   * Required correction: bind local DLL file identity, size and nanosecond modification/change timestamps to the hashed preflight context, retaining managed-file content checks.
   * Severity: Medium.

4. **Case-variant files could produce duplicate dropdown module identities.**
   * Evidence: the first inspector mapped filenames through case folding without grouping duplicates; `Version.dll` and `version.dll` would produce two options with the same value. The frontend's first entry map also used an ordinary prototype-bearing object for arbitrary basenames.
   * Expected behavior: never imply an unambiguous DLL choice where Wine case matching is ambiguous; do not treat a user module name as an object prototype property.
   * Required correction: suppress ambiguous case-variant files from the dropdown, warn, block custom rules targeting the ambiguity, and use a null-prototype frontend entry map.
   * Severity: Low.

**Non-blocking improvements:**

* Keep a clear distinction between requesting a supported proxy and proving that a game imports it. Retain that qualification in the UI and documentation.

**Verification performed:**

* Read the actual changed launch, inspection, allocation, engine, profile, UI and transaction integration code.
* Ran the first new regression file: 23 passed, 2 failed (findings 1 and 2).
* Ran the inherited suite and examined changed expectations. The external-file approval test revealed finding 3. Historical tests that expected destructive override replacement or schema 3 were updated only where the new requested behavior intentionally superseded them.
* Compared the official SDK/Proton flag paths and ReShade's supported module mapping with the implementation.

### Aesthetic Executioner

**Verdict:** REJECTED

**Blocking findings:**

1. **Refreshing same-game DLL inspection removed and reinserted the controls.**
   * Evidence/reproduction: the first rendered DLL workflow captured the inventory replaced by “Scanning DLLs…” and the proposal panel missing immediately after adding an override. Code inspection showed unconditional `setWineInfo(null)` on every relevant edit. This changed scroll geometry and could lose the focused dropdown.
   * Expected behavior: keep same-game controls mounted during recalculation, indicate that the proposal is refreshing, and clear the inventory only when the selected game/executable changes.
   * Required correction: retain the previous same-game inventory, add a stable refresh-status line, disable stale file selection until completion, label refreshing/failed proposals, and reject stale responses through the existing effect cleanup.
   * Severity: Medium.

**Non-blocking improvements:**

* Preserve concise module-name entry and explicit native/builtin labels rather than adding an unexplained raw shell-command editor.

**Verification performed:**

* Inspected actual Chromium screenshots at 1280×800 and the compact confirmation at 800×500, then examined the corresponding state/effect code.
* The first complete browser workflow exercised inherited override display, scanned DLL selection, custom entry creation/removal, cancel, real backend prepare/finish and wizard resume at 1280×800, 1024×640 and 800×500.
* The browser host uses real React and two separate Windows: a zero-height plugin module window and a visible application window with a 40-pixel top offset and 56-pixel simulated Steam footer. Decky widgets and Steam's API are simulated. The Python backend, asynchronous jobs, file transactions and launch-option verification logic are real.

### Codeweaver correction checklist

Completed all five blocking corrections. Added the missing watermark alias and DX12 proxy, guarded explicit standalone selection, bound external DLL metadata into confirmation, rejected ambiguous case-variant file choices, used a null-prototype map, and kept same-game refresh controls mounted. Rebuilt the bundle, reran the relevant checks and submitted the complete implementation to both review passes.

No finding was dismissed. Initial browser-script failures caused by mismatched test locator labels were corrected in the inspection harness, not counted as application defects.

## Iteration 2: final complete-implementation review

### Logic Inquisitor

**Verdict:** APPROVED

**Blocking findings:** None identified within the inspected configuration and workflow scope.

**Non-blocking improvements:**

* Game-specific proof that a chosen proxy is actually imported, real Wine load order after every possible third-party launcher, and GPU watermark/pacing observations require device access. The UI and README explicitly avoid claiming those observations.

**Verification performed:**

* Re-inspected the entire changed feature path: `main.py`, profile schema/defaults/migration, `fusion_wine.py`, launch parsing/merge/runtime diagnostics, INI patching, loader/payload protection, policy/engine preflight, approval/restore integration and frontend actions.
* Full fast Python suite: **163 passed**. New 1.2.0 file: **27 tests**, covering direct/alias watermark state, INT8 preservation, repeated/case-variant keys, grouped/wildcard/disabled overrides, unsafe input, last literal shell assignment, read-only global/per-game prefix inspection, protected existing mod files, native-only custom setup, alternative ReShade proxies, exhausted loader names, managed-proxy exclusion, restoration of a previously backed-up mod, rollback, explicit noncolliding ReShade selection, ambiguous case-variant rejection and preserving manual FPS values while removing presets.
* Subprocess execution of the actual persistent launch wrapper verified the disabled SDK environment flag and last-launch diagnostics with synthetic fixtures.
* Actual backend review/prepare/finish with a simulated Steam setter preserved the inherited `version=n,b;dinput8=` text, custom `winmm=n,b`, Version.dll and winmm.dll; selected a free OptiScaler proxy; wrote the watermark false without changing INT8 selection. The cancel path preserved game file bytes, saved profile bytes and launch text.
* Eight Node frontend/bundle/viewport checks passed. Python compilation and JavaScript syntax checks passed.
* No subprocess executed a game or a third-party graphics DLL. Fixtures are synthetic PE files, never represented as real GPU testing.

### Aesthetic Executioner

**Verdict:** APPROVED

**Blocking findings:** None identified in the rendered host or inspected UI paths.

**Non-blocking improvements:**

* Native Steam styling, physical controller focus and shoulder-button behavior remain subject to the user's hardware test. The plugin continues to use the existing native Decky Tabs; no claim of physical L1/R1 testing is made.

**Verification performed:**

* Re-inspected the complete rebuilt UI, including the unchanged cross-window sizing/recovery code and new DLL page, dropdown/entry actions, loader proposals, confirmation, wizard link/resume and removed preset controls.
* Re-ran the live-backend browser workflow for **1280×800, 1024×640 and 800×500**. No unhandled page errors or horizontal overflow. Both entry routes opened with the plugin module's viewport height deliberately set to zero.
* Verified that a same-game refresh retained the DLL select element; the updated status/proposal labels avoid the previous collapse.
* Confirm/cancel buttons stayed above the simulated footer; wizard actions remained in their non-shrinking action row. Main content remained scrollable inside its pane rather than scrolling the document.
* Reviewed actual screenshots, including the 1280×800 DLL proposal, 1024×640 confirmation, 800×500 DLL page, 800×500 confirmation and 800×500 resumed wizard.
* Manager bottoms/footer tops respectively: 728/744, 568/584, 428/444 pixels, providing 16 pixels of clearance in every recorded viewport. Body scroll remained zero.
* Reproducible evidence: `evidence/1.2.0/ui-inspection.json`, `evidence/1.2.0/*.png` and `tests/browser/inspect_120.py`. The report records the inspected frontend SHA-256.

## Rejection counters

* Logic Inquisitor: **1 rejected iteration**, corrected in iteration 2.
* Aesthetic Executioner: **1 rejected iteration**, corrected in iteration 2.
* Final result: both review roles approved the **same final implementation**, with no open blocking findings in the inspectable scope.

## Packaging and genuine limitations

The release builder requires source and built frontend equality, verifies recorded runtime/document hashes, checks ZIP CRCs and safe paths, excludes symlinks/caches/font files, and requires an empty privilege-flag list. The resulting ZIP retains the `deck-fusion/` root required by the existing installation. The separate checksum identifies the delivered archive. Clean-extraction verification results are supplied beside the archive.

This is not a claim of hardware certification or support for every game. No live FSR output, on-device watermark visibility, actual Wine DLL injection, native Decky controller traversal or display FPS was measured. The correction addresses the identified and reproduced flag/INI paths; scripts that alter settings after the plugin wrapper and different external diagnostic overlays remain outside this inspection. The prior limiter compatibility path is unchanged. Initial tools are still not embedded; existing caches and updater behavior are retained.
