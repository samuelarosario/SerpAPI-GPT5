param(
  [int] $Port = 8000,
  [switch] $All
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
  if (-not $pids -and $All) {
    # Fallback: kill common uvicorn/python processes if requested
    $uvicorn = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match 'python|uvicorn' }
    if ($uvicorn) { $pids = $uvicorn.Id }
  }

  if (-not $pids) { Write-Host "[stop-webapp] No process found listening on :$Port." -ForegroundColor Yellow; return }
  foreach ($procId in $pids) {
    try { Stop-Process -Id $procId -Force -ErrorAction Stop; Write-Host "[stop-webapp] Stopped PID $procId" -ForegroundColor Green }
    catch { Write-Warning ("[stop-webapp] Failed to stop PID {0}: {1}" -f $procId, ($_.Exception.Message)) }
  }
} finally {
  Pop-Location
}
