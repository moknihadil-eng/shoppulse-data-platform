$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $env:PATH = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin;" + $env:PATH
}
& docker compose stop dagster metabase
if ($LASTEXITCODE -ne 0) { throw 'Cannot pause interfaces for integration tests' }
try {
    & docker compose run --rm platform verify
    if ($LASTEXITCODE -ne 0) { throw 'Platform integration verification failed' }
} finally {
    & docker compose up -d --wait dagster metabase
}
if ($LASTEXITCODE -ne 0) { throw 'Cannot restart interfaces after integration tests' }
& docker compose run --rm platform metabase
if ($LASTEXITCODE -ne 0) { throw 'Metabase dashboard verification failed' }
