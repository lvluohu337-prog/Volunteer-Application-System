$ErrorActionPreference = "Stop"

$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtimeRoot = Join-Path $projectRoot ".local\postgresql"
$postgresExe = Join-Path $runtimeRoot "16\bin\postgres.exe"
$pgIsReadyExe = Join-Path $runtimeRoot "16\bin\pg_isready.exe"
$dataDir = Join-Path $runtimeRoot "16\data"
$stdoutLog = Join-Path $runtimeRoot "postgres-stdout.log"
$stderrLog = Join-Path $runtimeRoot "postgres-stderr.log"
$listenAddresses = "127.0.0.1,192.168.66.102"

if (Test-Path $pgIsReadyExe) {
    & $pgIsReadyExe -h 127.0.0.1 -p 5432 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "postgres-already-running"
        exit 0
    }
}

if (-not (Test-Path $postgresExe)) {
    throw "PostgreSQL runtime not found: $postgresExe"
}

if (-not (Test-Path $pgIsReadyExe)) {
    throw "pg_isready not found: $pgIsReadyExe"
}

if (-not (Test-Path $dataDir)) {
    throw "PostgreSQL data directory not found: $dataDir"
}

$canonicalPath = [System.Environment]::GetEnvironmentVariable("Path", "Process")
[System.Environment]::SetEnvironmentVariable("PATH", $null, "Process")
[System.Environment]::SetEnvironmentVariable("Path", $canonicalPath, "Process")

$argString = '-D "' + $dataDir + '" -h "' + $listenAddresses + '" -p 5432 -c "default_text_search_config=pg_catalog.simple"'

Start-Process `
    -FilePath $postgresExe `
    -ArgumentList $argString `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog | Out-Null

for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    & $pgIsReadyExe -h 127.0.0.1 -p 5432 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "postgres-started"
        exit 0
    }
}

if (Test-Path $stderrLog) {
    Get-Content $stderrLog -Tail 80
}

throw "PostgreSQL did not become ready on 127.0.0.1:5432 within 60 seconds."
