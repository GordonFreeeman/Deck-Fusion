# Deck Fusion 1.3.0: optional Cyberpunk prefix runtimes

1. Inspect the selected Cyberpunk executable and its actual detected Proton prefix, not bin/x64; never guess a prefix when multiple candidates exist.
2. Show runtime files and Winetricks receipts as evidence, not proof of successful mod loading.
3. Explicit confirmation installs d3dcompiler_47 and/or vcrun2022 through existing native/Flatpak Protontricks. A separate opt-in installs the official Flathub helper for the current user when missing.
4. Snapshot the selected prefix before any runtime execution; preserve symlinks without following them. Check free space, running processes, unfinished file transactions and stale approvals. Never reset or delete the prefix or saves.
5. Scope runtime execution to the approved prefix and selected Steam AppID, with a checked WINEPREFIX inside Protontricks. Use only fixed, allowlisted Winetricks verbs. No system Wine, sudo, global wineserver kill, insecure downloads or graphics DLL copying.
6. Offer bounded progress/logs, cancellation and a reviewed snapshot restore. Retain the displaced prefix on restore. Runtime errors must not be reported as success. Repeated installation must not silently force VC runtime replacement.
7. Preserve existing graphics settings, custom DLL overrides, force repair, watermark strategy and safe-area layout. Add an easy-to-reach Runtimes page and a link from Cyberpunk DLL diagnostics.
8. Focus checks on the new subprocess/backup boundary, negative cases and rendered controls. No physical Deck, Microsoft installer, native controller or GPU success claims.
