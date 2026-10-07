# v0.3-beta9 verification

385 backend tests passed in the full distribution, covering 381 shared regression checks and four offline bundle checks. All 61 frontend tests passed with no skips. The focused standard backend run passed 62 checks before the version-label update. Shared frontend and changed backend sources are identical in the standard and full packages.

The new checks cover D-pad directions, editor entry with A, keyboard text arrows, Tab boundaries, background focus rejection, access to the Steam keyboard and cleanup on close. Removal checks cover identified versus unknown DLLs, ambiguous names, symlinks, Undo after removal, disabled prefix entries, later registry entries, native-only protection and unreadable registries. Prefix files remain unchanged.

The registry parser follows Wine's `parse_load_order` in `dlls/ntdll/unix/loadorder.c` (ValveSoftware/wine, proton_11.0). It accepts the registry's token syntax separately from the strict custom-override editor.

The full bundle's dependency files are unchanged from beta8. The packaging script checks archive CRC, source hashes and compiled frontend consistency.

Physical Steam Deck input and live Steam rendering were not tested here. The frontend suite uses React and jsdom with mocked Steam events and layout. No independent agent review was run for this release.
