# v2.0 beta acceptance record

## Implemented and examined

1. Retain Decky's two existing entry routes and all eight feature areas.
2. Provide a custom graphical workspace with orbit animation, layered backgrounds, focus/hover states and reduced-motion behavior.
3. Replace scrolling settings forms with bounded pages and direct named page selection. Preserve dynamically discovered controls and help.
4. Support native focus targets, A/B, shoulder navigation, keyboard, mouse and touch; add a scoped right-pad/right-stick pointer from typed Steam callbacks.
5. Preserve all original draft, apply, transaction, diagnostics and recovery paths. No new elevated privileges or controller-layout modifications.
6. Preserve every character in paginated diagnostics; handle resize and focus changes.
7. Produce an installable v2 beta ZIP, source, independent review log and reproducible tests.

## Executed verification

- Python backend regression tests.
- Node frontend/module/viewport utility tests.
- Real React + jsdom tests with explicitly mocked geometry and Steam/Decky services.
- Independent implementation and aesthetic source reviews.
- Build, bundle equivalence, ZIP structure/CRC and SHA-256 checks.

Exact final counts and reviewer decisions are recorded in agent-review.md and evidence/2.0.0-beta.1/verification.txt.

## Not verified in this environment

- Rendered geometry, screenshots, native Steam focus tree and on-device visual quality.
- Physical right-trackpad/right-stick reporting on the installed Steam client.
- Actual gaming graphics performance, power cost, Proton or injection behavior.

The browser service explicitly blocked local preview URLs. This was not bypassed. DOM metrics in the executable tests are synthetic; they verify algorithms and interaction/state transitions, not actual CSS rendering. Delivery is a beta with these explicit limits, not a hardware-certified release.
