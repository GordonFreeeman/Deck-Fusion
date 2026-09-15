# Deck Fusion 1.3.1: game-independent compatibility tools

1. Runtime status, installation and snapshot restore accept any selected 32-bit or 64-bit Windows executable in an installed game's root. No Cyberpunk executable-name or AppID gate. Native Linux executables receive an accurate, non-destructive explanation.
2. Support Steam games and Steam-managed non-Steam Windows shortcuts when their initialized Proton prefix can be resolved. Preserve the opt-in non-Steam library filter. Never guess a missing/ambiguous prefix or touch arbitrary Wine folders.
3. Runtimes is accessible from Library, DLLs, the existing tab, and the wizard. Titles, warnings and confirmations identify the selected game, not Cyberpunk. Runtime choices are optional, with no automatic installation or recommendations for every game.
4. Changing games/executables clears prefix/receipt/selection state. Inspection never writes game settings. Confirmations bind target app ID, executable, prefix and recipe choices; cancelling changes nothing.
5. Provide general read-only graphics-file/log diagnostics for every game. Keep Cyberpunk's framework-specific checks only as a clearly optional extra for the matching game, never a dependency of general tools.
6. Retain existing snapshot, restore, process guards, free-space checks, strict downloads, overrides, force repair, watermark strategy, mouse controls, manual FPS and footer/cross-window fixes. No profile-schema or persisted-path migration.
7. Review the affected implementation, run lightweight code/packaging checks and inspect the rendered general workflow. Record actual verification and no invented hardware results. Deliver the complete ZIP and agent-review.md.
