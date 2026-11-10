# VEGA v0.9 — test and acceptance matrix

**This is a development release, not production certification.** Check the exact status below before calling any stage finished end-to-end.

| Stage | Function | Delivered in code | Real-world validation / gap |
|---|---|---|---|
| 5 | Nine character profiles and reference-media isolation | Yes | Manual image review; no trained face-consistency system |
| 5 | ComfyUI image/video backend | Existing v0.4 connector | Requires local compatible ComfyUI, models, GPU/CPU workflow tests |
| 5 | Voice | Voice profile metadata; optional CPU faster-whisper transcription | Chatterbox/VoiceStudio TTS and LatentSync are not integrated |
| 5 | Ollama local editorial LLM | Local-only HTTP adapter and editable prompts | Need to install a compatible local model, test AMD/CPU performance |
| 6 | SEO packs, hooks, hashtags, CTAs | Template + opt-in Ollama AI drafts | No paid/live trend research |
| 6 | Supervised approvals/calendar/Kill Switch | Yes, inherited and tested | No remote push notifications |
| 7 | Fanvue/IG/TikTok/X/Reddit integrations | Registry, statuses and audited offline delivery export | **NO official OAuth, connected accounts or posting; platform APIs need approval/credentials** |
| 8 | Analytics by model/platform and revenue calculation | Manual metric entry and totals | No real Fanvue or social account data; data entered manually |
| 9 | Local auth, LAN HTTPS setup, safe headers | Yes in code | iPhone/Android actual device tests pending |
| 9 | Backup and recovery | Consistent SQLite snapshot + media ZIP, hash verification, offline restore CLI | User must test restoring their own copy; do not restore over running app |
| 9 | Windows launcher / desktop installer | Batch startup, PyInstaller and Inno recipes | Windows `.exe` and `.msi/.exe` installer NOT built or tested in Linux environment |
| 9 | Desktop/mobile interface | PWA and responsive views | Offline Chromium UI smoke succeeded with mock API; physical devices untested |

## Security rules

- Owner-only API access uses scrypt password hashes and bearer tokens. LAN mode requires HTTPS with locally generated CA. Never expose port 8765/8766 to the public Internet.
- Public GitHub contains source and docs only. Media, generated content, databases, model weights, API tokens, KYC information and private archives stay local.
- Kill Switch is initially ON. Offline exports require approved+scheduled content and confirmed rights. Editing invalidates prepared exports. No actual publishing exists in code.
- Optional Ollama and ComfyUI endpoints remain on loopback. Unknown ComfyUI workflows/custom nodes can execute code and must be reviewed before use.
- Backup archives contain sensitive data (password hashes, photos, records). Copy and encrypt on user-controlled storage; do not email/upload them casually.
- 18+ assets should be handled only on permitted services and must comply with each platform's policies and labeling rules.
- Third-party repositories are not embedded automatically; licenses, updates and compatibility require review.

## Test evidence

- `python -m pytest -q`: 39 automated backend tests passing in the container used to author this build.
- `node --check web/app.js`: JavaScript syntax check passed.
- `python scripts/smoke_browser.py`: Chromium UI smoke tests at desktop 1365×860 and mobile 390×844 (with mocked API). Both passed, zero runtime JS errors. This is **not** an iOS/Android hardware test.
- Actual ComfyUI/Ollama/faster-whisper model tests on user's AMD PC: not run.
- Optional PyInstaller/Inno Windows build: untested.
