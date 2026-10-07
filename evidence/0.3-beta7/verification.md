# v0.3-beta7 verification

Standard: 352 Python tests and 55 frontend tests passed, with no skips.
Full: 356 Python tests passed, including installation of all bundled components with Python networking blocked. Its frontend, removal modules and shared tests match the verified standard files byte for byte.

Removal checks cover unchanged managed files, original restoration, edited presets, unidentified DLLs, untracked shared libraries, symbolic links, duplicate filename casing, stale approval, games starting after preview, staging races, interrupted writes, failed launch verification, Undo and damaged snapshots. Native-only or incompletely inspected prefix overrides stop removal. Restored originals retain their saved permissions.

Controller tests use React/jsdom with mocked Steam input and geometry. They cover six-phase and within-phase navigation, API and prefix gates, modal locking, trigger edges, duplicate Steam events, suppression of trigger-generated mouse clicks, ordinary mouse input after trigger release, and listener cleanup. Confirmation is still required for Apply and removal.

The PE resource reader correctly identifies the actual bundled OptiScaler v0.9.4, ReShade 6.8.0 32-bit and 64-bit injector DLLs without cache hash lookup. Source references used for the parser and Steam input mappings:

- https://github.com/optiscaler/OptiScaler/blob/master/OptiScaler/OptiScaler.rc
- https://github.com/crosire/reshade/blob/main/res/version.rc2
- https://github.com/SteamDeckHomebrew/decky-frontend-lib/blob/main/src/globals/steam-client/Input.ts
- https://github.com/SteamTracking/SteamTracking/blob/master/ClientExtracted/steamui/chunk~2dcc5aaf7.js

These are code and simulated input checks. Physical Steam Deck trigger behavior, the native mouse-event ordering, actual screen rendering and in-game behavior remain unverified. No independent agent review was run for beta7; older review files belong to their named releases.
