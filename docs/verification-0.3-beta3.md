# v0.3-beta3 change and verification record

Implemented and reviewed by the primary agent. Earlier records in `docs/` and `evidence/` describe historical builds.

## Changes

- Hide the Expert Mode sidebar button. Keep its route, tabs and backend for later reactivation.
- Put ReShade effects in Steam's native scroll panel. While the popup owns focus, route browser wheel events into its list even if the pointer is outside it. Release the listener on close; retain touch scrolling and avoid duplicate gamepad polling on this native path.
- On older clients, keep held right-stick scrolling active until neutral and clear it on focus loss, disconnection or route teardown. Resolve the native action-set and old raw-input providers independently.
- Open a repair popup automatically for missing or changed managed files. Its **Force apply settings** action uses a fresh, approved force plan, recopies every selected graphics file and regenerates settings. Existing selected loader files can be overwritten after backup.
- Add a separate launch-cleanup warning with the original and replacement commands. Remove recognized graphics overrides, injection variables and old launcher scripts; retain unrelated arguments and DLL overrides. Never execute launch text. Decline compound-shell rewrites that cannot be safely parsed.
- Carry the original Steam launch text into the transaction journal while planning against the approved cleaned text. Recheck the live launch text, graphics plan and game state before writes. Cancel performs no game-file or launch-option mutation.
- Retain exact-plan approval fingerprints, running-game and anti-cheat checks, target validation, backup integrity and rollback. Force apply does not bypass these checks.

## Verification

- **300 Python tests and 44 Node tests passed**, including 30 React/jsdom scenarios. See [full verification](evidence/0.3-beta3/verification.txt).
- Regression tests cover missing/modified file recovery, replacement of an occupied selected proxy, saved original bytes, original launch text in rollback, both Wine override spellings, wrapper arguments, selective layer cleanup, idempotence and malformed shell input.
- UI tests cover automatic repair prompts, cancel without writes, the explicit force flag and approved token, a game starting after review, separate cleanup confirmation and original-versus-cleaned launch text. Input tests cover missing raw APIs, scroll routing from outside the list, listener cleanup, held sticks and focus loss.
- Static inspection of Steam's published UI code confirmed the scroll panel's DOM ref and attribute forwarding. `ScrollPanelGroup` is itself a scrollable focus group, so it is not used as an outer provider. See [input investigation](docs/research-0.3-beta3.md) and [source provenance](evidence/0.3-beta3/steam-scroll-contract.json).
- JavaScript syntax passed. Packaging verifies ZIP CRCs, paths, source/bundle parity and recorded source hashes.
- Environment: Python 3.12, pytest 8.3.5, Node.js 24.19.0, React 18.3.1 and jsdom 30.0.1.

## Limits

No physical Steam Deck, native Steam/Decky session, Proton, Microsoft installer execution or game/GPU run was available. Input tests simulate Steam/Decky services, browser events and geometry; they do not establish device controller routing or screen fit.

The beta2 ReShade, renderer-detection and runtime-diagnostic fixes remain included. The original runtime exit-status-1 cause is still unconfirmed without its installer output. No new runtime-install success is claimed.
