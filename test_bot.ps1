$token = $env:BOT_TOKEN

# РџСЂРѕРІРµСЂРєР° webhook
Write-Host "Checking webhook status..."
try {
    $response = Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/getWebhookInfo" -TimeoutSec 10
    $response | ConvertTo-Json
} catch {
    Write-Host "Error: $_"
}

Write-Host "`nChecking bot info..."
try {
    $me = Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/getMe" -TimeoutSec 10
    $me | ConvertTo-Json
} catch {
    Write-Host "Error: $_"
}
