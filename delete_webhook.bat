@echo off
set PATH=%PATH%;C:\Program Files\PostgreSQL\18\bin
echo Deleting webhook...
curl -X POST "https://api.telegram.org/bot%BOT_TOKEN%/deleteWebhook"
echo.
echo Done!
pause
