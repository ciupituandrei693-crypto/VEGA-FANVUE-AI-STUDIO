@echo off
setlocal
cd /d "%~dp0"
set "VEGA_WHISPER_MODEL_PATH=%~dp0local_models\whisper-tiny"
if exist "%~dp0tools\ComfyUI\.venv\Scripts\python.exe" (
 echo [VEGA] Pornesc ComfyUI CPU pe localhost:8188
 start "VEGA ComfyUI CPU" /D "%~dp0tools\ComfyUI" "%~dp0tools\ComfyUI\.venv\Scripts\python.exe" main.py --cpu --listen 127.0.0.1 --port 8188
) else (
 echo [VEGA] ComfyUI CPU lipseste. Instaleaza cu INSTALL_ALL_WINDOWS.bat.
)
echo [VEGA] Ollama, daca exista, isi gestioneaza singur serviciul Windows.
call "%~dp0START_VEGA_WINDOWS.bat"
