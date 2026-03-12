-- Создание базы данных
CREATE DATABASE vacancy_bot;

-- Подключение к базе данных
\c vacancy_bot;

-- Создание таблицы вакансий
CREATE TABLE IF NOT EXISTS vacancies (
    id SERIAL PRIMARY KEY,
    source VARCHAR(10) NOT NULL,
    external_id VARCHAR(50) NOT NULL,
    name TEXT NOT NULL,
    company TEXT,
    salary INTEGER,
    description TEXT,
    skills TEXT[],
    experience VARCHAR(20),
    url TEXT,
    parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, external_id)
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_source_salary ON vacancies(source, salary);
CREATE INDEX IF NOT EXISTS idx_parsed_at ON vacancies(parsed_at);
CREATE INDEX IF NOT EXISTS idx_name ON vacancies(name);
CREATE INDEX IF NOT EXISTS idx_company ON vacancies(company);
