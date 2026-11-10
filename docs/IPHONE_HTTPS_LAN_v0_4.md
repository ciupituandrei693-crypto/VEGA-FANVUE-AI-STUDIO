# VEGA v0.4 — Acces securizat de pe iPhone (LAN HTTPS, fără server extern)

## Ce este implementat
- Server FastAPI + interfață PWA responsive pe IP-ul PC-ului din rețeaua privată, **HTTPS pe portul 8766**.
- TLS cu CA locală generată automat, certificat SAN pentru IP-ul LAN; **cheia CA nu este scrisă pe disc**, cheia serverului rămâne în `local_data/lan_certs/` exclusă din GitHub.
- Host header limitat la IP-ul LAN configurat / localhost; cereri HTTP fără TLS respinse în mod LAN.
- API privat protejat de autentificare cu sesiuni expirabile și limită de încercări login.
- Crearea primului administrator permisă doar de pe PC (`localhost`), nu de pe iPhone.
- PWA cu manifest și service worker pentru **doar fișierele UI publice**. API-ul, portretele, tokenurile și videoclipurile private **nu sunt cache-uite**.

## Pași Windows / iPhone
1. **Pe PC:** pornește `START_VEGA_WINDOWS.bat`, deschide `http://127.0.0.1:8765` și creează contul administrator cu parolă de minimum 12 caractere. Închide aplicația locală sau las-o pornită dacă dorești; pentru iPhone pornește și serviciul HTTPS separat.
2. În Windows, deschide `cmd`, rulează `ipconfig` și notează **IPv4** al adaptorului Wi-Fi/Ethernet conectat la rețeaua telefonului, de exemplu `192.168.1.25`.
3. Dublu-click pe **`START_VEGA_IPHONE_HTTPS.bat`** și introdu IP-ul. Scriptul instalează dependențele locale gratuite și generează certificatele; serverul ascultă **doar pe IP-ul privat**, pe portul 8766.
4. Dacă Windows Firewall întreabă, permite doar **Private networks**. Nu configura router port-forwarding, DMZ sau IP public.
5. Din folderul `local_data/lan_certs/`, transferă **`VEGA-CA.cer`** prin AirDrop sau alt transfer privat către iPhone. **Nu transfera `vega-server.key`, niciodată**.
6. Pe iPhone instalează profilul de certificat în **Settings → Profile Downloaded** (sau **General → VPN & Device Management**). Apoi activează încrederea în **Settings → General → About → Certificate Trust Settings → Enable full trust for root certificates**. Conform Apple, aceasta este o acțiune manuală distinctă.
7. Cu iPhone și PC pe **aceeași rețea Wi‑Fi**, deschide Safari la `https://IP-UL-PC:8766`, autentifică-te, apoi **Share → Add to Home Screen** pentru pictograma VEGA.

## Riscuri și limitări
- **Instalarea unei CA root mărește încrederea acordată acelui certificat pe iPhone**. Folosește această soluție numai pe propriile dispozitive și numai după verificarea amprentei certificatului. Șterge profilul CA din iPhone atunci când nu mai ai nevoie de acces. Dacă suspectezi compromiterea PC-ului, revocă imediat încrederea și regenerează certificatele.
- Dacă IP-ul PC-ului se schimbă, certificatul nu mai corespunde. Șterge manual `local_data/lan_certs/`, generează alt certificat și reinstalează CA pe iPhone (după eliminarea celei vechi).
- Nu deschide aplicația prin HTTP în rețeaua locală, nu accepta avertismente de certificat și nu dezactiva verificarea TLS. În modul LAN aplicația refuză HTTP.
- PWA **nu funcționează integral offline**; datele și motorul AI rămân pe PC, care trebuie să fie pornit. Pe rețelele de oaspeți, izolarea clienților Wi-Fi poate bloca conexiunea.
- **Nu am testat pe iPhone-ul utilizatorului**: au fost verificate certificatele și interfețele/protocolul în laborator; este nevoie de test efectiv pe dispozitiv.
- Portul 8766 rămâne numai LAN, fără server extern și fără GPU cloud.

Documentație oficială Apple despre încrederea certificatelor: https://support.apple.com/en-us/102390
