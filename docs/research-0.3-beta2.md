# Beta2 investigation

Checked on 2026-09-15. [Recorded upstream results](../evidence/0.3-beta2/upstream-check.json).

## ReShade

The failing catalogue entry requested `crosire/reshade-shaders/commits/master`. GitHub returned HTTP 422. The repository has distinct [slim](https://github.com/crosire/reshade-shaders/tree/slim) and [legacy](https://github.com/crosire/reshade-shaders/tree/legacy) branches. Standard stays on `slim`; Legacy now uses `legacy`.

All seven built-in commit endpoints resolved. The production download/extraction code fetched Legacy at `bcb5ba54199f4455026dd8ba66dc1b74461d3152` into an isolated cache with TLS verification enabled. Its archive SHA-256 was `99a05c4273e42d6de50e4509c66caf81c0045bfce2368bfbdf3b7812714306a1`. Parsing found 33 assets, 20 shader files and 29 techniques. No shader execution or game injection was tested.

## Graphics API

The previous detector inspected only the executable's PE imports. Unity games can put renderer imports in `UnityPlayer.dll`; other engines can also delegate through local DLLs. The new resolver follows a bounded set of imported local modules and ignores injection proxy DLLs. Multiple APIs remain ambiguous.

[Unity documents renderer command-line arguments](https://docs.unity3d.com/Manual/PlayerCommandLineArguments.html). Recognized explicit Unity flags take priority over import hints. Options are parsed as text and never executed.

[Subnautica: Below Zero's Steam requirements](https://store.steampowered.com/app/848450/Subnautica_Below_Zero/) list DirectX 11. The fallback is an inference about this title's default, guarded by Steam app ID 848450, the `SubnauticaZero.exe` name and Unity layout. It is not a live renderer measurement and does not establish a default for other Unity games.

## Windows runtimes

The user supplied exit status 1 and a log path, without the actual installer output. Its original cause is unconfirmed.

[Protontricks](https://github.com/Matoking/protontricks) selects Proton and the prefix; the existing command guard still verifies its resolved `WINEPREFIX` before Winetricks starts. [Winetricks](https://github.com/Winetricks/winetricks/blob/master/src/winetricks) supports `WINETRICKS_GUI=none`; that setting is retained. Quiet Windows installers can still need a display session.

The Decky backend can lack Steam's session fields. Beta2 fills only missing display, Xauthority, Wayland, runtime-directory and session-bus fields from a same-user Steam process. It preserves an existing session context and never imports Steam's graphics injection variables.

Nonzero exits now include bounded actual tool output. Recognized checksum, display, container, old-helper and VC-conflict messages add specific guidance. Unknown failures stay unclassified. The final output is retained even after the normal log limit. Guided setup reloads failed receipts and exposes the log through its own reader.

No Proton, Microsoft installer or Steam Deck hardware was available for execution. These changes must not be described as a confirmed repair of the user's original runtime failure.
