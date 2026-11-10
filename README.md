# ♛ VEGA UNIVERSAL — FANVUE AI STUDIO

**Version: v0.9.0-dev (stages 5–9 implementation package, local-first).**

**Important:** This is a functional local development release, **not** an end-to-end completed production system. Features requiring external provider authorization, actual AI weights or physical-device validation are clearly identified as pending. No social publishing, payments, cloud GPU or external server use. Repository is public: no private media/credentials are included.

## What is implemented

| Area | Available functionality |
|---|---|
| Existing v0.2–v0.4 | 9 models, authentication, posts/drafts, approvals, Kill Switch, editorial calendar, media library, FFmpeg slideshows, ComfyUI local adapter, opt-in HTTPS LAN/PWA |
| v0.5 | Model-specific visual/persona/voice presets and reference-image ownership checks; editable ComfyUI prompt builder; Ollama loopback model detection; optional CPU-only faster-whisper API |
| v0.6 | SEO packs via offline templates or explicit local Ollama model, audit, no self-approval |
| v0.7 | Fanvue, Instagram, TikTok, X, Reddit connector registry plus auditable **manual-only** delivery bundles, invalidated after post edit |
| v0.8 | User-entered daily impressions, clicks, subscribers, gross/cost USD, by-model totals and simplified net |
| v0.9 | Hash-verified SQLite+media backups, offline restore CLI (empty directory only), security status, desktop/mobile PWA view, optional Windows build scripts |

**Not implemented / not validated:** OAuth provider integrations and automatic posting, Fanvue revenue API, live SEO trends, Chatterbox/VoiceStudio TTS/lip-sync, actual image-generation benchmark on user's AMD graphics card, actual iPhone/Android hardware tests, a prebuilt Windows installer. See [acceptance matrix](docs/V09_ACCEPTANCE_MATRIX.md).

## Quick start — Windows

1. Install Python 3.12+ from [python.org](https://www.python.org/downloads/windows/) and enable PATH.
2. Unzip to `C:\VEGA`. Run `START_VEGA_WINDOWS.bat`. First run creates `.venv` and installs free Python packages, which requires internet on that first run.
3. Browse to **http://127.0.0.1:8765** on the PC. Create a local admin with a 12+ character password. No default password exists.
4. Create private media and presets. To use image/video AI, install compatible ComfyUI and models **separately**; for local text AI, install Ollama and a compatible language model **separately**.
5. To reach your iPhone on the same trusted Wi-Fi, use `START_VEGA_IPHONE_HTTPS.bat` and [local HTTPS instructions](docs/IPHONE_HTTPS_LAN_v0_4.md), **only after PC admin setup**.

For manual development:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn vega.main:app --host 127.0.0.1 --port 8765
```

### Optional add-ons (not included)

- **ComfyUI:** `http://127.0.0.1:8188`, original v0.4 API connector; image checkpoints and video workflows need installation and testing.
- **Ollama:** `http://127.0.0.1:11434`; install local model before using AI draft mode. No external URL is permitted.
- **FFmpeg:** required for video slideshows on CPU.
- **faster-whisper:** only if manually installed, with `VEGA_WHISPER_MODEL_PATH` pointing to an existing local model directory. No automatic model downloads.
- Windows build recipes in `windows/` are optional and have not yet been tested on actual Windows.

## Docs and tests

- [Operator workflow](docs/V09_WORKFLOW.md)
- [Acceptance and security matrix](docs/V09_ACCEPTANCE_MATRIX.md)
- [AI image/video setup](docs/AI_GENERATOR_v0_4.md)
- [iPhone HTTPS](docs/IPHONE_HTTPS_LAN_v0_4.md)
- [Media Studio](docs/MEDIA_STUDIO_v0_3.md)

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
node --check web/app.js
```

Baseline + new tests: **39 passed** in the authoring container. Optional Chromium desktop + mobile viewport smoke tests used mocked API data and passed; **not physical iOS/Android tests**.

## Protect private data

Private database, media and AI models are **never** part of this public repository. Backups go to a separate private directory. Preserve copies and test restoration only with VEGA stopped. The repository `.gitignore` intentionally excludes `.env`, `local_data/`, backups, credentials and compressed archives. Do not upload Fanvue passwords, tokens, KYC records or private photographs.

**Safety and scope:** Only original fictional adult AI identities and user-licensed assets; respect platform rules, local laws and disclosure requirements. **No YouTube. No KoboldCpp.** All AI and moderation decisions are supervised. Cloud/server infrastructure remains last-stage and only after explicit spending approval.
