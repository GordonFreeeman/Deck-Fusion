# Deck Fusion 1.3.0: prefix runtimes

Review scope: actual source and observable browser output. Codeweaver implements;
Logic Inquisitor and Aesthetic Executioner are separate review passes performed by
one assistant, not independently spawned agents. No Steam Deck, Steam client,
Proton, actual Flatpak app, Microsoft installers or game renderer is available.

## Acceptance criteria

See `docs/acceptance-1.3.0.md`. The request is optional installation of
`d3dcompiler_47` and `vcrun2022` into the correct initialized Cyberpunk Proton
prefix. Existing game DLLs, graphics profiles and Steam launch options must not
be rewritten by this operation. Backups, useful failure output and a separately
confirmed restore must exist. No silent dependency installation on opening the
plugin or launching a game; no sudo, global Wine or checksum bypass.

## Iteration 1

Codeweaver inspected the entire 1.2.2 project, built the prefix maintenance
module, integrated job cancellation and a Runtimes tab, and generated a bundle.
The supplied 1.2.2 source is retained as the baseline. The DLL-override,
transaction, watermark and graphics configuration algorithms are unchanged.

### Logic Inquisitor

**Verdict:** REJECTED

**Blocking findings:**

1. **Incomplete Flatpak filesystem access on separate Steam libraries**
   - Evidence: `PrefixRuntimes.command` grants the prefix parent and game root,
     but not the containing library's app manifests or a compatibility tool in
     another discovered library. Official Protontricks docs require filesystem
     access to additional libraries. The synthetic default-library case missed
     this.
   - Expected: a per-invocation grant for the detected Steam libraries needed by
     Protontricks, shown in the reviewed operation. No permanent host-wide grant.
   - Required correction: resolve library roots, include them in the plan and
     command, and verify an external-library fixture.
   - Severity: High.
2. **Restore disk-space estimate uses the wrong directory size**
   - Evidence: `_plan` always uses current prefix size. An older snapshot may be
     larger than the current prefix; staging could run out of disk space after
     an apparently successful preflight.
   - Expected: stage-space calculation uses the saved snapshot index for restore,
     while installation uses current prefix size plus workspace.
   - Required correction: bind the snapshot index identity into approval, validate
     its metadata and compute restore space from that index.
   - Severity: Medium.
3. **Corrupt receipt path not validated on status reads**
   - Evidence: status concatenates `runtime-last.json`'s `id` into a log path
     without checking that it is a generated 32-hex identifier. A tampered receipt
     could redirect the local log read beyond this application's job folder.
   - Expected: malformed receipts fail closed with a visible warning; only
     application-owned log paths are opened.
   - Required correction: validate receipt identity, app and prefix references,
     check log path containment, and cover malformed receipt fixtures.
   - Severity: Medium.

**Non-blocking improvements:**

- Show helper-install failure logs in the Runtimes page too, not only a filesystem
  path in an error message.
- Ensure cancellation during restore staging removes only the incomplete staging
  copy, never the original snapshot or live prefix.

**Verification performed:**

- Read target selection, allowlisted command generation, backup checksum path,
  atomic directory exchange, jobs/RPC integration and persistent launch guard.
- 14 focused new backend checks passed using synthetic prefixes and simulated
  installers, including real harmless child-process cancellation and prefix guard.
- 35 existing 1.2.1/1.2.2 checks passed.
- Python compilation, dependency-free build and JS syntax passed.
- Inspected the Chromium report for both 1280x800 and 800x500 and its simulated
  install/cancel/restore-confirmation calls to the real Python backend.

Rejection counter: Logic Inquisitor **1**; Aesthetic Executioner **0**.

### Aesthetic Executioner

**Verdict:** APPROVED (iteration-1 UI only; not final release approval)

**Blocking findings:** None identified in the inspected UI.

**Non-blocking improvements:**

- Runtime file inventories are verbose. A collapsed details section would put
  dependency selection and the install action earlier in the scrolling page.
- Bring helper setup logs into the same visible receipt pattern as runtime logs.

**Verification performed:**

- Visually inspected the actual Chromium screenshots `runtimes-1280x800.png`,
  `runtimes-800x500.png`, `confirm-800x500.png` and `receipt-1280x800.png`.
- The page is scrollable inside the safe frame, all eight tabs fit at 800 pixels,
  the modal's actions stay outside its scrolling content, and the simulated Steam
  footer remains clear. Long paths wrap and logs use readable fixed-width text.
- The report records the manager entry in the hidden-module/visible-owner
  window model used to reproduce the earlier black-screen regression.
- This browser uses React with simulated Decky components. Physical controller
  focus, Steam's actual native controls and a hardware keyboard were not tested.

## Codeweaver correction checklist

- [x] Correct per-invocation Flatpak library grants and show the paths in review.
- [x] Validate snapshot receipt/index and correct restore-space calculations.
- [x] Validate receipt/log paths and expose safe local error diagnostics.
- [x] Address incomplete staging cleanup and compact runtime evidence.
- [x] Rebuild and return the complete revised implementation to both reviewers.

## Iteration 2

### Codeweaver changes and revision verification

Fixed all iteration-1 blocking findings. The reviewed command now includes
per-invocation detected-library grants; confirmation displays those grants.
Restore binds a validated snapshot index and uses its copy size for disk-space
preflight. Receipt identifiers and log paths are validated. Helper-install output
is available in the UI; runtime file details are collapsed by default. Incomplete
restore staging is removed on failure without removing either original prefix.

A regression check during correction caught over-strict archive-style validation
rejecting Wine's legitimate `dosdevices/z:` name. Replaced it with Linux-relative
index validation; actual symlinks are preserved, never dereferenced during copies.
The rerun passed 54 selected backend checks and 13 Node checks. This was a
Codeweaver verification failure/correction, not a separate reviewer verdict.

### Logic Inquisitor

**Verdict:** REJECTED

**Blocking findings:**

1. **Restore still depends on install-checkbox selection**
   - Evidence: `_plan(restoring=True)` calls the install-only `options()` method.
     Unchecking both dependencies leaves Restore visible in the UI but makes its
     backend plan fail the nonempty-verb requirement.
   - Expected: a saved-prefix restore is independent of the dependency checklist.
   - Required correction: only validate installer verbs when planning installation;
     restoration must bind its own snapshot identity instead. Cover unchecked
     runtime selection while restoring.
   - Severity: Medium.

**Non-blocking improvements:**

- Recheck the reviewed prefix inventory after acquiring the maintenance lock and
  immediately before running installers. An unrelated process must not change the
  approved prefix while a potentially long snapshot is being prepared.

**Verification performed:**

- Re-read the complete new module and integration, including the corrected
  Flatpak command, snapshot manifest, atomic exchange and source UI selection.
- Examined the new external-library, log-path, large-snapshot and partial-copy
  fixtures, plus the reported 54 backend and 13 Node results.
- The three previous blocking corrections are accepted on code and fixture
  evidence. The new checkbox/restore defect is independent of those corrections.

Rejection counter: Logic Inquisitor **2**; Aesthetic Executioner **0**.

### Aesthetic Executioner

**Verdict:** REJECTED (verification pending for the rebuilt UI)

**Blocking findings:**

1. **The rebuilt collapsed-details and helper-log UI has not been re-rendered**
   - Evidence: the first screenshots refer to the earlier bundle hash.
   - Expected: final approval must examine the same built UI intended for release.
   - Required correction: rerender both target viewport sizes and inspect the new
     confirmation paths/logs, then review the complete resulting screenshots.
   - Severity: Low.

**Non-blocking improvements:** None beyond verifying the existing correction.

**Verification performed:**

- Read the revised runtime page and confirmation code, comparing them with the
  prior rendered UI. Deferred final visual approval until updated screenshots.
- No physical Deck or unperformed mouse/controller test is claimed.

Rejection counter: Logic Inquisitor **2**; Aesthetic Executioner **1**.

### Follow-through on iteration-2 visual rejection

The rebuilt screenshots were produced for both entry points. At 800x500 the
Flatpak permission card can be taller than the modal's content viewport. Source
inspection also showed no local keyboard scroll handler on confirmation cards.
Touch scrolling works in the containing pane, but a focused card cannot reliably
expose all its paths using keyboard navigation. Added this actionable finding to
the same outstanding aesthetic rejection: bound each card's height, add visible
focus and local Arrow/PageUp/PageDown scrolling, and inspect the corrected screen.
Severity: Medium. The confirm/cancel buttons themselves remain above the footer.

## Iteration 3: complete final implementation review

### Codeweaver revisions

Restore no longer depends on which install checkboxes are selected. Install now
rechecks the approved prefix inventory both after locking and after snapshot
preparation. The UI's confirmation cards are bounded, visibly focusable and
locally scrollable with Arrow/PageUp/PageDown keys. No additional changes were
made to the old DLL-loader selection, watermark, graphics transaction or FPS
algorithms. The runtime source diff and byte-identical module list are retained
in `evidence/1.3.0/`.

All checklist items above are completed. The verification command selected the
21 new runtime checks plus 35 relevant previous checks (56 passing in 3.41s),
not a game benchmark. Node ran 13 focused bundle/DLL/viewport checks. Chromium
was rerun against the complete rebuilt bundle, not only the latest diff.

### Logic Inquisitor

**Verdict:** APPROVED

**Blocking findings:** None remaining within the inspectable implementation scope.

**Non-blocking improvements:**

- A future on-device check should establish how the installed Protontricks and
  selected Proton version handle Microsoft's runtime installers and any dialogs.
  That empirical limitation is explicit and cannot be replaced by simulated
  installer success.

**Verification performed:**

- Re-read the complete `fusion_prereqs.py` implementation: executable/prefix
  selection, live launch assignments, root-user refusal, process gating,
  allowlisted verbs, generated checked shell, native/Flatpak commands, temporary
  library grants, clean installer environment and trusted helper install source.
- Reviewed hash-verified full-prefix copy, symlink preservation, cancellation,
  saved receipts and validated log paths, saved-index/size approval, atomic
  restore exchange and unconditional preservation of the displaced prefix.
- Confirmed the new RPC/job/cancellation integration and per-game launch guard;
  inspected the full source diff outside the new module. The existing graphics
  policy, Wine-override, shader, transaction and network modules are unchanged.
- Verified the 56-check backend report and 13-check Node report. New regression
  cases cover separate libraries, native/Flatpak command construction, actual
  harmless child process execution/cancellation, stale approvals, partial copy
  failure, tampered snapshot/log paths, restore with empty dependency choices,
  selected-prefix mutations and retained saves in the displaced restore copy.
- Reviewed the real-Python/Chromium workflow report for both entry points. No
  command result from a simulated runtime is called proof of Microsoft, game,
  CET, RED4ext or redscript operation.

The previous two logical rejections and all requested corrections are accepted.

### Aesthetic Executioner

**Verdict:** APPROVED

**Blocking findings:** None remaining in the revised rendered interface.

**Non-blocking improvements:**

- On-device Steam Input focus and Steam's native modal implementation remain to
  be evaluated by the user. Browser keyboard checks are not physical controller
  checks.

**Verification performed:**

- Inspected updated `confirm-1280x800.png`, `flatpak-grants-800x500.png` and
  `helper-log-800x500.png`, plus the runtime and receipt pages reviewed earlier.
  The new complete browser run also saves both viewport runtime, receipt,
  confirmation, restoration and helper-log views.
- Confirmed distinct install/restore verbs, the visible target pfx and copy-space
  estimate, plain-language runtime warnings, readable focused log cards and no
  overflow into the simulated Steam footer. The install button is not part of
  the scrollable modal content.
- Browser assertions verify local PageDown scrolling of the long Flatpak grant
  card, focusable log cards, a hidden zero-height module window with a healthy
  visible owner window, and no horizontal document overflow or page errors.
- 1280x800: frame bottom 728, footer top 744. 800x500: frame bottom 428, footer
  top 444. Thus the page reserves 16 pixels before the simulated Steam footer.
- Both Open Deck Fusion and Set up a game entry points were exercised on the
  final bundle; the wizard route retained its draft and entered Runtimes.

The outstanding aesthetic rejection and its long-card follow-through are closed.

## Final identity and limitations

Both final review passes examined the implementation represented by
`evidence/reviewed-code-sha256.json`.

- Runtime source manifest SHA-256:
  `02d2e6b5463d7d648e3145204dc080fa6f904bf961dc59388f80a8eb5f41ea98`
- Final rendered `dist/index.js` SHA-256:
  `6a4756c7562d880d6acd562b0a25f5197d24546c7e8fd2860c2b5cef0275eac5`
- Final rejection counters: Logic Inquisitor **2**, Aesthetic Executioner **1**.

The local environment had no Microsoft payload, actual Proton/Flatpak installation,
Steam Deck, Cyberpunk renderer or mod set. It also could not download external
binaries directly. These are genuine empirical limitations, not tests that were
silently treated as passing. Upstream dependency acquisition will occur on the
Deck only after explicit user confirmation. Network/installer/version failures
remain possible and are surfaced through the new logs and snapshot recovery.

This release supplies an opt-in dependency-installation mechanism. It does not
claim to have diagnosed or fixed the user's current Cyberpunk crash. Missing
runtimes, conflicting or overwritten loaders and incompatible mod versions remain
separate possibilities. No game directory wipe or prefix reset is performed.
