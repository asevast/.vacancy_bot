@echo off
set PATH=%PATH%;C:\Program Files\PostgreSQL\18\bin
echo ========================================
echo Creating vacancy_bot database
echo ========================================

echo Creating database...
psql -U postgres -c "DROP DATABASE IF EXISTS vacancy_bot;"
psql -U postgres -c "CREATE DATABASE vacancy_bot;"

echo Creating tables...
psql -U postgres -d vacancy_bot -c "CREATE TABLE IF NOT EXISTS vacancies (id SERIAL PRIMARY KEY, source VARCHAR(10) NOT NULL, external_id VARCHAR(50) NOT NULL, name TEXT NOT NULL, company TEXT, salary INTEGER, description TEXT, skills TEXT[], experience VARCHAR(20), url TEXT, parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(source, external_id));"

psql -U postgres -d vacancy_bot -c "CREATE INDEX IF NOT EXISTS idx_source_salary ON vacancies(source, salary);"
psql -U postgres -d vacancy_bot -c "CREATE INDEX IF NOT EXISTS idx_parsed_at ON vacancies(parsed_at);"

echo.
echo Done!
pause
    exit /b 1
)

echo Создаём базу данных...
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "DROP DATABASE IF EXISTS vacancy_bot;"
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE vacancy_bot;"

echo Создаём таблицы...
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d vacancy_bot -f "%~dp0init_db.sql"

echo.
echo Готово!
pause
