<#
Start the React dev server (Vite) in a separate PowerShell window.

Behavior:
- Kills any process on the target port before starting.
- Launches an external PowerShell that runs `npm run dev` with host/port options.
- Verifies readiness.
#>

param(
  [string] $BindHost = "127.0.0.1",
  [int] $Port = 5173
)

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot\..
try {
  $frontend = Join-Path (Get-Location) 'WebApp\\react-frontend'
  if (-not (Test-Path $frontend)) { throw "React frontend not found at $frontend" }

  function Get-PidsByPort([int]$p) {
    $pids = @()
    $net = netstat -ano | Select-String ":$p" | ForEach-Object { $_.ToString() }
    foreach ($line in $net) { if ($line -match "\s+(\d+)$") { $pids += [int]$Matches[1] } }
    return ($pids | Sort-Object -Unique)
  }

  # Kill any existing process bound to the port
  $existing = Get-PidsByPort -p $Port
  if ($existing) {
    Write-Warning ("[start-react] Found process(es) on :{0} -> {1}. Terminating..." -f $Port, ($existing -join ','))
  foreach ($procToKill in $existing) { try { Stop-Process -Id $procToKill -Force } catch {} }
    Start-Sleep -Milliseconds 500
  }

  $cmd = @(
    "Set-Location -LiteralPath '$frontend';",
    "npm run dev -- --host $BindHost --port $Port --strictPort"
  ) -join ' '
  Write-Host ("[start-react] Launching external PowerShell for Vite on http://{0}:{1} ..." -f $BindHost,$Port) -ForegroundColor Green
  $proc = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-NoExit','-Command', $cmd) -WindowStyle Normal -PassThru
  if ($proc) { Write-Host ("[start-react] External PowerShell PID={0}" -f $proc.Id) -ForegroundColor Green }

  # Wait for readiness
  $ok = $false
  for ($i=0; $i -lt 60; $i++) {
    try { if ((Test-NetConnection -ComputerName $BindHost -Port $Port).TcpTestSucceeded) { $ok = $true; break } } catch {}
    Start-Sleep -Milliseconds 500
  }
  if ($ok) {
    Write-Host "[start-react] Dev server is up." -ForegroundColor Green
    $url = "http://" + $BindHost + ":" + $Port + "/"
    try { (Invoke-WebRequest -UseBasicParsing -Uri $url).StatusCode | Out-Host } catch {}
  }
  else { Write-Warning "[start-react] Dev server not responding on port $Port yet." }
} finally {
  Pop-Location
}
