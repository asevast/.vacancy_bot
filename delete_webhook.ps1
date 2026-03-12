$token = "963650906:AAFZxqZJH_iZaRw6icp63cmMmTr6P971PYE"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$token/deleteWebhook"
