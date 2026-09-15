# fsr4xyz integration in 2.0.0-beta.2

## Verified release

Source: [the3rdparty1917/fsr4xyz, release 4.1.1b](https://github.com/the3rdparty1917/fsr4xyz/releases/tag/4.1.1b), published 2026-09-08; inspected 2026-09-13. Upstream describes an RDNA2 Windows ghosting fix for FSR 4.1 INT8. That description is not evidence of a successful Steam Deck game test.

- Asset: `FSR_4.1.1b_INT8_with_RDNA2_fix.7z`, 3,456,158 bytes.
- Archive SHA-256: `66e9a818e0c914def7712c8dac06b08e64a64dbcfe77f3162d43ea6de93869ff`, matched against the published GitHub digest.
- Extracted payload: `4.1.1b/amd_fidelityfx_upscaler_dx12.dll`, 34,013,696 bytes, inspected as a 64-bit Windows PE.
- DLL SHA-256: `0dd77d9c78d1ef9bc330cf4697ab3ffe24bc1aa7850e4130263dc922107fbd75`.

The real archive was downloaded, verified, safely extracted and passed through the component installer in an isolated temporary directory. The DLL was never executed. Structured inspection evidence is included at `evidence/2.0.0-beta.2/release-inspection.json`. Redistribution inside the plugin ZIP is not needed: the component downloads from its source when requested.

## Hardware default

Detection reads PCI vendor/device IDs from Linux DRM sysfs and recognizes an explicit AMD RDNA2 allowlist, including Van Gogh and Sephiroth. Steam Deck DMI product identification is a fallback only when no GPUs are enumerated. A non-RDNA2 or unknown GPU anywhere in the inventory prevents an automatic recommendation. Explicit saved true/false values always take precedence; no new profile schema number is needed for this additive default.

PCI families were checked against primary project sources: [Linux amdgpu PCI table](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/amd/amdgpu/amdgpu_drv.c) and [pciutils PCI ID database](https://github.com/pciutils/pciids/blob/master/pci.ids). These linked branches may evolve; the explicit implementation and tested IDs are captured in this ZIP.

This is a conservative hardware recommendation, not runtime renderer detection or proof of FSR 4 support. RDNA3, other architectures, unknown devices and mixed inventories default unchecked. The user may override either direction per game.

## Deployment and return to standard

Requirements include `fsr4fix` only for OptiScaler + FSR 4 INT8 + selected fix. Resolving the component pins both its release and archive digest. Extraction requires exactly one matching 64-bit DLL. Cached deployment verifies the pinned release metadata and recorded DLL checksum.

The payload replaces exactly one matching upscaler DLL from the standard OptiScaler payload inside the planned transaction. Missing or ambiguous targets block the operation. The original OptiScaler cache is never modified. Unchecking and applying regenerates the desired payload from that standard cache. Existing file conflict, backup, review, journal and rollback rules remain in force.

Automated tests cover default selection, explicit overrides, gating, integrity, cache repair, deployment and return to the standard DLL. They do not establish compatibility with a particular game, ghosting improvement, actual FSR4 model selection or frame rate under Proton.
