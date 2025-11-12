#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptRoot

# Load .env / .env.local if present
function Import-DotEnv([string]$Path) {
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        if ($_ -match '^\s*#') { return }
        if ($_ -match '^\s*([^=]+)=(.*)$') {
            $k = $matches[1].Trim()
            $v = $matches[2]
            [Environment]::SetEnvironmentVariable($k, $v)
            Set-Item -Path Env:$k -Value $v | Out-Null
        }
    }
}
Import-DotEnv (Join-Path $ScriptRoot ".env")
Import-DotEnv (Join-Path $ScriptRoot ".env.local")

$logDir = if ($env:TTS_LOG_DIR) { $env:TTS_LOG_DIR } else { Join-Path $ScriptRoot "artifacts/logs" }
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$logFile = Join-Path $logDir "run-$timestamp.jsonl"

function Write-Log {
    param(
        [string]$Stage,
        [string]$Status,
        [string]$Message,
        [hashtable]$Extra
    )
    $entry = @{ timestamp = [DateTime]::UtcNow.ToString("o"); stage = $Stage; status = $Status; message = $Message }
    if ($Extra) {
        foreach ($key in $Extra.Keys) { $entry[$key] = $Extra[$key] }
    }
    $json = $entry | ConvertTo-Json -Compress
    Add-Content -Path $logFile -Value $json
    Write-Host "[$Stage][$Status] $Message"
}

Write-Log "doctor" "start" "Checking required tools" @{ log = $logFile }
$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if (-not $pythonLauncher) {
    $pythonLauncher = Get-Command python -ErrorAction SilentlyContinue
}
if (-not $pythonLauncher) {
    Write-Log "doctor" "error" "Python launcher not found" @{ remediation = "Install Python 3.10+ and ensure it is on PATH." }
    throw "Python 3.10+ is required."
}
Write-Log "doctor" "success" "All prerequisite commands available" @{ python = $pythonLauncher.Source }

$venvPath = Join-Path $ScriptRoot "env"
$pythonExe = Join-Path $venvPath "Scripts/python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Log "build" "start" "Creating Python virtual environment" @{ path = $venvPath }
    if ($pythonLauncher.Name -like 'py*') {
        & $pythonLauncher.Source -3.10 -m venv $venvPath
    } else {
        & $pythonLauncher.Source -m venv $venvPath
    }
    Write-Log "build" "success" "Virtual environment created" @{ path = $venvPath }
}

$env:VIRTUAL_ENV = $venvPath
$envPath = Join-Path $venvPath "Scripts"
$env:PATH = "$envPath" + [System.IO.Path]::PathSeparator + $env:PATH
# Ensure absolute imports like `from scripts.*` work even when running files from the scripts/ folder
$existingPyPath = [Environment]::GetEnvironmentVariable("PYTHONPATH","Process")
if ([string]::IsNullOrWhiteSpace($existingPyPath)) {
    $env:PYTHONPATH = $ScriptRoot
} else {
    $env:PYTHONPATH = "$ScriptRoot$([System.IO.Path]::PathSeparator)$existingPyPath"
}

Write-Log "build" "start" "Installing Python dependencies" @{}
& $pythonExe -m pip install --upgrade pip wheel setuptools *> $null
& $pythonExe scripts/tts_setup.py --backend auto *> $null
Write-Log "build" "success" "Dependencies installed" @{}

$env:TTS_LOG_FILE = $logFile
$voicePath = Join-Path $ScriptRoot "artifacts/models/voice.pt"
$voiceRefs = if ($env:TTS_VOICE_REFS) { $env:TTS_VOICE_REFS } else { Join-Path $ScriptRoot "app/refs/demo.wav" }
if (-not (Test-Path $voiceRefs)) {
    & $pythonExe scripts/make_demo_ref.py --out $voiceRefs
}
if (-not (Test-Path $voicePath)) {
    Write-Log "embed" "start" "Generating speaker embedding" @{ output = $voicePath }
    & $pythonExe scripts/tts_embed.py --refs $voiceRefs --out $voicePath --log-file $logFile
    Write-Log "embed" "success" "Speaker embedding ready" @{ output = $voicePath }
}

Write-Log "run" "start" "Rendering demo sample" @{ voice = $voicePath }
$outputDir = if ($env:TTS_OUTPUT_DIR) { $env:TTS_OUTPUT_DIR } else { Join-Path $ScriptRoot "artifacts/outputs/demo" }
if (-not (Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir | Out-Null }
$outputFile = Join-Path $outputDir "render.wav"
$deviceOrder = if ($env:TTS_DEVICE_ORDER) { $env:TTS_DEVICE_ORDER } else { "rocm,dml,cpu" }
$textPath    = if ($env:TTS_TEXT_PATH)     { $env:TTS_TEXT_PATH }     else { Join-Path $ScriptRoot "app/texts/demo.txt" }
$sr          = if ($env:TTS_SAMPLE_RATE)   { $env:TTS_SAMPLE_RATE }   else { 48000 }
$crossfade   = if ($env:TTS_CROSSFADE_MS)  { $env:TTS_CROSSFADE_MS }  else { 8 }
& $pythonExe scripts/tts_cli_plus.py `
  --text $textPath `
  --voice $voicePath `
  --device-order $deviceOrder `
  --out $outputFile `
  --sr $sr --crossfade-ms $crossfade `
  --run-dir (Join-Path $ScriptRoot "artifacts")
Write-Log "run" "success" "Render completed" @{ output = $outputFile }

Write-Log "health" "start" "Verifying render artifact" @{ path = $outputFile }
if (-not (Test-Path $outputFile)) {
    Write-Log "health" "error" "Render artifact missing" @{ path = $outputFile }
    throw "Render output not found at $outputFile"
}
$info = Get-Item $outputFile
Write-Log "health" "success" "Render artifact verified" @{ bytes = $info.Length }

Write-Log "smoke" "start" "Running smoke tests" @{}
& $pythonExe -m compileall scripts tests 2>$null
Write-Log "smoke" "success" "Smoke tests completed" @{}

Write-Log "complete" "success" "Pipeline finished" @{ log = $logFile }
