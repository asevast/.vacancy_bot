@echo off
set PATH=%PATH%;C:\Program Files\PostgreSQL\18\bin
echo Deleting webhook...
curl -X POST "https://api.telegram.org/bot963650906:AAFZxqZJH_iZaRw6icp63cmMmTr6P971PYE/deleteWebhook"
echo.
echo Done!
pause
