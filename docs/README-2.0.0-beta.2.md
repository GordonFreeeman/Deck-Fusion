# Deck Fusion 2.0 beta

A new full-screen graphics workspace for Steam Deck, opened from the existing Decky sidebar. Version **2.0.0-beta.2**.

## What changed

- A graphite, cyan and violet interface with layered gradients, animated 3D orbit graphics, clear focus outlines and pointer hover feedback.
- Eight workspaces: Library, Motion (LSFG), Upscaling (OptiScaler), ReShade, DLLs, Runtimes, Apply and Tools.
- Fixed-height settings pages instead of long scrolling forms. Four controls per page on larger surfaces, two on compact or narrow surfaces. Use Previous / Next or the named page selector to reach every control.
- Searchable, paginated option pickers. Text and raw INI editors open in dedicated panels. Editing a long INI may scroll within the text editor; the settings pages themselves do not scroll.
- Help and diagnostic text use measured pagination, including recalculation after a resize. Apply/runtime confirmation details use the same approach.
- Mouse, touch, keyboard and Steam's native focus navigation. A route-local pointer can use Steam's reported right-trackpad or right-stick input without holding the Steam button.
- Pause interface animation from the sparkle button. System reduced-motion preferences are respected.

Existing per-game profiles, component caches, launch-option handling, conflict review, backups and recovery are retained. Profile schema remains 4. The optional RDNA2 fix adds hardware-aware defaults and a separately verified component; existing profiles retain explicit choices.

## Optional RDNA2 ghosting fix

Beta.2 adds the community [fsr4xyz 4.1.1b release](https://github.com/the3rdparty1917/fsr4xyz/releases/tag/4.1.1b), described upstream as an FSR 4.1 INT8 ghosting fix for RDNA2 Windows systems. Its behavior through Proton has not been tested on a physical Deck here.

| Detected hardware | Initial checkbox |
| --- | --- |
| Known Steam Deck / RDNA2 GPU IDs only | Checked |
| Steam Deck DMI identity, no enumerated GPU | Checked |
| RDNA3, other or unknown GPUs | Unchecked |
| Mixed GPU inventory, including RDNA2 plus another architecture | Unchecked |
| Existing explicit per-game choice | Preserved |

The **Install RDNA2 ghosting fix (FSR 4.1.1b)** switch appears in Upscaling, Tools and the relevant setup steps. You can check or uncheck it on any hardware. Detection uses the installed GPU inventory, not the GPU a particular game will render on. An unknown GPU defaults off.

The switch alone does not download or deploy anything and does not enable OptiScaler or FSR 4. The component is required only when **OptiScaler is enabled**, **FSR 4 INT8 is selected**, and **the switch is checked**. Prepare components downloads it on request. Review & apply installs its DLL through the existing tracked-file transaction. Uncheck and apply again to return that game to the standard DLL supplied by its current OptiScaler package. Restart the game after applying.

The pinned download has SHA-256 verification and a 64-bit PE check. The standard OptiScaler cache stays intact; the extra DLL has its own cache. A changed or missing cached DLL blocks deployment and can be repaired with the dedicated download/repair action. The beta does not silently track future fsr4xyz releases. See [release and detection details](docs/fsr4xyz-2.0.0-beta.2.md).

## Install the beta

1. In Decky Loader, open Settings, enable Developer Mode if needed, and use **Install Plugin from ZIP** to select `Deck-Fusion-2.0.0-beta.2.zip`.
2. Open **Deck Fusion** from the sidebar, then **Open Deck Fusion** or **Set up a game**.
3. Configure a game, then choose **Review & apply**. Existing game-file and launch-option changes still require the app's review step.

The ZIP has the standard `deck-fusion/` plugin root and includes its ready-to-load `dist/index.js`. No frontend package installation is needed on the Deck.

This beta does not add third-party LSFG, OptiScaler or ReShade payloads that were absent from the supplied 1.3.1 archive. Existing installed/cached components are reused; the Tools workspace retains the download and update functions.

## Controls

| Input | Action |
| --- | --- |
| D-pad / left stick | Navigate Steam focus targets |
| A | Activate the focused control |
| B | Close a local panel or return to Steam |
| L1 / R1 | Previous / next workspace |
| L2 / R2 | Previous / next settings or detail page |
| Mouse / touchscreen | Click or tap controls directly; drag sliders |
| Right trackpad | Move the local pointer; press the pad to click |
| Right stick | Move the local pointer; R3 clicks at its position |
| Arrow keys / Tab | Navigate controls; left/right adjusts a focused slider |
| Enter / Space | Activate |
| Page Up / Page Down | Change pages |
| Escape | Close a panel / return to Steam |
| Steam + X | Open Steam's keyboard for text entry when no keyboard is connected |

The raw pointer feature is capability-detected using `SteamClient.Input.RegisterForControllerStateChanges`. Steam client builds that do not expose or deliver that stream retain native focus navigation, physical mouse and touch. No Steam Input layouts are rewritten, and no OS-wide mouse injection is used. The local pointer only activates Deck Fusion or its own confirmation dialogs.

## Beta verification and limits

The Python regression suite and Node/React DOM tests were run against this release. The DOM suite executes the actual React components with simulated Steam/Decky services and explicitly mocked geometry. It covers all tab pages, draft editing, page focus, raw pointer events, owned-modal boundaries, cleanup, lossless reader pagination, retained RDNA2 opt-out and automatic setup dependency refresh. Final verification: 253 Python tests and 20 Node tests passed, including seven React/jsdom scenarios, with none skipped.

**No physical Steam Deck, native Steam/Decky session, game/GPU run, or current rendered screenshot was available for this beta.** The browser service blocked local preview URLs, and the shell environment could not run a browser with its required sockets. Consequently, actual viewport fit, Steam-native focus behavior, raw input delivery and graphical performance remain device-validation items. CSS was independently reviewed for 1280×800, 1024×640, 800×500 and 390×844; those are review targets, not screenshot-verified results.

Independent review findings, fixes and scope are recorded in [agent-review.md](agent-review.md). Previous screenshots under `evidence/1.x/` show historical releases only and are not evidence for v2.

## Development

The frontend uses Decky's existing React and UI components. There are no CDN assets, browser network dependencies or new backend privileges.

- `python3 scripts/build.py` combines `src/index.js` and `src/studio.js` into the self-contained `dist/index.js`.
- `python3 -m pytest tests -q` runs the Python regression suite (requires pytest).
- `node --test tests/*.test.mjs` runs core frontend tests; the optional DOM suite requires the setup below.
- To run the DOM suite, install `react@18 react-dom@18 jsdom` into a test-only directory and set `DF_TEST_MODULES` to its absolute `node_modules` path, then run `node --test tests/studio-dom.test.mjs`.
- `scripts/package.py` packages and checks ZIP CRCs, path safety, source/bundle correspondence and reviewed runtime hashes.

The browser harness in `tests/browser/` is a synthetic development host, not part of the installed entry point. It requires local React/ReactDOM and Python test dependencies. It must never be pointed at real game installations. Run the current host from the project root with:

```sh
DF_REACT_VENDOR=/absolute/test-tools/node_modules python3 -c "import inspect,sys,runpy;sys.path.insert(0,'tests/browser');runpy.run_path('tests/browser/serve_studio.py',run_name='__main__')"
```

The `inspect` pre-import avoids the historical `tests/browser/inspect.py` filename shadowing Python's standard module.

The full feature, compatibility and recovery documentation from the supplied version remains in [docs/README-1.3.1.md](docs/README-1.3.1.md).
