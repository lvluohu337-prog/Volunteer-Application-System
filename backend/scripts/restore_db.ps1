$ErrorActionPreference = "Stop"

param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)

$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$psqlExe = Join-Path $projectRoot ".local\postgresql\16\bin\psql.exe"
$envFile = Join-Path $projectRoot ".env"

if (-not (Test-Path $BackupFile)) {
    throw "Backup file not found: $BackupFile"
}

if (Test-Path $psqlExe) {
    $resolvedPsql = $psqlExe
}
else {
    $command = Get-Command psql -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "psql not found. Install PostgreSQL or place psql in PATH."
    }
    $resolvedPsql = $command.Source
}

if (-not (Test-Path $envFile)) {
    throw ".env not found: $envFile"
}

$config = @{}
foreach ($rawLine in Get-Content $envFile) {
    $line = $rawLine.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
        continue
    }

    $parts = $line.Split("=", 2)
    $key = $parts[0].Trim()
    $value = $parts[1].Trim().Trim("'`"")
    if ($key) {
        $config[$key] = $value
    }
}

$host = if ($config.ContainsKey("POSTGRES_HOST")) { $config["POSTGRES_HOST"] } else { "127.0.0.1" }
$port = if ($config.ContainsKey("POSTGRES_PORT")) { $config["POSTGRES_PORT"] } else { "5432" }
$database = if ($config.ContainsKey("POSTGRES_DB")) { $config["POSTGRES_DB"] } else { throw "POSTGRES_DB missing in .env" }
$user = if ($config.ContainsKey("POSTGRES_USER")) { $config["POSTGRES_USER"] } else { throw "POSTGRES_USER missing in .env" }
$password = if ($config.ContainsKey("POSTGRES_PASSWORD")) { $config["POSTGRES_PASSWORD"] } else { throw "POSTGRES_PASSWORD missing in .env" }

$env:PGPASSWORD = $password

try {
    & $resolvedPsql `
        -h $host `
        -p $port `
        -U $user `
        -d $database `
        -f $BackupFile
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
