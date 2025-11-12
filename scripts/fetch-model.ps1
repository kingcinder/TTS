#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
param(
    [switch]$AllowDownload,
    [string]$Destination = "artifacts/models/xtts_v2",
    [string]$ExpectedSha256 = ""
)

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptRoot '..')
Set-Location $RepoRoot

$LogDir = Join-Path $RepoRoot "artifacts/logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$LogFile = Join-Path $LogDir "fetch-model-$([DateTime]::UtcNow.ToString('yyyyMMddHHmmss')).jsonl"

function Write-Log {
    param([string]$Stage, [string]$Status, [string]$Message, [hashtable]$Extra)
    $entry = @{ timestamp = [DateTime]::UtcNow.ToString('o'); stage = $Stage; status = $Status; message = $Message }
    if ($Extra) {
        foreach ($key in $Extra.Keys) { $entry[$key] = $Extra[$key] }
    }
    Add-Content -Path $LogFile -Value ($entry | ConvertTo-Json -Compress)
    Write-Host "[$Stage][$Status] $Message"
}

$destPath = Resolve-Path -LiteralPath $Destination -ErrorAction SilentlyContinue
if (-not $destPath) {
    $destPath = Join-Path $ScriptRoot "../$Destination"
}
if (-not (Test-Path $destPath)) {
    New-Item -ItemType Directory -Path $destPath | Out-Null
}
$destPath = (Resolve-Path -LiteralPath $destPath).Path

$modelFile = Join-Path $destPath "xtts_v2.pth"

if (Test-Path $modelFile) {
    $hash = (Get-FileHash -Path $modelFile -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Log "verify" "success" "Existing model located" @{ path = $modelFile; sha256 = $hash }
    if ($ExpectedSha256 -and $hash -ne $ExpectedSha256.ToLowerInvariant()) {
        throw "SHA256 mismatch for $modelFile. Expected $ExpectedSha256, got $hash"
    }
    return
}

if (-not $AllowDownload) {
    Write-Log "download" "error" "Model file missing" @{ path = $modelFile; hint = "Run with -AllowDownload or place file manually." }
    throw "Model weights not present. Rerun with -AllowDownload to fetch from the public mirror."
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "Python executable not found. Install Python 3.10+."
}

Write-Log "download" "start" "Fetching XTTS v2 weights" @{ path = $modelFile }
& $python.Path (Join-Path $ScriptRoot "fetch_model.py") --dest $destPath

if (-not (Test-Path $modelFile)) {
    throw "Model download did not produce expected file at $modelFile"
}

$hash = (Get-FileHash -Path $modelFile -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Log "download" "success" "Model downloaded" @{ path = $modelFile; sha256 = $hash }

if ($ExpectedSha256 -and $hash -ne $ExpectedSha256.ToLowerInvariant()) {
    throw "SHA256 mismatch for $modelFile. Expected $ExpectedSha256, got $hash"
}
