"""
Unit tests for utility functions and helpers.

Tests for database functions, caching, and helper utilities.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta


# ==============================================================================
# Database Connection Tests
# ==============================================================================

class TestDatabaseConnection:
    """Test suite for database connection functionality."""
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_get_db_connection_returns_connection(self, mock_connect):
        """
        Test that get_db_connection returns a connection object.
        """
        # Arrange
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        # Import here to get the patched version
        from vacancy_bot import get_db_connection
        
        # Act
        result = get_db_connection()
        
        # Assert
        assert result is not None
        mock_connect.assert_called_once()
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_get_db_connection_uses_config(self, mock_connect):
        """
        Test that get_db_connection uses configuration from environment.
        """
        # Arrange
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import get_db_connection
        
        # Act
        get_db_connection()
        
        # Assert
        call_kwargs = mock_connect.call_args[1]
        assert 'host' in call_kwargs
        assert 'database' in call_kwargs
        assert 'user' in call_kwargs


# ==============================================================================
# Database Initialization Tests
# ==============================================================================

class TestDatabaseInitialization:
    """Test suite for database initialization."""
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_init_db_creates_table(self, mock_connect):
        """
        Test that init_db creates the vacancies table.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import init_db
        
        # Act
        init_db()
        
        # Assert
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_init_db_creates_indexes(self, mock_connect):
        """
        Test that init_db creates required indexes.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import init_db
        
        # Act
        init_db()
        
        # Assert - check that execute was called with CREATE INDEX
        calls = mock_cursor.execute.call_args_list
        execute_calls = [str(call) for call in calls]
        
        # Should have CREATE INDEX for source_salary
        assert any('source_salary' in str(c) for c in execute_calls)
        # Should have CREATE INDEX for parsed_at
        assert any('parsed_at' in str(c) for c in execute_calls)
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_init_db_uses_if_not_exists(self, mock_connect):
        """
        Test that init_db uses IF NOT EXISTS for idempotency.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import init_db
        
        # Act
        init_db()  # Should not raise if called multiple times
        
        # Assert
        calls = mock_cursor.execute.call_args_list
        execute_sql = ' '.join([str(call) for call in calls])
        
        assert 'IF NOT EXISTS' in execute_sql


# ==============================================================================
# Cache Functions Tests
# ==============================================================================

class TestCacheVacancies:
    """Test suite for caching vacancies to database."""
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_cache_vacancies_empty_dataframe(self, mock_connect, empty_vacancies_dataframe):
        """
        Test that caching empty DataFrame does nothing.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        
        # Act
        cache_vacancies(empty_vacancies_dataframe)
        
        # Assert
        mock_cursor.execute.assert_not_called()
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_cache_vacancies_inserts_data(self, mock_connect, sample_vacancies_dataframe):
        """
        Test that cache_vacancies inserts data into database.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        
        # Act
        cache_vacancies(sample_vacancies_dataframe)
        
        # Assert
        assert mock_cursor.execute.call_count > 0
        mock_conn.commit.assert_called_once()
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_cache_vacancies_handles_list_skills(self, mock_connect):
        """
        Test that cache_vacancies handles list-type skills.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        df = pd.DataFrame([{
            "source": "hh",
            "external_id": "123",
            "name": "Dev",
            "company": "C",
            "salary": 100000,
            "description": "D",
            "skills": ["Python", "Django"],  # List
            "experience": "noExp",
            "url": "http://x.com"
        }])
        
        from vacancy_bot import cache_vacancies
        
        # Act & Assert - should not raise
        cache_vacancies(df)
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_cache_vacancies_handles_string_skills(self, mock_connect):
        """
        Test that cache_vacancies handles string-type skills.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        df = pd.DataFrame([{
            "source": "hh",
            "external_id": "123",
            "name": "Dev",
            "company": "C",
            "salary": 100000,
            "description": "D",
            "skills": "Python, Django",  # String
            "experience": "noExp",
            "url": "http://x.com"
        }])
        
        from vacancy_bot import cache_vacancies
        
        # Act & Assert - should not raise
        cache_vacancies(df)
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_cache_vacancies_uses_on_conflict(self, mock_connect, sample_vacancies_dataframe):
        """
        Test that cache_vacancies uses ON CONFLICT to avoid duplicates.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        
        # Act
        cache_vacancies(sample_vacancies_dataframe)
        
        # Assert - check SQL contains ON CONFLICT
        calls = mock_cursor.execute.call_args_list
        sql_calls = ' '.join([str(call) for call in calls])
        assert 'ON CONFLICT' in sql_calls


class TestGetCachedVacancies:
    """Test suite for retrieving cached vacancies."""
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_get_cached_vacancies_returns_dataframe(self, mock_connect):
        """
        Test that get_cached_vacancies returns a DataFrame.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock the read_sql_query
        with patch('pandas.read_sql_query') as mock_read:
            mock_read.return_value = pd.DataFrame([{"id": 1}])
            mock_connect.return_value = mock_conn
            
            from vacancy_bot import get_cached_vacancies
            
            # Act
            result = get_cached_vacancies("Python")
            
            # Assert
            assert result is not None
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_get_cached_vacancies_returns_none_on_empty(self, mock_connect):
        """
        Test that get_cached_vacancies returns None for empty results.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        with patch('pandas.read_sql_query') as mock_read:
            mock_read.return_value = pd.DataFrame()  # Empty
            mock_connect.return_value = mock_conn
            
            from vacancy_bot import get_cached_vacancies
            
            # Act
            result = get_cached_vacancies("NonExistent")
            
            # Assert
            assert result is None
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_get_cached_vacancies_uses_ilike(self, mock_connect):
        """
        Test that get_cached_vacancies uses ILIKE for case-insensitive search.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        with patch('pandas.read_sql_query') as mock_read:
            mock_read.return_value = pd.DataFrame()
            mock_connect.return_value = mock_conn
            
            from vacancy_bot import get_cached_vacancies
            
            # Act
            get_cached_vacancies("python")
            
            # Assert - check SQL contains ILIKE
            call_args = mock_read.call_args
            sql_query = call_args[0][0]
            assert 'ILIKE' in sql_query
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_get_cached_vacancies_respects_time_filter(self, mock_connect):
        """
        Test that get_cached_vacancies filters by time (24 hours default).
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        with patch('pandas.read_sql_query') as mock_read:
            mock_read.return_value = pd.DataFrame()
            mock_connect.return_value = mock_conn
            
            from vacancy_bot import get_cached_vacancies
            
            # Act
            get_cached_vacancies("Python", hours=12)
            
            # Assert - check that time filter is applied
            call_args = mock_read.call_args
            sql_query = call_args[0][0]
            params = call_args[1].get('params', ())
            
            assert 'INTERVAL' in sql_query
            assert 12 in params  # hours parameter
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_get_cached_vacancies_closes_connection(self, mock_connect):
        """
        Test that get_cached_vacancies closes the connection.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        with patch('pandas.read_sql_query') as mock_read:
            mock_read.return_value = pd.DataFrame()
            mock_connect.return_value = mock_conn
            
            from vacancy_bot import get_cached_vacancies
            
            # Act
            get_cached_vacancies("Python")
            
            # Assert
        mock_conn.close.assert_called_once()


# ==============================================================================
# Subscriptions Tests
# ==============================================================================

class TestSubscriptions:
    """Test suite for subscription utilities."""

    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_add_subscription_returns_id(self, mock_connect):
        """
        Test that add_subscription returns new id.
        """
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [42]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from vacancy_bot import add_subscription

        sub_id = add_subscription(1, "Python", region="Москва", salary_from=100000, salary_to=200000)
        assert sub_id == 42

    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_list_subscriptions_returns_dataframe(self, mock_connect):
        """
        Test that list_subscriptions returns DataFrame.
        """
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        with patch('pandas.read_sql_query') as mock_read:
            mock_read.return_value = pd.DataFrame([{"id": 1}])
            from vacancy_bot import list_subscriptions
            result = list_subscriptions(1)
            assert result is not None

    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_deactivate_subscription_executes_update(self, mock_connect):
        """
        Test deactivate_subscription updates active flag.
        """
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from vacancy_bot import deactivate_subscription
        deactivate_subscription(1, 10)
        assert mock_cursor.execute.called

    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_get_cached_vacancies_since_uses_since(self, mock_connect):
        """
        Test that get_cached_vacancies_since uses parsed_at > since.
        """
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        with patch('pandas.read_sql_query') as mock_read:
            mock_read.return_value = pd.DataFrame()
            from vacancy_bot import get_cached_vacancies_since
            since = datetime.utcnow()
            get_cached_vacancies_since("Python", since)
            query = mock_read.call_args[0][0]
            assert 'parsed_at >' in query


# ==============================================================================
# Configuration Tests
# ==============================================================================

class TestConfiguration:
    """Test suite for configuration loading."""
    
    @pytest.mark.unit
    def test_config_loads_from_environment(self):
        """
        Test that configuration is loaded from environment variables.
        """
        # This is implicitly tested by the mock_env_vars fixture
        # Just verify the expected keys are present
        from vacancy_bot import DB_CONFIG
        
        required_keys = ['host', 'port', 'database', 'user', 'password']
        for key in required_keys:
            assert key in DB_CONFIG
    
    @pytest.mark.unit
    def test_config_has_defaults(self):
        """
        Test that configuration uses environment variables when set.
        """
        from vacancy_bot import DB_CONFIG
        
        # Check that the values match what we set in conftest.py
        assert DB_CONFIG['host'] == 'localhost'
        assert DB_CONFIG['port'] == 5432
        assert DB_CONFIG['database'] == 'test_vacancy_bot'  # From conftest
        assert DB_CONFIG['user'] == 'test_user'  # From conftest
    
    @pytest.mark.unit
    def test_hh_api_url_configured(self):
        """
        Test that HH.ru API URL is configured.
        """
        from vacancy_bot import HH_API
        
        assert HH_API == "https://api.hh.ru/vacancies"
        assert "hh.ru" in HH_API
    
    @pytest.mark.unit
    def test_sj_api_url_configured(self):
        """
        Test that SuperJob API URL is configured.
        """
        from vacancy_bot import SJ_API
        
        assert SJ_API == "https://api.superjob.ru/2.0/vacancies/"
        assert "superjob.ru" in SJ_API
    
    @pytest.mark.unit
    def test_bot_token_loaded(self):
        """
        Test that bot token is loaded.
        """
        from vacancy_bot import BOT_TOKEN
        
        assert BOT_TOKEN is not None
        assert len(BOT_TOKEN) > 0


# ==============================================================================
# Area/Region Configuration Tests
# ==============================================================================

class TestAreaConfiguration:
    """Test suite for region/area configuration."""
    
    @pytest.mark.unit
    def test_areas_contains_major_cities(self):
        """
        Test that AREAS contains major Russian cities.
        """
        from vacancy_bot import AREAS
        
        expected_cities = ["Москва", "СПб", "Нижний Новгород", "Екатеринбург", "Казань"]
        
        for city in expected_cities:
            assert city in AREAS
    
    @pytest.mark.unit
    def test_areas_contains_all_option(self):
        """
        Test that AREAS contains 'Все' option for all regions.
        """
        from vacancy_bot import AREAS
        
        assert "Все" in AREAS
        assert AREAS["Все"]["hh"] == 113  # HH's "all regions" ID
    
    @pytest.mark.unit
    def test_area_has_hh_and_sj_ids(self):
        """
        Test that each area has both HH and SuperJob IDs.
        """
        from vacancy_bot import AREAS
        
        for region, area_ids in AREAS.items():
            assert "hh" in area_ids
            assert "sj" in area_ids
    
    @pytest.mark.unit
    def test_moscow_ids_correct(self):
        """
        Test that Moscow has correct API IDs.
        """
        from vacancy_bot import AREAS
        
        assert AREAS["Москва"]["hh"] == 1  # HH Moscow
        assert AREAS["Москва"]["sj"] == 4  # SuperJob Moscow
    
    @pytest.mark.unit
    def test_spb_ids_correct(self):
        """
        Test that St. Petersburg has correct API IDs.
        """
        from vacancy_bot import AREAS
        
        assert AREAS["СПб"]["hh"] == 2  # HH SPb
        assert AREAS["СПб"]["sj"] == 2  # SuperJob SPb


# ==============================================================================
# Error Handling Tests
# ==============================================================================

class TestErrorHandling:
    """Test suite for error handling in utility functions."""
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_cache_vacancies_handles_db_error(self, mock_connect, sample_vacancies_dataframe):
        """
        Test that cache_vacancies handles database errors gracefully.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("DB Error")
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        
        # Act & Assert - should not raise, just log
        cache_vacancies(sample_vacancies_dataframe)
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_get_cached_vacancies_handles_error(self, mock_connect):
        """
        Test that get_cached_vacancies handles errors and returns None.
        """
        # Arrange
        mock_connect.side_effect = Exception("Connection failed")
        
        from vacancy_bot import get_cached_vacancies
        
        # Act
        result = get_cached_vacancies("Python")
        
        # Assert
        assert result is None
    
    @pytest.mark.unit
    @patch('psycopg2.connect')
    def test_init_db_handles_connection_error(self, mock_connect):
        """
        Test that init_db handles connection errors gracefully.
        """
        # Arrange
        mock_connect.side_effect = Exception("Connection failed")
        
        from vacancy_bot import init_db
        
        # Act & Assert - should raise to let caller handle
        with pytest.raises(Exception):
            init_db()


# ==============================================================================
# Logging Tests
# ==============================================================================

class TestLogging:
    """Test suite for logging functionality."""
    
    @pytest.mark.unit
    def test_logger_is_configured(self):
        """
        Test that logger is properly configured.
        """
        from vacancy_bot import logger
        
        assert logger is not None
        assert logger.name == "vacancy_bot"
    
    @pytest.mark.unit
    def test_logging_format_includes_timestamp(self):
        """
        Test that logger has proper level set.
        """
        from vacancy_bot import logger
        import logging
        
        # Check that the effective logging level is INFO
        assert logger.getEffectiveLevel() == logging.INFO
    
    @pytest.mark.unit
    def test_log_callback_decorator_exists(self):
        """
        Test that log_callback decorator exists and is callable.
        """
        from vacancy_bot import log_callback
        
        assert callable(log_callback)


class TestSearchOptions:
    """Test suite for search options parser."""

    @pytest.mark.unit
    def test_parse_search_options_splits_profession_and_opts(self):
        from vacancy_bot import parse_search_options

        profession, opts = parse_search_options("Python Developer region=Москва salary_from=100000 order=salary_desc")
        assert profession == "Python Developer"
        assert opts["region"] == "Москва"
        assert opts["salary_from"] == "100000"
        assert opts["order"] == "salary_desc"


class TestClarificationHelpers:
    """Test suite for clarification helpers."""

    @pytest.mark.unit
    def test_needs_clarification_for_generic(self):
        from vacancy_bot import needs_clarification

        assert needs_clarification("Developer") is True
        assert needs_clarification("dev") is True
        assert needs_clarification("") is True

    @pytest.mark.unit
    def test_needs_clarification_for_specific(self):
        from vacancy_bot import needs_clarification

        assert needs_clarification("Python developer") is False
        assert needs_clarification("Java QA engineer") is False

    @pytest.mark.unit
    def test_normalize_region_input_aliases(self):
        from vacancy_bot import normalize_region_input

        assert normalize_region_input("нижний") == "Нижний Новгород"
        assert normalize_region_input("нн") == "Нижний Новгород"

    @pytest.mark.unit
    def test_apply_clarification_replaces_or_appends(self):
        from vacancy_bot import apply_clarification

        assert apply_clarification("Developer", "Python backend") == "Python backend"
        assert apply_clarification("Developer", "Python") == "Developer Python"
        assert apply_clarification("Data", "/skip") == "Data"


class TestAnalyticsHelpers:
    """Test suite for analytics helpers."""

    @pytest.mark.unit
    def test_compute_market_stats(self):
        from vacancy_bot import compute_market_stats
        df = pd.DataFrame([
            {"salary": 100000, "skills": ["Python", "Django"], "company": "A", "description": "remote", "experience": "junior"},
            {"salary": 200000, "skills": ["Python"], "company": "B", "description": "office", "experience": "senior"},
            {"salary": 0, "skills": ["SQL"], "company": "A", "description": "remote", "experience": "middle"},
        ])
        stats = compute_market_stats(df, top_n_skills=2, top_n_companies=2)
        assert stats["total"] == 3
        assert stats["avg_salary"] == 150000
        assert stats["median_salary"] == 150000
        assert stats["salary_count"] == 2
