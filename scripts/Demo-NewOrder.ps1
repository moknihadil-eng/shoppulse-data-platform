$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $env:PATH = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin;" + $env:PATH
}
& docker compose run --rm platform demo-order
if ($LASTEXITCODE -ne 0) { throw 'Demo order did not propagate' }
& docker compose run --rm platform metabase
if ($LASTEXITCODE -ne 0) { throw 'Dashboard questions failed' }
Write-Host 'Refresh Metabase: the seed has 20 orders; demo order 9001 makes 21.'
