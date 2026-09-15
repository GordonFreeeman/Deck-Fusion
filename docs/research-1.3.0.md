# Prefix runtime integration research

Checked 2026-09-13 against primary project guidance and source. No third-party
DLL download sites, unofficial Protontricks websites or binary repackagers used.
These references justify the installation route; they do not diagnose a specific
user's current prefix or prove that installing the runtimes fixes a crash.

## Modding requirements and scope

- Cyberpunk modding community Linux guide:
  https://wiki.redmodding.org/cyberpunk-2077-modding/for-mod-users/users-modding-cyberpunk-2077/modding-on-linux
  Lists d3dcompiler_47, vcrun2022 and winmm/version native-first overrides. It also
  suggests Winetricks force for a particular failure; this plugin deliberately
  does not pass --force because upstream implements checksum bypass under it.
- CET Linux guide:
  https://wiki.redmodding.org/cyber-engine-tweaks/getting-started/installing/linux-proton
  Reviewed earlier in this implementation pass. The later web reread returned
  unsupported markdown content; the Linux modding guide above was separately
  retrieved and supplies the two-dependency recommendation. This is community
  mod-framework guidance, not a CD Projekt RED endorsement of these injectors.

## Protontricks

- Official project README:
  https://raw.githubusercontent.com/Matoking/protontricks/master/README.md
  Commands `protontricks APPID ACTIONS` and `protontricks -c COMMAND APPID`.
  STEAM_COMPAT_DATA_PATH selects `<path>/pfx`; STEAM_DIR disambiguates a Steam
  installation. Steam Deck uses the recommended Flatpak route. Additional
  libraries need explicit filesystem access. The README warns against a fake
  protontricks.com site; no request in this plugin is sent there.
- CLI source:
  https://raw.githubusercontent.com/Matoking/protontricks/master/src/protontricks/cli/main.py
  The generated command runs after Protontricks resolves the game's compatibility
  tool and exposes WINEPREFIX/PROTON_PATH. The code verifies WINEPREFIX before
  invoking Winetricks. No unrestricted caller-supplied shell action is exposed.
- CLI flags:
  https://raw.githubusercontent.com/Matoking/protontricks/master/src/protontricks/cli/util.py
  --no-background-wineserver is a supported switch. The plugin does not run a
  global wineserver kill or guess /usr/bin/wine for the installer.
- Prefix discovery/source:
  https://raw.githubusercontent.com/Matoking/protontricks/master/src/protontricks/steam.py
  Existing pfx and its initialization lock are required. The plugin never
  creates/resets a prefix as a way to make dependencies install.

## Winetricks

- Official source:
  https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
  Inspected the runtime verbs, unattended mode, receipt handling, conflicts and
  checksum verification. vcrun2022 is a package/verb for several VC runtime DLLs,
  not a DLL named vcrun2022.dll to be copied into bin/x64. The d3dcompiler_47 recipe
  installs into the Windows system directories in the selected prefix.
- The checksum function skips mismatches when WINETRICKS_FORCE=1. The same switch
  also bypasses conflicting-verb checks. Therefore this update does not expose
  the '--force vcrun2022' troubleshooting shortcut. A failing runtime operation
  retains the snapshot and reports the log instead of silently retrying unsafely.

## Flatpak packaging

- Official app manifest/project:
  https://github.com/flathub/com.github.Matoking.protontricks
  App ID: com.github.Matoking.protontricks.
- Flatpak run/install options:
  https://docs.flatpak.org/en/latest/flatpak-command-reference.html
  Optional helper installation uses the official Flathub user remote. Extra
  filesystem access is passed to a single invocation, not written as permanent
  Flatpak override permissions. No sudo or SteamOS package-manager write.

## Remaining empirical boundary

Proton's selected version and Linux graphics stack, actual Flatpak visibility,
Microsoft download availability, installer dialogs, VC conflicts, mod versions,
and Cyberpunk startup must still be checked on the user's Steam Deck. The
sandbox verified file/command boundaries with synthetic prefixes and explicitly
simulated installers, not Microsoft runtime functionality or game rendering.
