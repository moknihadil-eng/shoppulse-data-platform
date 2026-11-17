$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $env:PATH = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin;" + $env:PATH
}
Get-Content -Raw tests\check_deployment.py | & docker compose run --rm -T --no-deps --entrypoint python platform -
if ($LASTEXITCODE -ne 0) { throw 'Queued Dagster execution / interface verification failed' }
