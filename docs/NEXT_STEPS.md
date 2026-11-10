# VEGA — Planul de dezvoltare A–Z

## Implementat în v0.3
1. Backend FastAPI securizat minimal: cont local, scrypt, sesiuni expirabile, SQLite.
2. Cele 9 profiluri separate și interfață responsivă pentru desktop și mobile.
3. SEO Studio cu șabloane, schițe, aprobări și programare locală.
4. Kill Switch, jurnal de audit și export JSON local.
5. Media Vault și bazele PWA (manifest, iconuri).
6. Teste automate API și verificare în browser.
7. **Media Studio v0.3**: grafice 9:16/1:1/16:9 din fotografii încărcate și montaj slideshow MP4 cu FFmpeg, CPU local; 15 teste automate și migrare SQLite v0.2.

## De realizat, în ordine
7. **v0.4 — test real Windows/iOS**: instalator desktop opțional, HTTPS LAN securizat sau tunel privat, test iPhone Safari, PWA offline pentru asseturi publice, backup criptat, recuperare administrare.
8. **v0.5 — Media Production AI local (candidat)**: la v0.3 există deja compoziție Pillow și slideshow FFmpeg; în continuare testăm HyperFrames, voce și generare AI compatibilă; generare foto prin soluția hardware compatibilă (nu presupunem GPU AMD RX 580 compatibil cu orice model); VoiceStudio și LatentSync ca module opționale după audit.
9. **v0.6 — SEO AI real**: alegem un alt model local compatibil Windows (KoboldCpp indisponibil); instrumente Instagram/TikTok/X; bibliotecă personalități, control drepturi și etichetare AI; management campanii organice fără spam.
10. **v0.7 — Scheduler persistent**: worker local cu jurnal, coadă, retry, verificare aprobări la execuție și întrerupere imediată la Kill Switch. Inițial operații simulate.
11. **v0.8 — Account Control Center**: implementări OAuth autorizate individual, vault criptat pentru tokenuri, permisiuni restrânse, revocare și audit. Verificăm API-ul oficial Fanvue, Meta, TikTok, X și Reddit la data integrării.
12. **v0.9 — Pilot**: un singur model, test cap-coadă în mediu de test sau manual, aprobare, publicare exclusiv dacă permisă de API și disponibilă în cont.
13. **v0.10 — Extindere la 9 modele**: separarea completă pe cont, calendar, fișier, mesaje și rate-limit, după condițiile Fanvue și validarea pilotului.
14. **v1.0 — LAST**: abia după testele locale, server extern 24/7, GPU cloud plătit cu control cheltuieli, alerte iOS și mecanisme de rollback/backup. Nicio cheltuială fără aprobare.

## Cerințe permanente
- Fără YouTube.
- Cele nouă modele sunt aprobate; nu substituim fețele fără permisiune.
- Nivel 2: doar materialele aprobate pot fi programate/publicate; editarea anulează aprobarea.
- Nu începem automat reclame plătite, servicii cloud sau generare costisitoare.
- Secretele și materialele personale nu se publică în repository-ul public.
