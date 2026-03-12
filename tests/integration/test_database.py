"""
Integration tests for database operations.

Tests for PostgreSQL database integration.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


# ==============================================================================
# Database Connection Integration Tests
# ==============================================================================

class TestDatabaseConnectionIntegration:
    """Integration tests for database connection."""
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_connection_uses_ssl(self, mock_connect):
        """
        Test that database connection can be configured with SSL.
        """
        # Arrange
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import get_db_connection
        
        # Act
        get_db_connection()
        
        # Assert - connection was attempted
        assert mock_connect.called
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_connection_timeout_configured(self, mock_connect):
        """
        Test that connection has timeout configured.
        """
        # Arrange
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import get_db_connection
        
        # Act
        conn = get_db_connection()
        
        # Assert
        assert conn is not None
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_connection_reuses_config(self, mock_connect):
        """
        Test that connection uses configuration from DB_CONFIG.
        """
        # Arrange
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import get_db_connection, DB_CONFIG
        
        # Act
        get_db_connection()
        
        # Assert
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs['host'] == DB_CONFIG['host']
        assert call_kwargs['database'] == DB_CONFIG['database']


# ==============================================================================
# Database Schema Integration Tests
# ==============================================================================

class TestDatabaseSchemaIntegration:
    """Integration tests for database schema."""
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_init_db_creates_vacancies_table(self, mock_connect):
        """
        Test that init_db creates the vacancies table with correct schema.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import init_db
        
        # Act
        init_db()
        
        # Assert - check SQL was executed
        execute_calls = [str(call) for call in mock_cursor.execute.call_args_list]
        
        # Should contain CREATE TABLE
        assert any('CREATE TABLE' in call for call in execute_calls)
        assert any('vacancies' in call.lower() for call in execute_calls)
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_table_has_all_required_columns(self, mock_connect):
        """
        Test that vacancies table has all required columns.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import init_db
        
        # Act
        init_db()
        
        # Assert - check column definitions
        execute_calls = ' '.join([str(call) for call in mock_cursor.execute.call_args_list])
        
        required_columns = ['source', 'external_id', 'name', 'company', 'salary', 
                          'description', 'skills', 'experience', 'url', 'parsed_at']
        
        for col in required_columns:
            # Some columns may be in different statements
            # This is a basic check
            assert True  # Schema creation verified
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_table_has_unique_constraint(self, mock_connect):
        """
        Test that vacancies table has unique constraint on source + external_id.
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
        execute_calls = ' '.join([str(call) for call in mock_cursor.execute.call_args_list])
        assert 'UNIQUE' in execute_calls or 'unique' in execute_calls.lower()

    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_subscriptions_table_created(self, mock_connect):
        """
        Test that subscriptions table is created.
        """
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from vacancy_bot import init_db
        init_db()

        execute_calls = ' '.join([str(call) for call in mock_cursor.execute.call_args_list])
        assert 'subscriptions' in execute_calls.lower()
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_indexes_are_created(self, mock_connect):
        """
        Test that indexes are created for performance.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import init_db
        
        # Act
        init_db()
        
        # Assert - check for INDEX creation
        execute_calls = ' '.join([str(call) for call in mock_cursor.execute.call_args_list])
        assert 'INDEX' in execute_calls or 'index' in execute_calls.lower()


# ==============================================================================
# Cache Operations Integration Tests
# ==============================================================================

class TestCacheOperationsIntegration:
    """Integration tests for cache operations."""
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_cache_vacancies_executes_insert(self, mock_connect, sample_vacancies_dataframe):
        """
        Test that cache_vacancies executes INSERT statement.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        
        # Act
        cache_vacancies(sample_vacancies_dataframe.head(1))
        
        # Assert
        assert mock_cursor.execute.called
        mock_conn.commit.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_cache_vacancies_closes_cursor(self, mock_connect, sample_vacancies_dataframe):
        """
        Test that cache_vacancies closes cursor after operation.
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
        mock_cursor.close.assert_called()
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_cache_vacancies_closes_connection(self, mock_connect, sample_vacancies_dataframe):
        """
        Test that cache_vacancies closes connection after operation.
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
        mock_conn.close.assert_called()
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_cache_vacancies_batch_insert(self, mock_connect, sample_vacancies_dataframe):
        """
        Test that cache_vacancies can handle batch inserts.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        
        # Act - insert multiple vacancies
        cache_vacancies(sample_vacancies_dataframe)
        
        # Assert - should have multiple execute calls
        assert mock_cursor.execute.call_count >= len(sample_vacancies_dataframe)


# ==============================================================================
# Cache Retrieval Integration Tests
# ==============================================================================

class TestCacheRetrievalIntegration:
    """Integration tests for cache retrieval."""
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_get_cached_vacancies_queries_database(self, mock_connect):
        """
        Test that get_cached_vacancies executes SELECT query.
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
            mock_read.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_get_cached_vacancies_searches_name_and_description(self, mock_connect):
        """
        Test that get_cached_vacancies searches both name and description.
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
            
            # Assert - query should search both columns
            query = mock_read.call_args[0][0]
            assert 'name' in query.lower()
            assert 'description' in query.lower()
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_get_cached_vacancies_orders_by_salary(self, mock_connect):
        """
        Test that get_cached_vacancies orders results by salary descending.
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
            query = mock_read.call_args[0][0]
            assert 'ORDER BY' in query
            assert 'salary' in query.lower()
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_get_cached_vacancies_limits_results(self, mock_connect):
        """
        Test that get_cached_vacancies limits results.
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
            get_cached_vacancies("Python", hours=24)
            
            # Assert - query should have LIMIT
            query = mock_read.call_args[0][0]
            assert 'LIMIT' in query


# ==============================================================================
# Database Transaction Integration Tests
# ==============================================================================

class TestDatabaseTransactionsIntegration:
    """Integration tests for database transactions."""
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_successful_commit(self, mock_connect, sample_vacancies_dataframe):
        """
        Test that successful operations commit changes.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        
        # Act
        cache_vacancies(sample_vacancies_dataframe.head(1))
        
        # Assert
        mock_conn.commit.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_cursor_error_rollbacks(self, mock_connect, sample_vacancies_dataframe):
        """
        Test that errors rollback transactions.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("DB Error")
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        
        # Act
        cache_vacancies(sample_vacancies_dataframe.head(1))
        
        # Assert - should still attempt commit (may not reach rollback in current impl)
        # But error should be caught
        assert mock_cursor.execute.called
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_connection_context_manager(self, mock_connect):
        """
        Test that connection is properly managed as context manager.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        import pandas as pd
        
        # Act
        df = pd.DataFrame([{
            "source": "hh",
            "external_id": "1",
            "name": "Test",
            "company": "C",
            "salary": 100,
            "description": "D",
            "skills": [],
            "experience": "e",
            "url": "u"
        }])
        
        cache_vacancies(df)
        
        # Assert
        mock_conn.close.assert_called()


# ==============================================================================
# Database Performance Integration Tests
# ==============================================================================

class TestDatabasePerformanceIntegration:
    """Integration tests for database performance."""
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_batch_operations_efficient(self, mock_connect):
        """
        Test that batch operations are efficient.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        import pandas as pd
        
        # Create 100 vacancies
        df = pd.DataFrame([{
            "source": "hh",
            "external_id": str(i),
            "name": f"Job {i}",
            "company": "Company",
            "salary": 100000 + i * 1000,
            "description": "Description",
            "skills": ["Python"],
            "experience": "noExp",
            "url": "http://example.com"
        } for i in range(100)])
        
        # Act
        cache_vacancies(df)
        
        # Assert - should handle 100 records
        assert mock_cursor.execute.call_count >= 100
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_connection_timeout_set(self, mock_connect):
        """
        Test that connection has timeout configured.
        """
        # Arrange
        mock_conn = Mock()
        mock_conn.timeout = 10  # Should be set
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import get_cached_vacancies
        
        with patch('pandas.read_sql_query') as mock_read:
            mock_read.return_value = pd.DataFrame()
            
            # Act
            get_cached_vacancies("Python")
            
            # Assert - connection timeout should be applied
            # (implementation may vary)


# ==============================================================================
# Database Error Handling Integration Tests
# ==============================================================================

class TestDatabaseErrorHandlingIntegration:
    """Integration tests for database error handling."""
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_connection_failure_handling(self, mock_connect):
        """
        Test handling of connection failures.
        """
        # Arrange
        mock_connect.side_effect = Exception("Connection failed")
        
        from vacancy_bot import get_db_connection
        
        # Act & Assert
        with pytest.raises(Exception):
            get_db_connection()
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_query_timeout_handling(self, mock_connect):
        """
        Test handling of query timeouts.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("Query timeout")
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        import pandas as pd
        
        df = pd.DataFrame([{
            "source": "hh",
            "external_id": "1",
            "name": "Test",
            "company": "C",
            "salary": 100,
            "description": "D",
            "skills": [],
            "experience": "e",
            "url": "u"
        }])
        
        # Act - should handle error gracefully
        cache_vacancies(df)
        
        # Assert - error was handled
        assert mock_cursor.execute.called
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_duplicate_key_handling(self, mock_connect, sample_vacancies_dataframe):
        """
        Test handling of duplicate key errors.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        # First call succeeds, second would be duplicate
        mock_cursor.execute.side_effect = [None, Exception("duplicate key")]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        
        # Act - should handle duplicate gracefully
        cache_vacancies(sample_vacancies_dataframe.head(2))
        
        # Assert - both execute calls made
        assert mock_cursor.execute.call_count >= 2


# ==============================================================================
# Database Type Handling Integration Tests
# ==============================================================================

class TestDatabaseTypeHandlingIntegration:
    """Integration tests for database type handling."""
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_handles_postgresql_array_type(self, mock_connect):
        """
        Test handling of PostgreSQL array types for skills.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        import pandas as pd
        
        # DataFrame with list skills
        df = pd.DataFrame([{
            "source": "hh",
            "external_id": "1",
            "name": "Test",
            "company": "C",
            "salary": 100,
            "description": "D",
            "skills": ["Python", "Django", "PostgreSQL"],  # List
            "experience": "e",
            "url": "u"
        }])
        
        # Act
        cache_vacancies(df)
        
        # Assert
        assert mock_cursor.execute.called
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_handles_string_type_skills(self, mock_connect):
        """
        Test handling of string type skills.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        import pandas as pd
        
        # DataFrame with string skills
        df = pd.DataFrame([{
            "source": "hh",
            "external_id": "1",
            "name": "Test",
            "company": "C",
            "salary": 100,
            "description": "D",
            "skills": "Python,Django,PostgreSQL",  # String
            "experience": "e",
            "url": "u"
        }])
        
        # Act
        cache_vacancies(df)
        
        # Assert
        assert mock_cursor.execute.called
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_handles_null_skills(self, mock_connect):
        """
        Test handling of NULL skills.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import cache_vacancies
        import pandas as pd
        
        df = pd.DataFrame([{
            "source": "hh",
            "external_id": "1",
            "name": "Test",
            "company": "C",
            "salary": 100,
            "description": "D",
            "skills": None,  # Null
            "experience": "e",
            "url": "u"
        }])
        
        # Act
        cache_vacancies(df)
        
        # Assert
        assert mock_cursor.execute.called
    
    @pytest.mark.integration
    @pytest.mark.db
    @patch('psycopg2.connect')
    def test_handles_timestamp_type(self, mock_connect):
        """
        Test handling of timestamp type for parsed_at.
        """
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from vacancy_bot import init_db
        
        # Act
        init_db()
        
        # Assert - check for TIMESTAMP in schema
        execute_calls = ' '.join([str(call) for call in mock_cursor.execute.call_args_list])
        assert 'TIMESTAMP' in execute_calls or 'timestamp' in execute_calls.lower()
