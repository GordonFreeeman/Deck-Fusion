# Deck Fusion 1.3.1: implementation review log

The Codeweaver implements changes. The Logic Inquisitor and Aesthetic Executioner
are separate review passes by the same assistant, not separately executed models.
Evidence uses synthetic executables and simulated Decky/Steam UI and installer
boundaries. No physical Steam Deck, actual Microsoft installer, game renderer or
native controller interaction is claimed. Prior reviews are in docs/.

Scope: docs/acceptance-1.3.1.md. Source baseline: supplied Deck-Fusion-1.3.0.zip.

## Baseline inspection

Both backend target selection and runtime-page visibility were tied to
Cyberpunk2077.exe. A valid synthetic Test-Win64-Shipping.exe with an initialized
prefix was refused. Recorded in evidence/1.3.1/baseline.json.

## Iteration 1

### Logic Inquisitor

**Verdict:** REJECTED

**Blocking findings:**

1. Root-folder executables have an incomplete generic DLL inventory.
   Evidence: the game-root Game.exe + winmm.dll reproduction reports no DLLs
   and an unsafe-path note for '.'. See iteration-1/root-diagnostics.json.
   Expected: root and nested executable directories receive the same local checks.
   Required correction: handle the already validated root explicitly without
   weakening safe_relative or following paths outside the game. Add a regression.
   Severity: Medium.

**Non-blocking improvements:** None recorded.

**Verification performed:** Inspected target validation, generated Protontricks
commands, game-independent diagnostics, shared-prefix/approval boundaries and the
new tests. 48 selected backend tests passed. Additional root-directory reproduction
above revealed a missing case not covered by those tests. Runtime/native gating
is based on PE file format, not executable name or AppID.

### Aesthetic Executioner

**Verdict:** REJECTED

**Blocking findings:**

1. Native-Linux selection still presents Windows dependency checkboxes and an
   instruction to use a disabled prefix check. Retained scroll position can open
   the page below its explanation. Evidence: inspected native-800x500.png and the
   runtime branch/scroll-container code. Expected: a clear non-applicable state
   with an actionable route back to executable selection, no unusable recipe form.
   Required correction: render a dedicated native/unselected-executable state;
   scope scroll containers to the selected tab/game/executable.
   Severity: Medium.

**Non-blocking improvements:** None recorded.

**Verification performed:** Real Chromium/React/Python workflow using mocked
Decky/Steam at 1280x800, 1024x640 and 800x500. Inspected runtime-1280x800,
confirmation-800x500 and native-800x500 screenshots. Confirmation buttons clear
simulated Steam's footer. No browser errors. Geometry-only visibility assertions
did not detect the native-page discoverability issue. The browser harness also
had a wrong expected wizard label; this was corrected to match the unchanged
actual title. That harness error was not an application failure.

### Codeweaver correction checklist

- Handle a root-folder diagnostic inventory using its authoritative validated root.
- Add root-level and unsafe-link regression coverage.
- Show a compact native/no-executable runtime explanation and return action.
- Reset tab scroll ownership when game or executable changes.
- Recheck the full final source and applicable workflows with both review passes.

Rejection counters so far: Logic Inquisitor 1; Aesthetic Executioner 1.

## Codeweaver revisions after iteration 1

1. Generic diagnostics now use the already validated game root directly for a
   root-folder executable. Nested subpaths still use the original safe-target
   checks. The new root-folder regression finds winmm.dll; external log symlinks
   remain unreadable to the diagnostic reader.
2. Native/no-executable runtime selection now displays an explanation and
   "Choose a Windows executable" instead of Windows recipe controls. Each tab's
   scroll-container identity includes the tab, selected AppID and executable.
   Changing games cannot reuse another game's runtime selections or inspection.
3. The full suite found one instrumentation-version assertion left at 1.3.0.
   The wrapper's reported version is now 1.3.1 and the historical test reads the
   package version. Comparing bytes after replacing that one version string
   proves there is no other launch-wrapper change. The original failure and
   final passing results are retained as evidence, not hidden.
4. Rebuilt the self-contained frontend, reran both entry routes and wizard
   resume, compared guarded runtime methods against 1.3.0, and checked the
   installable layout through a clean extraction.

## Iteration 2: complete revised implementation

### Logic Inquisitor

**Verdict:** APPROVED

**Blocking findings:** None remaining within the reviewed scope.

**Non-blocking improvements:** No additional changes are required for this
request. General game eligibility must not be described as universal graphics,
anti-cheat, mod or runtime compatibility. The present UI and README explicitly
state the initialized-Proton-prefix and supported-runner boundaries.

**Verification performed:**

- Reinspected the final target resolver, RPC dispatch, read-only generic
  diagnostics, UI target/recipe state, installation confirmation and recovery
  integration. There is no Cyberpunk filename or AppID gate in the runtime path.
  The remaining named-game check only enables an optional diagnostic adapter.
- Twelve new tests cover unrelated 32-bit and 64-bit PE games, a Windows PE with
  no .exe suffix, Steam-managed non-Steam Windows shortcuts, independent prefixes
  and approvals, missing-prefix refusal, native/invalid-file rejection,
  read-only bounded logs, external links and root-folder DLL discovery.
- The complete backend suite passed: 231 tests in 11.97 seconds. The thirteen
  frontend checks passed. Python compilation and JavaScript syntax passed.
  This is local verification, not a claim of execution on SteamOS.
- Synthetic install/restore checks executed the actual snapshot, planning,
  approval, game-isolation and restore code. Only the external installer was
  replaced with an explicitly labeled fixture. No Microsoft installer or actual
  Protontricks command was executed.
- AST comparison of PrefixRuntimes shows target, idle, evidence and status as
  the only changed methods. Guarded command generation, subprocess execution,
  snapshot, restore, helper installation and confirmation binding are unchanged.
  idle/evidence/status changes are presentation wording. The target change
  replaces a filename allowlist with Windows PE validation.
- Reviewed hashes show unchanged graphics, override, transaction and network
  modules. The persistent launch wrapper differs only in its version label.
- Cleanly extracted package code started the real backend without an installed
  game, reported 1.3.1, passed the twelve new backend regressions and the
  frontend bundle smoke test. Source and bundled UI are identical; archive CRC,
  safe paths, no-symlink rules, no-root flags and reviewed code hashes passed.

The iteration-1 root-folder finding is resolved by the checked-in implementation
and its passing reproduction. The final target-isolation and safety boundary is
accepted. Actual Proton compatibility/runtime outcomes remain an on-device check,
not a reason to conceal or overstate the implementation evidence.

### Aesthetic Executioner

**Verdict:** APPROVED

**Blocking findings:** None remaining within the reviewed scope.

**Non-blocking improvements:** No further visual changes are required for the
requested generalization. Native Decky component rendering and physical controller
focus still need device validation; the browser harness does not establish them.

**Verification performed:**

- Reviewed the complete manager/wizard navigation, DLL diagnostics, runtime page,
  confirmation, progress/receipt and unavailable/native states in the final code.
- Rendered the real React frontend in Chromium against the real Python backend,
  with explicitly simulated Decky/Steam controls and a synthetic installer.
  Used 1280x800, 1024x640 and 800x500 viewports. Opened both quick-access entries.
  At 800x500, paused the wizard on Choose features, entered runtime setup and
  resumed the same wizard step and draft.
- Inspected runtime, confirmation, generic diagnostic, second-game and native
  state screenshots, including native-action-800x500.png and
  second-game-1280x800.png. Native selection no longer shows installation
  checkboxes or a disabled instruction loop. The return action is reachable.
- Checked game titles and AppIDs in the page and confirmation, unchecked-by-
  default optional runtime recipes, and clearing of selections, prefixes and
  prior receipts when switching games. The UI does not present Cyberpunk tools
  for unrelated executables; general diagnostics remain available.
- Included a hidden module window with zero height plus the visible page and
  simulated 56-pixel Steam footer. Page bottoms were 728/568/428, against footer
  tops 744/584/444. No document horizontal overflow occurred. Focused action and
  confirmation buttons remained above the footer at all three sizes.
- Cancel did not install, take a snapshot or rewrite launch text. The single
  simulated install workflow showed the real orchestration result. General
  inspection left launch text unchanged. No unhandled browser page errors were
  captured. Screenshots/results are under evidence/1.3.1/.

The iteration-1 native-page/scroll finding is resolved and the revised result is
accepted. This verdict covers observable browser behavior and the inspected
implementation, not actual Steam Input, Wine windows or GPU output.

## Acceptance evidence

| Criterion | Final evidence |
| --- | --- |
| No title/filename gate for Windows runtimes | target resolver and test_131's unrelated 32/64-bit/extensionless executables |
| Steam and non-Steam Proton games, safe prefix selection | real shortcut-VDF fixture; distinct AppIDs/prefixes; missing-prefix and crossed-approval refusals |
| General, discoverable runtime setup | Library and DLL entries, Runtimes tab, wizard detour/resume at 800x500 |
| Per-game state and confirmation isolation | two-game backend cases; browser clears choices, prefix and receipts; cancel is read-only |
| General diagnostics plus optional game adapters | bounded generic inventory/log tests, root-directory fix, browser unrelated-game diagnostic page |
| Existing safeguards/features preserved | unchanged-method AST and source-hash audit; full backend suite; prior frontend safety checks |
| Deliverable and truthful verification | rebuilt bundle, clean-extracted startup/regressions, source manifest, scoped browser evidence |

## Final rejection counters and limitations

Logic Inquisitor: **1 rejection**, resolved in iteration 2.
Aesthetic Executioner: **1 rejection**, resolved in iteration 2.
Both final verdicts apply to the same final 1.3.1 code recorded in
`evidence/reviewed-code-sha256.json`. Browser evidence additionally records the
bundled frontend SHA-256. Final ZIP integrity is checked again after embedding
this completed review; ZIP metadata is emitted outside the archive to avoid
self-referential hashes.

No physical Steam Deck was used. No live game, actual Microsoft runtime installer,
real Protontricks installation, rendering, frame generation or physical controller
interaction was verified. Supported runtime targets require an initialized,
safely resolved Proton prefix. Arbitrary standalone Wine/Lutris/Heroic runners
and native Linux executables are not silently altered. Dependencies are optional;
neither recipe is assumed necessary or installed automatically for every game.
