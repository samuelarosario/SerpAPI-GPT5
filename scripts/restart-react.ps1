param(
  [string] $BindHost = '127.0.0.1',
  [int] $Port = 9000
)
$ErrorActionPreference = 'Stop'
& "$PSScriptRoot\stop-react.ps1" -Port $Port
& "$PSScriptRoot\start-react.ps1" -BindHost $BindHost -Port $Port
