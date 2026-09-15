# Deck Fusion beta.3 change and verification record

This iteration was implemented and reviewed by the primary agent. No independent-agent approval is claimed for beta.3. Historical independent reviews are preserved in `docs/agent-review-2.0.0-beta.1.md` and `docs/agent-review-2.0.0-beta.2.md`.

## Changes

1. Removed slogans from every tab and setup stage; compacted the heading area.
2. Replaced fixed three/five-item option pages and stretched cards with measured lists of compact 44px rows. Kept filtering, selection, pagination and resize focus.
3. Reserved the Steam header area inside the measured app bounds and applied the same top inset to local pickers and editors.
4. Added Steam browser action-set support for native trackpad mouse events, visible-window bridge preference and lifecycle cleanup. Raw input remains a fallback and is not processed alongside native mouse mode.
5. Changed all top-level exits to `/library/home`, with local B/Escape still closing panels first.

## Findings addressed during implementation

The screenshot's oversized picker corresponded to explicit `short ? 3 : 5` pagination and fractionally stretched rows. Its title could overlap the persistent Steam header because the overlay started at route y=0. Both causes were corrected.

Raw controller reporting alone did not request Steam's mouse input bindings. Inspection of Steam's actual UI identified its browser action-set lifecycle. The similarly named cursor action set was rejected as a design choice because its mouse-position preset lacks normal directional bindings. The browser action set supplies mouse-click and navigation bindings; documentation now identifies R2 as click in that mode.

Two initial regression assertions were corrected: the native-mode test used an incorrect toggle label, and the standalone picker fixture needed a key to remount between its game/shader cases. The completed tests verify actual click effects and all 23 options across pages, including resize.

## Final automated verification

253 Python tests and 24 Node tests passed, including ten React/jsdom scenarios with none skipped. Build and JavaScript syntax checks passed. Command output is in `evidence/2.0.0-beta.3/verification.txt`. Runtime hashes and ZIP integrity are checked during packaging.

The new cases cover plain tab titles, top-level Home exit, mouse action-set enable/suspend/resume/release, physical mouse editing, duplicate raw-input avoidance, measured game/shader list pagination, resize focus, and Steam header clearance at zero/offset/scaled route origins. Existing tests retain coverage of profiles, file transactions, RDNA2 defaults and fallback pointer boundaries.

## Limits

No native Steam/Decky session, rendered browser screenshot, hardware trackpad test or in-game test was performed. The supplied screenshot is evidence of the old build's problem. Synthetic geometry validates the layout calculations, not actual visual fit. Physical Deck verification remains outstanding.
