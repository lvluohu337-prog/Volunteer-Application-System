$ErrorActionPreference = "Stop"

$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtimeRoot = Join-Path $projectRoot ".local\postgresql"
$postgresExe = Join-Path $runtimeRoot "16\bin\postgres.exe"
$dataDir = Join-Path $runtimeRoot "16\data"
$stdoutLog = Join-Path $runtimeRoot "postgres-stdout.log"
$stderrLog = Join-Path $runtimeRoot "postgres-stderr.log"

try {
    $client = New-Object System.Net.Sockets.TcpClient
    $client.Connect("127.0.0.1", 5432)
    $client.Close()
    Write-Host "postgres-already-running"
    exit 0
} catch {
}

if (-not (Test-Path $postgresExe)) {
    throw "PostgreSQL runtime not found: $postgresExe"
}

if (-not (Test-Path $dataDir)) {
    throw "PostgreSQL data directory not found: $dataDir"
}

$canonicalPath = [System.Environment]::GetEnvironmentVariable("Path", "Process")
[System.Environment]::SetEnvironmentVariable("PATH", $null, "Process")
[System.Environment]::SetEnvironmentVariable("Path", $canonicalPath, "Process")

$argString = '-D "' + $dataDir + '" -h 127.0.0.1 -p 5432 -c "default_text_search_config=pg_catalog.simple"'
Start-Process `
    -FilePath $postgresExe `
    -ArgumentList $argString `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog

for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect("127.0.0.1", 5432)
        $client.Close()
        Write-Host "postgres-started"
        exit 0
    } catch {
    }
}

if (Test-Path $stderrLog) {
    Get-Content -Tail 80 $stderrLog
}

throw "PostgreSQL did not become ready on 127.0.0.1:5432 within 30 seconds."
