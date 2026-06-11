$ErrorActionPreference = "Stop"

$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pgDumpExe = Join-Path $projectRoot ".local\postgresql\16\bin\pg_dump.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment not found: $pythonExe"
}

if (Test-Path $pgDumpExe) {
    $resolvedPgDump = $pgDumpExe
}
else {
    $command = Get-Command pg_dump -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "pg_dump not found. Install PostgreSQL or place pg_dump in PATH."
    }
    $resolvedPgDump = $command.Source
}

$env:PG_DUMP_PATH = $resolvedPgDump

& $pythonExe (Join-Path $projectRoot "backend\backup_db.py")
