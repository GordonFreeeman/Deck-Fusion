# Beta3 input and recovery investigation

Checked on 2026-09-15.

## Effects scrolling

The old implementation depended on `RegisterForControllerStateChanges` packets or a browser-standard gamepad. Steam clients without that raw API can therefore lose the scrolling path. A held raw stick also stopped after a short packet timeout, even if it had not returned to neutral.

The [Decky scroll-component adapter](https://github.com/SteamDeckHomebrew/decky-frontend-lib/blob/main/src/components/Scroll.ts) exports Steam's native scroll components. Static inspection of [Steam's published UI code](https://github.com/SteamDatabase/SteamTracking/blob/master/ClientExtracted/steamui/chunk~2dcc5aaf7.js) confirmed that `ScrollPanel` forwards `scrollDirection`, DOM attributes, styles and its element ref. `ScrollPanelGroup` adds its own scroll and focus behavior; it is not a context-only wrapper.

The effects list now uses `ScrollPanel` with vertical scrolling. The open popup routes browser wheel events into that list, including events aimed outside it by the browser cursor. This supports Steam browser input without requiring the removed raw callback. Touch drag remains native. Older clients retain the raw/standard-gamepad fallback, with held-stick state cleared on loss of focus.

The downloaded Steam source is not redistributed. Its URL, size and SHA-256 are recorded in [source provenance](../evidence/0.3-beta3/steam-scroll-contract.json). Static source inspection and simulated wheel events are not a physical right-stick test.

## Force apply

The existing transaction engine already supported approved repair of managed-file drift. Guided setup now exposes this as an automatic popup and an explicit force-reinstall action. Force mode also permits overwriting the user's selected graphics proxy after saving its current bytes. It does not delete unrelated game files or bypass target, game-state or backup-integrity checks.

## Launch cleanup

A read-only parser identifies known graphics hooks before preparing the final review. The popup shows the exact current and proposed launch text; confirmation only approves the proposal. Files and launch options change during Apply.

Tests cover `WINEDLLOVERRIDES` and the misspelled `WINEDLLOVERIDES`, `~/LSFG` and known launcher scripts, graphics layer/preload entries, preserved unrelated arguments and overrides, and compound-shell rejection. Original launch text is journaled separately from the cleaned planning input so rollback retains the user's previous command.
