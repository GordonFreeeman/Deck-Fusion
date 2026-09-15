# v0.3-beta1 change and verification record

Implemented and reviewed by the primary agent. No independent-agent review is claimed. Earlier records in `docs/` and `evidence/` describe historical builds.

## Changes

- `Open Deck Fusion` launches guided setup. `Run Deck Fusion (Expert Mode)` launches the full interface. The old setup entry and Expert wizard links are removed.
- Guided setup has five phases and up to eight screens. Each requested stage has its own Next action; ReShade effects and upscaling are skipped when disabled. There is no sidebar, page selector or Components screen.
- Steam’s running app is preferred at startup, with a read-only process hint as fallback. Existing game-running mutation checks remain in place.
- The effects popup includes all built-in shader packs and cached custom packs, with individual switches, search, touch scrolling and right-stick scrolling. Background setup controls are disabled while a popup is open.
- ReShade always loads through OptiScaler while OptiScaler is active, including in Expert Mode. It returns to standalone loading when OptiScaler is disabled.
- Guided setup defaults the Deck limiter option on at first use; later explicit opt-outs persist. Existing RDNA2 detection and explicit fix choices are retained.
- Missing dependencies download automatically. The Lossless Scaling DLL is detected automatically, with an in-flow path field or an off switch if unavailable.
- Selected runtimes, helper installation and prefix backups run from the final Apply action. Already recorded runtimes are skipped. Stale prefix selections clear; ambiguous targets remain selectable inside setup.
- Plain tab titles, compact game pickers, native browser mouse input and Steam Home exit are retained.

## Installation checks

Before runtime changes, the current graphics plan and live Steam launch options must still match the review. After successful runtime installation, prefix registry evidence may change without requiring another Apply. Continuation is allowed only when the resolved graphics profile, loader allocation, file state, configuration/manifest hashes, file changes, launch text, warnings and other plan fields still match. The backend receives the fresh approval token and revalidates it.

Failed or cancelled runtimes prevent graphics preparation. A changed graphics file or loader plan stops for a refreshed review. Existing transaction rollback, prefix snapshots, runtime receipts and launch-option verification are preserved. Runtime installs and graphics installation are separate operations; successful runtimes remain installed if graphics application later fails.

## Input and layout

Steam browser action-set activation still follows the visible owner window’s focus/visibility lifecycle. Native mode never synthesizes raw pointer clicks. Raw right-stick packets are read only to scroll the active effects popup; standard Gamepad API input is a fallback for that scrolling. Raw pointer emulation remains available on clients without the browser action-set API. Subscriptions and browser input mode are released on exit.

Setup uses compact rows and a plain text review list. The Steam header inset remains applied to the page and overlays. Short layouts move supplementary notes into the Step information popup; errors retain their Details action.

## Verification

- `npm ci --ignore-scripts --no-audit --no-fund` completed using the supplied lockfile.
- `npm test`: **262 Python tests and 32 Node tests passed**, including **18 React/jsdom scenarios**, with none skipped.
- JavaScript syntax, source/bundle parity, ZIP CRC/path checks and recorded source hashes passed during packaging.
- Environment: Python 3.12, pytest 8.3.5, Node.js 24.19.0, React 18.3.1 and jsdom 30.0.1.

Output is recorded in [evidence/0.3-beta1/verification.txt](evidence/0.3-beta1/verification.txt). Hashes record package integrity, not an independent approval.

The tests cover all guided stages, conditional skips, draft persistence, running-game selection, the two sidebar routes, effects filtering/toggles, right-stick scrolling, popup boundaries, runtime ordering, stale-plan rejection, runtime failure/cancellation, missing DLL recovery and moved/ambiguous prefixes. Existing regressions cover Expert controls, file transactions, FSR4 deployment, input cleanup and viewport calculations.

## Limits

No native Steam/Decky session, physical Steam Deck input test, newly rendered screenshot or game/GPU run was available for this iteration. React tests use simulated Steam/Decky services and explicitly mocked geometry. They validate behavior and layout calculations, not actual viewport fit, native focus routing or rendering performance. Historical screenshots are not previews of this release.
