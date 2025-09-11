<#
Start the WebApp in a separate PowerShell window using the repo's Python venv.

Behavior (made permanent per request):
- Always launches in an external PowerShell console (outside VS Code).
- Before starting, finds and kills any process listening on the target port.
- Uses .\.venv\Scripts\python.exe if present; if missing, runs scripts/bootstrap.ps1 -RunServer.
- Waits briefly and verifies the port is listening; prints status.

Usage:
  .\scripts\start-webapp.ps1                            # start on 127.0.0.1:8000
  .\scripts\start-webapp.ps1 -BindHost 0.0.0.0 -Port 8000 # custom bind
#>

param(
  [string] $BindHost = "127.0.0.1",
  [int] $Port = 8000,
  [switch] $Foreground
)

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot\..
try {
  function Get-PidsByPort([int]$p) {
    $pids = @()
    $net = netstat -ano | Select-String ":$p" | ForEach-Object { $_.ToString() }
    foreach ($line in $net) { if ($line -match "\s+(\d+)$") { $pids += [int]$Matches[1] } }
    return ($pids | Sort-Object -Unique)
  }

  $py = ".\\.venv\\Scripts\\python.exe"
  if (-not (Test-Path $py)) {
    Write-Warning "[start-webapp] .venv not found. Bootstrapping environment..."
    & ".\\scripts\\bootstrap.ps1" -RunServer | Out-Null
    return
  }

  # Kill any existing process bound to the port (permanent behavior)
  $existing = Get-PidsByPort -p $Port
  if ($existing -and $existing.Count -gt 0) {
    Write-Warning ("[start-webapp] Found process(es) on :{0} -> {1}. Terminating..." -f $Port, ($existing -join ','))
    foreach ($procId in $existing) {
      try { Stop-Process -Id $procId -Force -ErrorAction Stop; Write-Host ("[start-webapp] Stopped PID {0}" -f $procId) -ForegroundColor Yellow } catch { Write-Warning ("[start-webapp] Failed to stop PID {0}: {1}" -f $procId, $_.Exception.Message) }
    }
    Start-Sleep -Milliseconds 500
  }

  # Launch in an external PowerShell window
  $cmd = @(
    "Set-Location -LiteralPath '$(Get-Location)';",
    "& '$py' -m uvicorn WebApp.app.main:app --host $BindHost --port $Port --log-level info"
  ) -join ' '

  Write-Host "[start-webapp] Launching external console on http://${BindHost}:$Port ..." -ForegroundColor Green
  $proc = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-NoExit','-Command', $cmd) -WindowStyle Normal -PassThru
  if ($proc) { Write-Host ("[start-webapp] External PowerShell PID={0}" -f $proc.Id) -ForegroundColor Green }

  # Wait for readiness
  $ok = $false
  for ($i=0; $i -lt 60; $i++) {
    try { if ((Test-NetConnection -ComputerName $BindHost -Port $Port).TcpTestSucceeded) { $ok = $true; break } } catch {}
    Start-Sleep -Milliseconds 500
  }
  if ($ok) { Write-Host "[start-webapp] Web server is up." -ForegroundColor Green } else { Write-Warning "[start-webapp] Server not responding yet on port $Port." }
} finally {
  Pop-Location
}
