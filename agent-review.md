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
