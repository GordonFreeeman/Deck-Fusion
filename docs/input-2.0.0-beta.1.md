# Input implementation and evidence

Primary reference inspected: SteamDeckHomebrew/decky-frontend-lib, commit `247eb635ea7acdc3e7807d5f99722daf854aaa70`.

- [Focusable props](https://github.com/SteamDeckHomebrew/decky-frontend-lib/blob/247eb635ea7acdc3e7807d5f99722daf854aaa70/src/components/Focusable.ts): native `onActivate`, `onCancel`, focus classes and ref support.
- [Gamepad event enum](https://github.com/SteamDeckHomebrew/decky-frontend-lib/blob/247eb635ea7acdc3e7807d5f99722daf854aaa70/src/components/FooterLegend.ts): shoulder codes 5/6, trigger codes 7/8, horizontal directions 11/12.
- [Steam Input types](https://github.com/SteamDeckHomebrew/decky-frontend-lib/blob/247eb635ea7acdc3e7807d5f99722daf854aaa70/src/globals/steam-client/Input.ts): `RegisterForControllerStateChanges`, right-pad coordinates/touch/click, right-stick axes/click and unsubscribe.
- [Modal props](https://github.com/SteamDeckHomebrew/decky-frontend-lib/blob/247eb635ea7acdc3e7807d5f99722daf854aaa70/src/components/Modal.ts): owned confirmation class names; native approval/cancel callbacks retained.

These are community-maintained descriptions of Steam internals, not a stable Valve SDK contract. The code capability-checks optional raw input and cleans up subscriptions/animation frames/cursor DOM when the route unmounts. It never edits Steam controller layouts, calls OS mouse injection or disables Steam Input.

The pointer is attached to the visible owner document. Hit testing permits only the local editor or a class-marked Deck Fusion confirmation. Unrelated Steam UI cannot be clicked by the local pointer. Synthetic event tests cover a centered R3 press after an idle interval, held-button suppression, owned confirmation activation, foreign-element rejection and teardown.

Native Steam focus behavior and actual raw event delivery require a physical Deck. The implementation does not treat simulated tests as hardware evidence.
