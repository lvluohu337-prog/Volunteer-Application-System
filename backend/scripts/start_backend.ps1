$ErrorActionPreference = "Stop"

$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment not found: $pythonExe"
}

& $pythonExe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
