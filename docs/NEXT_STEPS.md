# VEGA — Next steps after v0.9 development release

The current repository includes local implementations for stages 5–9. See [v0.9 acceptance matrix](V09_ACCEPTANCE_MATRIX.md) for feature-by-feature completion and gaps.

## External integrations remain gated

- Real Fanvue, Instagram, TikTok, X and Reddit OAuth/API connectors and permission checks.
- Model-specific photo/video identity-consistency workflows on user's hardware.
- Voice synthesis and lip-sync tools (VoiceStudio/Chatterbox/LatentSync), subject to licensing and performance.
- Accurate earnings/account analytics via authorized platforms, not currently available.
- Real device testing on Windows, iOS and Android; tested here only in mocked browser viewports.
- A fully built and tested native Windows installer.

## Final stage 10: external infrastructure

Do not connect an external server or cloud GPU without explicit approval and cost caps. Cloud is not part of the v0.9 local build.
