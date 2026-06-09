$ErrorActionPreference = "Stop"

$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$pgCtl = Join-Path $projectRoot ".local\postgresql\16\bin\pg_ctl.exe"
$dataDir = Join-Path $projectRoot ".local\postgresql\16\data"

if (-not (Test-Path $pgCtl) -or -not (Test-Path $dataDir)) {
    Write-Host "postgres-not-installed"
    exit 0
}

& $pgCtl -D $dataDir stop -m fast
