# v0.3-beta6 verification

This release repairs stale runtime receipts that could stop Apply before launch-option replacement, and changes how the app opens and exits Steam's navigation history. Verified by the primary agent; no new independent review is claimed.

- 333 Python tests passed. Eight new cases cover stale VC 2022/2015/2017/2019 receipts, healthy existing runtimes, unrelated receipts, linked-file rejection and restoring the original prefix after a failed installer.
- 50 frontend tests passed, with none skipped. The combined Apply test repairs a stale runtime, refreshes its plan and writes the approved replacement once, keeping the original launch text for rollback. The navigation test opens and closes the compiled plugin three times without leaving it in the simulated Back history; the recovery exit uses the same replacement path.
- Prefix snapshots finish before receipt repair. Compatible runtimes remain untouched. The installer keeps checksum verification enabled, and failed native-DLL verification still blocks graphics changes.
- Steam's extracted client source confirms the second Navigate argument selects history replacement. Both entering and exiting use it, avoiding an extra Home entry on every visit.

The full test logs and navigation contract record are in `evidence/0.3-beta6/`. The packaging script checks ZIP CRCs, path safety, source hashes and source/bundle parity.

Runtime installers were simulated, and the UI tests use React/jsdom with simulated Steam/Decky interfaces. Actual Proton installation, game injection and the physical Steam Deck B button remain unverified. Entries already left in Steam history by an older plugin version are not erased; the new entry and exit handling prevents creating them during subsequent visits.

Earlier verification records follow below.

> Beta5 updates the README, DLL injection help text and version labels. The beta4 test results below describe the underlying implementation; the beta5 bundle and archive were rebuilt and checked separately.

# v0.3-beta4 verification

Implemented and checked by the primary agent. Historical verification records apply only to their named builds.

## Changes

- Guided DLL injection screen with per-game OptiScaler and standalone ReShade filename choices. Manual choices remain fixed; occupied names require another choice or the backed-up force apply flow.
- BG3's DirectX 11 executable is preferred in scan results. Its Vulkan and DirectX 11 identities are recognized even without renderer imports. Mismatched API selections are rejected.
- Automatic BG3 OptiScaler loading uses winmm.dll. ReShade is sideloaded as ReShade64.dll with LoadReshade=true.
- The wrapper selects the reviewed BG3 executable only in a recognized Steam/Proton command. It preserves Proton, other arguments, other games and custom launch chains. The renderer decision is logged.
- vcrun2022 uses the bundled unmodified Winetricks recipe, checked against its pinned SHA-256 before invocation. The selected game's Protontricks runner and prefix guard remain in place. Flatpak receives read-only access to the recipe directory for that invocation.
- Visual C++ detection checks Microsoft's registry entry and the required DLL version resources and architecture. Complete VC 14.44+ 14.x installations can satisfy setup without Winetricks receipts. Missing, old, symlinked and Wine builtin/placeholder DLLs cannot.

## Results

- **325 Python tests passed.** New tests cover transaction outputs for all seven OptiScaler proxy names, matching Wine overrides, BG3 defaults, shared ReShade configuration, manual collision handling, retiring an old proxy, renderer command selection, native runtime evidence and pinned recipe integrity.
- **48 Node tests passed**, with no skips. New React/jsdom tests exercise DLL selectors, saved manual choices, shared ReShade loading, runtime skipping without receipts and blocking graphics writes after failed DLL verification.
- Downloaded the x86 and x64 Microsoft VC 2022 installers to verify the recipe hashes. Both matched. No installer was executed or included in the ZIP.
- Production bundle built successfully and passed JavaScript syntax validation.
- Packaging checks ZIP CRCs, path safety, source/bundle parity and source hashes, including the bundled Winetricks source and license.

The full logs are in `evidence/0.3-beta4/`. Test DLLs contain synthetic version-resource data; they are not Microsoft runtimes. Steam, Decky and Proton interfaces are simulated in tests.

## Limits

No physical Steam Deck, live Steam/Decky UI, BG3 game run, GPU injection or Microsoft runtime execution was available. Rendered screen fit was not verified. The user's original vcrun2022 error remains undiagnosed without its installer output. This build addresses old recipes and unnecessary reinstallation; it does not claim to resolve every Protontricks failure.

## Sources

- [BG3 Linux loader report](https://github.com/optiscaler/OptiScaler/discussions/495)
- [OptiScaler supported proxy names](https://github.com/optiscaler/OptiScaler/wiki/Manual-Installation)
- [ReShade sideloading](https://github.com/optiscaler/OptiScaler/wiki/Compatibility-with-other-mods-(Reshade,-SpecialK))
- [Pinned Winetricks source](https://github.com/Winetricks/winetricks/blob/f3890f670867b5ffbc3938726db45c0f7d16c8ba/src/winetricks)
- [Microsoft Visual C++ runtime compatibility](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
