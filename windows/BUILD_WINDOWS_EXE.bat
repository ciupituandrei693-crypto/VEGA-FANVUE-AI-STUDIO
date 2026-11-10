@echo off
setlocal
cd /d "%~dp0\.."
echo [VEGA] This builds a local executable on WINDOWS. Python and PyInstaller are required for BUILD ONLY.
where py >nul 2>&1 || (echo Python not found && pause && exit /b 1)
py -3 -m pip install --upgrade pyinstaller || goto :failed
py -3 -m pip install -r requirements.txt || goto :failed
py -3 -m PyInstaller --clean --noconfirm --onedir --name VEGA --add-data "web;web" --collect-all uvicorn --collect-all fastapi --collect-all starlette --collect-all pydantic --hidden-import vega.main scripts\vega_launcher.py || goto :failed
echo [VEGA] Built: dist\VEGA\VEGA.exe . No ComfyUI/AI models included.
echo [VEGA] Build is NOT validated on a real Windows machine yet.
pause
exit /b 0
:failed
echo Build failed. Inspect output and dependencies.
pause
exit /b 1
