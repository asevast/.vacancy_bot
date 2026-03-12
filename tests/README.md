# Тестирование Vacancy Bot

## Обзор

Набор тестов для проекта `vacancy_bot.py` включает:
- **Unit тесты** - быстрые изолированные тесты отдельных функций
- **Integration тесты** - тесты взаимодействия с внешними сервисами (API, БД)
- **Functional тесты** - сквозные тесты пользовательских сценариев

## Структура тестов

```
tests/
├── conftest.py           # Общие фикстуры и настройки
├── unit/
│   ├── test_parsing.py  # Тесты парсинга HH.ru и SuperJob
│   ├── test_ml.py       # Тесты ML кластеризации
│   └── test_utils.py    # Тесты утилит и БД функций (включая подписки)
├── integration/
│   ├── test_api.py      # Тесты API интеграции
│   ├── test_ai.py       # Тесты AI интеграции
│   └── test_database.py # Тесты БД операций
└── functional/
    ├── test_fsm.py       # Тесты FSM состояний
    └── test_end_to_end.py # Сквозные тесты
```

## Требования

### Версия Python
- Python 3.8+ (рекомендуется 3.11)

### Зависимости
```bash
# Основные зависимости
pip install -r requirements.txt

# Зависимости для тестирования
pip install -r requirements-test.txt
```

## Запуск тестов

### Все тесты
```bash
pytest -v
```

### Только unit тесты (быстрые)
```bash
pytest -v -m unit
```

### Только integration тесты
```bash
pytest -v -m integration
```

### Только functional тесты
```bash
pytest -v -m functional
```

### С покрытием кода
```bash
pytest -v --cov=vacancy_bot --cov-report=html --cov-report=term
```

### Параллельное выполнение
```bash
pytest -n auto  # Требует pytest-xdist
```

### С таймаутами
```bash
pytest --timeout=60
```

## Фикстуры

### Основные фикстуры (conftest.py)

- `mock_env_vars` - мок переменных окружения
- `sample_hh_vacancy_data` - пример данных HH.ru
- `sample_sj_vacancy_data` - пример данных SuperJob
- `sample_vacancies_dataframe` - пример DataFrame вакансий
- `mock_db_connection` - мок подключения к БД
- `mock_message` - мок сообщения Telegram
- `mock_callback` - мок callback запроса
- `mock_state` - мок FSM состояния

## Маркеры

- `@pytest.mark.unit` - Unit тесты
- `@pytest.mark.integration` - Integration тесты
- `@pytest.mark.functional` - Functional тесты
- `@pytest.mark.slow` - Медленные тесты
- `@pytest.mark.network` - Тесты с сетевыми вызовами
- `@pytest.mark.db` - Тесты с БД

## CI/CD

### GitHub Actions
```bash
# Автоматический запуск при push/pull request
.github/workflows/ci.yml
```

### Локальный запуск CI проверок
```bash
# Все проверки
pytest -v && flake8 vacancy_bot.py

# Только быстрые тесты
pytest -v -m "unit and not slow"
```

## Покрытие кода

### Целевое покрытие
- Unit тесты: 90%+
- Integration тесты: 80%+
- Functional тесты: 70%+

### Генерирование отчета
```bash
# HTML отчет
pytest --cov=vacancy_bot --cov-report=html

# Консольный отчет
pytest --cov=vacancy_bot --cov-report=term

# XML (для CI)
pytest --cov=vacancy_bot --cov-report=xml
```

## Примеры тестов

### Unit тест
```python
@pytest.mark.unit
def test_parse_hh_vacancies_returns_dataframe(mocker, sample_hh_vacancy_data):
    """Test that parser returns DataFrame."""
    mock_response = mocker.Mock()
    mock_response.json.return_value = sample_hh_vacancy_data
    mocker.patch("requests.get", return_value=mock_response)
    
    result = parse_hh_vacancies("Python Developer")
    
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
```

### Integration тест
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_ask_kilo_auto_returns_response(mocker):
    """Test AI function with mocked HTTP."""
    mock_session = mocker.patch("aiohttp.ClientSession")
    # ... настройка мока
    
    result = await ask_kilo_auto("Test prompt")
    
    assert isinstance(result, str)
```

### Functional тест
```python
@pytest.mark.functional
@pytest.mark.asyncio
async def test_search_workflow():
    """Test complete search workflow."""
    # ... тест сквозного сценария
```

## Мокирование внешних зависимостей

### HTTP запросы
```python
mocker.patch("requests.get", return_value=mock_response)
```

### База данных
```python
mocker.patch("psycopg2.connect", return_value=mock_conn)
```

### AI API
```python
mocker.patch("aiohttp.ClientSession")
```

## Устранение проблем

### Тесты падают с ImportError
```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### Проблемы с кодировкой (Windows)
```bash
set PYTHONIOENCODING=utf-8
pytest -v
```

### Таймауты тестов
```bash
pytest --timeout=120
```

### Параллельное выполнение
```bash
pytest -n 4  # 4 процесса
```

## Рекомендации

1. **命名ование тестов**: Используйте descriptive имена `test_<что_тестируем>_<сценарий>`
2. **Изоляция**: Каждый тест должен быть независимым
3. **Фикстуры**: Выносите повторяющийся код в фикстуры
4. **Mocking**: Мокируйте все внешние зависимости
5. **Ассерты**: Используйте понятные сообщения об ошибках

## Дополнительные инструменты

### Покрытие
- `pytest-cov` - генерация отчета о покрытии

### Параллелизация
- `pytest-xdist` - параллельное выполнение тестов

### Тестирование async
- `pytest-asyncio` - поддержка async функций

### Безопасность
- `bandit` - проверка безопасности кода
- `safety` - проверка уязвимостей в зависимостях
