@echo off
setlocal
cd /d "%~dp0"
echo === VEGA — iPhone HTTPS local, fara cloud ===
echo Mai intai configureaza administratorul din START_VEGA_WINDOWS.bat pe acelasi PC.
echo Deschide ipconfig intr-o alta fereastra si copiaza IPv4-ul placii conectate la Wi-Fi.
set /p "VEGA_LAN_IP=Adresa IPv4 privata PC (ex. 192.168.1.25): "
if "%VEGA_LAN_IP%"=="" goto :fail
where py >nul 2>&1
if %errorlevel%==0 (set "PYTHON=py -3") else (set "PYTHON=python")
if not exist ".venv\Scripts\python.exe" (
 %PYTHON% -m venv .venv || goto :fail
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt -r requirements-lan.txt || goto :fail
".venv\Scripts\python.exe" scripts\create_lan_cert.py "%VEGA_LAN_IP%" || goto :fail
".venv\Scripts\python.exe" scripts\verify_admin.py || goto :fail
set "VEGA_LAN_MODE=1"
echo Pornire securizata doar pe IP-ul local %VEGA_LAN_IP%:8766
echo Nu deschide port forwarding in router. Accepta firewall doar in reteaua privata.
".venv\Scripts\python.exe" -m uvicorn vega.main:app --host %VEGA_LAN_IP% --port 8766 --ssl-keyfile "local_data\lan_certs\vega-server.key" --ssl-certfile "local_data\lan_certs\vega-server.crt"
exit /b %errorlevel%
:fail
echo Pornirea a esuat. Verifica IP-ul local, Python si parola administratorului.
pause
exit /b 1
