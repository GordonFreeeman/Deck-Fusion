# Deck Fusion v0.3-beta1

A Decky Loader plugin for per-game LSFG frame generation, OptiScaler upscaling and ReShade effects on Steam Deck.

## Install

1. Download `Deck-Fusion-v0.3-beta1.zip` from this repository’s Releases.
2. In Decky Loader’s developer settings, install the plugin from the ZIP.
3. Open Deck Fusion in the Decky sidebar.
4. Choose **Open Deck Fusion** for guided setup, or **Run Deck Fusion (Expert Mode)** for all controls.

The ZIP includes the compiled frontend and Python backend. No build tools are needed on the Deck. When updating, install over the existing plugin to retain profiles and backups. This release replaces the earlier `2.0.0-beta.*` numbering; a manual ZIP install may be needed because the new version number is lower.

## Guided setup

A running game is preselected. Each screen advances with **Next**; **Back** returns to the previous screen without discarding edits. There is no settings sidebar.

| Phase | Screens |
| --- | --- |
| Game | Choose a game → Check executable and graphics API |
| Features | Toggle LSFG, OptiScaler and ReShade → Choose ReShade effects |
| Runtimes | Select optional `d3dcompiler_47` and `vcrun2022` |
| Performance | Set base FPS cap, LSFG multiplier and Deck limiter → Select upscaling output and RDNA2 fix |
| Review | Read the configuration list → **Apply this game** |

The effects screen is skipped when ReShade is off. The upscaling screen is skipped when OptiScaler is off. Each arrow between setup screens is a separate Next press.

- The ReShade popup lists individual effects from all built-in packs and cached custom packs. Search, toggle, and scroll with the right stick, touch or mouse wheel. Downloaded effects are only enabled when selected.
- ReShade loads through OptiScaler whenever OptiScaler is enabled. Otherwise, it uses its own loader.
- **Respect Deck FPS limiter** starts on in guided setup. An opt-out made here is retained. Set the desired output limit in Steam’s Performance menu.
- The **FSR 4.1.1b RDNA2 fix** starts checked on detected Steam Deck/RDNA2 hardware. Other, unknown and mixed-GPU systems default off. An existing explicit choice is preserved. It is downloaded and deployed only with OptiScaler, FSR 4 INT8 and the checkbox enabled.
- Missing components and shader packs are prepared automatically. The Components page is omitted.
- Selected Windows runtimes install on Apply. Deck Fusion detects the game’s Proton prefix, skips runtimes already recorded as installed, backs up the prefix, and installs the user-level Protontricks helper if needed. If several prefixes exist, choose one on the runtimes screen.

Close the game before applying file or runtime changes. If it has no Proton prefix yet, run it once through Steam first. Launch or restart the game after Apply. Exit returns to Steam Home and its main game reel.

## Requirements and limits

- SteamOS, Decky Loader and an installed game. Downloads need internet access.
- LSFG requires your purchased Lossless Scaling installation on its `lsfg-vk` branch. The proprietary DLL is not included; automatic detection runs during setup, with a path field if needed.
- OptiScaler requires a compatible 64-bit Windows game with a supported upscaler input. Enable that input in the game after setup.
- ReShade installation supports Windows DirectX/OpenGL games through Proton. Native Linux and Windows Vulkan ReShade injection are not implemented.
- FSR 4 INT8 and the [community RDNA2 fix](https://github.com/the3rdparty1917/fsr4xyz/releases/tag/4.1.1b) are experimental on Steam Deck. The fix is pinned to 4.1.1b and checked against its SHA-256 digest.
- The Deck limiter preset uses FIFO pacing with Gamescope WSI disabled for this game. This can affect HDR. The base cap applies to DXVK/VKD3D.
- Games with detected anti-cheat are blocked from injection. Effect compatibility, depth access, visual quality and performance depend on the game.

The new guided interface is covered by automated tests with simulated Steam/Decky services. It has not been tested on physical Steam Deck hardware. See [verification](agent-review.md).

## Controls

| Input | Action |
| --- | --- |
| D-pad / left stick | Navigate controls |
| A / Enter / Space | Activate |
| B / Escape | Close a popup or go back; first setup screen stays open |
| Right trackpad / mouse / touch | Point, click or tap |
| Right stick / mouse wheel / touch drag | Scroll the effects popup |
| R2 | Click under Steam’s native browser input bindings |
| L1 / R1 | Change tabs in Expert Mode |
| Steam + X | Open Steam’s keyboard for text entry |

Native browser input is enabled while Deck Fusion owns focus and released on exit. It does not save controller-layout changes. Mouse and touch work directly; older Steam clients use the local pointer fallback where available.

## Expert Mode and recovery

Expert Mode retains the Library, Motion, Upscaling, ReShade, DLLs, Runtimes, Apply and Tools tabs. It includes advanced INI/preset editing, extra shader repositories, DLL overrides, diagnostics, component updates, live LSFG controls, repair and restore. The old setup-wizard entry is removed.

Game-file changes use tracked backups and verified Steam launch-option writes. Restore in Expert Mode’s Apply tab restores managed files and launch options. Runtime prefix snapshots are separate and can be restored from Runtimes. Successful runtime installs remain installed if a later graphics operation fails; their receipts and backups are retained.

## Development

Use Python 3.10+ and Node.js 24+ with npm. The frontend uses Decky’s React and UI at runtime; npm dependencies are only for tests.

```sh
python3 -m pip install -r requirements-dev.txt
npm ci
npm test
```

`python3 scripts/build.py` combines `src/index.js`, `src/studio.js` and `src/setup.js` into `dist/index.js` without npm dependencies. To package a checked build:

```sh
python3 scripts/hash_manifest.py
python3 scripts/package.py
```

The package script checks ZIP paths, CRCs, source/bundle parity and the recorded file hashes. It writes the ZIP and a SHA-256 sidecar beside the source directory. Public release/tag naming is `v0.3-beta1`; npm uses the equivalent three-part version `0.3.0-beta1`.

## License

Deck Fusion is MIT licensed. The embedded Decky API adapter is LGPL-2.1-only; the CA bundle is MPL-2.0. See [LICENSE](LICENSE), [licenses](licenses/) and [certificates](certs/README.md). Downloaded components and shader packs retain their upstream licenses. Proprietary Lossless Scaling and Microsoft runtime payloads are not bundled.
