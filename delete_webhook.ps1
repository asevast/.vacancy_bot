$token = $env:BOT_TOKEN
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$token/deleteWebhook"
