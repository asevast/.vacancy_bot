$ErrorActionPreference = "Stop"

function Get-EnvValue {
    param([string]$Path, [string]$Key)
    if (-not (Test-Path $Path)) { return $null }
    $line = Get-Content $Path | Where-Object { $_ -match "^\s*$Key\s*=" } | Select-Object -First 1
    if (-not $line) { return $null }
    return ($line -replace "^\s*$Key\s*=\s*", "")
}

function Set-EnvValue {
    param([string]$Path, [string]$Key, [string]$Value)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType File -Path $Path -Force | Out-Null
    }
    $content = Get-Content $Path
    $pattern = "^\s*$Key\s*="
    if ($content -match $pattern) {
        $content = $content | ForEach-Object {
            if ($_ -match $pattern) { "$Key=$Value" } else { $_ }
        }
    } else {
        $content += "$Key=$Value"
    }
    Set-Content -Path $Path -Value $content -Encoding UTF8
}

$envPath = Join-Path $PSScriptRoot ".env"
$port = Get-EnvValue -Path $envPath -Key "WEB_PORT"
if (-not $port) { $port = "8080" }

Write-Host "Starting Cloudflare Tunnel for http://localhost:$port"
$proc = Start-Process -FilePath "cloudflared" -ArgumentList @("tunnel", "--url", "http://localhost:$port") -NoNewWindow -PassThru -RedirectStandardOutput "$PSScriptRoot\tunnel.log" -RedirectStandardError "$PSScriptRoot\tunnel.err"

Start-Sleep -Seconds 3

$trySeconds = 30
$publicUrl = $null
for ($i = 0; $i -lt $trySeconds; $i++) {
    if (Test-Path "$PSScriptRoot\tunnel.log") {
        $log = Get-Content "$PSScriptRoot\tunnel.log" -Tail 200
        $match = $log | Select-String -Pattern "https://[a-z0-9\-]+\.trycloudflare\.com" -AllMatches | Select-Object -Last 1
        if ($match) {
            $publicUrl = $match.Matches[0].Value
            break
        }
    }
    Start-Sleep -Seconds 1
}

if (-not $publicUrl) {
    Write-Host "Не удалось определить публичный URL. Проверьте tunnel.log и tunnel.err."
    exit 1
}

Set-EnvValue -Path $envPath -Key "PUBLIC_BASE_URL" -Value $publicUrl
Set-EnvValue -Path $envPath -Key "WEB_HOST" -Value "0.0.0.0"
Set-EnvValue -Path $envPath -Key "WEB_PORT" -Value $port

Write-Host "PUBLIC_BASE_URL обновлен: $publicUrl"
Write-Host "Tunnel process id: $($proc.Id)"
Write-Host "Оставьте это окно открытым, чтобы туннель работал."
