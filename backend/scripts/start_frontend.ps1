param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ViteArgs
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$viteCli = Join-Path $projectRoot "node_modules\vite\bin\vite.js"

if (-not (Test-Path $viteCli)) {
    throw "Vite CLI not found: $viteCli"
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

& $nodeExe $viteCli @ViteArgs
