$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker failed: $($args -join ' ')" }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker absent. Installer puis ouvrir Docker Desktop et rouvrir PowerShell. Voir README.'
}
Invoke-Docker --version
Invoke-Docker compose version
Invoke-Docker info --format '{{.ServerVersion}}'
if (-not (Test-Path .env)) { throw 'Creer .env avec Copy-Item .env.example .env puis modifier les mots de passe.' }
New-Item -ItemType Directory -Force .local | Out-Null
Invoke-Docker compose config --quiet
Invoke-Docker compose up -d --build --wait postgres minio
Invoke-Docker compose build foundation
Invoke-Docker compose run --rm foundation init
Invoke-Docker compose run --rm foundation before
# No init/seed between recreation and comparison: lost data cannot be hidden.
Invoke-Docker compose down
Invoke-Docker compose up -d --wait postgres minio
Invoke-Docker compose run --rm foundation after
Invoke-Docker compose ps -a
