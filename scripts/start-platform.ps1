$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$ApiDir = Join-Path $Root "apps\api"
$WebDir = Join-Path $Root "apps\web"
$ComposeFile = Join-Path $Root "infra\litellm\compose.yaml"
$Python = Join-Path $ApiDir ".venv\Scripts\python.exe"

function Test-ListeningPort {
    param([int]$Port)
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

if (-not (Test-Path $Python)) {
    throw "Python environment not found: $Python"
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker compose -f $ComposeFile up -d
} else {
    Write-Warning "Docker CLI was not found. LiteLLM and PostgreSQL were not started."
}

if (-not (Test-ListeningPort 8899)) {
    Start-Process powershell.exe -WorkingDirectory $Root -ArgumentList @(
        "-NoExit",
        "-Command",
        "& '$Python' '$Root\tools\direct_proxy.py'"
    )
    Write-Host "STARTED LLM-DIRECT-PROXY-8899"
} else {
    Write-Host "PORT 8899 ALREADY ACTIVE"
}

if (-not (Test-ListeningPort 8002)) {
    Start-Process powershell.exe -WorkingDirectory $ApiDir -ArgumentList @(
        "-NoExit",
        "-Command",
        "& '$Python' -m uvicorn main:app --host 127.0.0.1 --port 8002"
    )
    Write-Host "STARTED LLM-API-8002"
} else {
    Write-Host "PORT 8002 ALREADY ACTIVE"
}

if (-not (Test-ListeningPort 5500)) {
    Start-Process powershell.exe -WorkingDirectory $WebDir -ArgumentList @(
        "-NoExit",
        "-Command",
        "& '$Python' -m http.server 5500 --bind 127.0.0.1"
    )
    Write-Host "STARTED LLM-WEB-5500"
} else {
    Write-Host "PORT 5500 ALREADY ACTIVE"
}

Write-Host ""
Write-Host "Web:      http://127.0.0.1:5500"
Write-Host "API docs: http://127.0.0.1:8002/docs"
Write-Host "Usage:    http://127.0.0.1:5500/usage.html"
