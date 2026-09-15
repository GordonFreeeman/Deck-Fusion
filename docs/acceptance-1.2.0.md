# Deck Fusion 1.2.0 acceptance criteria

1. Watermark OFF explicitly disables the AMD SDK flag before Proton starts, suppresses Proton's indicator enablement, and writes an unambiguous false in every matching managed INI assignment. INT8 model/output settings are preserved. Diagnostic flag state is recorded without claiming GPU validation.
2. A dedicated DLLs section reads existing Steam launch WINEDLLOVERRIDES, the selected game's Wine prefix defaults and executable-specific overrides (read-only), and relevant DLL files alongside the selected executable. Pre-existing launch text and DLLs remain intact.
3. Manual additional native/builtin/disabled overrides can be added, edited, removed, and selected from detected matching-architecture local DLLs. Malformed values and unsafe names are rejected. Removing a custom entry returns to inherited settings; it does not delete a DLL or registry entry.
4. Apply proposes free, supported OptiScaler/ReShade loaders. Existing override names, case variants, wildcard-specific names, unmanaged DLLs and backed-up originals reserve names. No available supported loader means a clear blocker, not replacement of another mod.
5. Merging retains unrelated names and load orders, grouped assignments, wildcard entries and disabled overrides. The review displays custom override changes and the resulting loader configuration. Cancel is non-mutating; stale confirmation and rollback protection remain intact.
6. Both 33-to-66 buttons and preset-specific help are removed. Manually chosen base FPS/multiplier values survive migration unchanged.
7. Existing cross-window viewport/error-boundary fixes and footer clearance remain intact. Both entry routes and DLL controls render at Deck and reduced viewport sizes with a simulated Steam footer.
8. Versioned developer ZIP contains built source, backend, tests, research and agent-review.md. No physical Deck, Proton injection, or GPU-validation claims.
