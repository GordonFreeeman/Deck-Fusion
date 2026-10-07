# Deck Fusion

**LSFG, OptiScaler and ReShade on Steam Deck, configured through a Decky plugin.**

I wanted to use frame generation, better upscaling and a few ReShade effects on my Deck without having to remember which files go where, which DLL filename a game needs, and what to put in its launch options. Deck Fusion handles that setup through a guided interface you can use with the controller, trackpad, mouse or touchscreen.

You choose a game, enable the features you want, adjust their settings and apply. Each game keeps its own configuration, so you can use a different combination for Cyberpunk, The Witcher 3 or Baldur's Gate 3 without starting from scratch every time.

**Current version: v0.3-beta12.** Cyberpunk 2077, The Witcher 3 and Baldur's Gate 3 have been set up successfully during development. That isn't a compatibility guarantee for every game, and the project is still in beta.

## What it does

- **LSFG frame generation:** configure the multiplier, base FPS cap and whether to respect the Deck's FPS limiter.
- **OptiScaler upscaling:** choose FSR or XeSS output in compatible games, including experimental FSR 4 INT8 support and the optional RDNA2 ghosting fix.
- **ReShade effects:** browse the available shaders and toggle individual effects in a searchable popup. When OptiScaler is enabled, ReShade loads through it automatically.
- **DLL injection:** choose the filename used to load OptiScaler or standalone ReShade, with the corresponding Wine overrides handled for you.
- **Windows runtimes:** install optional dependencies such as `d3dcompiler_47` and `vcrun2022` into the game's Proton prefix.
- **Removal:** review an existing OptiScaler / ReShade installation, remove identified files with backups, and undo the removal if needed.
- **Repair:** reinstall missing or changed files and replace conflicting launch options after showing you what will change.

## What you need

You'll need SteamOS, [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader), an installed game and its selected Proton version. Launch the game once while online so Steam can finish installing Proton and the Steam Linux Runtime. The full ZIP includes Deck Fusion's component downloads; the standard ZIP downloads them during setup.

**LSFG requires a purchased copy of Lossless Scaling**, installed on its `lsfg-vk` branch. Deck Fusion looks for its DLL during setup; if automatic detection fails, you can enter the path yourself. The Lossless Scaling DLL is not included in this repository or the release ZIP.

OptiScaler needs a compatible 64-bit Windows game with a supported upscaler input. ReShade currently supports Windows DirectX and OpenGL games through Proton; its Vulkan injection path is not implemented here. Games with detected anti-cheat are blocked from injection, and you should check a game's rules before using graphics mods online.

## Installation

1. Download `Deck-Fusion-v0.3-beta12_full.zip` for offline setup, or `Deck-Fusion-v0.3-beta12.zip` for the smaller download from this repository's **Releases**. Use the plugin ZIP rather than GitHub's automatically generated source archive.
2. Open Decky Loader's settings, enable developer mode if necessary, and install the plugin from the ZIP.
3. Open Deck Fusion in the Decky sidebar, then select **Open Deck Fusion**.

You can install an update over the existing plugin to keep your profiles and backups. The release ZIP contains the compiled plugin as well as the source, so you don't need to build anything on the Deck.

## Full offline version

`Deck-Fusion-v0.3-beta12_full.zip` includes the tools and runtime payloads that setup would otherwise download. I made this version so a moved release, broken link or changed runtime installer won't prevent you from setting up a game. The included versions will get older, but the files remain available inside the ZIP.

| Component | Included version |
| --- | --- |
| lsfg-vk layer | 2.0.0, upstream x86 and x86-64 archive |
| OptiScaler | v0.9.4, complete upstream archive |
| ReShade | 6.8.0 standard build, both DLL architectures |
| RDNA2 FSR 4 fix | fsr4xyz 4.1.1b INT8 |
| Shader packs | Standard, SweetFX, FXShaders, qUINT, prod80, fubax and legacy |
| Visual C++ 2022 | Both x86 and x64 redistributables matched to the pinned Winetricks recipe |
| d3dcompiler_47 | Both Microsoft SDK CAB payloads, containing the x86 and x64 DLLs |
| Runtime helpers | Protontricks 1.14.1 command-line helper, VDF 3.4, Winetricks and cabextract 1.11 |

Install it through Decky in the same way as the standard ZIP. Setup unpacks the bundled tools into Deck Fusion's data folder and uses a separate, writable runtime cache. You don't need to install Protontricks through Discover or Flathub for this version. Allow extra free space for the extracted tools and the prefix backup made before runtime installation.

The full build doesn't check for newer components or download extra shader repositories. Missing or damaged bundled files stop the affected operation and ask you to reinstall the complete ZIP. Existing cached tools and per-game settings are retained, so installing the full ZIP over a working installation won't silently downgrade its tools. Install the standard ZIP if you want online component updates again.

SteamOS, Decky, Steam, your games, Proton and Steam Linux Runtime remain prerequisites. **The purchased Lossless Scaling DLL is not included** and must already be installed if you want LSFG. Bundling these files prevents broken component downloads; it cannot guarantee compatibility with future SteamOS, Steam or game updates.

The exact shader commits, source URLs and SHA-256 hashes are recorded in [`bundled/manifest.json`](bundled/manifest.json). [Full bundle notes](bundled/README.md) describe the helper build and included source archives. Attach the full ZIP to a GitHub **Release**; use the standard version's source for the repository itself.

## Setting up a game

The setup walks you through the game executable and graphics API, feature selection, DLL injection, ReShade effects, optional runtimes, performance settings and a final review. Each screen has **Next** and **Back** buttons, and sections you don't need are skipped. If a game is already running when you open Deck Fusion, it will be preselected. Closing the app returns to Steam Home and replaces its navigation entry, so pressing B does not reopen Deck Fusion.

Make sure you've selected the actual game executable rather than its launcher. You can edit settings while the game is running, but close it before applying file or runtime changes. If runtime setup cannot find a Proton prefix, launch the game through Steam once, close it and try again.

**Respect Deck FPS limiter** is enabled by default; set your desired output limit in Steam's Performance menu. When using LSFG, turn off the game's own frame generation to avoid stacking them. If you're using OptiScaler, you also need to enable a compatible upscaler input in the game's graphics settings after applying the configuration.

The optional [FSR 4.1.1b RDNA2 fix](https://github.com/the3rdparty1917/fsr4xyz/releases/tag/4.1.1b) is preselected on detected Steam Deck/RDNA2 hardware and can be unchecked. It is only installed when OptiScaler and FSR 4 INT8 are selected. This is a community build, and its results and performance will depend on the game.

## Manual OptiScaler settings

Open **Upscaling output > Advanced OptiScaler settings** to edit the full `OptiScaler.ini` for the selected game. You can start with the configuration Deck Fusion would apply, choose **Load installed settings** to import the file already in the game's executable folder, or choose **Use guided settings** to return to the normal presets.

**Save to draft** checks the INI and remembers it for that game. **Cancel** discards the editor's changes. The game folder is updated when you press **Apply this game**, using the same backup and recovery process as the rest of setup. Restart the game afterwards. Use the **D-pad** to highlight the editor, then **A** to enter text editing. A or X requests the keyboard directly through the Steam UI window containing the editor. The D-pad moves the caret and scrolls the INI when the keyboard is closed. While Steam’s keyboard is open, it owns D-pad and B input. **Open Steam keyboard** performs the same native request. Text mode suspends Deck Fusion’s browser controller mode so Steam + X can work normally. If Steam does not display its keyboard, the editor shows an error and retains your text. **B** returns to the editor controls. **Edit line** opens the line at the caret in Steam’s native text field; press A in that field for keyboard entry, then choose **Use edited line**. The complete INI remains available, and a physical keyboard works directly. No setting values are guessed or automatically substituted.

While a manual INI is active, the guided output picker is disabled so it cannot overwrite your changes. `LoadReshade` still follows Deck Fusion's ReShade toggle. Keep the renderer settings and `[FrameGen]` section, and set `Enabled` to `true` or `false` explicitly. Enabling OptiScaler frame generation while LSFG is enabled is rejected.

Games may need different settings, and the editor does not apply a universal Witcher 3 preset. Start from a configuration that works for your chosen DirectX renderer, change the relevant settings and apply it to that game.

## If OptiScaler or ReShade doesn't load

Try a different DLL filename on the **DLL injection** screen. Some games work with `dxgi.dll`, while others need `winmm.dll`, `version.dll` or another supported name. Deck Fusion copies the selected DLL and sets its Wine override when you apply; you don't need to add those parameters manually.

**Baldur's Gate 3 works best with `winmm.dll`.** Select **Use BG3 DirectX 11** on the executable screen and leave OptiScaler's DLL selection on Automatic, which uses `winmm.dll` for BG3. This selects `bin/bg3_dx11.exe`; the other executable, `bin/bg3.exe`, uses Vulkan. Recognized Steam/Proton launch commands are adjusted to use your selected renderer, while custom launch scripts may need manual adjustment.

When OptiScaler is enabled, ReShade uses `ReShade64.dll` through OptiScaler's loader. Standalone ReShade has its own list of supported graphics DLL names, so `winmm.dll` and `version.dll` are only offered for OptiScaler.

In game, **Insert** opens OptiScaler and **Home** opens ReShade. You can bind those keys through Steam Input to access the overlays without a keyboard.

## Runtime errors and repairs

The runtime step is optional. Deck Fusion checks for a compatible existing Visual C++ installation before trying to install it again, including installations made by Steam that have no Winetricks receipt. For `vcrun2022`, it uses an included, pinned Winetricks recipe through the game's Protontricks runner, with checksum verification enabled. The full build supplies both supported runtimes from its local cache.

If Winetricks says a selected runtime is already installed but its files are missing, incomplete or too old, Deck Fusion removes the stale receipt after backing up the prefix and runs the installer again. When upgrading to `vcrun2022`, this also clears older VC 2015, 2017 and 2019 receipts that would block it. Other components' receipts are kept, and the installed runtime must still pass verification before the graphics settings are applied.

If an installation fails, open **Installer log** from the runtime or review screen to see the actual error. Deck Fusion keeps a backup of the prefix before installation and stops the graphics installation if the selected runtimes cannot be verified. The standard build can use Protontricks installed through Discover. The full build uses its bundled command-line helper.

If you've deleted files from the game folder or changed them manually, **Force apply settings** reinstalls the selected files and configuration after backing up what it replaces. Review also has a **Force apply…** button for a full reinstall of the selected components.

Existing launch options that could conflict with Deck Fusion produce a separate warning showing the proposed replacement. Check that list before confirming, especially if you use other mods: DLL overrides such as `version` and `winmm` can belong to those mods too. Unrelated game arguments are retained.

Profiles, backups and logs are stored under:

```text
~/.local/share/deck-fusion/profiles/<appid>/
```

## Removing an existing setup

On **Choose a game**, select **Remove existing OptiScaler / ReShade**. Deck Fusion scans the game folder and shows which files it can remove, which originals it can restore, and which files it will keep. Nothing changes until you press **Back up and remove**, and the game must be closed.

For files installed by Deck Fusion, removal checks the recorded hashes and restores the original backups where available. For an installation made by another tool, a DLL must match a cached injector or identify itself as OptiScaler or ReShade in its version resources. A filename such as `version.dll` is never enough. Unknown DLLs, edited configuration files, untracked presets and shader folders, and untracked shared SDK libraries stay where they are. An older or unusual build that cannot be identified is also kept.

The removal button appears only when Deck Fusion identifies an OptiScaler or ReShade injector DLL. Unknown filenames and leftover presets do not make it appear. Every changed file gets a recovery copy under the game's profile directory. Choose **Undo last removal** on the game selection screen to review restoring the files and settings, even when no injector DLL remains. Undo stops if those files or the Steam launch options have changed since removal, so it cannot silently overwrite later edits. If an operation was interrupted, the game selection screen also offers **Recover interrupted operation**.

Removal keeps your applied LSFG settings, frame cap and Windows runtimes; unapplied draft edits are discarded. Launch overrides are only stripped for identified injector filenames that have been removed. If a Proton prefix forces native-only loading for one of those missing DLLs, removal stops until that override is corrected. It does not edit the prefix behind your back.

## Controls

| Input | Action |
| --- | --- |
| D-pad / left stick | Navigate |
| A / Enter / Space | Select |
| B / Escape | Go back or close a popup; on 1 Game, ask to quit |
| Right trackpad | Move the pointer |
| Mouse / touchscreen | Click or tap |
| L1 / R1 | Previous / next main setup step (1–6) |
| L2 / R2 | Previous / next tab within the current step |
| Right stick / mouse wheel / touch drag | Scroll the effects list |
| A / X in an editor | Enter text mode and request Steam’s native keyboard |
| D-pad in text mode | Move the caret and scroll to keep it visible |
| Steam + X / Open Steam keyboard | Open Steam’s keyboard while text is focused |
| B in text mode | Return to the editor controls |

R2 is reserved for tab navigation. Use A to activate the focused control, or click with a mouse or tap the screen. Navigation buttons do not confirm Apply or removal, and they stay locked while a popup is open. Steps with no applicable settings are skipped.

On the first **1 Game** tab, B opens **Quit Deck Fusion?**. A confirms and returns to Steam Home; B cancels. Exiting releases Deck Fusion’s controller input handlers and returns to Steam Home and the game reel.

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

The package script writes the release ZIP and its SHA-256 file beside the source directory. It checks the archive's integrity and that the compiled frontend matches the source. Public versions use `v0.3-beta12`; the package metadata uses `0.3.0-beta12`.

The backend and interface tests use simulated game files and Steam/Decky services. They cover configuration, installation transactions and UI behavior, but cannot establish game compatibility or GPU performance. Previous test results and their limits are documented in [the verification record](agent-review.md).

## Credits and licenses

Deck Fusion builds on [lsfg-vk](https://lsfg-vk.dev/), [OptiScaler](https://github.com/optiscaler/OptiScaler), [ReShade](https://reshade.me/), [Protontricks](https://github.com/Matoking/protontricks), [Winetricks](https://github.com/Winetricks/winetricks) and Decky Loader. These projects do the underlying work; Deck Fusion brings their setup and configuration together on the Deck.

Deck Fusion is released under the [MIT license](LICENSE). The embedded Decky API adapter, CA bundle and included Winetricks source retain their own licenses, available in `licenses/`, `certs/` and `vendor/winetricks/`. Components and shader packs retain their upstream licenses; the full bundle includes their notices and available source archives under `bundled/`. The full ZIP includes Microsoft runtime installers but does not include the proprietary Lossless Scaling DLL. The lsfg-vk 2.0.0 archive is supplied unchanged under CC BY-NC-ND 4.0, so the full bundle is for noncommercial distribution.
