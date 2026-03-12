# Vacancy Analyzer PRO

Telegram-бот для поиска и анализа вакансий с платформ HH.ru и SuperJob с использованием ML-кластеризации.

## 📋 Функционал

### Основные возможности
- **Поиск вакансий** с HH.ru и SuperJob по названию профессии
- **Больше источников**: Habr Career и агрегаторы (если настроены)
- **ML-кластеризация** вакансий по уровню сложности (Junior/Middle/Senior)
- **Кэширование** результатов в PostgreSQL (24 часа)
- **Подписки и дайджесты** по заданным фильтрам
- **FSM-интерфейс** для пошагового поиска с фильтрами
- **Профиль пользователя**: регион, зарплата, уровень, формат и технологии по умолчанию

### Кластеризация
Бот анализирует описания вакансий и навыки с помощью TF-IDF и KMeans, группируя вакансии по уровню на основе средней зарплаты.

### Команды
- `/start` — главное меню
- `/search <профессия> [options]` — быстрый поиск с фильтрами и сортировкой
- `/stats <профессия> [options]` — аналитика рынка по запросу
- `/cache` — показать кэшированные вакансии
- `/subscribe` — создать подписку (FSM)
- `/subscriptions` — список подписок
- `/unsubscribe <id>` — отключить подписку
- `/digest` — получить дайджест сейчас
- `/profile` — показать профиль
- `/profile_set` — настроить профиль (FSM)
- `/sources` — список источников и подсказки по токенам

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

# SuperJob API (опционально)
SJ_API_KEY=your_superjob_api_key

# Habr Career API (опционально)
HABR_API_URL=https://career.habr.com/api/v1/vacancies
HABR_API_TOKEN=your_habr_token

# Jooble API (опционально)
JOOBLE_API_KEY=your_jooble_api_key

# Adzuna API (опционально)
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
ADZUNA_COUNTRY=ru

# Aggregator API (опционально)
AGGREGATOR_API_URL=https://example.com/api/v1/vacancies
AGGREGATOR_API_TOKEN=your_aggregator_token

# Web list viewer (опционально)
WEB_HOST=0.0.0.0
WEB_PORT=8080
PUBLIC_BASE_URL=http://localhost:8080

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

### 6. Внешний доступ к спискам (Cloudflare Tunnel)
1. Установите cloudflared:
```powershell
winget install Cloudflare.cloudflared
```
2. Авторизуйтесь:
```powershell
cloudflared tunnel login
```
3. Запустите туннель и автоматически обновите `PUBLIC_BASE_URL`:
```powershell
.\start_tunnel.ps1
```
Скрипт запишет публичный URL в `.env`. Оставьте окно с туннелем открытым.

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
5. При необходимости уточните специализацию/стек (например, Python backend)
6. Укажите желаемую зарплату (или /skip)
7. Выберите регион
8. Подтвердите параметры (Да/Нет)

Профиль пользователя используется как значения по умолчанию для региона и зарплаты. Также профильные настройки уровня/формата/технологий применяются как дополнительные фильтры при поиске.

### Через команду
```
/search Python
/search Java region=Москва salary_from=150000
/search Frontend order=salary_asc limit=20
/search DevOps source=hh experience=between1And3 only_with_salary=1
/stats Python region=Москва
/stats Data Scientist source=hh period=30
```
Если запрос слишком общий, бот попросит уточнить специализацию или стек. Для пошагового уточнения используйте `/start`.

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
| HABR_API_URL | URL API Habr Career | https://career.habr.com/api/v1/vacancies |
| HABR_API_TOKEN | Токен Habr Career (опционально) | your_habr_token |
| JOOBLE_API_KEY | API ключ Jooble (опционально) | your_jooble_api_key |
| ADZUNA_APP_ID | App ID Adzuna (опционально) | your_adzuna_app_id |
| ADZUNA_APP_KEY | App Key Adzuna (опционально) | your_adzuna_app_key |
| ADZUNA_COUNTRY | Страна Adzuna | ru |
| AGGREGATOR_API_URL | URL API агрегатора (опционально) | https://example.com/api/v1/vacancies |
| AGGREGATOR_API_TOKEN | Токен агрегатора (опционально) | your_aggregator_token |
| DB_NAME | Имя базы данных | vacancy_bot |
| DB_USER | Пользователь PostgreSQL | postgres |
| DB_PASS | Пароль PostgreSQL | my_password |
| WEB_HOST | Хост веб-страницы списков | 0.0.0.0 |
| WEB_PORT | Порт веб-страницы списков | 8080 |
| PUBLIC_BASE_URL | Публичный URL для ссылок | http://localhost:8080 |

## 📄 Лицензия

MIT
- `region=Москва|СПб|Все` — регион
- `salary_from=100000` / `salary_to=200000` — зарплатная вилка
- `source=hh|sj|habr|jooble|adzuna|agg` — источник
- `order=salary_desc|salary_asc` — сортировка
- `limit=20` — ограничение вывода
- `experience=between1And3` — опыт (HH)
- `employment=full` — тип занятости (HH)
- `only_with_salary=1` — только с зарплатой (HH)
- `schedule=remote` — график (HH)
- `professional_role=96` — проф. роль (HH)
- `search_field=name` — поле поиска (HH)
- `period=30` — период в днях (HH)
- `currency=RUR` — валюта (HH)
- `label=with_address` — метка (HH)
- `order_by=salary_desc` — сортировка HH (HH)
