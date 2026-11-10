@echo off
setlocal
cd /d "%~dp0"
echo.
echo  ===== VEGA UNIVERSAL - INSTALARE LOCALA WINDOWS =====
echo  Verificare si instalare componente suportate. Nu foloseste GPU cloud.
echo  Necesita internet pentru pachete oficiale si suficient spatiu liber.
echo.
echo  Windows va cere aprobarea ta inainte de eventuale instalari.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Install-VEGAComponents.ps1" -DownloadSmallModel
if errorlevel 1 (
 echo.
 echo Unele componente nu au fost instalate. Consulta raportul din local_data.
) else (
 echo.
 echo Instalarea componentelor suportate s-a incheiat. Verifica raportul.
)
echo.
pause
