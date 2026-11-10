# ♛ VEGA UNIVERSAL — FANVUE AI STUDIO

**Versiune:** `v0.2.0` — MVP executabil **local-first**, cu autentificare și teste automate.

> **Acesta nu este produsul complet A–Z.** Este prima versiune de aplicație funcțională, pe care o vom extinde etapizat. Nu sunt conectate conturi, servere externe, GPU cloud și niciun API social. Nu publică pe internet.

## Ce funcționează în această versiune

- **Dashboard universal** responsiv pentru Windows și ecrane de telefon; PWA cu manifest și icon.
- **9 profiluri AI**: Aria Vale, Maya Solis, Elena Hart, Nova Quinn, Selene Voss, Claudia Rose, Irina Sky, Liora Maren, Evelyn Frost.
- **Login local** cu parolă hash-uită scrypt, sesiuni temporare și autentificare obligatorie pentru API și fișierele media.
- **SEO Studio offline**: 3 hook-uri, descriere, hashtaguri și CTA pentru Instagram, TikTok, X, Reddit și Fanvue. În acest MVP sunt șabloane, *nu un model AI generativ și nu cercetare live de trenduri*.
- **Schițe și aprobări**: `draft → in_review → approved → scheduled_local`. Salvarea unei modificări anulează aprobarea și data programată.
- **Kill Switch**, activ la prima pornire, care blochează aprobarea și programarea.
- **Calendar local**, doar în baza de date; nimic nu este transmis către platforme.
- **Bibliotecă media privată** JPG/PNG/WebP/MP4, maxim 50 MB/fișier, cu verificare de semnătură minimală și descărcare autentificată.
- **Jurnal de audit**, export JSON al materialelor aprobate.
- **Regulă conținut 18+**: clasificarea 18+ este permisă doar în schițele Fanvue; drepturile asupra materialului și etichetarea AI trebuie confirmate înainte de aprobare.
- **Fără YouTube, fără KoboldCpp**, fără autentificări Fanvue/Meta/TikTok/X/Reddit, fără plăți sau generare foto/video.

## Pornește în Windows

1. Instalează Python 3.12+ de la https://www.python.org/downloads/windows/ și activează `Add python.exe to PATH`.
2. Descarcă pachetul ZIP **VEGA_UNIVERSAL_DEV_v0_2.zip** din conversație sau clonează repository-ul GitHub.
3. Dezarhivează într-un folder personal, de exemplu `C:\VEGA` (nu în `Program Files`).
4. Dublu-click pe **`START_VEGA_WINDOWS.bat`**. Scriptul creează un mediu virtual în `.venv` și instalează dependențele gratuite cu `pip`. *Pentru prima instalare este necesar internet pentru Python packages; aplicația, după instalare, nu face cereri către API-uri externe.*
5. Deschide http://127.0.0.1:8765 pe **același PC**. Creează administratorul local, cu parolă de minimum 12 caractere. Nu există parolă implicită.
6. Dezactivează Kill Switch doar când dorești să aprobi/programmezi materialele. **Această acțiune nu pornește nicio publicare online.**

Poți rula și manual:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn vega.main:app --host 127.0.0.1 --port 8765
```

## Date private și backup

- Baza SQLite se creează la `local_data/vega.sqlite3`.
- Fișierele încărcate se salvează în `local_data/media/`.
- Acest director este exclus din GitHub. **Nu publica fișierele `local_data`, copii ale bazelor de date sau portrete private într-un repository public.**
- Pentru backup închide aplicația și copiază întregul director `local_data` pe o unitate securizată.
- Sesiunile expiră după 12 ore. Nu există încă recuperare automată a parolei; păstrează parola într-un manager de parole.

## iPhone / Android

Designul este adaptabil și există manifest PWA, însă **accesul de pe telefon nu este activat încă**: serverul este legat deliberat la `127.0.0.1`, accesibil numai PC-ului local. Pentru iOS va urma o etapă cu TLS/HTTPS, autentificare testată și acces securizat între dispozitive (fără expunere neprotejată de port și fără a configura încă serverul extern). Adăugarea pe Home Screen și testele iOS reale nu au fost finalizate.

## Teste

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

În mediul de dezvoltare au trecut **11 teste automate**. Acestea nu înlocuiesc un audit de securitate independent sau testarea iOS/Windows pe echipamente reale.

## Arhitectură

- `vega/main.py`: API FastAPI, aprobare, calendar, upload, audit, autentificare și Kill Switch.
- `vega/store.py`: SQLite, schema locală, modelele și jurnalul.
- `vega/security.py`: hash scrypt, sesiuni Bearer expirabile.
- `vega/seo.py`: propuneri SEO strict offline, prin șabloane.
- `web/`: interfață responsive fără build Node, manifest PWA și iconuri.
- `tests/`: teste de integrare API.
- `docs/`: planul etapelor următoare și limitele aplicației.

Când trecem la producție, analizăm și integrăm controlat bibliotecile trimise: FastAPI, Next.js, Postiz, n8n, Instagram Agent Skill, Claude Content Skills, HyperFrames, FFmpeg, VoiceStudio, LatentSync. **Nu sunt instalate sau incluse în v0.2, cu excepția FastAPI ca dependență Python.** KoboldCpp a fost eliminat conform cerinței.

## Limite și condiții de siguranță

- Nu există rută API care publică la servicii externe.
- Lipsesc conectorii OAuth oficiali, notificările Push, editarea video AI, programatorul care execută joburi reale, fluxurile de generare AI și sistemul de plăți.
- Nu expune serverul din această versiune direct pe internet sau pe Wi‑Fi public. API-ul este local, fără protecții avansate pentru producție.
- Folosește numai personaje și materiale asupra cărora ai drepturile necesare, indică faptul că personajele sunt generate AI și respectă KYC și politicile platformelor.
- Înainte de integrarea oricărui repository terț, verificăm licențele, securitatea și compatibilitatea hardware.
- Serverul extern (~25 USD/lună) și GPU-ul cloud (plafon 50 USD/lună) rămân **strict ultimele etape și necesită aprobare explicită**.

Vezi [Planul v0.3 și etapele A–Z](docs/NEXT_STEPS.md).
