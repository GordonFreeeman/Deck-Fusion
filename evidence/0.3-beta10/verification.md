# v0.3-beta10 verification

62 frontend tests passed with no skips. 385 backend tests passed in the full distribution. Node syntax validation passed. The backend changes in this release are version labels only.

## Focus containment

The shared panel hook registers Decky/Steam onGamepadDirection and cancels its default navigation, including at edges and on repeated presses. Direction handling is separate from onButtonDown, so a press cannot move focus twice. The native callback contract and direction codes were checked against @decky/ui 4.12.1 FooterLegend.d.ts and Focusable.d.ts.

Checks cover the OptiScaler navigation geometry and edit entry, text and ReShade raw INI panels, ranges, selections, effects and confirmation panels. They exercise separate button/direction callbacks, repeated edges, Tab wrapping, background focus rejection, keyboard text arrows, Steam keyboard access and cleanup. Existing native effect scrolling checks pass. The new direction checks were also run against the unchanged beta9 frontend and failed because the native direction handler and general-panel isolation were absent.

These are React/jsdom tests with explicitly mocked Steam/Decky and layout. Physical Steam Deck input and live Steam rendering were not tested. The fix is based on the callback contract and regression evidence; it is not a hardware-verification claim.

Packaging verifies CRC, source/distribution parity and file hashes. The bundled dependencies are byte-for-byte identical to beta9.
