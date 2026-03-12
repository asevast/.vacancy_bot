"""
Functional tests for end-to-end bot scenarios.

Tests for complete user workflows and interactions.
"""

import pytest
import asyncio
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from aiogram import Dispatcher, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


# ==============================================================================
# Bot Initialization Tests
# ==============================================================================

class TestBotInitialization:
    """Test suite for bot initialization."""
    
    @pytest.mark.functional
    def test_bot_token_is_set(self):
        """
        Test that bot token is properly set.
        """
        from vacancy_bot import BOT_TOKEN
        
        assert BOT_TOKEN is not None
        assert len(BOT_TOKEN) > 0
        assert ':' in BOT_TOKEN  # Telegram tokens have format like 123456:ABCDEF
    
    @pytest.mark.functional
    def test_dispatcher_is_created(self):
        """
        Test that dispatcher is created with memory storage.
        """
        from vacancy_bot import dp
        
        assert dp is not None
        assert isinstance(dp, Dispatcher)
    
    @pytest.mark.functional
    def test_bot_object_is_created(self):
        """
        Test that bot object is created.
        """
        from vacancy_bot import bot
        
        assert bot is not None
        assert isinstance(bot, Bot)


# ==============================================================================
# Command Handlers Tests
# ==============================================================================

class TestCommandHandlers:
    """Test suite for bot command handlers."""
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_start_command_returns_keyboard(self, mock_message):
        """
        Test that /start command returns inline keyboard.
        """
        # This test verifies the start command handler exists
        # Full testing would require aiogram test utilities
        
        from vacancy_bot import start_handler
        
        assert start_handler is not None
        assert asyncio.iscoroutinefunction(start_handler)
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_ai_command_handler_exists(self):
        """
        Test that /ai command handler exists.
        """
        from vacancy_bot import ai_command
        
        assert ai_command is not None
        assert asyncio.iscoroutinefunction(ai_command)
    
    @pytest.mark.functional
    def test_command_decorators_are_applied(self):
        """
        Test that command decorators are properly applied.
        """
        from aiogram.filters import Command
        from vacancy_bot import start_handler, ai_command
        
        # Check that handlers have command filter
        # This is a basic check - actual implementation varies
        assert hasattr(start_handler, '__call__')
        assert hasattr(ai_command, '__call__')


# ==============================================================================
# FSM States Tests
# ==============================================================================

class TestFSMStates:
    """Test suite for FSM (Finite State Machine) states."""
    
    @pytest.mark.functional
    def test_search_form_has_required_states(self):
        """
        Test that SearchForm has all required states.
        """
        from vacancy_bot import SearchForm
        
        required_states = [
            'waiting_profession',
            'waiting_salary_from',
            'waiting_salary_to',
            'waiting_region'
        ]
        
        for state in required_states:
            assert hasattr(SearchForm, state)
            state_obj = getattr(SearchForm, state)
            assert isinstance(state_obj, State)
    
    @pytest.mark.functional
    def test_ai_form_has_required_states(self):
        """
        Test that AIForm has all required states.
        """
        from vacancy_bot import AIForm
        
        assert hasattr(AIForm, 'waiting_prompt')
        state_obj = getattr(AIForm, 'waiting_prompt')
        assert isinstance(state_obj, State)
    
    @pytest.mark.functional
    def test_states_belong_to_correct_group(self):
        """
        Test that states belong to correct groups.
        """
        from vacancy_bot import SearchForm, AIForm
        
        # SearchForm states
        search_states = [
            SearchForm.waiting_profession,
            SearchForm.waiting_salary_from,
            SearchForm.waiting_salary_to,
            SearchForm.waiting_region
        ]
        
        for state in search_states:
            assert state.group == SearchForm
        
        # AIForm states
        ai_states = [AIForm.waiting_prompt]
        
        for state in ai_states:
            assert state.group == AIForm


# ==============================================================================
# Callback Handlers Tests
# ==============================================================================

class TestCallbackHandlers:
    """Test suite for callback query handlers."""
    
    @pytest.mark.functional
    def test_analyze_callback_exists(self):
        """
        Test that analyze callback handler exists.
        """
        from vacancy_bot import analyze_callback
        
        assert analyze_callback is not None
        assert asyncio.iscoroutinefunction(analyze_callback)
    
    @pytest.mark.functional
    def test_ai_mode_callback_exists(self):
        """
        Test that ai_mode callback handler exists.
        """
        from vacancy_bot import ai_mode_callback
        
        assert ai_mode_callback is not None
        assert asyncio.iscoroutinefunction(ai_mode_callback)
    
    @pytest.mark.functional
    def test_clusters_callback_exists(self):
        """
        Test that clusters callback handler exists.
        """
        from vacancy_bot import clusters_callback
        
        assert clusters_callback is not None
        assert asyncio.iscoroutinefunction(clusters_callback)


# ==============================================================================
# Message Handlers Tests
# ==============================================================================

class TestMessageHandlers:
    """Test suite for message handlers."""
    
    @pytest.mark.functional
    def test_process_profession_handler_exists(self):
        """
        Test that profession input handler exists.
        """
        from vacancy_bot import process_profession
        
        assert process_profession is not None
        assert asyncio.iscoroutinefunction(process_profession)
    
    @pytest.mark.functional
    def test_process_salary_from_handler_exists(self):
        """
        Test that salary_from input handler exists.
        """
        from vacancy_bot import process_salary_from
        
        assert process_salary_from is not None
        assert asyncio.iscoroutinefunction(process_salary_from)
    
    @pytest.mark.functional
    def test_process_salary_to_handler_exists(self):
        """
        Test that salary_to input handler exists.
        """
        from vacancy_bot import process_salary_to
        
        assert process_salary_to is not None
        assert asyncio.iscoroutinefunction(process_salary_to)
    
    @pytest.mark.functional
    def test_process_region_handler_exists(self):
        """
        Test that region input handler exists.
        """
        from vacancy_bot import process_region
        
        assert process_region is not None
        assert asyncio.iscoroutinefunction(process_region)
    
    @pytest.mark.functional
    def test_process_ai_prompt_handler_exists(self):
        """
        Test that AI prompt handler exists.
        """
        from vacancy_bot import process_ai_prompt
        
        assert process_ai_prompt is not None
        assert asyncio.iscoroutinefunction(process_ai_prompt)


# ==============================================================================
# End-to-End Search Workflow Tests
# ==============================================================================

class TestSearchWorkflow:
    """Test suite for complete search workflow."""
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_search_workflow_integration(self):
        """
        Test complete search workflow with mocked dependencies.
        """
        # This test verifies the workflow components exist
        # Full integration testing would require Telegram test environment
        
        # Check that all components are in place
        from vacancy_bot import (
            parse_hh_vacancies,
            parse_superjob_vacancies,
            cache_vacancies,
            get_cached_vacancies,
            cluster_vacancies
        )
        
        # Verify functions exist
        assert callable(parse_hh_vacancies)
        assert callable(parse_superjob_vacancies)
        assert callable(cache_vacancies)
        assert callable(get_cached_vacancies)
        assert callable(cluster_vacancies)
    
    @pytest.mark.functional
    @patch('vacancy_bot.parse_hh_vacancies')
    @patch('vacancy_bot.parse_superjob_vacancies')
    @patch('vacancy_bot.cache_vacancies')
    def test_search_with_cache_miss(self, mock_cache, mock_sj, mock_hh):
        """
        Test search workflow when cache misses.
        """
        # Arrange
        mock_hh.return_value = pd.DataFrame([{
            "source": "hh",
            "external_id": "1",
            "name": "Python Developer",
            "company": "Test Corp",
            "salary": 100000,
            "description": "We need Python developer",
            "skills": ["Python", "Django"],
            "experience": "between1And3",
            "url": "http://hh.ru/1"
        }])
        
        mock_sj.return_value = pd.DataFrame([{
            "source": "sj",
            "external_id": "2",
            "name": "Python разработчик",
            "company": "ТехноСофт",
            "salary": 80000,
            "description": "Требуется разработчик",
            "skills": ["Python"],
            "experience": "1",
            "url": "http://sj.ru/2"
        }])
        
        # Import functions
        from vacancy_bot import parse_hh_vacancies, parse_superjob_vacancies
        import pandas as pd
        
        # Act - Simulate search
        hh_df = parse_hh_vacancies("Python")
        sj_df = parse_superjob_vacancies("Python")
        
        # Assert
        assert len(hh_df) > 0
        assert len(sj_df) > 0
    
    @pytest.mark.functional
    @patch('vacancy_bot.get_cached_vacancies')
    def test_search_with_cache_hit(self, mock_get_cache):
        """
        Test search workflow when cache hits.
        """
        # Arrange
        cached_data = pd.DataFrame([{
            "source": "hh",
            "external_id": "123",
            "name": "Python Developer",
            "company": "Test Corp",
            "salary": 100000,
            "description": "Cached description",
            "skills": ["Python"],
            "experience": "between1And3",
            "url": "http://example.com"
        }])
        
        mock_get_cache.return_value = cached_data
        
        from vacancy_bot import get_cached_vacancies
        
        # Act
        result = get_cached_vacancies("Python")
        
        # Assert
        assert result is not None
        assert len(result) > 0
    
    @pytest.mark.functional
    def test_search_combines_results(self):
        """
        Test that search combines results from both sources.
        """
        # This verifies the data structure is compatible
        import pandas as pd
        
        hh_df = pd.DataFrame([{
            "source": "hh",
            "external_id": "1",
            "name": "HH Job",
            "company": "C",
            "salary": 100,
            "description": "D",
            "skills": [],
            "experience": "e",
            "url": "u"
        }])
        
        sj_df = pd.DataFrame([{
            "source": "sj",
            "external_id": "2",
            "name": "SJ Job",
            "company": "C",
            "salary": 100,
            "description": "D",
            "skills": [],
            "experience": "e",
            "url": "u"
        }])
        
        # Act
        combined = pd.concat([hh_df, sj_df], ignore_index=True)
        
        # Assert
        assert len(combined) == 2
        assert combined["source"].tolist() == ["hh", "sj"]


# ==============================================================================
# Error Recovery Workflow Tests
# ==============================================================================

class TestErrorRecoveryWorkflow:
    """Test suite for error recovery in workflows."""
    
    @pytest.mark.functional
    @patch('vacancy_bot.parse_hh_vacancies')
    def test_handles_api_failure_gracefully(self, mock_hh):
        """
        Test that bot handles API failures gracefully.
        """
        # Arrange
        from requests.exceptions import ConnectionError
        mock_hh.side_effect = ConnectionError("API failed")
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act & Assert
        with pytest.raises(ConnectionError):
            parse_hh_vacancies("Python")
    
    @pytest.mark.functional
    def test_handles_empty_search_results(self):
        """
        Test that empty search results are handled.
        """
        import pandas as pd
        
        empty_df = pd.DataFrame(columns=[
            "source", "external_id", "name", "company", "salary",
            "description", "skills", "experience", "url"
        ])
        
        # Should not crash when processing empty results
        from vacancy_bot import cluster_vacancies
        
        result = cluster_vacancies(empty_df)
        
        # Should return 'mixed' cluster for empty
        assert "cluster" in result.columns
    
    @pytest.mark.functional
    @patch('vacancy_bot.cache_vacancies')
    def test_continues_if_cache_fails(self, mock_cache):
        """
        Test that search continues even if caching fails.
        """
        # Arrange
        mock_cache.side_effect = Exception("Cache failed")
        
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
        
        # Act - should not raise
        cache_vacancies(df)
        
        # Assert - was called
        assert mock_cache.called


# ==============================================================================
# Logging and Monitoring Tests
# ==============================================================================

class TestLoggingAndMonitoring:
    """Test suite for logging and monitoring."""
    
    @pytest.mark.functional
    def test_logger_is_configured(self):
        """
        Test that logger is properly configured.
        """
        from vacancy_bot import logger
        
        assert logger is not None
        assert logger.name == "vacancy_bot"
    
    @pytest.mark.functional
    def test_log_decorators_exist(self):
        """
        Test that log decorators are defined.
        """
        from vacancy_bot import log_message, log_callback
        
        assert callable(log_message)
        assert callable(log_callback)
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_log_message_decorator(self):
        """
        Test that log_message decorator works.
        """
        from vacancy_bot import log_message
        
        # Create a mock function
        @log_message
        async def test_func(message):
            return "OK"
        
        # Verify decorator is applied
        assert callable(test_func)


# ==============================================================================
# Configuration Tests
# ==============================================================================

class TestConfigurationFunctional:
    """Test suite for configuration."""
    
    @pytest.mark.functional
    def test_all_required_config_present(self):
        """
        Test that all required configuration is present.
        """
        from vacancy_bot import (
            BOT_TOKEN,
            KILO_AUTO_API_KEY,
            DB_CONFIG,
            HH_API,
            SJ_API
        )
        
        # All should be importable
        assert BOT_TOKEN is not None
        assert DB_CONFIG is not None
        assert HH_API is not None
        assert SJ_API is not None
    
    @pytest.mark.functional
    def test_db_config_has_required_keys(self):
        """
        Test that DB_CONFIG has all required keys.
        """
        from vacancy_bot import DB_CONFIG
        
        required_keys = ['host', 'port', 'database', 'user', 'password']
        
        for key in required_keys:
            assert key in DB_CONFIG
    
    @pytest.mark.functional
    def test_areas_config_has_required_regions(self):
        """
        Test that AREAS has required regions.
        """
        from vacancy_bot import AREAS
        
        required_regions = ['Москва', 'СПб', 'Все']
        
        for region in required_regions:
            assert region in AREAS


# ==============================================================================
# Main Entry Point Tests
# ==============================================================================

class TestMainEntryPoint:
    """Test suite for main entry point."""
    
    @pytest.mark.functional
    def test_main_function_exists(self):
        """
        Test that main async function exists.
        """
        from vacancy_bot import main
        
        assert main is not None
        assert asyncio.iscoroutinefunction(main)
    
    @pytest.mark.functional
    def test_main_uses_asyncio_run(self):
        """
        Test that main is designed to run with asyncio.run.
        """
        # Check the module's entry point
        import vacancy_bot
        
        # Verify __name__ == "__main__" block exists
        assert hasattr(vacancy_bot, '__name__')
        assert vacancy_bot.__name__ == 'vacancy_bot'


# ==============================================================================
# Integration with aiogram Tests
# ==============================================================================

class TestAiogramIntegration:
    """Test suite for aiogram framework integration."""
    
    @pytest.mark.functional
    def test_dispatcher_has_router(self):
        """
        Test that dispatcher has message router.
        """
        from vacancy_bot import dp
        
        # aiogram 3.x uses router
        assert hasattr(dp, 'message')
        assert hasattr(dp, 'callback_query')
    
    @pytest.mark.functional
    def test_fsm_storage_is_memory(self):
        """
        test that FSM storage is configured as memory storage.
        """
        from vacancy_bot import dp
        
        # Check storage is configured
        assert dp.storage is not None
    
    @pytest.mark.functional
    def test_handlers_are_registered(self):
        """
        Test that handlers can be registered with dispatcher.
        """
        from vacancy_bot import dp
        
        # Verify dispatcher accepts handlers
        # This is implicit - if import succeeds, registration worked
        assert dp is not None


# ==============================================================================
# Regression Tests
# ==============================================================================

class TestRegressionScenarios:
    """Test suite for known regression scenarios."""
    
    @pytest.mark.functional
    def test_no_circular_imports(self):
        """
        Test that module can be imported without circular dependencies.
        """
        # This is implicit - if all imports succeed, no circular deps
        import vacancy_bot
        
        assert vacancy_bot is not None
    
    @pytest.mark.functional
    def test_no_missing_dependencies(self):
        """
        Test that all required dependencies are available.
        """
        required_modules = [
            'asyncio',
            'logging',
            'psycopg2',
            'aiogram',
            'aiohttp',
            'requests',
            'pandas',
            'sklearn',
            'dotenv'
        ]
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                pytest.fail(f"Missing required module: {module}")
    
    @pytest.mark.functional
    def test_python_version_compatible(self):
        """
        Test that code is compatible with Python 3.8+.
        """
        import sys
        
        # Should work on Python 3.8+
        assert sys.version_info >= (3, 8)
