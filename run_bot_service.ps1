$ErrorActionPreference = "Stop"

$projectDir = "C:\Users\Flesheater\.vacancy_bot"
Set-Location $projectDir

# Wait for Docker engine after boot.
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 5
}

if (-not $ready) {
    throw "Docker engine did not become ready in time."
}

docker compose up -d
