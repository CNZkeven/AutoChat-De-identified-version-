$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$EnvFile = Join-Path $RootDir ".env"
$ExampleFile = Join-Path $RootDir ".env.example"

if (-not (Test-Path $EnvFile)) {
    Copy-Item $ExampleFile $EnvFile
    Write-Host "[dev] Created $EnvFile from $ExampleFile."
}

docker compose up --build
