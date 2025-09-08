Param(
    [int]$Port = 8000,
    [string]$BindHost = '127.0.0.1',
    [switch]$Reload,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg) {
    if(-not $Quiet){ Write-Host "[INFO] $msg" -ForegroundColor Cyan }
}
function Write-Err($msg) {
    Write-Host "[ERR ] $msg" -ForegroundColor Red
}

# Determine directories
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path           # .../WebApp/scripts
$webAppDir = Split-Path -Parent $scriptDir                              # .../WebApp
# Project root is parent of WebApp (assumes standard layout)
$projectRoot = Split-Path -Parent $webAppDir
if(-not (Test-Path (Join-Path $projectRoot 'WebApp'))){
    # Fallback: if assumption wrong, use parent containing scripts folder
    $projectRoot = Split-Path -Parent $scriptDir
}
Set-Location $projectRoot

# Python executable (fallback to 'python' if python3.13.exe not found)
$pyCandidates = @(
    "$env:LOCALAPPDATA/Microsoft/WindowsApps/python3.13.exe",
    "$env:LOCALAPPDATA/Microsoft/WindowsApps/python.exe",
    'python'
)
$python = $null
foreach($c in $pyCandidates){ if(Test-Path $c){ $python = $c; break } }
if(-not $python){ Write-Err 'Python not found.'; exit 1 }

# Basic health check function
function Test-Health([string]$url){
    try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 $url).StatusCode -eq 200 } catch { return $false }
}

$reloadFlag = ''
if ($Reload.IsPresent) { $reloadFlag = '--reload' }
Write-Info "Starting WebApp on http://${BindHost}:$Port $reloadFlag"

# Prepare log directory at project root
$logDir = Join-Path $projectRoot 'runtime_logs'
if(-not (Test-Path $logDir)){ New-Item -ItemType Directory -Path $logDir | Out-Null }
$procLog = Join-Path $logDir "webapp-uvicorn-$Port.log"

function Start-Uvicorn {
    Write-Info 'Launching uvicorn process'
    $args = "-m uvicorn WebApp.app.main:app --host $BindHost --port $Port --loop asyncio --http h11 $reloadFlag"
    # Redirect stdout and stderr to separate files then tail primary
    $outLog = $procLog
    Start-Process -FilePath $python -ArgumentList $args -PassThru -RedirectStandardOutput $outLog
}

$proc = Start-Uvicorn
Start-Sleep -Seconds 2
$tries = 0
while(-not (Test-Health "http://${BindHost}:$Port/health") -and $tries -lt 10){
    Start-Sleep -Milliseconds 500
    $tries++
}
if(Test-Health "http://${BindHost}:$Port/health"){ Write-Info 'Initial health check: OK' } else { Write-Err 'Initial health check failed.' }

Write-Info "Logging to $procLog"
Write-Info 'Press Ctrl+C to stop supervision. Auto-restart enabled.'

while($true){
    Start-Sleep -Seconds 3
    if($proc.HasExited){
        Write-Err "Process exited with code $($proc.ExitCode). Restarting..."
        Start-Sleep -Seconds 1
        $proc = Start-Uvicorn
        Start-Sleep -Seconds 2
    }
}
