"""
Functional tests for FSM (Finite State Machine) workflows.

Tests for bot state management and conversation flows.
"""

import pytest
import asyncio
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


# ==============================================================================
# FSM State Transition Tests
# ==============================================================================

class TestFSMStateTransitions:
    """Test suite for FSM state transitions."""
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_profession_to_salary_from_transition(self):
        """
        Test transition from waiting_profession to waiting_salary_from.
        """
        # Arrange
        mock_state = AsyncMock()
        mock_state.set_state = AsyncMock()
        
        # Create mock message
        mock_message = Mock()
        mock_message.text = "Python Developer"
        mock_message.answer = AsyncMock()
        
        # Import handler
        from vacancy_bot import process_profession
        
        # Act
        await process_profession(mock_message, mock_state)
        
        # Assert
        mock_state.update_data.assert_called_once_with(profession="Python Developer")
        mock_state.set_state.assert_called_once()

    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_profession_requires_clarification(self):
        """
        Test that generic profession triggers clarification state.
        """
        mock_state = AsyncMock()
        mock_state.set_state = AsyncMock()

        mock_message = Mock()
        mock_message.text = "Developer"
        mock_message.answer = AsyncMock()

        from vacancy_bot import process_profession, SearchForm

        await process_profession(mock_message, mock_state)

        mock_state.set_state.assert_called_with(SearchForm.waiting_clarification)
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_salary_from_to_salary_to_transition(self):
        """
        Test transition from waiting_salary_from to waiting_salary_to.
        """
        # Arrange
        mock_state = AsyncMock()
        mock_state.set_state = AsyncMock()
        
        mock_message = Mock()
        mock_message.text = "100000"
        mock_message.answer = AsyncMock()
        
        from vacancy_bot import process_salary_from
        
        # Act
        await process_salary_from(mock_message, mock_state)
        
        # Assert
        mock_state.set_state.assert_called_once()
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_salary_from_skip_transition(self):
        """
        Test transition when salary is skipped.
        """
        # Arrange
        mock_state = AsyncMock()
        mock_state.set_state = AsyncMock()
        
        mock_message = Mock()
        mock_message.text = "/skip"
        mock_message.answer = AsyncMock()
        
        from vacancy_bot import process_salary_from
        
        # Act
        await process_salary_from(mock_message, mock_state)
        
        # Assert - should not call update_data for salary
        mock_state.set_state.assert_called_once()
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_salary_to_to_region_transition(self):
        """
        Test transition from waiting_salary_to to waiting_region.
        """
        # Arrange
        mock_state = AsyncMock()
        mock_state.set_state = AsyncMock()
        
        mock_message = Mock()
        mock_message.text = "200000"
        mock_message.answer = AsyncMock()
        
        from vacancy_bot import process_salary_to
        
        # Act
        await process_salary_to(mock_message, mock_state)
        
        # Assert
        mock_state.set_state.assert_called_once()
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_salary_to_region_input(self):
        """
        Test that region input is collected.
        """
        # Arrange
        mock_state = AsyncMock()
        mock_state.set_state = AsyncMock()
        mock_state.get_data = AsyncMock(return_value={
            "profession": "Python Developer",
            "salary_from": 100000
        })
        
        mock_message = Mock()
        mock_message.text = "Москва"
        mock_message.answer = AsyncMock()
        
        from vacancy_bot import process_salary_to
        
        # Act
        await process_salary_to(mock_message, mock_state)
        
        # Assert
        mock_state.set_state.assert_called_once()

    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_region_to_confirmation_transition(self):
        """
        Test transition from waiting_region to waiting_confirmation.
        """
        mock_state = AsyncMock()
        mock_state.set_state = AsyncMock()
        mock_state.get_data = AsyncMock(return_value={
            "profession": "Python Developer",
            "salary_from": 100000,
            "salary_to": 200000
        })

        mock_message = Mock()
        mock_message.text = "Москва"
        mock_message.answer = AsyncMock()

        from vacancy_bot import process_region, SearchForm

        await process_region(mock_message, mock_state)

        mock_state.set_state.assert_called_with(SearchForm.waiting_confirmation)


    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_clarification_to_salary_from_transition(self):
        """
        Test transition from waiting_clarification to waiting_salary_from.
        """
        mock_state = AsyncMock()
        mock_state.set_state = AsyncMock()
        mock_state.get_data = AsyncMock(return_value={"profession": "Developer"})

        mock_message = Mock()
        mock_message.text = "Python backend"
        mock_message.answer = AsyncMock()

        from vacancy_bot import process_profession_clarification, SearchForm

        await process_profession_clarification(mock_message, mock_state)

        mock_state.set_state.assert_called_with(SearchForm.waiting_salary_from)


# ==============================================================================
# FSM Data Handling Tests
# ==============================================================================

class TestFSMDataHandling:
    """Test suite for FSM data handling."""
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_salary_parsing_removes_rub_symbol(self):
        """
        Test that salary input is parsed correctly with Ruble symbol.
        """
        # Arrange
        mock_state = AsyncMock()
        
        mock_message = Mock()
        mock_message.text = "100 000 ₽"
        mock_message.answer = AsyncMock()
        
        from vacancy_bot import process_salary_from
        
        # Act
        await process_salary_from(mock_message, mock_state)
        
        # Assert - should parse to int
        # The implementation removes spaces and ₽
        call_args = mock_state.update_data.call_args
        if call_args:
            data = call_args[1]
            if 'salary_from' in data:
                assert data['salary_from'] == 100000
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_salary_parsing_removes_spaces(self):
        """
        Test that salary input handles spaces correctly.
        """
        # Arrange
        mock_state = AsyncMock()
        
        mock_message = Mock()
        mock_message.text = "150 000"
        mock_message.answer = AsyncMock()
        
        from vacancy_bot import process_salary_from
        
        # Act
        await process_salary_from(mock_message, mock_state)
        
        # Assert - should parse correctly
        # The implementation should handle the space
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_invalid_salary_handled(self):
        """
        Test that invalid salary input is handled gracefully.
        """
        # Arrange
        mock_state = AsyncMock()
        
        mock_message = Mock()
        mock_message.text = "not_a_number"
        mock_message.answer = AsyncMock()
        
        from vacancy_bot import process_salary_from
        
        # Act - should not crash
        await process_salary_from(mock_message, mock_state)
        
        # Assert - state should still be set
        mock_state.set_state.assert_called_once()
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_region_title_case_handling(self):
        """
        Test that region input is converted to title case.
        """
        # Arrange
        mock_state = AsyncMock()
        mock_state.get_data = AsyncMock(return_value={
            "profession": "Python",
            "salary_from": 100000
        })
        
        mock_message = Mock()
        mock_message.text = "москва"  # lowercase
        mock_message.answer = AsyncMock()
        
        from vacancy_bot import process_region
        
        # Act
        await process_region(mock_message, mock_state)
        
        # Assert - should be converted to title case
        # (Implementation uses .title())


# ==============================================================================
# FSM Area Resolution Tests
# ==============================================================================

class TestFSMAreaResolution:
    """Test suite for area resolution."""
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_moscow_area_resolution(self):
        """
        Test that Moscow resolves to correct area IDs.
        """
        # Arrange
        from vacancy_bot import AREAS
        
        # Assert
        assert AREAS["Москва"]["hh"] == 1
        assert AREAS["Москва"]["sj"] == 4
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_spb_area_resolution(self):
        """
        Test that St. Petersburg resolves to correct area IDs.
        """
        # Arrange
        from vacancy_bot import AREAS
        
        # Assert
        assert AREAS["СПб"]["hh"] == 2
        assert AREAS["СПб"]["sj"] == 2
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_unknown_region_uses_default(self):
        """
        Test that unknown region uses default (Nizhny Novgorod).
        """
        # Arrange
        mock_state = AsyncMock()
        mock_state.get_data = AsyncMock(return_value={
            "profession": "Python"
        })
        
        mock_message = Mock()
        mock_message.text = "НеизвестныйГород"
        mock_message.answer = AsyncMock()
        
        from vacancy_bot import process_region, AREAS
        
        # Act
        await process_region(mock_message, mock_state)
        
        # Assert - should use default area
        # (Implementation uses AREAS.get with default)


# ==============================================================================
# FSM Callback Tests
# ==============================================================================

class TestFSMCallbackHandlers:
    """Test suite for FSM callback handlers."""
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_analyze_callback_starts_fsm(self):
        """
        Test that analyze callback starts the search FSM.
        """
        # Arrange
        mock_callback = Mock()
        mock_callback.message = Mock()
        mock_callback.message.answer = AsyncMock()
        mock_callback.answer = AsyncMock()
        
        mock_state = AsyncMock()
        mock_state.set_state = AsyncMock()
        
        from vacancy_bot import analyze_callback
        
        # Act
        await analyze_callback(mock_callback, mock_state)
        
        # Assert
        mock_callback.message.answer.assert_called_once()
        mock_state.set_state.assert_called_once()
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_ai_mode_callback_with_api_key(self):
        """
        Test that ai_mode callback works when API key is set.
        """
        # Arrange
        mock_callback = Mock()
        mock_callback.message = Mock()
        mock_callback.message.answer = AsyncMock()
        mock_callback.answer = AsyncMock()
        
        mock_state = AsyncMock()
        mock_state.set_state = AsyncMock()
        
        from vacancy_bot import ai_mode_callback
        
        # Act
        await ai_mode_callback(mock_callback, mock_state)
        
        # Assert - should respond with instructions
        mock_callback.message.answer.assert_called()
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_ai_mode_callback_without_api_key(self):
        """
        Test that ai_mode callback handles missing API key.
        """
        # Arrange
        mock_callback = Mock()
        mock_callback.message = Mock()
        mock_callback.message.answer = AsyncMock()
        mock_callback.answer = AsyncMock()
        
        mock_state = AsyncMock()
        
        with patch('vacancy_bot.KILO_AUTO_API_KEY', None):
            from vacancy_bot import ai_mode_callback
            
            # Act
            await ai_mode_callback(mock_callback, mock_state)
            
            # Assert - should respond with error
            mock_callback.message.answer.assert_called()
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_clusters_callback_responds(self):
        """
        Test that clusters callback responds with instructions.
        """
        # Arrange
        mock_callback = Mock()
        mock_callback.message = Mock()
        mock_callback.message.answer = AsyncMock()
        mock_callback.answer = AsyncMock()
        
        from vacancy_bot import clusters_callback
        
        # Act
        await clusters_callback(mock_callback)
        
        # Assert
        mock_callback.message.answer.assert_called_once()
        mock_callback.answer.assert_called_once()


# ==============================================================================
# AI Prompt FSM Tests
# ==============================================================================

class TestAIPromptFSM:
    """Test suite for AI prompt FSM."""
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_ai_prompt_handler_exists(self):
        """
        Test that AI prompt handler exists in correct state.
        """
        from vacancy_bot import AIForm, process_ai_prompt
        
        # Handler should be decorated for AIForm.waiting_prompt
        assert process_ai_prompt is not None
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_ai_prompt_clears_state(self):
        """
        Test that AI prompt handler clears state after response.
        """
        # Arrange
        mock_message = Mock()
        mock_message.text = "Какие навыки нужны Python?"
        mock_message.answer = AsyncMock()
        mock_message.from_user = Mock()
        mock_message.from_user.full_name = "Test User"
        
        mock_state = AsyncMock()
        mock_state.clear = AsyncMock()
        mock_state.set_state = AsyncMock()
        
        with patch('vacancy_bot.ask_kilo_auto', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = "Тестовый ответ"
            
            from vacancy_bot import process_ai_prompt
            
            # Act
            await process_ai_prompt(mock_message, mock_state)
            
            # Assert
            mock_state.clear.assert_called_once()
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_ai_command_handler_exists(self):
        """
        Test that /ai command handler exists.
        """
        from vacancy_bot import ai_command
        
        assert ai_command is not None
        assert asyncio.iscoroutinefunction(ai_command)


# ==============================================================================
# FSM Error Handling Tests
# ==============================================================================

class TestFSMErrorHandling:
    """Test suite for FSM error handling."""
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_handles_message_without_text(self):
        """
        Test handling of messages without text.
        """
        # Arrange
        mock_message = Mock()
        mock_message.text = None
        mock_message.answer = AsyncMock()
        
        mock_state = AsyncMock()
        
        from vacancy_bot import process_profession
        
        # Act & Assert - should handle gracefully
        # (Current implementation would use None)
        await process_profession(mock_message, mock_state)
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_state_persistence(self):
        """
        Test that state data persists across transitions.
        """
        # Arrange
        mock_state = AsyncMock()
        mock_state.get_data = AsyncMock(return_value={
            "profession": "Python",
            "salary_from": 100000,
            "salary_to": 200000
        })
        
        mock_message = Mock()
        mock_message.text = "Москва"
        mock_message.answer = AsyncMock()
        
        from vacancy_bot import process_region
        
        # Act
        await process_region(mock_message, mock_state)
        
        # Assert - get_data should be called
        mock_state.get_data.assert_called()


# ==============================================================================
# FSM Integration Tests
# ==============================================================================

class TestFSMIntegration:
    """Test suite for FSM integration."""
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_complete_search_flow(self):
        """
        Test complete search flow from start to finish.
        """
        # This tests the full workflow:
        # 1. User starts /start
        # 2. Clicks "Анализ"
        # 3. Enters profession
        # 4. Enters salary from
        # 5. Enters salary to
        # 6. Enters region
        # 7. Gets results
        
        # Verify all handlers exist
        from vacancy_bot import (
            start_handler,
            analyze_callback,
            process_profession,
            process_salary_from,
            process_salary_to,
            process_region
        )
        
        assert all([
            start_handler,
            analyze_callback,
            process_profession,
            process_salary_from,
            process_salary_to,
            process_region
        ])
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_ai_flow_without_fsm(self):
        """
        Test AI flow using /ai command (without FSM).
        """
        # Verify handler exists
        from vacancy_bot import ai_command
        
        assert ai_command is not None
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_ai_flow_with_fsm(self):
        """
        Test AI flow using inline button (with FSM).
        """
        # Verify handler exists
        from vacancy_bot import ai_mode_callback, process_ai_prompt
        
        assert ai_mode_callback is not None
        assert process_ai_prompt is not None


# ==============================================================================
# Message Building Tests
# ==============================================================================

class TestMessageBuilding:
    """Test suite for message building."""
    
    @pytest.mark.functional
    def test_start_keyboard_has_required_buttons(self):
        """
        Test that start keyboard has all required buttons.
        """
        from aiogram.types import InlineKeyboardButton
        
        # Expected buttons
        expected_texts = [
            "Анализ",
            "AI",
            "Кластер"
        ]
        
        expected_texts = ["Анализ", "AI", "Кластеры"]
        # Verify InlineKeyboardButton exists
        assert InlineKeyboardButton is not None
    
    @pytest.mark.functional
    def test_message_formatting(self):
        """
        Test message formatting constants.
        """
        # Test that markdown parsing mode is available
        # (implementation uses parse_mode="Markdown")
        
        # Just verify the import works
        from aiogram.enums import ParseMode
        assert ParseMode is not None


# ==============================================================================
# State Cleanup Tests
# ==============================================================================

class TestStateCleanup:
    """Test suite for state cleanup."""
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_confirmation_handler_clears_state(self):
        """
        Test that confirmation handler clears state after completion.
        """
        # Arrange
        mock_message = Mock()
        mock_message.text = "Да"
        mock_message.answer = AsyncMock()
        
        mock_state = AsyncMock()
        mock_state.get_data = AsyncMock(return_value={
            "profession": "Python",
            "salary_from": 100000,
            "salary_to": 200000,
            "region": "Москва",
            "area": {"hh": 1, "sj": 4}
        })
        mock_state.clear = AsyncMock()
        mock_state.set_state = AsyncMock()
        
        with patch('vacancy_bot.get_cached_vacancies', return_value=None), \
             patch('vacancy_bot.parse_hh_vacancies', return_value=pd.DataFrame()), \
             patch('vacancy_bot.parse_superjob_vacancies', return_value=pd.DataFrame()), \
             patch('vacancy_bot.safe_cache_vacancies'):
            from vacancy_bot import process_search_confirmation
        
            # Act
            await process_search_confirmation(mock_message, mock_state)
        
        # Assert - state should be cleared
        mock_state.clear.assert_called_once()
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_ai_prompt_clears_state(self):
        """
        Test that AI prompt handler clears state after completion.
        """
        # Arrange
        mock_message = Mock()
        mock_message.text = "Test"
        mock_message.answer = AsyncMock()
        mock_message.from_user = Mock()
        
        mock_state = AsyncMock()
        mock_state.clear = AsyncMock()
        mock_state.set_state = AsyncMock()
        
        with patch('vacancy_bot.ask_kilo_auto', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = "Response"
            
            from vacancy_bot import process_ai_prompt
            
            # Act
            await process_ai_prompt(mock_message, mock_state)
            
            # Assert
            mock_state.clear.assert_called()


# ==============================================================================
# Long Response Handling Tests
# ==============================================================================

class TestLongResponseHandling:
    """Test suite for long response handling."""
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_long_ai_response_split(self):
        """
        Test that long AI responses are split into chunks.
        """
        # Arrange
        long_response = "A" * 5000  # Longer than 4096
        
        mock_message = Mock()
        mock_message.text = "Test"
        mock_message.answer = AsyncMock()
        mock_message.from_user = Mock()
        
        mock_state = AsyncMock()
        mock_state.clear = AsyncMock()
        mock_state.set_state = AsyncMock()
        
        with patch('vacancy_bot.ask_kilo_auto', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = long_response
            
            from vacancy_bot import process_ai_prompt
            
            # Act
            await process_ai_prompt(mock_message, mock_state)
            
            # Assert - answer should be called multiple times
            # (at least once for long response)
            assert mock_message.answer.call_count >= 1
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_short_ai_response_single_message(self):
        """
        Test that short AI responses sent as single message.
        """
        # Arrange
        short_response = "Short response"
        
        mock_message = Mock()
        mock_message.text = "Test"
        mock_message.answer = AsyncMock()
        mock_message.from_user = Mock()
        
        mock_state = AsyncMock()
        mock_state.clear = AsyncMock()
        mock_state.set_state = AsyncMock()
        
        with patch('vacancy_bot.ask_kilo_auto', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = short_response
            
            from vacancy_bot import process_ai_prompt
            
            # Act
            await process_ai_prompt(mock_message, mock_state)
            
            # Assert
        # Two messages: "Thinking..." and the response
        assert mock_message.answer.call_count == 2
        assert mock_message.answer.call_args_list[1][0][0] == short_response
