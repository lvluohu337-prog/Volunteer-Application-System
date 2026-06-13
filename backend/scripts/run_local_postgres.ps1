$ErrorActionPreference = "Stop"

$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtimeRoot = Join-Path $projectRoot ".local\postgresql"
$postgresExe = Join-Path $runtimeRoot "16\bin\postgres.exe"
$dataDir = Join-Path $runtimeRoot "16\data"
$stdoutLog = Join-Path $runtimeRoot "postgres-stdout.log"
$stderrLog = Join-Path $runtimeRoot "postgres-stderr.log"
$listenAddresses = "127.0.0.1,192.168.66.102"

if (-not (Test-Path $postgresExe)) {
    throw "PostgreSQL runtime not found: $postgresExe"
}

if (-not (Test-Path $dataDir)) {
    throw "PostgreSQL data directory not found: $dataDir"
}

& $postgresExe `
    -D $dataDir `
    -h $listenAddresses `
    -p 5432 `
    -c "default_text_search_config=pg_catalog.simple" `
    1>> $stdoutLog `
    2>> $stderrLog
