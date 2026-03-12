# Vacancy Analyzer PRO

Telegram-бот для поиска и анализа вакансий с платформ HH.ru и SuperJob с использованием ML-кластеризации.

## 📋 Функционал

### Основные возможности
- **Поиск вакансий** с HH.ru и SuperJob по названию профессии
- **ML-кластеризация** вакансий по уровню сложности (Junior/Middle/Senior)
- **Кэширование** результатов в PostgreSQL (24 часа)
- **FSM-интерфейс** для пошагового поиска с фильтрами

### Кластеризация
Бот анализирует описания вакансий и навыки с помощью TF-IDF и KMeans, группируя вакансии по уровню на основе средней зарплаты.

### Команды
- `/start` — главное меню
- `/search <профессия>` — быстрый поиск
- `/cache` — показать кэшированные вакансии

## 🛠 Установка

### 1. Клонирование репозитория
```bash
cd your_folder
```

### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 3. Настройка PostgreSQL

#### Установка PostgreSQL (если не установлен)
Скачайте с https://www.postgresql.org/download/windows/

#### Создание базы данных
```bash
.\init_db.bat
```

Или вручную через pgAdmin:
1. Создайте БД `vacancy_bot`
2. Выполните SQL из `init_db.sql`

### 4. Настройка переменных окружения

Отредактируйте файл `.env`:
```env
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token

# Kilo Auto AI (опционально)
KILO_AUTO_API_KEY=your_kilo_auto_api_key
KILO_AUTO_API_URL=https://api.kilo-auto.ai/v1/chat/completions
KILO_AUTO_MODEL=kilo-auto

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vacancy_bot
DB_USER=postgres
DB_PASS=your_password
```

### 5. Удаление webhook (если требуется)
```powershell
.\delete_webhook.ps1
```

## 🚀 Запуск

```bash
python vacancy_bot.py
```

## 📱 Использование

### Через интерфейс бота
1. Откройте бота в Telegram
2. Нажмите `/start`
3. Выберите "🔍 Анализ HH+SuperJob"
4. Введите название профессии (например, Python)
5. Укажите желаемую зарплату (или /skip)
6. Выберите регион

### Через команду
```
/search Python
/search Java Москва
/search Frontend 100000
```

## 🗄 Структура базы данных

```sql
vacancies (
    id SERIAL PRIMARY KEY,
    source VARCHAR(10),      -- 'hh' или 'sj'
    external_id VARCHAR(50), -- ID на источнике
    name TEXT,               -- Название вакансии
    company TEXT,            -- Компания
    salary INTEGER,          -- Зарплата (руб)
    description TEXT,        -- Описание
    skills TEXT[],           -- Навыки (массив)
    experience VARCHAR(20),  -- Опыт
    url TEXT,                -- Ссылка на вакансию
    parsed_at TIMESTAMP      -- Время парсинга
)
```

## 📦 Зависимости

- aiogram>=3.0.0 — Telegram Bot API
- psycopg2-binary — PostgreSQL
- requests — HTTP-запросы
- pandas — Работа с данными
- scikit-learn — ML (TF-IDF, KMeans)
- python-dotenv — Переменные окружения

## 🔧 Устранение проблем

### Ошибка "psql не найден"
Добавьте путь в PATH:
```powershell
$env:PATH += ";C:\Program Files\PostgreSQL\18\bin"
```

### Ошибка webhook
```powershell
.\delete_webhook.ps1
```

### Не подключается к БД
Проверьте настройки в `.env` и убедитесь, что PostgreSQL запущен.

## 🐳 Docker

### Быстрый старт

1. Скопируйте `.env.example` в `.env` и заполните значения:
```bash
cp .env.example .env
```

2. Запустите контейнеры:
```bash
docker-compose up -d
```

3. Проверьте статус:
```bash
docker-compose logs -f bot
```

### Команды Docker

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Пересборка
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f
docker-compose logs -f bot   # только бот
docker-compose logs -f db    # только БД

# Перезапуск
docker-compose restart bot
```

### Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|--------|
| BOT_TOKEN | Токен Telegram бота | 123456:ABC-DEF... |
| KILO_AUTO_API_KEY | API ключ Kilo Auto (опционально) | your_key_here |
| KILO_AUTO_API_URL | URL API Kilo Auto (опционально) | https://api.kilo-auto.ai/v1/chat/completions |
| KILO_AUTO_MODEL | Модель Kilo Auto (опционально) | kilo-auto |
| DB_NAME | Имя базы данных | vacancy_bot |
| DB_USER | Пользователь PostgreSQL | postgres |
| DB_PASS | Пароль PostgreSQL | my_password |

## 📄 Лицензия

MIT
