# Primary-source notes for 1.3.1

Retrieved for this release on 2026-09-13.

## Protontricks is game-independent

The official README describes running Winetricks for a selected Steam app ID,
resolving Proton from Steam, and a custom STEAM_COMPAT_DATA_PATH yielding
WINEPREFIX=$STEAM_COMPAT_DATA_PATH/pfx. These are general facilities, not a
Cyberpunk requirement. The repository changelog and launcher source also cover
non-Steam shortcut detection and mount handling.

Official README, retrieved through the GitHub connector:
https://github.com/Matoking/protontricks/blob/master/README.md

Official source search (non-Steam support):
https://github.com/Matoking/protontricks/blob/master/CHANGELOG.md
https://github.com/Matoking/protontricks/blob/master/src/protontricks/data/scripts/bwrap_launcher.sh

The README identifies protontricks.com as an unaffiliated fake site. No guidance,
commands, binary or install URL from that site was used. The helper installer
remains on official Flathub, with its previously reviewed URL/remote checks.

## Implementation boundary

Version 1.3.0 had imposed a Cyberpunk basename restriction itself. It was not an
upstream Protontricks requirement. This release removes that restriction but
retains valid PE format, selected-game path, initialized-prefix, Steam tool,
checksum, backup and approval validation. It does not introduce a generic shell
or arbitrary Winetricks-verb API, or claim autonomous dependency detection.

Earlier runtime-recipe details remain in research-1.3.0.md. No recipe list or
third-party download behavior was changed in this release.
