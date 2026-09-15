# Deck Fusion v2.0.0-beta.1 independent review log

Only the Codeweaver (parent implementation agent) changed project code. The Logic Inquisitor and Aesthetic Executioner independently inspected the same implementation, reported findings, and did not edit it.

This log records actual work. No current browser screenshot or physical Steam Deck test is claimed. The shell browser environment could not use the required sockets; the browser service blocked local preview URLs. Reviewers therefore used source inspection and executable DOM/input tests within the available scope.

## Rejection counters

- Logic Inquisitor: 1 rejected iteration so far.
- Aesthetic Executioner: 1 rejected iteration so far.

## Iteration 1: Logic Inquisitor

**Verdict: REJECTED**

### Blocking findings

1. **High: Focus disappears after changing settings pages.** Keyed card replacement can unmount the focused control. Focus recovery depended only on the tab/game/wizard key, leaving focus on body after pagination. Required recovery after page and control-inventory changes.
2. **High: Reader pagination can hide diagnostics.** Character-count chunking did not account for line breaks or available height, while CSS hid overflow. Required measured pagination and resize handling.
3. **High: Local pointer cannot reach confirmations.** Hit testing was confined to the Studio frame, while native Apply/runtime dialogs live in an external portal. Those dialogs also retained scrolling details. Required owned-dialog input scope and bounded detail pages.
4. **Medium: R3 click after a pause fails.** Raw-controller ownership reset after 250 ms and could only be reacquired by touch or stick movement, so a centered R3 press was skipped. The reviewer executed the actual hook with synthetic typed packets and reproduced zero clicks after a 500 ms pause, then a successful pad click.

### Non-blocking improvements

Explain right-pad/R3 controls and explicitly describe settings pages in release notes.

### Verification performed

Read Studio, Manager, both confirmation components and Decky input definitions. Independently ran 231 Python and 13 core Node tests, all passing. Syntax checked Studio and the generated bundle, verified build correspondence, compared the uploaded backend (version-literal changes only) and unchanged bundle payloads. Executed the actual raw input hook in a Node VM to reproduce the R3 bug. Browser/device behavior was not verified.

### Corrections made by Codeweaver

- Restore focus after page size, page, game/tab and control-inventory changes.
- Replace character-based splitting with binary-fit DOM measurements and ResizeObserver; preserve every original character.
- Render confirmation details through StudioReviewContent, retaining native authorization/cancel callbacks. Identify owned modal roots explicitly and confine pointer hit testing to them or the local editor.
- Put the cursor above the owned modal portal with lifecycle cleanup.
- Let pointer-click buttons reacquire controller ownership after idle.
- Document all controls and fallback behavior.

## Iteration 1: Aesthetic Executioner

**Verdict: REJECTED**

### Blocking findings

1. **High: Newline-rich reader content is clipped.** The reviewer executed the exact splitter with 100 numbered lines totaling 289 characters. It produced one page at all three limits, although the text required at least 1950 px. Required measured fitting and lossless pagination.
2. **Medium: Disabled actions look active.** StudioButton renders U.Focusable with aria-disabled, while CSS only styled native button:disabled. Required styling the actual disabled attributes and suppressing active hover.

### Non-blocking improvements

Style data-pointer-hover for virtual-pointer feedback. Inspect the narrow header because brand and action widths shared one unwrapped row.

### Verification performed

Read Studio in full and relevant Manager/viewport/wizard/diagnostic code. Examined normal, short and narrow CSS branches for the 1280×800, 1024×640, 800×500 and 390×844 target sizes. Executed the splitter reproduction. Reviewed focus, input labels, reduced motion and pagination. No current browser rendering or screenshot inspection was performed.

### Corrections made by Codeweaver

- Measured lossless reader pagination as above.
- Style aria-disabled targets directly, including opacity and pointer behavior.
- Add a visible virtual-pointer hover outline.
- Hide the animation shortcut and shorten the Apply label on narrow headers.
- Display otherwise empty wizard summaries as inspectable information cards.

## Iteration 2

Both reviewers were asked to examine the complete revised implementation independently. Final verdicts and any subsequent corrections are appended below.

### Logic Inquisitor, iteration 2

**Verdict: APPROVED**

**Blocking findings:** None within the inspected implementation. All four previous findings were explicitly accepted as corrected. The packaging script reconstructs the combined source before comparing it with the generated bundle.

**Non-blocking improvements:** None required for this beta.

**Verification performed:** Independently passed 231 Python tests, 13 existing Node tests and five React/jsdom scenarios. Inspected the complete revised Studio, Manager, confirmations, input, build and packaging code. Additionally exercised the actual Manager confirmation flow in jsdom: only a planning job ran before confirmation; Cancel removed the dialog without starting file preparation. Simulated native horizontal input changed a slider from 2 to 3. Verified JavaScript syntax, exact source/bundle correspondence and release limitations.

**Reviewed bundle SHA-256:** `0f2d9091a5a714ed63d525237b717196aeac953e4d290279fc6684ed3e46dac2`.

### Aesthetic Executioner, iteration 2

**Verdict: APPROVED**

Approval covers source and executable DOM review. It does not certify rendered appearance or physical Steam Deck behavior.

**Blocking findings:** None remaining. Measured readers preserve full newline-rich text; disabled actions have explicit styling; the virtual pointer has hover feedback; narrow headers are compacted; summary-only screens expose paginated information cards.

**Verification performed:** Reviewed the complete revised Studio and confirmation, wizard, viewport and settings integration. Examined normal, compact and narrow layout branches. Independently ran five React/jsdom tests: five passed, zero failed/skipped. Examined pagination, focus recovery, keyboard input, reduced motion and disabled states.

**Non-blocking observation:** The resize test originally closed over its initial dimensions. Codeweaver corrected the test getter to use the changed viewport and strengthened the assertion to require fewer pages with a taller reader. All five DOM tests passed again. This changed test evidence only, not the approved application code.

## Final delivery gate

- Rejection totals: **Logic 1; Aesthetic 1**.
- Both reviewers approve the same final application implementation within the declared source/DOM scope.
- Aggregate verification: **231 Python + 18 Node tests passed**, with zero failures and zero skips when the DOM dependencies are enabled.
- Build and runtime-source correspondence checked. Package CRC, paths, no-root flag and reviewed-file hashes checked by scripts/package.py.
- Runtime bundle hash remains the one approved above.

## Genuine remaining limitations

Actual rendering, viewport fit, visual polish, Steam-native focus behavior, physical trackpad/stick input delivery and game/GPU performance were not tested. The browser service blocked local preview URLs, and no workaround was used. Geometry in the DOM tests is mocked explicitly. This is an installable beta for on-device evaluation, not a claim that those unavailable checks passed.
