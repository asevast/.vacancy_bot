"""
Pytest configuration and fixtures for vacancy_bot tests.

This module provides reusable fixtures for testing all layers of the vacancy_bot application.

IMPORTANT: This conftest.py must be loaded BEFORE vacancy_bot module is imported.
The autouse session fixture ensures environment variables are set correctly.
"""

import os
import sys
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from typing import Generator, AsyncGenerator

import pytest
import pandas as pd


# ==============================================================================
# IMPORTANT: Set up environment BEFORE any vacancy_bot imports
# ==============================================================================

# Valid test token for aiogram (format: digits:alphanumeric, min 1 char after colon)
_TEST_BOT_TOKEN = "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghij"

# Set test environment variables BEFORE importing vacancy_bot
os.environ["BOT_TOKEN"] = _TEST_BOT_TOKEN
os.environ["KILO_AUTO_API_KEY"] = "test_kilo_api_key"
os.environ["KILO_AUTO_API_URL"] = "https://test-api.kilo-auto.ai/v1/chat/completions"
os.environ["KILO_AUTO_MODEL"] = "test-model"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_NAME"] = "test_vacancy_bot"
os.environ["DB_USER"] = "test_user"
os.environ["DB_PASS"] = "test_password"


# ==============================================================================
# Session-scoped fixtures (once per test session)
# ==============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def mock_env_vars():
    """
    Mock environment variables for testing.
    
    Returns a dictionary of test environment variables.
    """
    return {
        "BOT_TOKEN": _TEST_BOT_TOKEN,
        "KILO_AUTO_API_KEY": "test_kilo_api_key",
        "KILO_AUTO_API_URL": "https://test-api.kilo-auto.ai/v1/chat/completions",
        "KILO_AUTO_MODEL": "test-model",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "test_vacancy_bot",
        "DB_USER": "test_user",
        "DB_PASS": "test_password",
    }


@pytest.fixture(scope="function", autouse=True)
def setup_test_env(mock_env_vars):
    """
    Setup test environment variables for each test function.
    
    This fixture ensures environment variables are set for each test.
    """
    # Save and set test environment
    original_env = {k: os.environ.get(k) for k in mock_env_vars}
    
    for key, value in mock_env_vars.items():
        os.environ[key] = value
    
    yield
    
    # Restore original environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


# ==============================================================================
# Function-scoped fixtures (once per test function)
# ==============================================================================

@pytest.fixture
def sample_hh_vacancy_data():
    """
    Sample HH.ru vacancy data as returned by the API.
    
    Returns:
        dict: Sample vacancy data from HH.ru API
    """
    return {
        "items": [
            {
                "id": "12345678",
                "name": "Python Developer",
                "employer": {"name": "Test Company LLC"},
                "salary": {"currency": "RUR", "from": 100000, "to": 150000},
                "key_skills": [
                    {"name": "Python"},
                    {"name": "Django"},
                    {"name": "PostgreSQL"}
                ],
                "snippet": {
                    "requirement": "Опыт работы от 3 лет",
                    "responsibility": "Разработка веб-приложений"
                },
                "experience": {"id": "between1And3"},
                "alternate_url": "https://hh.ru/vacancy/12345678"
            },
            {
                "id": "87654321",
                "name": "Senior Python Developer",
                "employer": {"name": "Big Tech Corp"},
                "salary": {"currency": "RUR", "from": 200000},
                "key_skills": [
                    {"name": "Python"},
                    {"name": "FastAPI"},
                    {"name": "Kubernetes"}
                ],
                "snippet": {
                    "requirement": "Опыт работы от 5 лет",
                    "responsibility": "Архитектура системы"
                },
                "experience": {"id": "moreThan6"},
                "alternate_url": "https://hh.ru/vacancy/87654321"
            }
        ]
    }


@pytest.fixture
def sample_sj_vacancy_data():
    """
    Sample SuperJob vacancy data as returned by the API.
    
    Returns:
        dict: Sample vacancy data from SuperJob API
    """
    return {
        "objects": [
            {
                "id": 1234567,
                "profession": "Python разработчик",
                "firm_name": "ТехноСофт",
                "payment_from": 80000,
                "payment_to": 120000,
                "candidat": "Требуется Python разработчик",
                "professions": ["Python", "Django", "SQL"],
                "experience": {"id": "1"},
                "link": "https://www.superjob.ru/vakansii/1234567.html"
            },
            {
                "id": 7654321,
                "profession": "Senior Python Developer",
                "firm_name": "Инновационные Технологии",
                "payment_from": 180000,
                "payment_to": 250000,
                "candidat": "Ведущий разработчик",
                "professions": ["Python", "FastAPI", "ML"],
                "experience": {"id": "3"},
                "link": "https://www.superjob.ru/vakansii/7654321.html"
            }
        ]
    }


@pytest.fixture
def sample_vacancies_dataframe():
    """
    Sample vacancies as pandas DataFrame.
    
    Returns:
        pd.DataFrame: Sample vacancies data
    """
    return pd.DataFrame([
        {
            "source": "hh",
            "external_id": "12345678",
            "name": "Python Developer",
            "company": "Test Company LLC",
            "salary": 125000,
            "description": "Опыт работы от 3 лет. Разработка веб-приложений",
            "skills": ["Python", "Django", "PostgreSQL"],
            "experience": "between1And3",
            "url": "https://hh.ru/vacancy/12345678"
        },
        {
            "source": "hh",
            "external_id": "87654321",
            "name": "Senior Python Developer",
            "company": "Big Tech Corp",
            "salary": 200000,
            "description": "Опыт работы от 5 лет. Архитектура системы",
            "skills": ["Python", "FastAPI", "Kubernetes"],
            "experience": "moreThan6",
            "url": "https://hh.ru/vacancy/87654321"
        },
        {
            "source": "sj",
            "external_id": "1234567",
            "name": "Python разработчик",
            "company": "ТехноСофт",
            "salary": 100000,
            "description": "Требуется Python разработчик",
            "skills": ["Python", "Django", "SQL"],
            "experience": "1",
            "url": "https://www.superjob.ru/vakansii/1234567.html"
        }
    ])


@pytest.fixture
def empty_vacancies_dataframe():
    """
    Empty vacancies DataFrame.
    
    Returns:
        pd.DataFrame: Empty DataFrame with correct columns
    """
    return pd.DataFrame(columns=[
        "source", "external_id", "name", "company", "salary",
        "description", "skills", "experience", "url"
    ])


@pytest.fixture
def sample_search_params():
    """
    Sample search parameters for vacancy search.
    
    Returns:
        dict: Sample search parameters
    """
    return {
        "profession": "Python Developer",
        "salary_from": 100000,
        "salary_to": 200000,
        "region": "Москва"
    }


# ==============================================================================
# Mock fixtures for external dependencies
# ==============================================================================

@pytest.fixture
def mock_requests_get(mocker):
    """
    Mock requests.get function.
    
    Returns:
        Mock: Mocked requests.get function
    """
    return mocker.patch("requests.get")


@pytest.fixture
def mock_aiohttp_client_session(mocker):
    """
    Mock aiohttp.ClientSession for async HTTP calls.
    
    Returns:
        Mock: Mocked aiohttp.ClientSession
    """
    mock_session = mocker.patch("aiohttp.ClientSession")
    return mock_session


@pytest.fixture
def mock_psycopg2_connect(mocker):
    """
    Mock psycopg2.connect for database operations.
    
    Returns:
        Mock: Mocked psycopg2.connect function
    """
    return mocker.patch("psycopg2.connect")


@pytest.fixture
def mock_db_connection(mock_psycopg2_connect):
    """
    Mock database connection with cursor.
    
    Returns:
        tuple: (mock_connection, mock_cursor)
    """
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_psycopg2_connect.return_value = mock_conn
    return mock_conn, mock_cursor


# ==============================================================================
# Fixtures for AI/ML testing
# ==============================================================================

@pytest.fixture
def sample_ai_response():
    """
    Sample AI response from Kilo Auto.
    
    Returns:
        dict: Sample AI response
    """
    return {
        "choices": [
            {
                "message": {
                    "content": "Python разработчик требует навыков: Python, Django, FastAPI, SQL, PostgreSQL. Средняя зарплата: 100000-150000 руб."
                }
            }
        ]
    }


@pytest.fixture
def sample_cluster_data():
    """
    Sample data for clustering testing.
    
    Returns:
        pd.DataFrame: DataFrame suitable for clustering
    """
    # Create data with different salary ranges for different clusters
    data = {
        "source": ["hh"] * 10,
        "external_id": [str(i) for i in range(10)],
        "name": ["Junior Dev"] * 3 + ["Middle Dev"] * 4 + ["Senior Dev"] * 3,
        "company": ["Company"] * 10,
        "salary": [50000, 60000, 70000, 100000, 120000, 130000, 140000, 200000, 220000, 250000],
        "description": ["Simple tasks"] * 3 + ["Medium tasks"] * 4 + ["Complex tasks"] * 3,
        "skills": [["Python"]] * 10,
        "experience": ["noExperience"] * 3 + ["between1And3"] * 4 + ["moreThan6"] * 3,
        "url": ["http://example.com"] * 10
    }
    return pd.DataFrame(data)


# ==============================================================================
# Fixtures for bot testing
# ==============================================================================

@pytest.fixture
def mock_message():
    """
    Mock Telegram message object.
    
    Returns:
        Mock: Mocked aiogram Message object
    """
    message = Mock()
    message.from_user = Mock()
    message.from_user.id = 123456789
    message.from_user.full_name = "Test User"
    message.from_user.username = "testuser"
    message.text = "test message"
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_callback():
    """
    Mock Telegram callback query object.
    
    Returns:
        Mock: Mocked aiogram CallbackQuery object
    """
    callback = Mock()
    callback.from_user = Mock()
    callback.from_user.id = 123456789
    callback.from_user.full_name = "Test User"
    callback.from_user.username = "testuser"
    callback.data = "test_callback_data"
    callback.message = Mock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    return callback


@pytest.fixture
def mock_state():
    """
    Mock FSM state object.
    
    Returns:
        Mock: Mocked FSMContext object
    """
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state


# ==============================================================================
# Fixtures for error testing
# ==============================================================================

@pytest.fixture
def network_error():
    """
    Network error for testing.
    
    Returns:
        Exception: Network-related exception
    """
    from requests.exceptions import ConnectionError
    return ConnectionError("Network connection failed")


@pytest.fixture
def timeout_error():
    """
    Timeout error for testing.
    
    Returns:
        Exception: Timeout exception
    """
    from requests.exceptions import Timeout
    return Timeout("Request timeout")


@pytest.fixture
def api_error_response():
    """
    Sample API error response.
    
    Returns:
        dict: Sample error response
    """
    return {"errors": [{"value": "Invalid token"}], "request_id": "12345"}


# ==============================================================================
# Temporary directory fixtures
# ==============================================================================

@pytest.fixture
def temp_db_file():
    """
    Create a temporary database file for testing.
    
    Returns:
        str: Path to temporary database file
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def temp_env_file(mock_env_vars):
    """
    Create a temporary .env file for testing.
    
    Returns:
        str: Path to temporary env file
    """
    fd, path = tempfile.mkstemp(suffix=".env")
    
    with os.fdopen(fd, "w") as f:
        for key, value in mock_env_vars.items():
            f.write(f"{key}={value}\n")
    
    yield path
    
    if os.path.exists(path):
        os.remove(path)


# ==============================================================================
# Helper functions for tests
# ==============================================================================

def create_mock_response(status_code: int = 200, json_data: dict = None) -> Mock:
    """
    Create a mock HTTP response.
    
    Args:
        status_code: HTTP status code
        json_data: JSON data to return
    
    Returns:
        Mock: Mocked response object
    """
    response = Mock()
    response.status_code = status_code
    response.json = Mock(return_value=json_data or {})
    return response


def assert_valid_vacancy_dataframe(df: pd.DataFrame, min_rows: int = 0):
    """
    Assert that a DataFrame has valid vacancy structure.
    
    Args:
        df: DataFrame to validate
        min_rows: Minimum number of rows expected
    """
    required_columns = [
        "source", "external_id", "name", "company", "salary",
        "description", "skills", "experience", "url"
    ]
    
    assert isinstance(df, pd.DataFrame), "Expected pandas DataFrame"
    assert len(df) >= min_rows, f"Expected at least {min_rows} rows"
    
    for col in required_columns:
        assert col in df.columns, f"Missing required column: {col}"


# ==============================================================================
# Pytest hooks for custom behavior
# ==============================================================================

def pytest_configure(config):
    """
    Pytest configuration hook.
    
    Register custom markers.
    """
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (external dependencies)"
    )
    config.addinivalue_line(
        "markers", "functional: Functional tests (end-to-end)"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test items after collection.
    
    Add markers based on test location.
    """
    for item in items:
        # Auto-mark tests based on their location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "functional" in str(item.fspath):
            item.add_marker(pytest.mark.functional)
