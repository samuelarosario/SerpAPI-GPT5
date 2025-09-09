<#
Start the WebApp using the current repository's Python environment.

Behavior:
- Uses .\.venv\Scripts\python.exe if present (current environment)
- If .venv is missing, falls back to scripts/bootstrap.ps1 -RunServer
- Checks if the port is already listening and exits early
- Supports foreground or detached mode (default detached with logs)

Usage:
  .\scripts\start-webapp.ps1                          # start on 127.0.0.1:8013 (detached)
  .\scripts\start-webapp.ps1 -Foreground              # run in foreground
  .\scripts\start-webapp.ps1 -Host 0.0.0.0 -Port 9000 # custom bind
#>

param(
  [string] $BindHost = "127.0.0.1",
  [int] $Port = 8013,
  [switch] $Foreground
)

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot\..
try {
  $py = ".\\.venv\\Scripts\\python.exe"
  if (-not (Test-Path $py)) {
    Write-Warning "[start-webapp] .venv not found. Bootstrapping environment..."
    & ".\\scripts\\bootstrap.ps1" -RunServer | Out-Null
    return
  }

  # Early port check
  $listening = $false
  try { $listening = (Test-NetConnection -ComputerName $BindHost -Port $Port).TcpTestSucceeded } catch { $listening = $false }
  if ($listening) {
    Write-Host "[start-webapp] Server already running on http://${BindHost}:$Port" -ForegroundColor Green
    return
  }

  if ($Foreground) {
    Write-Host "[start-webapp] Starting foreground server on http://${BindHost}:$Port ..." -ForegroundColor Green
    & $py -m uvicorn WebApp.app.main:app --host $BindHost --port $Port --log-level info
  } else {
    $logDir = "WebApp\\runtime_logs"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $out = Join-Path $logDir ("webapp-uvicorn-{0}.log" -f $Port)
    $err = Join-Path $logDir ("webapp-uvicorn-{0}.err.log" -f $Port)
    Write-Host "[start-webapp] Starting detached server on http://${BindHost}:$Port ..." -ForegroundColor Green
    Start-Process -FilePath $py -ArgumentList @(
      "-m","uvicorn","WebApp.app.main:app","--host",$BindHost,"--port",$Port,"--log-level","info"
    ) -RedirectStandardOutput $out -RedirectStandardError $err | Out-Null
    Start-Sleep -Seconds 2
    try {
      if ((Test-NetConnection -ComputerName $BindHost -Port $Port).TcpTestSucceeded) {
        Write-Host "[start-webapp] Web server is up." -ForegroundColor Green
      } else {
        Write-Warning "[start-webapp] Server did not respond on port $Port. Check logs in $logDir"
      }
    } catch { Write-Warning "[start-webapp] Connectivity check failed: $_" }
  }
} finally {
  Pop-Location
}
