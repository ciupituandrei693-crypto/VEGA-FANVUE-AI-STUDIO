# VEGA — Planul de dezvoltare A–Z

## Implementat până la v0.4
1. Backend local FastAPI + SQLite, cont administrator, nouă modele, bibliotecă media și audit.
2. SEO offline (șabloane), schițe, aprobări, programare exclusiv locală, Kill Switch implicit.
3. Media Studio: grafice locale și MP4 slideshow cu FFmpeg, fără AI.
4. **Generator AI prin ComfyUI local** — adapter T2I și workflow video importat; sarcini, progres și rezultate private. Necesită ComfyUI și modelele instalate separat.
5. **iPhone LAN HTTPS opt-in** — script Windows, certificate locale, PWA, host allowlist și sesiuni autentificate. Nu este încă testat pe iPhone-ul utilizatorului.
6. Teste automate și ghiduri de utilizare; nicio integrare API social.

## Pașii rămași
- Testare reală pe Windows cu ComfyUI și hardware-ul disponibil; alegere de modele/checkpoint-uri compatibile AMD RX 580 sau CPU.
- Test efectiv pe iPhone în aceeași rețea, verificarea instalării profilului TLS și PWA.
- Modul de păstrare a identității celor nouă modele (referințe, LoRA/control, după verificarea drepturilor și costurilor).
- Motor SEO AI local (fără KoboldCpp), voce, lip-sync și subtitrare după audit de compatibilitate.
- Scheduler robust și testele cap-coadă pe un model pilot.
- OAuth autorizat, cu verificare API Fanvue/Instagram/TikTok/X/Reddit și fără YouTube.
- **ULTIMA ETAPĂ:** server extern și GPU cloud, numai cu aprobare expresă a utilizatorului.
