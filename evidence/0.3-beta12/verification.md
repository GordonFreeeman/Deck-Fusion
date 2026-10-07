# v0.3-beta12 verification

72 frontend tests pass without skips; 385 backend tests pass in the full distribution. Node syntax validation passes. Backend changes are version labels only.

## Corrected keyboard path

Beta11 only focused the textarea on A. X and the keyboard button sent an external Steam URI through OpenInSystemBrowser. That tested an API call, not the in-window Steam UI keyboard. The plugin also retained SetWebBrowserActionset(true) during text editing, competing with the input mode Steam needs for keyboard interaction.

Beta12 invokes VirtualKeyboardManager.SetVirtualKeyboardVisible() on the Steam window whose BrowserWindow is the editor's owner window. Candidate windows come from SteamUIStore and Decky's Router window store. A and X both request the keyboard from the highlighted editor and text mode; paired X callbacks are deduplicated. The ineffective URI path is removed.

The native contract is present in the BetterKeyboard plugin's primary source:
https://github.com/chenx-dust/BetterKeyboard/blob/main/src/utility/context.ts
https://github.com/chenx-dust/BetterKeyboard/blob/main/src/types.d.ts

Decky's owner-window routing contract is present in:
https://github.com/SteamDeckHomebrew/decky-frontend-lib/blob/main/src/modules/Router.ts

The plugin releases its browser action set synchronously when caret mode begins or a text field gains focus, before requesting the keyboard. It remains released through keyboard interaction and returns after leaving text mode. Steam retains ownership of keyboard action sets; Deck Fusion never guesses or sets them directly.

While the native keyboard is visible, or a request is pending, caret movement, panel cancellation, plugin scrolling and keyboard shortcuts yield to Steam. The focus trap permits native keyboard controls, including a portal beneath the plugin frame. Normal caret behavior resumes after the keyboard closes. Line editing uses the same opener without applying the full INI caret trap to the native single-line field.

A request is checked against Steam's native element with id="virtual keyboard". Missing window managers, thrown requests and no visible keyboard within two seconds show an error. The draft remains intact. A void method return is not treated as proof of display.

## Regression evidence

The React/jsdom Steam-window model rejects requests while browser mode is enabled. It renders a separate native keyboard element and models text insertion without an external URI. Checks cover A/X opening, X before caret mode, paired X events, the matching manager receiver and window, Router fallback, keyboard direction and B ownership, focus through a portal, native typing, caret persistence, mode restoration, missing/throwing managers, display timeout, retry and line-edit controls. The effects popup also yields browser mode and cancellation while its text filter uses the keyboard.

All five new keyboard-specific tests fail against the exact beta11 compiled bundle and pass in beta12. Beta11 fails to call the native manager on A, retains browser mode on text focus, lacks failure reporting and has no explicit line-editor X handler. Existing caret, scrolling, save and Quit confirmation regressions continue to pass.

## Testing limitation

This remains source-backed React/jsdom verification with mocked Steam APIs and layout. No physical Steam Deck, live Steam keyboard rendering or actual Steam + X controller chord was tested here. The new checks distinguish the failed beta11 implementation, but passing them does not prove hardware success.

## Packaging

Both installable ZIPs undergo CRC, safe-path, version, frontend source/distribution parity and runtime hash verification. Full-bundle dependency payloads are compared byte-for-byte with beta11 and remain unchanged. The repository update contains only changed files and preserves their relative paths.
