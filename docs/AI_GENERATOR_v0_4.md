# VEGA v0.4 — Generare foto/video AI (local, ComfyUI)

## Ce este implementat
- Adapter HTTP **fixat la `127.0.0.1:8188`**. Nu poate fi redirecționat prin interfață spre cloud sau spre un IP arbitrar.
- Fotografii noi: workflow ComfyUI standard `CheckpointLoaderSimple`, text encoder, sampler, VAE, SaveImage; **512 × 768** implicit, 16 pași. Checkpoint-ul trebuie instalat de utilizator.
- Videoclipuri: import **workflow API-format JSON** exportat din ComfyUI cu un model video existent. Înlocuire text pozitiv `__VEGA_PROMPT__` (sau primul `CLIPTextEncode`); `__VEGA_NEGATIVE__` opțional; `__VEGA_IMAGE__` sau `LoadImage` pentru fotografie de referință. Rezultatele MP4/WebM sunt salvate în biblioteca privată.
- Joburi cu `queued`, `complete`, `failed` și verificarea manuală a progresului. Nicio postare pe social media.
- Separare pe cele nouă modele și verificare de identitate pentru fotografia-sursă.

## Limite reale
- VEGA **nu include ComfyUI, checkpoint-uri ori modele video**. Trebuie instalate separat pe PC. Verificarea implementării s-a făcut cu teste simulate, nu cu un checkpoint generativ pe hardware-ul utilizatorului.
- GPU AMD RX 580 8 GB nu garantează compatibilitate sau performanță ComfyUI. Pentru rulare poate fi necesar modul CPU, lent, ori alte adaptoare compatibile, de evaluat separat. Nu instalăm GPU cloud acum.
- T2I simplu **nu păstrează fața** modelelor la fel ca un workflow cu referințe și control de identitate. Video I2V necesită model și workflow corespunzător. Un workflow necunoscut sau cu custom nodes poate executa cod: importă numai ceea ce ai verificat.
- Nu există auto-download sau auto-install de modele; spațiul pe disc și memoria sunt responsabilitatea utilizatorului.
- Respectă drepturile asupra fotografiilor, vocii și identităților; marchează materialele generate AI și verifică politica platformei pentru conținutul distribuit.

## Procedură de utilizare
1. Pe PC pornește un **ComfyUI local** cu API la `http://127.0.0.1:8188`. Nu îl expune în rețeaua locală și nu activa `--listen 0.0.0.0` pentru ComfyUI.
2. Instalează un checkpoint compatibil în ComfyUI. Deschide VEGA → **Generator Foto / Video AI** → verifică statusul și lista de checkpoint-uri.
3. Selectează unul dintre cele nouă modele și scrie promptul. Pentru imagine alege „Fotografie AI”, apoi „Trimite generarea”; verifică progresul.
4. Pentru video importă un workflow video compatibil, exportat **în format API** din ComfyUI. Introdu un placeholder `__VEGA_PROMPT__` și opțional `__VEGA_IMAGE__` în graph. Selectează video și, opțional, o fotografie-sursă din biblioteca aceluiași model.
5. Rezultatele devin fișiere private în `local_data/media`, nu sunt publicate și nu sunt sincronizate în GitHub.

Workflow-uri publice ComfyUI: https://github.com/Comfy-Org/workflow_templates (verifică modelele cerute și resursele PC).
Documentație API: https://docs.comfy.org/development/comfyui-server/comms_routes
