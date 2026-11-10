# VEGA local Windows installer. Runs only after user double-clicks INSTALL_ALL_WINDOWS.bat.
# Does not install a cloud service, connect social accounts, or execute downloaded remote scripts.
[CmdletBinding()]
param(
    [switch]$DownloadSmallModel,
    [switch]$SkipComfyUI,
    [switch]$SkipOllama,
    [switch]$SkipWhisper,
    [switch]$SkipVoiceStudio
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
$data = Join-Path $root 'local_data'
New-Item -ItemType Directory -Force -Path $data | Out-Null
$report = [ordered]@{timestamp=(Get-Date -Format 's'); mode='Windows local CPU-first'; steps=[ordered]@{}; warnings=@()}
function Status([string]$step, [string]$value, [string]$details='') {
    $report.steps[$step] = @{status=$value; details=$details}
    $tag = if ($value -eq 'OK') {'[OK]'} elseif ($value -eq 'SKIP') {'[SKIP]'} else {'[WARN]'}
    Write-Host "$tag $step $details"
}
function Warn([string]$message) { $script:report.warnings += $message; Write-Warning $message }
function Installed([string]$name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }
function Install-Winget([string]$package) {
    if (-not (Installed 'winget.exe')) { throw 'winget indisponibil; instaleaza App Installer din Microsoft Store si reincearca.' }
    Write-Host "[VEGA] winget: $package (accepti instalarile si dialogurile Windows)"
    & winget.exe install --id $package --exact --source winget --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) { throw "winget $package a iesit cu codul $LASTEXITCODE" }
}
function Find-Python312 {
    $candidates = New-Object System.Collections.Generic.List[string]
    if (Installed 'py.exe') {
        try {
            $location = (& py.exe -3.12 -c 'import sys;print(sys.executable)' 2>$null | Select-Object -First 1)
            if ($LASTEXITCODE -eq 0 -and $location) { $candidates.Add([string]$location) }
        } catch {}
    }
    $candidates.Add((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'))
    $candidates.Add('C:\Program Files\Python312\python.exe')
    $candidates.Add('C:\Python312\python.exe')
    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        try {
            $version = (& $candidate -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>$null | Select-Object -First 1)
            if ($version -eq '3.12') { return $candidate }
        } catch {}
    }
    return $null
}
function Pip([string]$py, [string[]]$arguments) {
    & $py -m pip @arguments
    if ($LASTEXITCODE -ne 0) { throw "pip failure (exit code $LASTEXITCODE): $($arguments -join ' ')" }
}
function Get-GitPath {
    if (Installed 'git.exe') { return (Get-Command git.exe).Source }
    foreach($p in @('C:\Program Files\Git\cmd\git.exe', 'C:\Program Files\Git\bin\git.exe')) {
        if(Test-Path -LiteralPath $p) { return $p }
    }
    return $null
}
function Clone-IfMissing([string]$git, [string]$url, [string]$target) {
    if (Test-Path -LiteralPath (Join-Path $target '.git')) { Write-Host "[VEGA] Deja prezent: $target"; return }
    if (Test-Path -LiteralPath $target) { throw "Director deja ocupat, fara .git: $target. Nu suprascriu." }
    & $git clone --depth 1 -- $url $target
    if($LASTEXITCODE -ne 0) { throw "Git clone failed: $url" }
    & $git -C $target rev-parse HEAD
    if($LASTEXITCODE -ne 0) {throw "No git revision: $target"}
}

Write-Host "`n===== VEGA: instalare locala Windows ====="
Write-Host 'NU porneste cloud GPU, conturi sociale, publicare sau plati.'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Acest pachet este exclusiv pentru Windows.' }
$system = Get-CimInstance Win32_ComputerSystem
$graphics = @(Get-CimInstance Win32_VideoController | ForEach-Object Name)
Write-Host "RAM: $([math]::Round($system.TotalPhysicalMemory/1GB,1)) GB. Video: $($graphics -join '; ')"
$drive = [System.IO.DriveInfo]::new([System.IO.Path]::GetPathRoot($root))
$freeGB=[math]::Round($drive.AvailableFreeSpace/1GB,1)
Write-Host "Spatiu disponibil: $freeGB GB"
if($freeGB -lt 8) { throw 'Mai putin de 8 GB liberi. Oprire pentru a preveni umplerea discului.' }
if($graphics -match 'RX 580|2048SP') { Warn 'AMD RX 580: se foloseste ComfyUI CPU; accelerarea ROCm Windows nu este garantata. Generarea video avansata poate fi impracticabil de lenta.' }
Write-Host "Instalare in: $root"
Write-Host 'Software-ul este descarcat doar de la Python, winget, PyPI, PyTorch si GitHub oficial.'
$confirmation = Read-Host 'Tasteaza INSTALARE pentru a continua (altfel opresc)'
if($confirmation -cne 'INSTALARE') { Write-Host 'Anulat fara instalare.'; exit 2 }

$python = Find-Python312
if(-not $python) {
    try { Install-Winget 'Python.Python.3.12'; $python = Find-Python312 } catch { Status 'Python312' 'NEEDS_ACTION' $_.Exception.Message }
}
if(-not $python) {
    Warn 'Python 3.12 nu a fost detectat dupa instalare. Repornieste terminalul/Windows daca este necesar, apoi ruleaza din nou.'
    Status 'VEGA' 'NEEDS_ACTION' 'Python 3.12 necesar'
} else {
    Status 'Python312' 'OK' $python
    $vegaPy = Join-Path $root '.venv\Scripts\python.exe'
    try {
        if(-not (Test-Path -LiteralPath $vegaPy)) {
            & $python -m venv (Join-Path $root '.venv')
            if($LASTEXITCODE -ne 0) { throw 'Creare .venv esuata' }
        }
        Pip $vegaPy @('install','-r',(Join-Path $root 'requirements.txt'),'-r',(Join-Path $root 'requirements-lan.txt'))
        & $vegaPy -c 'import fastapi, uvicorn, PIL, cryptography; print("VEGA deps OK")'
        if($LASTEXITCODE -ne 0) { throw 'Nu pot importa dependintele VEGA' }
        Status 'VEGA' 'OK' 'Dependinte locale si HTTPS'
    } catch { Status 'VEGA' 'NEEDS_ACTION' $_.Exception.Message }
}

if(-not (Installed 'ffmpeg.exe')) {
    try { Install-Winget 'Gyan.FFmpeg'; Status 'FFmpeg' 'OK' 'winget instalat, poate necesita terminal nou pentru PATH' }
    catch { Status 'FFmpeg' 'NEEDS_ACTION' $_.Exception.Message }
} else { Status 'FFmpeg' 'OK' 'Exista deja' }

if(-not $SkipOllama) {
    $ollama = Get-Command ollama.exe -ErrorAction SilentlyContinue
    $ollamaPath = if ($ollama) {$ollama.Source} else { Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe' }
    if(-not (Test-Path -LiteralPath $ollamaPath)) {
        try { Install-Winget 'Ollama.Ollama' } catch { Status 'Ollama' 'NEEDS_ACTION' $_.Exception.Message }
    }
    if(-not (Test-Path -LiteralPath $ollamaPath)) {
        $ollama = Get-Command ollama.exe -ErrorAction SilentlyContinue
        if($ollama){$ollamaPath=$ollama.Source}
    }
    if (Test-Path -LiteralPath $ollamaPath) {
        Status 'Ollama' 'OK' 'Instalat; API local 127.0.0.1:11434, fara cloud'
        if($DownloadSmallModel) {
            $choice = Read-Host 'Descarc modelul local qwen3:0.6b (~0.5-1 GB)? scrie DA'
            if($choice -ceq 'DA') {
                try {
                    & $ollamaPath pull 'qwen3:0.6b'
                    if($LASTEXITCODE -ne 0) { throw "ollama pull failed: $LASTEXITCODE" }
                    Status 'OllamaModel' 'OK' 'qwen3:0.6b prezent local'
                } catch { Status 'OllamaModel' 'NEEDS_ACTION' $_.Exception.Message }
            } else { Status 'OllamaModel' 'SKIP' 'Modelul nu a fost descarcat' }
        }
    } else {Status 'Ollama' 'NEEDS_ACTION' 'Nu se gaseste ollama.exe; poate fi necesar restart/log out'}
} else { Status 'Ollama' 'SKIP' 'Argument SkipOllama' }

$git = Get-GitPath
if(-not $git) {
    try { Install-Winget 'Git.Git'; $git=Get-GitPath } catch { Status 'Git' 'NEEDS_ACTION' $_.Exception.Message }
}
if($git) {Status 'Git' 'OK' $git} else {Status 'Git' 'NEEDS_ACTION' 'Git indisponibil in aceasta sesiune'}

if(-not $SkipComfyUI) {
    if(-not $git -or -not $python) { Status 'ComfyUI' 'NEEDS_ACTION' 'Necesita Git si Python 3.12' }
    else {
        $comfy = Join-Path $root 'tools\ComfyUI'
        $comfyPy = Join-Path $comfy '.venv\Scripts\python.exe'
        try {
            New-Item -ItemType Directory -Force -Path (Join-Path $root 'tools') | Out-Null
            Clone-IfMissing $git 'https://github.com/Comfy-Org/ComfyUI.git' $comfy
            if(-not (Test-Path -LiteralPath $comfyPy)) {
                & $python -m venv (Join-Path $comfy '.venv')
                if($LASTEXITCODE -ne 0){throw 'Creare mediu ComfyUI esuata'}
            }
            # CPU PyTorch keeps incompatible RX 580 ROCm installers away from this Windows PC.
            Pip $comfyPy @('install','torch','torchvision','torchaudio','--index-url','https://download.pytorch.org/whl/cpu')
            Pip $comfyPy @('install','-r',(Join-Path $comfy 'requirements.txt'))
            & $comfyPy -c 'import torch;print("ComfyUI Torch CPU:",torch.__version__)'
            if($LASTEXITCODE -ne 0){throw 'torch failed to import'}
            Status 'ComfyUI' 'OK' 'CPU backend, pornire cu --cpu; fara modele de generare incluse'
            $manager=Join-Path $comfy 'custom_nodes\ComfyUI-Manager'
            try {
                Clone-IfMissing $git 'https://github.com/ltdrdata/ComfyUI-Manager.git' $manager
                if(Test-Path -LiteralPath (Join-Path $manager 'requirements.txt')) {
                    Pip $comfyPy @('install','-r',(Join-Path $manager 'requirements.txt'))
                }
                Status 'ComfyUIManager' 'OK' 'Manager prezent; NU instala custom nodes necunoscute'
            } catch {Status 'ComfyUIManager' 'NEEDS_ACTION' $_.Exception.Message}
        } catch {Status 'ComfyUI' 'NEEDS_ACTION' $_.Exception.Message}
    }
} else {Status 'ComfyUI' 'SKIP' 'Argument SkipComfyUI'}

if(-not $SkipWhisper) {
    $vegaPy=Join-Path $root '.venv\Scripts\python.exe'
    if(Test-Path -LiteralPath $vegaPy) {
        try {
            Pip $vegaPy @('install','faster-whisper')
            & $vegaPy -c 'from faster_whisper import WhisperModel;print("faster-whisper import OK")'
            if($LASTEXITCODE -ne 0) { throw 'faster-whisper import failed' }
            Status 'faster-whisper' 'OK' 'CPU inference posibil, modelul tiny poate fi descarcat separat'
        } catch { Status 'faster-whisper' 'NEEDS_ACTION' $_.Exception.Message }
    } else {Status 'faster-whisper' 'NEEDS_ACTION' 'VEGA .venv lipseste'}
} else {Status 'faster-whisper' 'SKIP' 'Argument SkipWhisper'}

if(-not $SkipVoiceStudio) {
    # Do not execute opaque "irm ... | iex" scripts. The signed/official installer should be inspected by user.
    Status 'VoiceStudio' 'NEEDS_ACTION' 'Descarca si ruleaza programul Windows oficial din GitHub Releases; alegerea vocii si a modelelor este manuala.'
    Write-Host 'VoiceStudio: https://github.com/debpalash/VoiceStudio/releases/latest'
} else {Status 'VoiceStudio' 'SKIP' 'Argument SkipVoiceStudio'}
Status 'Chatterbox' 'NEEDS_ACTION' 'Arhiva de cercetare neintretinuta, necesita validare CPU si dependinte; NU instalata automat.'
Status 'LatentSync' 'NEEDS_ACTION' 'CUDA/GPU; 1.6 necesita ~18 GB VRAM. RX 580 are 8 GB, NU instalat automat.'
Status 'AI-photo-model' 'NEEDS_ACTION' 'ComfyUI nu contine checkpoint-urile (licente si spatiu); alege explicit un checkpoint compatibil.'
Status 'iPhone' 'NEEDS_ACTION' 'Lanseaza START_VEGA_IPHONE_HTTPS.bat si aproba manual certificatul doar pe iPhone-ul propriu.'
Status 'SocialAPIs' 'SKIP' 'Fara credentiale OAuth si aprobare pentru publicare'
Status 'Cloud' 'SKIP' 'Fara GPU cloud/server si fara plati'

$reportPath=Join-Path $data 'vega_install_report.json'
($report | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "`n===== REZULTAT: $reportPath ====="
foreach($key in $report.steps.Keys) { $v=$report.steps[$key]; Write-Host ('{0,-20} {1}' -f $key,$v.status) }
Write-Host 'Dupa orice instalare winget, daca executabilele lipsesc din PATH, redeschide terminalul si ruleaza din nou.'
Write-Host 'Incearca VERIFY_ALL_WINDOWS.bat. Pentru VEGA: START_VEGA_FULL_WINDOWS.bat.'
