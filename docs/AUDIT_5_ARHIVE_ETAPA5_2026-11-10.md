# VEGA — Audit preliminar al celor 5 arhive pentru etapa 5

Data evaluării: 10 noiembrie 2026. Analiză **statică** a fișierelor ZIP, fără instalare/executare, fără conectare GPU/cloud.

## Integritate și inventar

| Arhivă | Fișiere ZIP | Mărime ZIP (MiB) | Extrase (MiB) | Test CRC | Căi periculoase |
|---|---:|---:|---:|---|---|
| `ComfyUI-master(2).zip` | 1558 | 12.98 | 47.58 | OK | Nu au fost găsite |
| `ComfyUI-Manager-main.zip` | 151 | 2.42 | 12.82 | OK | Nu au fost găsite |
| `ollama-main(1).zip` | 1835 | 26.58 | 48.16 | OK | Nu au fost găsite |
| `chatterbox-master(2).zip` | 82 | 1.40 | 1.78 | OK | Nu au fost găsite |
| `faster-whisper-master(2).zip` | 49 | 20.40 | 22.74 | OK | Nu au fost găsite |

Toate arhivele au CRC valid, fără căi absolute/traversare de directoare sau symlink-uri suspecte detectate de acest control. Aceasta NU garantează absența codului malițios, vulnerabilităților sau incompatibilităților.

## Componente și decizia de integrare

| Componentă | Versiune din surse | Licență din arhivă | Utilizare în VEGA |
|---|---|---|---|
| ComfyUI | 0.44.0 | GPL-3.0 | Conector generare imagine/video; depozit de surse, nu include checkpoint; backend GPU pe RX 580 de validat. |
| ComfyUI-Manager | 3.42 | GPL-3.0 | Opțional, doar în instalarea ComfyUI locală; poate instala/extinde cod terț. |
| Ollama | sursă Go, go.mod 1.26.10 | MIT | Motor conversațional/SEO local; mai simplu instalator oficial decât compilare; RX 580 fără suport oficial ROCm Windows, posibil Vulkan/CPU. |
| Chatterbox TTS | 0.1.7 | MIT | Sinteză vocală; Nano/CPU de testat, proiect declarat arhivat fără mentenanță din august 2026; dependență Git nefixată pentru Perth. |
| faster-whisper | 1.2.1 | MIT | Transcriere/subtitrări; CPU INT8 recomandat inițial; GPU CUDA recomandat oficial în README. |

## Limitări importante

- Arhivele conțin în principal **cod sursă**, nu aplicații instalate și nu toate greutățile modelelor AI. `faster-whisper` include doar un model auxiliar VAD ONNX. Modelele foto/video, vocile și modelele LLM trebuie achiziționate/descărcate separat cu verificarea licențelor și mărimilor.
- ComfyUI și ComfyUI-Manager sunt GPL-3.0: preferabil să ruleze separat și să fie apelate prin API local; consultăm obligațiile de distribuție la orice redistribuire. Nu copiem sursele lor integral în repository-ul public VEGA.
- Manager poate instala noduri și dependențe terțe care execută cod. Începem fără auto-instalare și activăm doar extensii auditate.
- Ollama folosește MIT; instalarea oficială precompilată este preferabilă încercării de a compila din sursa ZIP (`go.mod` solicită Go 1.26.10).
- Chatterbox este proiect de cercetare **retras și nemaiîntreținut**, anunț confirmat pe pagina oficială a repository-ului. Conține dependență `resemble-perth @ git+...@master`; pentru reproductibilitate, versiunea trebuie fixată dacă îl folosim.
- faster-whisper poate rula CPU `int8`; documentația din arhivă descrie GPU pe NVIDIA/CUDA. Pentru AMD există experimentări HIP comunitare, dar nu le activăm ca soluție implicită.
- Pentru Windows cu **Radeon RX 580 8 GB și 16 GB RAM**, suportul ROCm official Ollama nu enumeră RX 580; Vulkan poate fi încercat cu un model mic, iar ComfyUI pe această generație nu este garantat. Preferăm test de resurse mic și fallback CPU.
- Interfața VEGA pe iPhone trebuie să comunice numai cu backendul securizat VEGA. Serviciile interne ComfyUI/Ollama/Manager trebuie să rămână pe `127.0.0.1`, fără acces direct din rețea sau pe internet.
- Generarea de voce cu timbru de persoană reală necesită drepturi și consimțământ; mediile cu modele virtuale au obligații separate de divulgare/etichetare.

## Plan propus, fără instalări încă

1. Test de conectivitate cu servicii simulate (mock) pentru ComfyUI și Ollama, fără instalare pe PC și fără GPU.
2. În Windows: Ollama oficial + model mic, prioritar CPU sau Vulkan doar dacă driverul permite, port 11434 local.
3. ComfyUI separat cu checkpoint mic, la început un singur job, limită resurse și jurnal. Manager doar când chiar avem nevoie de noduri suplimentare.
4. Subtitrări cu faster-whisper CPU INT8 model `tiny` sau `base`; voce Chatterbox Nano doar după verificarea instalării și licenței ponderilor.
5. Prezentarea rezultatelor pe dashboard/iPhone cu joburi, aprobări, status și Kill Switch. Fără publicare automată.

## Amprente SHA-256

- `ComfyUI-master(2).zip`: `72fef03652f5697272ed8a90ca76f30d301bb618920e9aa8b2ae37124b32dff4`
- `ComfyUI-Manager-main.zip`: `8dde05c8bdbfaea5f7f36a397361bd13d8a0e92346ecd4a22e2dffee26f159f9`
- `ollama-main(1).zip`: `946bb5b17f2c542bc6fddf4a7535c4c15fa7012e33ae36e4debd1c2c24cf9fdc`
- `chatterbox-master(2).zip`: `785c4990ae6dd023eeb54161bfd3cd39a12d5ba9c74a04a7b7ab4d632d6f1c3f`
- `faster-whisper-master(2).zip`: `7ac138cb7e5773ce6615625d6fa3695f16187f7003183dd9a6f94e852a6d7807`

## Surse publice de verificare

- https://github.com/comfyanonymous/ComfyUI
- https://github.com/ltdrdata/ComfyUI-Manager
- https://github.com/ollama/ollama
- https://github.com/resemble-ai/chatterbox
- https://github.com/SYSTRAN/faster-whisper
- https://docs.ollama.com/gpu

**Statut: arhive verificate la nivel ZIP și evaluate static; integrarea efectivă și testele hardware sunt în așteptare.**