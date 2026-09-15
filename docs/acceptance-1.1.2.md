# 1.1.2 black-screen hotfix acceptance

1. Both existing quick-access actions must render the manager/wizard when the plugin module executes in a zero-height window and React renders into another, visible document.
2. Sizing, resize listeners, frame scheduling and observer constructors must use the rendered element's owning window. Invalid, detached or transitional measurements must never commit a zero-height page.
3. Keep wizard actions above a simulated Steam footer at 1280x800, 1024x640 and 800x500. Focus scrolling must stay inside the content pane, including for cross-window nodes.
4. A descendant render/effect failure must display a recovery screen with retry and return-to-Steam actions, not an empty route. Recovery must not reset profiles or apply game changes.
5. Preserve 1.1.1 backend, runtime, TLS, FSR watermark defaults, LSFG configuration, component caches and transaction logic byte-for-byte. Only UI, version metadata, focused tests and documentation are changed.
6. Build the self-contained frontend, run targeted frontend/layout checks and the existing short backend suite, verify ZIP contents from a clean extraction, and include honest reviewer evidence. No GPU, FPS, native Steam control or on-device success claims.
