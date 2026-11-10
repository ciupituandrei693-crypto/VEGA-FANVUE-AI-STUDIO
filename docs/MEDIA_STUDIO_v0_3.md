# VEGA Media Studio v0.3 — instrucțiuni locale

## Funcționalități livrate
- Composer imagine: fotografie deja încărcată + titlu + subtitlu → PNG 9:16 (720×1280), 1:1 (1080×1080) sau 16:9 (1280×720).
- Compozitor video: 1–6 fotografii ale **aceluiași model**, fiecare 2, 3 sau 4 secunde → MP4 H.264, 24 fps, **fără audio**, pe CPU cu FFmpeg. Pe vertical se exportă 720×1280.
- Fișierele originale rămân nemodificate. Rezultatele sunt în biblioteca privată locală cu `origin=graphic/slideshow`.
- Fără conturi externe, cheltuieli, rețele sociale, API de publicare sau GPU.

## Instalare / utilizare
1. Pornește `START_VEGA_WINDOWS.bat` pe Windows. Necesită Python 3.12+ și pachetele din `requirements.txt` (inclusiv Pillow).
2. În `Biblioteca media`, încarcă o fotografie JPG/PNG/WebP pentru unul dintre cele 9 modele.
3. În `Media Studio · Local`, selectează același model, fotografia și formatul; introdu titlul și generează imaginea.
4. Pentru MP4, instalează separat un executabil FFmpeg de încredere și adaugă-l în `PATH` sau configurează `VEGA_FFMPEG_PATH` cu calea spre `ffmpeg.exe`.
5. Bifează 1–6 fotografii, selectează durata și compune video. Previzualizează sau descarcă fișierul.

**Atenție:** arhiva `FFmpeg-master.zip` este cod sursă, nu executabil Windows. Nu e necesară pentru exporturile PNG.

## Limite tehnice și de securitate
- Fișiere media maxim 50 MB; raster validat prin decodare, rezoluție maxim 28 milioane pixeli.
- Montaj CPU se poate executa mai lent pe PC-uri mai slabe. Timpul maxim de randare este limitat la 150 de secunde.
- Nu se lansează subtitrări AI, modele de imagini, lip-sync sau clonare voci în v0.3.
- Kill Switch afectează aprobările și programarea postărilor; nu blochează procesarea media locală, care nu publică nimic.
- Doar surse cu drepturi de utilizare. Păstrează datele personale în afara GitHub; nu expune serverul HTTP din rețeaua locală.
