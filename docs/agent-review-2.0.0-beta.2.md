# Deck Fusion v2.0.0-beta.2 independent review log

Date: 2026-09-13. Only Codeweaver (the parent implementation agent) modified project code. Logic Inquisitor and Aesthetic Executioner performed independent read-only reviews.

## Scope

This addition introduces an optional pinned fsr4xyz 4.1.1b RDNA2 DLL, conservative Steam Deck/RDNA2 defaults, retained per-game choices, separate verified download/cache, conditional deployment, standard-DLL restoration, and switches in Upscaling, Tools and setup. The v2 Studio interface from beta.1 is retained.

## Rejection counters and history

- Logic Inquisitor: 0 rejected iterations for beta.2; 1 in the preceding beta.1 review.
- Aesthetic Executioner: 0 rejected iterations for beta.2; 1 in the preceding beta.1 review.

The complete preceding findings and corrections are preserved in `docs/agent-review-2.0.0-beta.1.md`. No rejected findings have been removed from that history.

## Implementation corrections before final approval

- A full regression run caught an accidental reference to `component` in shader archive installation during cache-generation editing. Codeweaver removed that unrelated insertion; the full suite subsequently passed.
- Codeweaver identified that changing the checkbox during component preparation cleared displayed requirements but previously needed a manual refresh. A cancelable read-only effect now recalculates requirements for the current draft on that step. Both reviewers inspected the effect. A dedicated DOM regression confirms opt-out enables progression without any install job.
- During construction of that test, its fixture first retained the prior session draft and then incorrectly expected an enabled button to serialize `aria-disabled="false"` instead of omitting the attribute. The fixture now clears the old session draft before remounting; the test checks enabled behavior by actually advancing to the summary. These were test-harness corrections, not runtime defects.

## Logic Inquisitor

**Final verdict: APPROVED**, including the final cancelable requirements-refresh effect.

**Blocking findings:** None. **Non-blocking improvements:** None required.

Independently inspected hardware defaults, profile migration and explicit choices, pinned package resolution, safe extraction and PE checks, cache integrity and repair, dependency gating, transaction deployment, standard-DLL restoration and UI draft handling. Reran 253 Python tests and the final 20 Node tests, none skipped. Verified exact source/distribution correspondence and Node syntax. Independently hashed the real downloaded archive and confirmed the production pin.

The reviewer rechecked effect cleanup, preparation and Next-step validation. Stale effect responses cannot overwrite current requirements after draft changes or leaving the preparation step. The final DOM scenario reaches the application summary after unchecking without starting an installation job.

## Aesthetic Executioner

**Final verdict: APPROVED within source and executable DOM scope.**

**Blocking findings:** None. **Non-blocking improvements:** None identified for this addition.

Inspected fix controls in Upscaling, Tools, wizard targets and preparation, contextual help and final DLL summary. Independently exercised wizard FSR 4 INT8 selection, prechecked switch appearance, opt-out retention through preparation and Tools, and contextual help. Verified that toggles trigger no install jobs and preparation automatically requests current requirements. Final React/jsdom rerun: seven tests passed, zero failed or skipped. Exact source/build parity passed.

Checked accessible switch state and bounded pagination in source and mocked 1280×800, 800×500 and 390×844 viewport scenarios. These scenarios do not establish actual rendered fit.

## Final verification evidence

- Python: **253 passed**.
- Node: **20 passed**, including seven real React/jsdom scenarios, none skipped.
- Final build and Node syntax check passed.
- Real release archive: SHA-256 matched the published digest; extracted DLL inspected as PE64 and accepted through the component installer in an isolated temporary directory. The DLL was never executed.
- `evidence/2.0.0-beta.2/verification.txt` contains the final command output.
- `evidence/2.0.0-beta.2/release-inspection.json` records the archive and payload inspection.
- `evidence/reviewed-code-sha256.json` binds packaged sources and runtime files. Packaging checks CRCs, safe paths and exact source/bundle correspondence.

## Limits

No physical Steam Deck, Steam/Decky session, game launch, GPU compatibility run or ghosting improvement was tested. Upstream describes a Windows RDNA2 fix; compatibility and improvement through Proton remain unverified. React/jsdom geometry is explicitly mocked. Browser rendering, actual screen fit, graphical performance, native focus navigation and raw Steam input delivery remain device-validation items. Browser access limitations from beta.1 remain applicable; no browser workaround was attempted for this addition.
