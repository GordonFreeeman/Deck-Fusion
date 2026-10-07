# v0.3-beta8 verification

365 standard backend tests and 58 frontend tests passed, with no skips. After tightening the one-time reset behavior, all 369 full backend tests passed, including the shared regression suite and offline component checks; 51 focused standard backend checks also passed. The full frontend is byte-identical to the verified standard frontend.

The new checks cover manual setting persistence through Apply, installed-file import, returning to guided settings without keeping old manual values, read-only preview and Save, malformed INIs, case-duplicate sections/keys, frame-generation conflicts, ReShade chaining, original-file backups, symlink protection, oversized files, editor cancellation, invalid-save recovery and navigation locking. The parser also accepts the real shipped OptiScaler INI.

The full bundle's dependency files are unchanged from beta7. Archive integrity, source hashes and compiled frontend consistency are checked by the packaging script.

Physical Steam Deck editor input and Witcher 3 compatibility were not tested here. Manual editing provides per-game configuration; this release does not claim to supply a universal working Witcher 3 preset. Earlier agent-review files refer to their original releases; no independent agent review was run for beta8.
