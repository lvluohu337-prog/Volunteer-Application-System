param()

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
$viteCli = Join-Path $projectRoot "node_modules\vite\bin\vite.js"
$checkScript = Join-Path $projectRoot "scripts\check_frontend_error_states.cjs"

if (-not (Test-Path $viteCli)) {
    throw "Vite CLI not found: $viteCli"
}

if (-not (Test-Path $checkScript)) {
    throw "Frontend regression script not found: $checkScript"
}

$candidateNodes = @(
    "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe",
    (Get-Command node -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue)
)

$nodeExe = $candidateNodes |
    Where-Object {
        $_ -and
        (Test-Path $_) -and
        ($_ -notlike "C:\Program Files\WindowsApps\*")
    } |
    Select-Object -First 1

if (-not $nodeExe) {
    throw "Node.js not found. Install Node or make sure the Codex bundled runtime still exists."
}

$bundledNodeModules = Join-Path (Split-Path $nodeExe -Parent | Split-Path -Parent) "node_modules"
$pnpmNodeModules = Join-Path $bundledNodeModules ".pnpm\node_modules"

$nodePathParts = @()
if (Test-Path $bundledNodeModules) {
    $nodePathParts += $bundledNodeModules
}
if (Test-Path $pnpmNodeModules) {
    $nodePathParts += $pnpmNodeModules
}
if ($env:NODE_PATH) {
    $nodePathParts += $env:NODE_PATH
}
if ($nodePathParts.Count -gt 0) {
    $env:NODE_PATH = ($nodePathParts | Select-Object -Unique) -join ";"
}

Write-Host "Building frontend for regression check..."
& $nodeExe $viteCli build
if ($LASTEXITCODE -ne 0) {
    throw "Frontend build failed."
}

Write-Host "Running frontend error-state regression..."
& $nodeExe $checkScript
if ($LASTEXITCODE -ne 0) {
    throw "Frontend error-state regression failed."
}
