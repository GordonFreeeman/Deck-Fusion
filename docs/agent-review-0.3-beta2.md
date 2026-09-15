# v0.3-beta2 change and verification record

Implemented and reviewed by the primary agent. Earlier records in `docs/` and `evidence/` describe historical builds.

## Changes

- Correct the Legacy ReShade catalogue branch from `master` to `legacy`; Standard remains on `slim`.
- Let unavailable, unselected optional shader packs report their errors without blocking other effects. Required dependencies still must succeed; retry success clears the unavailable warning.
- Add bounded renderer inspection through imported local engine DLLs. Ignore injection proxies, external paths, symlinks and mismatched architectures. Recognized Unity renderer flags take priority; ambiguous results require a selection.
- Add a guarded DirectX 11 default hint for Subnautica: Below Zero. Setup displays the resolved API and checks unresolved selections before component downloads. Scan, Wine context, validation and Apply use the same resolver.
- Recover missing display/session fields from a same-user Steam process for runtime helper commands, while preserving existing session context and stripping graphics-injection variables.
- Show bounded actual installer output and relevant failure guidance. Preserve the final output after the normal log cap. Refresh failed runtime/helper receipts and expose their logs from guided setup.
- Keep prefix snapshots, exact-prefix guards, approval fingerprints, failure stops and transaction recovery. No force or checksum bypass was added.

## Verification

- Full suite: **281 Python tests and 38 Node tests passed**. See [full verification](evidence/0.3-beta2/verification.txt).
- After the final retry-message correction and its new regression, **all 39 Node tests passed**, including **25 React/jsdom scenarios**. See [final frontend verification](evidence/0.3-beta2/frontend-final.txt). Python sources were unchanged after their full passing run.
- All seven built-in shader commit endpoints resolved. Production code downloaded and unpacked the actual Legacy archive with verified HTTPS. Its parsed catalogue contains 20 shader files and 29 techniques. See [upstream checks](evidence/0.3-beta2/upstream-check.json) and [investigation notes](docs/research-0.3-beta2.md).
- JavaScript syntax and source/bundle parity are checked. Packaging verifies ZIP CRCs, paths and recorded source hashes.
- Environment: Python 3.12, pytest 8.3.5, Node.js 24.19.0, React 18.3.1 and jsdom 30.0.1.

Tests cover DLL-delegated API detection, renderer flags and ambiguity, title-default scope, proxy and path exclusions, the corrected shader download reference, session field isolation, actual stderr propagation, output limits, optional/required shader failures and recovery, early API selection, and retained runtime/helper log access. Existing transaction, prefix, input and guided-flow tests remain passing.

## Limits

The original exit-status-1 cause remains unknown because the installer log contents were not supplied. The session-environment change addresses a possible service-launch failure; it is not evidence that this specific runtime installation now succeeds.

No physical Steam Deck, native Steam/Decky session, Proton, Microsoft installer execution or game/GPU run was available. React tests use simulated Steam/Decky services and synthetic geometry; they do not prove real screen fit, controller routing or renderer compatibility. Historical screenshots are not previews of this release.
