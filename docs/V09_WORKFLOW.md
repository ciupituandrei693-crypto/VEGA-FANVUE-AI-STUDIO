# VEGA v0.9 — operator workflow

## 1. Work locally first
Run `START_VEGA_WINDOWS.bat` with Python 3.12+ and first-run internet for package installation. Open http://127.0.0.1:8765 on Windows; set a 12+ character administrator password. All local data goes into `local_data/`, which is excluded from GitHub. The optional compiled launcher, if built on Windows, stores data under `%LOCALAPPDATA%\\VEGA\\local_data`.

## 2. Set identities (v0.5)
Open **Identitate & personalitate**. Select each model; add original visual preset, negative prompt, editorial persona, voice profile and an optional approved local photo. References cannot be assigned across characters. Use *Pregătește prompt* to copy the settings for ComfyUI. Photo and video AI still require ComfyUI installed separately with compatible models, checkpoints and workflow. No model weights in the repository.

## 3. SEO packs (v0.6)
Open **Pachete SEO AI**. Choose model, platform, topic. Template mode always runs offline. Opt in to **Ollama local** only if you have installed a model and started Ollama at `127.0.0.1:11434`. Optional environment variables: `VEGA_OLLAMA_URL=http://127.0.0.1:11434`, `VEGA_OLLAMA_MODEL=<installed-model-tag>`. The result is a **draft**; it cannot self-approve or publish. Content remains subject to platform review.

## 4. Connectors and approvals (v0.7)
The 5 connector statuses are present, but ALL are `unconfigured`. OAuth credentials and actual publishing are NOT implemented. Draft → review → approval → scheduled_local are necessary. Kill Switch must be disabled before approval; a prepared manual export still never posts. Editing the post invalidates the prepared export. Adult content is managed only for Fanvue, subject to its policies.

## 5. Analytics (v0.8)
Open **Analytics manual**. Record observed daily impressions, clicks, *new subscribers for that day*, gross USD and costs USD. All values are user-entered; reports are not connected to Fanvue. The same model/platform/day overwrites the previous record to avoid duplicates. Gross minus cost is simplified net (before taxes/fees unless user explicitly inputs them as costs).

## 6. Backup and recovery (v0.9)
From the Windows PC only, open **Backup & securitate** → **Creează backup privat**. A ZIP containing a consistent SQLite snapshot plus media is stored in `vega_private_backups` next to `local_data`. Verify checksums in the UI. To recover, **STOP VEGA**, then run in the application directory:

```
python scripts/restore_backup.py "C:\path\to\vega-backup-...zip" --to "C:\VEGA_RESTORE_CLEAN"
python scripts/restore_backup.py "C:\path\to\vega-backup-...zip" --to "C:\VEGA_RESTORE_CLEAN" --confirm
```

The destination must be empty. Inspect the recovered data, then manually move it to your intended VEGA data folder while the application is closed. No live restore route exists.

## 7. iPhone/Android (local Wi-Fi only)
First create the owner on Windows. Use `START_VEGA_IPHONE_HTTPS.bat` to generate a local HTTPS CA and serve on the **PC's private IPv4**. Read `docs/IPHONE_HTTPS_LAN_v0_4.md` for the explicit trust steps. Only trust a CA that you generated and can verify. Use Safari *Add to Home Screen* or Android browser's equivalent. Actual phone hardware security testing is pending; DO NOT forward the port outside your LAN.

## 8. Optional audio captions
Install `faster-whisper` on PC if desired and point `VEGA_WHISPER_MODEL_PATH` to a model **already downloaded and reviewed**. The backend uses CPU int8 and never auto-downloads weights. The API `/api/media/{id}/transcribe` works on private MP4 files only and is optional; voice synthesis and lip-sync are not yet implemented.

## 9. Optional Windows build
`windows/BUILD_WINDOWS_EXE.bat` prepares a native one-folder app with PyInstaller on Windows. The optional `windows/VEGA.iss` builds an installer when Inno Setup is installed and the PyInstaller build has succeeded. Neither is prebuilt here; verify the output on your own Windows machine before considering a distributable release.

**Explicitly not included:** online publishing; live social analytics; device push notifications; real-time trend research; trained identity-preserving image pipelines; native mobile apps; server/GPU cloud deployment. They are separate gated integrations; no paid services are authorized.
