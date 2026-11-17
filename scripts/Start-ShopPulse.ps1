param([switch]$SkipBuild, [switch]$SkipBI)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $dockerBin = Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin'
    if (Test-Path $dockerBin) { $env:PATH = $dockerBin + ';' + $env:PATH }
}
function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker failed: $($args -join ' ')" }
}
Invoke-Docker info --format '{{.ServerVersion}}'
if (-not (Test-Path .env)) {
    $settings = Get-Content .env.example
    $settings = $settings -replace '^POSTGRES_PASSWORD=.*$', ('POSTGRES_PASSWORD='+[guid]::NewGuid().ToString('N'))
    $settings = $settings -replace '^MINIO_ROOT_PASSWORD=.*$', ('MINIO_ROOT_PASSWORD='+[guid]::NewGuid().ToString('N'))
    $settings = $settings -replace '^METABASE_ADMIN_PASSWORD=.*$', ('METABASE_ADMIN_PASSWORD=Sp!'+[guid]::NewGuid().ToString('N'))
    $settings = $settings -replace '^METABASE_READ_PASSWORD=.*$', ('METABASE_READ_PASSWORD='+[guid]::NewGuid().ToString('N'))
    [IO.File]::WriteAllLines((Join-Path (Get-Location) '.env'), $settings, (New-Object Text.UTF8Encoding($false)))
}
# Migrate an existing M1/M2 configuration without rotating its existing secrets.
$configured = Get-Content .env
$newSettings = @()
foreach ($line in (Get-Content .env.example)) {
    if ($line -match '^([A-Z_]+)=(.*)$') {
        $key = $Matches[1]
        if (-not ($configured -match ('^' + $key + '='))) {
            if ($key -like '*PASSWORD') { $line = $key + '=Sp!' + [guid]::NewGuid().ToString('N') }
            $newSettings += $line
        }
    }
}
if ($newSettings.Count) {
    [IO.File]::AppendAllText((Join-Path (Get-Location) '.env'), "`r`n" + ($newSettings -join "`r`n") + "`r`n", (New-Object Text.UTF8Encoding($false)))
}
New-Item -ItemType Directory -Force .local\reports | Out-Null
Invoke-Docker compose config --quiet
Invoke-Docker compose stop dagster metabase
if (-not $SkipBuild) { Invoke-Docker compose build minio foundation ingestion source-api platform }
Invoke-Docker compose up -d --wait postgres minio warehouse source-api
Invoke-Docker compose run --rm foundation init
Invoke-Docker compose run --rm platform run
Invoke-Docker compose up -d --wait dagster dbt-docs
if (-not $SkipBI) {
    Invoke-Docker compose up -d --wait metabase
    Invoke-Docker compose run --rm platform metabase
}
Invoke-Docker compose ps
Write-Host 'Dagster: http://localhost:3000 | Metabase: http://localhost:3001 | dbt docs: http://localhost:8081'
