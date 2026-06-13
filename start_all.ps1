$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$backendScript = Join-Path $projectRoot "backend\scripts\start_backend.ps1"
$frontendScript = Join-Path $projectRoot "backend\scripts\start_frontend.ps1"
$pgScript = Join-Path $projectRoot "backend\scripts\start_local_postgres.ps1"

# -------------------------------------------------------------------
# 1. Start PostgreSQL and wait until it is actually ready
# -------------------------------------------------------------------
if (Test-Path $pgScript) {
    Write-Host "[PG] Starting PostgreSQL..." -ForegroundColor Cyan
    & $pgScript
    Write-Host "[PG] PostgreSQL is ready." -ForegroundColor Green
} else {
    Write-Host "[PG] PostgreSQL script not found, skipping." -ForegroundColor DarkGray
}

# -------------------------------------------------------------------
# 2. Start Backend (new window)
# -------------------------------------------------------------------
Write-Host "[BACKEND] Starting backend (uvicorn :8000)..." -ForegroundColor Cyan
$backendJob = Start-Process powershell.exe -ArgumentList @(
    "-NoProfile",
    "-NoExit",
    "-Command",
    "`$host.UI.RawUI.WindowTitle = 'Backend - uvicorn :8000'; & '$backendScript'"
) -PassThru
Write-Host "[BACKEND] Backend process started (PID: $($backendJob.Id))" -ForegroundColor Green

# Wait for backend to be ready before starting frontend
Write-Host "[WAIT] Waiting for backend to be ready..." -ForegroundColor DarkGray
$backendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "[WAIT] Backend is ready!" -ForegroundColor Green
            $backendReady = $true
            break
        }
    } catch {
        # keep waiting
    }
}
if (-not $backendReady) {
    Write-Host "[WAIT] Backend not ready within 30s, starting frontend anyway." -ForegroundColor Yellow
}

# -------------------------------------------------------------------
# 3. Start Frontend (new window)
# -------------------------------------------------------------------
Write-Host "[FRONTEND] Starting frontend (vite :5173)..." -ForegroundColor Cyan
$frontendJob = Start-Process powershell.exe -ArgumentList @(
    "-NoProfile",
    "-NoExit",
    "-Command",
    "`$host.UI.RawUI.WindowTitle = 'Frontend - vite :5173'; & '$frontendScript'"
) -PassThru
Write-Host "[FRONTEND] Frontend process started (PID: $($frontendJob.Id))" -ForegroundColor Green

# -------------------------------------------------------------------
# 4. Wait for user input, press any key to exit
# -------------------------------------------------------------------
Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  All services started!" -ForegroundColor Green
Write-Host "  Backend : http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  Frontend: http://127.0.0.1:5173" -ForegroundColor White
Write-Host "  API Docs: http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Press any key to stop all services and exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# -------------------------------------------------------------------
# 5. Stop all services
# -------------------------------------------------------------------
Write-Host ""
Write-Host "Stopping all services..." -ForegroundColor Yellow

if ($backendJob -and !$backendJob.HasExited) {
    Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
    Write-Host "[BACKEND] Backend stopped" -ForegroundColor Green
}
if ($frontendJob -and !$frontendJob.HasExited) {
    Stop-Process -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue
    Write-Host "[FRONTEND] Frontend stopped" -ForegroundColor Green
}

Write-Host "All services stopped. Goodbye!" -ForegroundColor Magenta
