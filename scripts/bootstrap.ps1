<#
Bootstrap the Python environment and start the Web App (Windows PowerShell).

Actions:
- Create .venv (if missing)
- Upgrade pip
- Install requirements.txt (root, includes WebApp deps)
- Optional: install WebApp/webapp_requirements.txt if present (noop if merged)
- Start uvicorn at 127.0.0.1:8000 (detached) with logs in WebApp/runtime_logs

Usage:
  .\scripts\bootstrap.ps1                # setup only (Python + deps; build React if package.json exists)
  .\scripts\bootstrap.ps1 -RunServer     # setup + build React + start server (single port)

Note:
  Run from repo root: C:\Users\MY PC\SerpAPI - V5 - GPT5
#>

param(
  [switch] $RunServer,
  [switch] $SkipFrontendBuild
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

function Build-ReactFrontend {
  $frontend = "WebApp/react-frontend"
  if (-not (Test-Path $frontend)) { return }
  if ($SkipFrontendBuild) { Write-Host "[bootstrap] Skipping React build (flag)." -ForegroundColor Yellow; return }
  Push-Location $frontend
  try {
    if (-not (Test-Path "node_modules")) {
      Write-Host "[bootstrap] Installing frontend dependencies (npm ci)..." -ForegroundColor Cyan
      npm ci | Out-Null
    }
    Write-Host "[bootstrap] Building React frontend (npm run build)..." -ForegroundColor Cyan
    npm run build | Out-Null
    if (Test-Path "dist/index.html") {
      Write-Host "[bootstrap] React build complete (dist)." -ForegroundColor Green
    } else {
      Write-Warning "[bootstrap] React build did not produce dist/index.html"
    }
  } catch {
    Write-Warning "[bootstrap] React build failed: $($_.Exception.Message)"
  } finally {
    Pop-Location
  }
}

function Start-WebServer {
  $logDir = "WebApp\runtime_logs"
  New-Item -ItemType Directory -Force -Path $logDir | Out-Null
  $out = Join-Path $logDir "webapp-uvicorn-8000.log"
  $err = Join-Path $logDir "webapp-uvicorn-8000.err.log"
  Write-Host "[bootstrap] Starting uvicorn on http://127.0.0.1:8000 ..." -ForegroundColor Green
  Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList @(
    "-m","uvicorn","WebApp.app.main:app","--host","127.0.0.1","--port","8000","--log-level","info"
  ) -RedirectStandardOutput $out -RedirectStandardError $err | Out-Null
  Start-Sleep -Seconds 2
  try {
    $ok = (Test-NetConnection -ComputerName 127.0.0.1 -Port 8000).TcpTestSucceeded
    if ($ok) { Write-Host "[bootstrap] Web server is up." -ForegroundColor Green }
    else { Write-Warning "[bootstrap] Server did not respond on port 8000. Check logs in $logDir" }
  } catch { Write-Warning "[bootstrap] Connectivity check failed: $_" }
}

Push-Location $PSScriptRoot\..
try {
  Initialize-Venv
  Install-Requirements
  Build-ReactFrontend
  if ($RunServer) { Start-WebServer }
  Write-Host "[bootstrap] Done." -ForegroundColor Green
} finally {
  Pop-Location
}
