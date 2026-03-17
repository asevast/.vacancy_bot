@echo off
set PATH=%PATH%;C:\Program Files\PostgreSQL\18\bin

echo ========================================
echo Creating vacancy_bot database
echo ========================================

psql -U postgres -c "DROP DATABASE IF EXISTS vacancy_bot;"
psql -U postgres -c "CREATE DATABASE vacancy_bot;"
psql -U postgres -d vacancy_bot -f "%~dp0init_db.sql"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Database initialization failed.
    pause
    exit /b 1
)

echo.
echo Done!
pause
