$ErrorActionPreference = "Stop"

$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtimeRoot = Join-Path $projectRoot ".local\postgresql"
$launcher = Join-Path $PSScriptRoot "run_local_postgres.ps1"
$stderrLog = Join-Path $runtimeRoot "postgres-stderr.log"

try {
    $client = New-Object System.Net.Sockets.TcpClient
    $client.Connect("127.0.0.1", 5432)
    $client.Close()
    Write-Host "postgres-already-running"
    exit 0
} catch {
}

$powershellExe = Join-Path $PSHOME "powershell.exe"
$cmd = 'start "" /b "' + $powershellExe + '" -NoProfile -ExecutionPolicy Bypass -File "' + $launcher + '"'
cmd.exe /c $cmd | Out-Null

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
