# Deck Fusion 1.0.0 Agent Review Log

## Scope and acceptance criteria

Final review of the Deck Fusion 1.0.0 runtime intended for Decky Loader Developer Mode ZIP installation. The implementation was reviewed against the original graphics-manager requirements and the six defects reported from the RC1 Steam Deck test.

Acceptance criteria:

1. Steam games are shown by default; non-Steam/EmuDeck shortcuts are opt-in and the preference persists.
2. Executable discovery scans nested game directories and ranks the actual rendering executable ahead of launchers, reporters and support binaries.
3. OptiScaler advanced INI controls and ReShade shader controls render useful empty states and real controls when schemas/effects exist.
4. Review Configuration reports structured actionable errors rather than a generic Decky Python Exception.
5. HTTPS downloads retain certificate/hostname validation, work with SteamOS trust or the bundled CA fallback, and preserve valid cached packages on failure.
6. LSFG 2.0.0 is pinned for initial installation, stable 2.x updates are discoverable without guessing archive filenames, latest stable OptiScaler and standard ReShade can be resolved, and shader packs can be installed/updated.
7. Per-game LSFG, OptiScaler, standalone ReShade, and ReShade-through-OptiScaler configuration can be reviewed, applied and restored transactionally without destroying unrelated game files or launch options.
8. The frontend bundle is self-contained, the Decky plugin requests no root flag, and the release ZIP has exactly one plugin root containing all runtime dependencies.
9. The UI remains usable at Steam Deck 1280x800 and smaller harness viewports without horizontal overflow, with six discoverable tabs and Decky-native tab navigation semantics.
10. Limitations that cannot be verified in this environment are stated rather than inferred.

## Iteration record

### Iteration 1, Logic Inquisitor: REJECTED

**Reason:** LSFG stable resolution used a guessed `lsfg-vk-<version>.tar.xz` path and parsed only unsuffixed filenames. Upstream packaging can use platform/architecture suffixes, so a valid LSFG 2.0.0 release could fail with HTTP 404 even though it existed.

**Evidence:** `fusion_downloads.py` hard-coded the pinned URL and its update regex only matched `lsfg-vk-(2.x.y).tar.xz`.

**Expected behavior:** Discover the exact stable 2.x filename from the official LSFG build index, accept known stable x86-64/platform naming variants, reject prerelease/git snapshots, and never guess a missing pinned URL.

**Required correction:** Replace the guessed URL with official-index discovery and add regression tests for archive naming variants and missing pinned releases.

**Severity:** High

### Iteration 1, Codeweaver correction

Implemented `_resolve_lsfg()` using the official build index. It accepts stable 2.x `.tar.xz` archives with bare, `-x86_64`, `-amd64`, or `-linux` names, prefers x86-64 where multiple 2.0.0 files exist, rejects dev/RC/git-style names, uses the exact discovered URL, and errors if pinned 2.0.0 is absent rather than constructing a speculative URL. Added regression coverage. Also removed a stale RC2 diagnostics version string found during the same release pass.

## Logic Inquisitor final review

**Verdict:** APPROVED

**Blocking findings:**

None remain within the implementation and environment-verifiable scope.

**Non-blocking improvements:**

* Actual third-party graphics injection still requires validation on physical Steam Deck hardware and representative Proton titles. Automated fixture tests cannot prove compatibility with every game, anti-cheat policy, graphics API implementation, or Proton version.
* ReShade binaries and its shader distribution are deliberately not redistributed in this ZIP. The plugin obtains supported upstream artifacts on demand. This means first-time setup requires a working network connection unless a future legally redistributable offline payload is supplied.

**Verification performed:**

* Inspected `main.py`, `fusion_engine.py`, `fusion_steam.py`, `fusion_downloads.py`, `fusion_network.py`, `fusion_launch.py`, `fusion_transaction.py`, `fusion_shaders.py`, plugin metadata, release manifest, and the generated frontend bundle.
* Verified Steam-only default filtering and persistent non-Steam opt-in behavior with a synthetic library containing 1,000 C64 shortcuts.
* Verified a Cyberpunk-style nested `bin/x64/Cyberpunk2077.exe` fixture is ranked ahead of `REDprelauncher.exe` and `REDEngineErrorReporter.exe`.
* Verified structured RPC errors, async review jobs, transactional prepare/finish/restore, launch-option preservation, recovery journals, and non-destructive failure behavior.
* Verified TLS trust fallback, certificate rejection, hostname rejection, hash mismatch behavior, safe redirects, archive traversal rejection, archive size/file limits, and offline bundle validation.
* Verified LSFG pinned/latest resolution with bare, `-x86_64`, `-amd64`, and `-linux` stable names plus prerelease/git exclusions.
* Ran `python3 -m pytest tests -q`: 106 tests passed.
* Ran `node --test tests/frontend.test.mjs`: 1 frontend bundle smoke test passed.
* Ran Python bytecode compilation and Node syntax checks on all runtime JavaScript.
* Ran the browser workflow harness using the built frontend and real Python backend fixture path; review/apply/restore and configuration edits completed without unhandled browser errors.
* Scanned release runtime files for stale RC branding, TODO/FIXME/XXX markers, unresolved source imports, and Decky root flags.

## Aesthetic Executioner final review

**Verdict:** APPROVED

**Blocking findings:**

None remain within the rendered browser-harness scope.

**Non-blocking improvements:**

* The harness emulates Decky components and keyboard tab switching. Physical L1/R1 Steam Input focus behavior and SharedJSContext rendering cannot be truthfully approved until exercised on an actual Steam Deck.
* Some long configuration pages necessarily scroll. Their hierarchy and controls are usable, but actual Decky typography metrics may differ slightly from the harness.

**Verification performed:**

* Inspected the actual rendered browser-harness output, not only source code.
* Inspected `library-1280x800.png`: Steam-focused Library view, actual-executable selector, API selector, explanatory text, and safety warning are aligned and readable.
* Inspected `opti-populated.png`: populated Advanced INI section and generated Sharpness control render correctly rather than an empty popup.
* Inspected `reshade-populated.png`: shader selection, technique toggle, and parameter slider render correctly and remain legible.
* Inspected `tools-800x500.png`: compact viewport retains tab discoverability, readable tool/update state, and usable controls without clipping.
* Browser harness checked all six tabs at 1280x800, 1024x640, and 800x500; each had usable vertical scrolling and no document-level horizontal overflow.
* Verified the visible `L1 / R1 · tabs` affordance and use of Decky-native `Tabs` with `autoFocusContents`.
* Verified missing OptiScaler/shader states render actionable explanatory UI instead of black Cancel-only selectors.

## Final common verdict

Logic Inquisitor: **APPROVED**

Aesthetic Executioner: **APPROVED**

Both reviewers approved the same Deck Fusion 1.0.0 implementation for release as a developer-installable Decky ZIP, subject to the explicitly unverified physical-Steam-Deck and real-game injection limitations above.
