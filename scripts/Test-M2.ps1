$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker failed: $($args -join ' ')" }
}
Invoke-Docker compose config --quiet
Invoke-Docker compose up -d --build --wait postgres minio source-api
Invoke-Docker compose build ingestion
# Demo changes the countries of synthetic customers 1 and 2 to test updates.
Invoke-Docker compose run --rm --entrypoint python ingestion verify_m2.py
Invoke-Docker compose ps
