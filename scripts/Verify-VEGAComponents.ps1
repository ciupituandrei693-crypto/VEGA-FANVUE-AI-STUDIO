# Read-only audit of the local install; does not download anything.
$ErrorActionPreference = 'Continue'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
function Test-Executable([string]$command) {
    $exe=Get-Command $command -ErrorAction SilentlyContinue
    return [bool]$exe
}
function Test-Url([string]$url) {
    try {
        $r=Invoke-WebRequest -Uri $url -TimeoutSec 2 -UseBasicParsing
        return ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400)
    } catch { return $false }
}
Write-Host '===== RAPORT VERIFICARE VEGA ====='
$tests = [ordered]@{
    'VEGA venv' = (Test-Path (Join-Path $root '.venv\Scripts\python.exe'))
    'FFmpeg PATH' = (Test-Executable 'ffmpeg.exe')
    'Git PATH' = (Test-Executable 'git.exe')
    'Ollama API (local)' = (Test-Url 'http://127.0.0.1:11434/api/tags')
    'ComfyUI source' = (Test-Path (Join-Path $root 'tools\ComfyUI\main.py'))
    'ComfyUI Python' = (Test-Path (Join-Path $root 'tools\ComfyUI\.venv\Scripts\python.exe'))
    'ComfyUI Manager' = (Test-Path (Join-Path $root 'tools\ComfyUI\custom_nodes\ComfyUI-Manager'))
    'ComfyUI API (local)' = (Test-Url 'http://127.0.0.1:8188/system_stats')
    'VEGA API (local)' = (Test-Url 'http://127.0.0.1:8765/')
}
foreach($pair in $tests.GetEnumerator()) {Write-Host ('{0,-28} {1}' -f $pair.Key,$pair.Value)}
$py=Join-Path $root '.venv\Scripts\python.exe'
if(Test-Path $py){
    & $py -c 'import importlib.util; print("faster-whisper:",bool(importlib.util.find_spec("faster_whisper")));print("FastAPI:",bool(importlib.util.find_spec("fastapi")))'
}
Write-Host 'False pentru API poate insemna ca serviciul nu e pornit, nu ca instalarea a esuat.'
Write-Host 'Nu verifica si nu transmite parole, chei sau media personale.'
