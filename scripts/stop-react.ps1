param(
  [int] $Port = 5173
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

  $pids = Get-PidsByPort -p $Port
  if (-not $pids) { Write-Host "[stop-react] No process found listening on :$Port." -ForegroundColor Yellow; return }
  foreach ($procId in $pids) {
    try { Stop-Process -Id $procId -Force -ErrorAction Stop; Write-Host "[stop-react] Stopped PID $procId" -ForegroundColor Green }
    catch { Write-Warning ("[stop-react] Failed to stop PID {0}: {1}" -f $procId, ($_.Exception.Message)) }
  }
} finally {
  Pop-Location
}
