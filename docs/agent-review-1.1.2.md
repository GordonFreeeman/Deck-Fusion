# Deck Fusion 1.1.2: black-screen regression review

## Scope and evidence

Request: after installing 1.1.1, both quick-access actions open a black screen. Deliver a corrected installable ZIP, retaining existing configuration and the earlier bottom-bar clearance fix. Keep verification focused rather than simulating GPU behavior.

The role names below represent separate implementation and adversarial review passes by this assistant, not three external processes. No physical Steam Deck was available. Historical logs are retained in `docs/agent-review-1.1.1.md` and earlier files; their earlier approvals do not override the reproduced regression.

Acceptance criteria are in `docs/acceptance-1.1.2.md`. The installed frontend is self-contained. Python runtime modules, downloaded-component handling, launch settings and transactions are unchanged from 1.1.1, verified byte-for-byte in `evidence/1.1.2/unchanged-backend-sha256.json`.

## Iteration 1: examine and reproduce the supplied 1.1.1 regression

### Logic Inquisitor

**Verdict:** REJECTED

**Blocking findings:**

1. **The viewport hook reads the wrong Window and accepts a zero-height result.**
   - Evidence: `useSteamViewport` uses module-global `window.innerHeight`, `window.visualViewport`, `requestAnimationFrame` and `ResizeObserver`. In a two-window browser host, the plugin module window has `innerHeight=0`, while the React-rendered frame's `ownerDocument.defaultView.innerHeight=800`. The original build writes `height: 0px`. Both routes reproduce the failure without a Python exception or an unhandled JavaScript error.
   - Expected behavior: geometry and lifecycle APIs refer to the window that owns the rendered DOM, and a hidden or transitional viewport cannot collapse the interface.
   - Required correction: use the DOM element's owning window, guard unusable measurements, retain a CSS/last-valid fallback and bind cleanup to the same window.
   - Severity: High.
2. **DOM focus helpers also assume a single browser realm.**
   - Evidence: the scroll helper tests nodes against the module-global `HTMLElement`; the raw editor searches the module-global `document`. Those references do not necessarily belong to the visible page. `scrollIntoView` can additionally scroll outer Steam containers rather than only the settings pane.
   - Expected behavior: focus works on the visible controls and does not move the outer Steam route.
   - Required correction: use a textarea ref and local scroll geometry without a cross-realm `instanceof` check.
   - Severity: Medium.

**Non-blocking improvements:** Add a route-local render/effect error boundary so another native-component exception provides visible recovery controls. This is a separate safeguard; the demonstrated zero-height failure does not itself throw an exception.

**Verification performed:** Compared 1.1.0 and 1.1.1 source, route registration, manager initialization and layout changes. Ran both quick-access actions in a real Chromium/React host. 1.1.0 rendered in the two-window case; 1.1.1 rendered with one window, but both actions went blank with two windows. Measurements and page-error results are in `baseline-reproduction.json`.

### Aesthetic Executioner

**Verdict:** REJECTED

**Blocking findings:**

1. **All visible content and navigation are clipped away.**
   - Evidence: opened the actual reproduction screenshot `baseline-1.1.1-black-screen.png`. Only the simulated Steam footer remains. The frame's inline height is zero; its measured 42-pixel box contains only top padding, with overflow hidden.
   - Expected behavior: the manager or wizard is visible, while its actions remain clear of the bottom bar.
   - Required correction: repair window sizing without reverting to the original full-height layout that hid the bottom buttons.
   - Severity: High.

**Non-blocking improvements:** A recovery view should keep its message and actions readable and should not depend on the same measured-layout hook or Decky component that could have failed.

**Verification performed:** Inspected the before/after-source layout and opened the 1280x800 baseline black-screen screenshot. Confirmed the old single-window test arrangement did not cover this failure mode. No native Steam screenshots were invented.

### Codeweaver corrections

- Sizing, observers, resize/visual-viewport events and animation scheduling now use `frame.ownerDocument.defaultView`.
- Detached, hidden, invalid and implausibly small measurements do not overwrite the last valid height. Initial rendering has a CSS fallback. Optional observer initialization can fail without preventing the page from opening.
- The 72-logical-pixel bottom-bar reserve is retained. Normal content scrolls inside the frame, with a separate wizard action row.
- Focus scrolls only the local content pane, without cross-window constructor tests. Raw-editor activation uses the rendered textarea ref.
- Both entry routes are wrapped in a local error boundary. Its fallback is plain DOM, independent of native Decky widgets and the measurement hook, with Retry opening and Back to Steam controls.
- No Python backend, stored profile schema, download code, launch environment, FSR settings or LSFG pacing setting was changed.

## Iteration 2: review the corrected implementation

### Logic Inquisitor

**Verdict:** APPROVED

**Blocking findings:** None remaining in the inspected black-screen fix.

**Non-blocking improvements:** The fallback's native controller behavior cannot be certified without the Steam focus system. Its browser actions and DOM rendering were verified. Keep the physical-device limitation explicit.

**Verification performed:**

- Reviewed both registered routes, the complete replacement viewport/focus helpers, the recovery boundary, raw editor, manager startup and wizard/normal tab rendering. Compared all runtime changes against 1.1.1; all backend files are identical.
- Eight Node tests pass, including bundle route registration, zero-height module versus visible owner window, owner-document fallback, scaled geometry, zero visual-viewport dimensions, detached/invalid/offscreen measurements, owner-window scheduling/listener cleanup with a failing optional observer, and cross-window local-pane focus scrolling.
- The existing backend suite passes: 136 tests in 4.97 seconds. No new GPU simulation or benchmark was run.
- The actual built frontend renders both entry points with a zero-height module window and a visible owner window. Resizing the owner window updates the height even when the optional observer constructor is made to fail.
- Intentionally throwing in a simulated native Tabs component displays the recovery boundary. Retry remounts the originating route, and Back to Steam navigates out. No settings/apply/write RPC was issued by the exercised entry/recovery paths.
- Source/build equality, JavaScript syntax and Python compilation passed. The runtime source hash list is generated for archive verification.

### Aesthetic Executioner

**Verdict:** APPROVED

**Blocking findings:** None remaining in the inspected route-opening and footer-safety scope.

**Non-blocking improvements:** At the smallest tested viewport, the instructions and fields require inner-pane scrolling. The fixed actions remain visible. Native Steam typography, focus traversal, scaling and the physical controller bar can differ from the mock widgets and still require the user's device run.

**Verification performed:**

- Ran the actual final frontend in Chromium using React 19.1.1 from the installed Playwright distribution, with two distinct browser windows. Decky widgets, Steam APIs, session storage and backend read responses are explicitly simulated. Backend read fixtures are generated from real Python test helpers; no real game binaries or GPU operation is involved.
- Both quick-access actions were checked at 1280x800, 1024x640 and 800x500. Frame bottoms were 728, 568 and 428 pixels, compared with simulated footer tops of 744, 584 and 444. No horizontal document overflow or unexpected page error was recorded.
- Exercised all six normal tabs, inner-pane scrolling, a clipped control's focus, wizard Next/Back and fixed-action hit testing. The outer document did not scroll.
- Visually inspected the corrected 1280x800 wizard, the 800x500 wizard, the 1280x800 manager in its deliberately scrolled state, and the 800x500 recovery screen. Also inspected the original black-screen reproduction for comparison. Buttons and recovery actions were above the simulated footer. The intermediate viewport was measured and exercised in the browser rather than represented as a separately hand-inspected screenshot.
- Verified the resize/unavailable-observer path, induced component error, Retry opening and Back to Steam. The seven-case report and screenshots are in `evidence/1.1.2/`.

## Verification limitations and failed harness attempts

A local HTTP browser navigation was blocked by this environment's administrator policy. The final harness instead injects local source into an in-memory page, without changing browser policy. External npm access was unavailable. The installed Playwright distribution supplied real React 19.1.1 for the inspection; it is not a production dependency and is not bundled with the plugin. Session storage and Steam/Decky APIs are mocks.

An initial inspection assertion incorrectly expected Retry to return to the Library tab even when the originating route was the wizard. It timed out. The assertion was corrected to require the originating screen to reopen, then test its navigation. No production code was changed to satisfy that mistaken expectation. The packaged inspection script was subsequently rerun successfully.

This is a concrete reproduced layout fix, not confirmation from a physical Steam Deck. It makes no new claims about FPS caps, frame pacing, FSR4 output, shader execution, Proton compatibility or anti-cheat safety. The prior graphics configuration and limitations are unchanged.

## Final accounting

Review iterations: 2. Logic Inquisitor rejections: 1. Aesthetic Executioner rejections: 1. Both final approvals refer to the same frontend hash in `evidence/1.1.2/ui-inspection.json`. All blocking findings listed above have corrections and verification evidence. The ZIP integrity check validates the reviewed source manifest, source/build equality, file paths, symlink exclusion and absence of a root flag. A clean extracted-package backend startup is checked separately during final packaging.
