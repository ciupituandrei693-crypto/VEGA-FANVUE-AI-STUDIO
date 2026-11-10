# VEGA — instalarea componentelor locale pe Windows

## Ce este acest pachet

Este VEGA v0.9 împreună cu un **instalator local** pentru dependențele principale. Nu este un Windows `.exe` complet autonom, nici o instalare realizată deja pe calculatorul tău. Descărcarea din internet se face doar **când rulezi tu** scriptul pe PC-ul propriu. Scripturile pot fi citite înainte de execuție.

### Cum îl folosești

1. Fă backup pentru folderul VEGA anterior, în special `local_data`, dacă există. **Nu copia baza de date în repository public.**
2. Extrage arhiva în `C:\VEGA`. Evită `Program Files` (permisiuni). Nu șterge sau suprascrie propriul `local_data` înainte de backup.
3. Dublu-click pe `INSTALL_ALL_WINDOWS.bat`; examinează textul și confirmă cu `INSTALARE`. Pentru modelul Qwen local, confirmă separat `DA`. Toate pachetele sunt gratuite, dar necesită internet și spațiu pe disc.
4. După instalare, rulează `VERIFY_ALL_WINDOWS.bat`. Raportul este salvat în `local_data/vega_install_report.json`.
5. Pornește `START_VEGA_FULL_WINDOWS.bat`: VEGA pe `127.0.0.1:8765`; ComfyUI în mod CPU pe `127.0.0.1:8188`, dacă a fost instalat. Ollama este instalat separat și servește, când este pornit, pe `127.0.0.1:11434`.
6. Pentru iPhone, după ce creezi administratorul pe PC, folosește `START_VEGA_IPHONE_HTTPS.bat` și consultă `docs/IPHONE_HTTPS_LAN_v0_4.md`. Certificatele trebuie verificate și instalate manual pe telefon. Nu expune porturile în internet.

### Ce încearcă să instaleze automat

| Componentă | Metodă | Observații |
|---|---|---|
| Python 3.12 | winget dacă lipsește | mediu separat `.venv` |
| VEGA, HTTPS, PWA | pip din `requirements.txt` și `requirements-lan.txt` | local |
| FFmpeg | winget Gyan.FFmpeg | doar pe PC |
| Git | winget Git.Git | pentru surse oficiale |
| Ollama | winget Ollama.Ollama | fără API cloud |
| Model text mic Qwen 3 0.6B | `ollama pull qwen3:0.6b`, cu confirmare separată | gratuit, descărcare online, inferență locală |
| ComfyUI | GitHub oficial, Python venv separat, PyTorch CPU | nu include checkpoint-uri; generarea poate fi foarte lentă |
| ComfyUI-Manager | GitHub oficial, în `custom_nodes` | nu instala extensii necunoscute |
| faster-whisper | pip în `.venv` VEGA | CPU; un model de transcriere trebuie descărcat înainte de folosire |

### Ce NU poate fi finalizat într-un singur click pe configurația AMD RX 580

- **VoiceStudio:** există o versiune Windows, însă instalarea programului și alegerea vocilor/modelelor necesită controlul tău. Descarcă numai de la https://github.com/debpalash/VoiceStudio/releases/latest. Nu executăm automat scripturi PowerShell descărcate necunoscute.
- **Chatterbox:** proiect de cercetare arhivat/neîntreținut în august 2026; integrarea TTS reală necesită testarea compatibilității CPU.
- **LatentSync:** 1.6 necesită minim 18 GB VRAM, incompatibil cu RX 580 8 GB. Versiunea 1.5 cere 8 GB VRAM, dar baza originală depinde de CUDA și hardware compatibil; nu garantăm că va rula pe Windows cu RX 580.
- **ComfyUI generare foto/video reală:** frameworkul poate fi instalat, dar checkpointurile și workflowurile trebuie selectate și descărcate separat, respectând licențele lor. PyTorch CPU este mult mai lent decât GPU, iar RX 580 nu este garantat pentru ROCm Windows.
- **iPhone:** pentru accesul prin Wi-Fi și HTTPS trebuie să aprobi manual certificatul pe telefon.
- **API-uri sociale și Fanvue:** nu avem și nu instalăm automat tokenuri OAuth, conexiuni la conturi sau publicare. Se configurează numai cu permisiuni explicite și respectarea politicilor platformelor.
- **Cloud:** neactivat, fără server și fără costuri.

### Securitate

Codul terț este descărcat numai de la surse oficiale, dar software-ul instalat din GitHub, PyPI sau winget trebuie tratat ca o dependență externă care poate primi actualizări. Scriptul **nu** rulează comenzi de forma `irm URL | iex`, **nu** configurează forwarding public și **nu** instalează automat modele de persoane, voci clonabile sau noduri ComfyUI din surse necunoscute.

Instalarea pe PC-ul tău nu a fost executată/verificată de ChatGPT; acest pachet este pregătit și validat static în mediul de lucru. Urmărește rezultatele generate de `VERIFY_ALL_WINDOWS.bat` pentru a determina ce s-a instalat efectiv.

Surse: https://github.com/Comfy-Org/ComfyUI · https://github.com/ltdrdata/ComfyUI-Manager · https://github.com/ollama/ollama · https://github.com/SYSTRAN/faster-whisper · https://github.com/resemble-ai/chatterbox · https://github.com/bytedance/LatentSync · https://github.com/debpalash/VoiceStudio
