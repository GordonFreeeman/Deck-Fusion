# Deck Fusion 1.2.1: one-time force repair

## Requested behavior
The user manually deleted OptiScaler and ReShade files from Cyberpunk and cannot reinstall because the ownership manifest records them as externally changed. Provide an explicit force/repair route without resetting the game profile or losing backups.

## Acceptance criteria
1. Normal Apply continues to block unexpected deletion/replacement of tracked binaries and shaders, but explains repair and exposes a direct review action.
2. Apply has a Force repair / reinstall toggle, off by default, never persisted in a profile/session draft. Reset it after success, cancellation, failure, and game selection. Restore does not use force.
3. Repair review lists missing and changed tracked files and the proposed action. Planning/cancelling cannot change game files, saved profiles, or launch options.
4. Approved repair reinstalls desired tracked files from the already selected local component packages, including missing shaders/configuration. Snapshot current replacements before overwriting them; retain original backups and recovery receipts.
5. A changed obsolete tracked file is kept in place and untracked, not silently deleted. An already deleted obsolete file stays absent unless a verified pre-installation original exists, in which case restore that original (for example a mod loader whose override is preserved). Explain every action in confirmation.
6. Repair consent is tied to the exact plan, current files and component content. Subsequent changes invalidate it. An unapproved force RPC cannot mutate files.
7. Running-game, anti-cheat, pending-operation, protected mod-loader/Wine override, unsafe-path/symlink/casing, damaged-backup and disk-space safety checks remain active. Recovery is never forced.
8. The same two-phase Steam launch verification and rollback work in repair mode, preserving the pre-attempt state, including files that were absent.
9. No changes to FPS limiting, INT8 settings, custom DLL overrides, game selection or the existing hidden-window/footer fixes.
10. Package an install-over 1.2.0 Decky ZIP with source, review log and focused evidence. No claim of Steam Deck/GPU validation.

## Affected systems
- `fusion_transaction.py`: drift inspection, explicit repair authorization, backup snapshots, obsolete-file handling, receipts, stale-state validation.
- `fusion_engine.py` / `main.py`: operation-scoped flag, plan binding, useful blocked-plan response, final checks.
- `src/index.js` / generated `dist/index.js`: one-shot toggle, blocked-dialog repair route, explicit confirmation, reset semantics.
- Version metadata, README, regression checks and release records.

## Scope of verification
Short synthetic-backend regressions, existing quick suite, syntax/bundle checks and rendered workflow inspection with simulated Decky/Steam at relevant viewports. No download or GPU benchmark campaign. Review the complete resulting changes and the existing interacting paths.
