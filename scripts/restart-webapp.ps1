[CmdletBinding()]
param(
  [string] $BindHost = '127.0.0.1',
  [int] $Port = 8000
)
$ErrorActionPreference = 'Stop'
& "$PSScriptRoot\stop-webapp.ps1" -Port $Port
& "$PSScriptRoot\start-webapp.ps1" -BindHost $BindHost -Port $Port

