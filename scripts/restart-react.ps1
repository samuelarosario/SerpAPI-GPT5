param(
  [string] $BindHost = '127.0.0.1',
  [int] $Port = 5173
)
$ErrorActionPreference = 'Stop'
# Deprecated: React dev scripts are no longer used.
Write-Host "[restart-react] Deprecated. Use 'npm run dev' from WebApp/react-frontend for local hot reload." -ForegroundColor Yellow
exit 0
