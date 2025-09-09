param(
  [int] $Port = 8013
)

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot\..
try {
  $pids = @()
  $net = netstat -ano | Select-String ":$Port" | ForEach-Object { $_.ToString() }
  foreach ($line in $net) {
    if ($line -match "\s+(\d+)$") { $pids += [int]$Matches[1] }
  }
  $pids = $pids | Sort-Object -Unique
  if (-not $pids) {
    Write-Host "[stop-webapp] No process found listening on :$Port." -ForegroundColor Yellow
    return
  }
  foreach ($procId in $pids) {
    try {
      Stop-Process -Id $procId -Force -ErrorAction Stop
      Write-Host "[stop-webapp] Stopped PID $procId" -ForegroundColor Green
    } catch {
      Write-Warning ("[stop-webapp] Failed to stop PID {0}: {1}" -f $procId, ($_.Exception.Message))
    }
  }
} finally {
  Pop-Location
}
