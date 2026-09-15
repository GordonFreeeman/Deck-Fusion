# Input, layout and exit fixes in beta.3

## Source inspection

Steam's extracted UI uses `SteamClient.Input.SetWebBrowserActionset(true)` while a browser without gamepad-specific support is active and calls the same setter with `false` on cleanup. Deck Fusion now uses that temporary action set for its editor, preferring the Steam bridge belonging to the rendered document. It pauses when focus leaves the editor or an owned confirmation, on window blur and while hidden. It releases the action set on unmount.

The implementation deliberately does not use `SetCursorActionset`: Steam's Mouse action set is intended for its mouse-position chooser and lacks the normal directional navigation bindings. The WebBrowser configuration contains right-pad/right-stick mouse sources, click bindings, and directional navigation. In that mode R2 is a mouse click, so the on-screen Previous/Next controls are the page navigation path; shoulder navigation remains native. The old raw fallback retains trigger paging and R3 clicking. Native mode and raw packet processing are mutually exclusive.

Primary sources inspected:

- [Steam's extracted UI source](https://github.com/SteamDatabase/SteamTracking/blob/master/ClientExtracted/steamui/chunk~2dcc5aaf7.js), captured Git blob SHA `c105af433f2ad6b60cc343808d09d66f94639853`. Inspected browser action-set lifecycle and route definitions: Library Home resolves to `/library/home`.
- [Steam's default UI controller configuration](https://github.com/SteamDatabase/SteamTracking/blob/master/ClientExtracted/controller_base/basicui.vdf), inspected WebBrowser and Mouse presets, mouse-click and directional bindings.
- [Decky navigation wrapper](https://github.com/SteamDeckHomebrew/decky-frontend-lib/blob/247eb635ea7acdc3e7807d5f99722daf854aaa70/src/modules/Router.ts), navigation precedes closing side menus.

These are internal Steam interfaces, not a stable public Valve SDK. The downloaded sources were inspected locally; no Steam controller layout file is modified or redistributed by this beta.

## Layout

The supplied device screenshot shows the old picker title behind Steam's top bar and three oversized choices. The old code had an explicit three-item limit on compact surfaces and stretched each row with fractional grid sizing.

Pickers now measure their own available list height. Each row is 44 CSS pixels with a six-pixel gap; capacity is floor((height + 6) / 50). Labels can wrap to two 17-pixel lines. Pagination keeps every option reachable and restores focus if a resize or page replacement removes the focused item.

The route retains its measured bottom clearance and adds an internal top inset where its origin overlaps the first 48 CSS pixels of Steam's window. Both normal content and local overlays use the same inset. Routes already below that boundary do not receive duplicate padding.

## Verification limits

Regression tests run the actual React components in jsdom with explicitly synthetic layout metrics and mocked Steam APIs. They verify action-set calls, mouse edits, suppression of duplicate raw input, suspension/resume/cleanup, plain headings, Home exit routes, header-inset calculation, picker capacity, option retention and resize focus.

No live browser rendering, physical Steam Deck input or native Steam focus/layout verification was available. The screenshot was used as bug evidence, not as proof that the new build has been rendered on a Deck.
