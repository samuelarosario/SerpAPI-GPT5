<#
Bootstrap the Python environment and start the Web App (Windows PowerShell).

Actions:
- Create .venv (if missing)
- Upgrade pip
- Install requirements.txt (root, includes WebApp deps)
- Optional: install WebApp/webapp_requirements.txt if present (noop if merged)
- Start uvicorn at 127.0.0.1:8013 (detached) with logs in WebApp/runtime_logs

Usage:
  .\scripts\bootstrap.ps1                # setup only, no server
  .\scripts\bootstrap.ps1 -RunServer     # setup + start server

Note:
  Run from repo root: C:\Users\MY PC\SerpAPI - V5 - GPT5
#>

param(
  [switch] $RunServer
)

$ErrorActionPreference = 'Stop'

function Initialize-Venv {
  if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[bootstrap] Creating venv..." -ForegroundColor Cyan
    py -3 -m venv .venv
  }
}

function Invoke-Python([string]$PyArgs) {
  & ".\.venv\Scripts\python.exe" $PyArgs
}

function Install-Requirements {
  Write-Host "[bootstrap] Upgrading pip..." -ForegroundColor Cyan
  Invoke-Python "-m pip install --upgrade pip"
  Write-Host "[bootstrap] Installing root requirements.txt..." -ForegroundColor Cyan
  Invoke-Python "-m pip install -r requirements.txt"
  if (Test-Path "WebApp\webapp_requirements.txt") {
    Write-Host "[bootstrap] Installing WebApp/webapp_requirements.txt..." -ForegroundColor Cyan
    Invoke-Python "-m pip install -r WebApp/webapp_requirements.txt"
  }
}

function Start-WebServer {
  $logDir = "WebApp\runtime_logs"
  New-Item -ItemType Directory -Force -Path $logDir | Out-Null
  $out = Join-Path $logDir "webapp-uvicorn-8013.log"
  $err = Join-Path $logDir "webapp-uvicorn-8013.err.log"
  Write-Host "[bootstrap] Starting uvicorn on http://127.0.0.1:8013 ..." -ForegroundColor Green
  Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList @(
    "-m","uvicorn","WebApp.app.main:app","--host","127.0.0.1","--port","8013","--log-level","info"
  ) -RedirectStandardOutput $out -RedirectStandardError $err | Out-Null
  Start-Sleep -Seconds 2
  try {
    $ok = (Test-NetConnection -ComputerName 127.0.0.1 -Port 8013).TcpTestSucceeded
    if ($ok) { Write-Host "[bootstrap] Web server is up." -ForegroundColor Green }
    else { Write-Warning "[bootstrap] Server did not respond on port 8013. Check logs in $logDir" }
  } catch { Write-Warning "[bootstrap] Connectivity check failed: $_" }
}

Push-Location $PSScriptRoot\..
try {
  Initialize-Venv
  Install-Requirements
  if ($RunServer) { Start-WebServer }
  Write-Host "[bootstrap] Done." -ForegroundColor Green
} finally {
  Pop-Location
}
