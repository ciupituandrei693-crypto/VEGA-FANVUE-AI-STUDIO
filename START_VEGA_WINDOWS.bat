@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
 set "PYTHON=py -3"
) else (
 set "PYTHON=python"
)
if not exist ".venv\Scripts\python.exe" (
 echo [VEGA] Creating local environment...
 %PYTHON% -m venv .venv || goto :fail
)
echo [VEGA] Installing/updating free dependencies...
 ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
echo [VEGA] Open http://127.0.0.1:8765 in browser
start "" "http://127.0.0.1:8765"
".venv\Scripts\python.exe" -m uvicorn vega.main:app --host 127.0.0.1 --port 8765
exit /b %errorlevel%
:fail
echo Could not start VEGA. Check Python and connection.
pause
exit /b 1
