# Deck Fusion

**LSFG, OptiScaler and ReShade on Steam Deck, configured through a Decky plugin.**

I wanted to use frame generation, better upscaling and a few ReShade effects on my Deck without having to remember which files go where, which DLL filename a game needs, and what to put in its launch options. Deck Fusion handles that setup through a guided interface you can use with the controller, trackpad, mouse or touchscreen.

You choose a game, enable the features you want, adjust their settings and apply. Each game keeps its own configuration, so you can use a different combination for Cyberpunk, The Witcher 3 or Baldur's Gate 3 without starting from scratch every time.

**Current version: v0.3-beta5.** Cyberpunk 2077, The Witcher 3 and Baldur's Gate 3 have been set up successfully during development. That isn't a compatibility guarantee for every game, and the project is still in beta.

## What it does

- **LSFG frame generation:** configure the multiplier, base FPS cap and whether to respect the Deck's FPS limiter.
- **OptiScaler upscaling:** choose FSR or XeSS output in compatible games, including experimental FSR 4 INT8 support and the optional RDNA2 ghosting fix.
- **ReShade effects:** browse the available shaders and toggle individual effects in a searchable popup. When OptiScaler is enabled, ReShade loads through it automatically.
- **DLL injection:** choose the filename used to load OptiScaler or standalone ReShade, with the corresponding Wine overrides handled for you.
- **Windows runtimes:** install optional dependencies such as `d3dcompiler_47` and `vcrun2022` into the game's Proton prefix.
- **Repair:** reinstall missing or changed files and replace conflicting launch options after showing you what will change.

## What you need

You'll need SteamOS, [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader), an installed game and an internet connection for component downloads.

**LSFG requires a purchased copy of Lossless Scaling**, installed on its `lsfg-vk` branch. Deck Fusion looks for its DLL during setup; if automatic detection fails, you can enter the path yourself. The Lossless Scaling DLL is not included in this repository or the release ZIP.

OptiScaler needs a compatible 64-bit Windows game with a supported upscaler input. ReShade currently supports Windows DirectX and OpenGL games through Proton; its Vulkan injection path is not implemented here. Games with detected anti-cheat are blocked from injection, and you should check a game's rules before using graphics mods online.

## Installation

1. Download `Deck-Fusion-v0.3-beta5.zip` from this repository's **Releases**. Use the plugin ZIP rather than GitHub's automatically generated source archive.
2. Open Decky Loader's settings, enable developer mode if necessary, and install the plugin from the ZIP.
3. Open Deck Fusion in the Decky sidebar, then select **Open Deck Fusion**.

You can install an update over the existing plugin to keep your profiles and backups. The release ZIP contains the compiled plugin as well as the source, so you don't need to build anything on the Deck.

## Setting up a game

The setup walks you through the game executable and graphics API, feature selection, DLL injection, ReShade effects, optional runtimes, performance settings and a final review. Each screen has **Next** and **Back** buttons, and sections you don't need are skipped. If a game is already running when you open Deck Fusion, it will be preselected.

Make sure you've selected the actual game executable rather than its launcher. You can edit settings while the game is running, but close it before applying file or runtime changes. If runtime setup cannot find a Proton prefix, launch the game through Steam once, close it and try again.

**Respect Deck FPS limiter** is enabled by default; set your desired output limit in Steam's Performance menu. When using LSFG, turn off the game's own frame generation to avoid stacking them. If you're using OptiScaler, you also need to enable a compatible upscaler input in the game's graphics settings after applying the configuration.

The optional [FSR 4.1.1b RDNA2 fix](https://github.com/the3rdparty1917/fsr4xyz/releases/tag/4.1.1b) is preselected on detected Steam Deck/RDNA2 hardware and can be unchecked. It is only installed when OptiScaler and FSR 4 INT8 are selected. This is a community build, and its results and performance will depend on the game.

## If OptiScaler or ReShade doesn't load

Try a different DLL filename on the **DLL injection** screen. Some games work with `dxgi.dll`, while others need `winmm.dll`, `version.dll` or another supported name. Deck Fusion copies the selected DLL and sets its Wine override when you apply; you don't need to add those parameters manually.

**Baldur's Gate 3 works best with `winmm.dll`.** Select **Use BG3 DirectX 11** on the executable screen and leave OptiScaler's DLL selection on Automatic, which uses `winmm.dll` for BG3. This selects `bin/bg3_dx11.exe`; the other executable, `bin/bg3.exe`, uses Vulkan. Recognized Steam/Proton launch commands are adjusted to use your selected renderer, while custom launch scripts may need manual adjustment.

When OptiScaler is enabled, ReShade uses `ReShade64.dll` through OptiScaler's loader. Standalone ReShade has its own list of supported graphics DLL names, so `winmm.dll` and `version.dll` are only offered for OptiScaler.

In game, **Insert** opens OptiScaler and **Home** opens ReShade. You can bind those keys through Steam Input to access the overlays without a keyboard.

## Runtime errors and repairs

The runtime step is optional. Deck Fusion checks for a compatible existing Visual C++ installation before trying to install it again, including installations made by Steam that have no Winetricks receipt. For `vcrun2022`, it uses an included, pinned Winetricks recipe through the game's Protontricks runner, with download checksum verification enabled.

If an installation fails, open **Installer log** from the runtime or review screen to see the actual error. Deck Fusion keeps a backup of the prefix before installation and stops the graphics installation if the selected runtimes cannot be verified. Protontricks and its dependencies can be updated through Discover.

If you've deleted files from the game folder or changed them manually, **Force apply settings** reinstalls the selected files and configuration after backing up what it replaces. Review also has a **Force apply…** button for a full reinstall of the selected components.

Existing launch options that could conflict with Deck Fusion produce a separate warning showing the proposed replacement. Check that list before confirming, especially if you use other mods: DLL overrides such as `version` and `winmm` can belong to those mods too. Unrelated game arguments are retained.

Profiles, backups and logs are stored under:

```text
~/.local/share/deck-fusion/profiles/<appid>/
```

## Controls

| Input | Action |
| --- | --- |
| D-pad / left stick | Navigate |
| A / Enter / Space | Select |
| B / Escape | Go back or close a popup |
| Right trackpad / mouse / touchscreen | Point, click or tap |
| R2 | Click with Steam's browser input bindings |
| Right stick / mouse wheel / touch drag | Scroll the effects list |
| Steam + X | Open the on-screen keyboard |

Exiting Deck Fusion returns to Steam Home and the game reel.

## Building from source

The repository root should contain `plugin.json`, `package.json`, `main.py`, `src/` and `py_modules/`. If you're uploading the release ZIP's source to GitHub, upload the contents of its `deck-fusion` folder as the repository root and attach the installable ZIP to a release.

Development uses Python 3.10+ and Node.js 24+. From the repository root:

```sh
python3 -m pip install -r requirements-dev.txt
npm ci
npm test
```

To rebuild and package the plugin:

```sh
python3 scripts/build.py
python3 scripts/hash_manifest.py
python3 scripts/package.py
```

The package script writes the release ZIP and its SHA-256 file beside the source directory. It checks the archive's integrity and that the compiled frontend matches the source. Public versions use `v0.3-beta5`; the package metadata uses `0.3.0-beta5`.

The backend and interface tests use simulated game files and Steam/Decky services. They cover configuration, installation transactions and UI behavior, but cannot establish game compatibility or GPU performance. Previous test results and their limits are documented in [the verification record](agent-review.md).

## Credits and licenses

Deck Fusion builds on [lsfg-vk](https://github.com/PancakeTAS/lsfg-vk), [OptiScaler](https://github.com/optiscaler/OptiScaler), [ReShade](https://reshade.me/), [Protontricks](https://github.com/Matoking/protontricks), [Winetricks](https://github.com/Winetricks/winetricks) and Decky Loader. These projects do the underlying work; Deck Fusion brings their setup and configuration together on the Deck.

Deck Fusion is released under the [MIT license](LICENSE). The embedded Decky API adapter, CA bundle and included Winetricks source retain their own licenses, available in `licenses/`, `certs/` and `vendor/winetricks/`. Downloaded components and shader packs retain their upstream licenses. Microsoft runtime installers and the proprietary Lossless Scaling DLL are not bundled.
