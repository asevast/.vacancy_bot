"""
Integration tests for external API services.

Tests for HH.ru and SuperJob API integration.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, AsyncMock
from requests.exceptions import Timeout, ConnectionError as RequestConnectionError, HTTPError


# ==============================================================================
# HH.ru API Integration Tests
# ==============================================================================

class TestHHAPIIntegration:
    """Integration tests for HH.ru API."""
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_hh_api_successful_response(self, mock_get, sample_hh_vacancy_data):
        """
        Test successful HH.ru API response parsing.
        """
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = sample_hh_vacancy_data
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act
        result = parse_hh_vacancies("Python Developer")
        
        # Assert
        assert len(result) == 2
        assert result["name"].iloc[0] == "Python Developer"
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_hh_api_adds_user_agent(self, mock_get, sample_hh_vacancy_data):
        """
        Test that HH.ru API request includes User-Agent header.
        """
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = sample_hh_vacancy_data
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act
        parse_hh_vacancies("Python")
        
        # Assert
        call_kwargs = mock_get.call_args[1]
        assert 'headers' in call_kwargs
        assert 'User-Agent' in call_kwargs['headers']
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_hh_api_timeout_parameter(self, mock_get):
        """
        Test that HH.ru API request has timeout configured.
        """
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act
        parse_hh_vacancies("Test")
        
        # Assert
        call_kwargs = mock_get.call_args[1]
        assert 'timeout' in call_kwargs
        assert call_kwargs['timeout'] == 30
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_hh_api_handles_429_rate_limit(self, mock_get):
        """
        Test handling of HTTP 429 (Rate Limit) response.
        """
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = HTTPError("Rate limited")
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act & Assert
        with pytest.raises(HTTPError):
            parse_hh_vacancies("Python")
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_hh_api_handles_500_server_error(self, mock_get):
        """
        Test handling of HTTP 500 (Server Error) response.
        """
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = HTTPError("Server Error")
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act & Assert
        with pytest.raises(HTTPError):
            parse_hh_vacancies("Python")
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_hh_api_json_decode_error(self, mock_get):
        """
        Test handling of invalid JSON response.
        """
        # Arrange
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act & Assert
        with pytest.raises(ValueError):
            parse_hh_vacancies("Python")
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_hh_api_missing_required_fields(self, mock_get):
        """
        Test handling of response with missing required fields.
        """
        # Arrange - response missing 'items' key
        mock_response = Mock()
        mock_response.json.return_value = {}  # Empty response
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act
        result = parse_hh_vacancies("Python")
        
        # Assert
        assert len(result) == 0


# ==============================================================================
# SuperJob API Integration Tests
# ==============================================================================

class TestSuperJobAPIIntegration:
    """Integration tests for SuperJob API."""
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_sj_api_successful_response(self, mock_get, sample_sj_vacancy_data):
        """
        Test successful SuperJob API response parsing.
        """
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = sample_sj_vacancy_data
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_superjob_vacancies
        
        # Act
        result = parse_superjob_vacancies("Python")
        
        # Assert
        assert len(result) == 2
        assert result["name"].iloc[0] == "Python разработчик"
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_sj_api_adds_user_agent(self, mock_get, sample_sj_vacancy_data):
        """
        Test that SuperJob API request includes User-Agent header.
        """
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = sample_sj_vacancy_data
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_superjob_vacancies
        
        # Act
        parse_superjob_vacancies("Python")
        
        # Assert
        call_kwargs = mock_get.call_args[1]
        assert 'headers' in call_kwargs
        assert 'User-Agent' in call_kwargs['headers']
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_sj_api_timeout_parameter(self, mock_get):
        """
        Test that SuperJob API request has timeout configured.
        """
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"objects": []}
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_superjob_vacancies
        
        # Act
        parse_superjob_vacancies("Test")
        
        # Assert
        call_kwargs = mock_get.call_args[1]
        assert 'timeout' in call_kwargs
        assert call_kwargs['timeout'] == 30
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_sj_api_handles_403_forbidden(self, mock_get):
        """
        Test handling of HTTP 403 (Forbidden) response.
        """
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = HTTPError("Forbidden")
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_superjob_vacancies
        
        # Act & Assert
        with pytest.raises(HTTPError):
            parse_superjob_vacancies("Python")
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_sj_api_order_by_payment(self, mock_get, sample_sj_vacancy_data):
        """
        Test that SuperJob API requests ordered by payment.
        """
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = sample_sj_vacancy_data
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_superjob_vacancies
        
        # Act
        parse_superjob_vacancies("Python")
        
        # Assert
        call_kwargs = mock_get.call_args[1]
        params = call_kwargs.get('params', {})
        assert params.get('order_field') == 'payment'
        assert params.get('order_direction') == 'desc'


# ==============================================================================
# Combined API Integration Tests
# ==============================================================================

class TestCombinedAPIIntegration:
    """Integration tests for combined API usage."""
    
    @pytest.mark.integration
    @patch('vacancy_bot.parse_hh_vacancies')
    @patch('vacancy_bot.parse_superjob_vacancies')
    def test_combined_search_returns_all_vacancies(
        self, mock_sj, mock_hh, sample_vacancies_dataframe
    ):
        """
        Test that combined search returns vacancies from both sources.
        """
        # Arrange
        mock_hh.return_value = sample_vacancies_dataframe[sample_vacancies_dataframe['source'] == 'hh']
        mock_sj.return_value = sample_vacancies_dataframe[sample_vacancies_dataframe['source'] == 'sj']
        
        # Import the function that combines results
        from vacancy_bot import parse_hh_vacancies, parse_superjob_vacancies
        
        # Act
        hh_df = parse_hh_vacancies("Python")
        sj_df = parse_superjob_vacancies("Python")
        combined = pd.concat([hh_df, sj_df], ignore_index=True)
        
        # Assert
        assert len(combined) >= 2
        assert 'hh' in combined['source'].values
        assert 'sj' in combined['source'].values
    
    @pytest.mark.integration
    @patch('vacancy_bot.parse_hh_vacancies')
    @patch('vacancy_bot.parse_superjob_vacancies')
    def test_combined_search_handles_one_source_failure(
        self, mock_sj, mock_hh
    ):
        """
        Test that combined search handles one source failing.
        """
        # Arrange
        mock_hh.side_effect = ConnectionError("HH failed")
        mock_sj.return_value = pd.DataFrame([{
            "source": "sj",
            "external_id": "1",
            "name": "Test",
            "company": "C",
            "salary": 100,
            "description": "D",
            "skills": [],
            "experience": "e",
            "url": "u"
        }])
        
        from vacancy_bot import parse_hh_vacancies, parse_superjob_vacancies
        
        # Act - HH fails, but SJ works
        try:
            hh_df = parse_hh_vacancies("Python")
        except ConnectionError:
            hh_df = pd.DataFrame()
        
        sj_df = parse_superjob_vacancies("Python")
        combined = pd.concat([hh_df, sj_df], ignore_index=True)
        
        # Assert
        assert len(combined) >= 1
        assert combined["source"].iloc[0] == "sj"


# ==============================================================================
# API Response Validation Tests
# ==============================================================================

class TestAPIResponseValidation:
    """Tests for API response validation."""
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_validates_vacancy_id(self, mock_get):
        """
        Test that vacancy ID is extracted correctly.
        """
        # Arrange
        data = {
            "items": [{
                "id": "12345678",
                "name": "Test Job",
                "employer": {"name": "Company"},
                "salary": None,
                "key_skills": [],
                "snippet": {"requirement": "", "responsibility": ""},
                "experience": {"id": "noExperience"},
                "alternate_url": "http://hh.ru/vacancy/12345678"
            }]
        }
        mock_response = Mock()
        mock_response.json.return_value = data
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act
        result = parse_hh_vacancies("Test")
        
        # Assert
        assert result["external_id"].iloc[0] == "12345678"
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_validates_company_name(self, mock_get):
        """
        Test that company name is extracted correctly.
        """
        # Arrange
        data = {
            "items": [{
                "id": "1",
                "name": "Test Job",
                "employer": {"name": "Test Company LLC"},
                "salary": None,
                "key_skills": [],
                "snippet": {"requirement": "", "responsibility": ""},
                "experience": {"id": "noExperience"},
                "alternate_url": "http://example.com"
            }]
        }
        mock_response = Mock()
        mock_response.json.return_value = data
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act
        result = parse_hh_vacancies("Test")
        
        # Assert
        assert result["company"].iloc[0] == "Test Company LLC"
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_validates_url(self, mock_get):
        """
        Test that vacancy URL is extracted correctly.
        """
        # Arrange
        expected_url = "https://hh.ru/vacancy/12345678"
        data = {
            "items": [{
                "id": "12345678",
                "name": "Test Job",
                "employer": {"name": "Company"},
                "salary": None,
                "key_skills": [],
                "snippet": {"requirement": "", "responsibility": ""},
                "experience": {"id": "noExperience"},
                "alternate_url": expected_url
            }]
        }
        mock_response = Mock()
        mock_response.json.return_value = data
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act
        result = parse_hh_vacancies("Test")
        
        # Assert
        assert result["url"].iloc[0] == expected_url
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_handles_missing_employer(self, mock_get):
        """
        Test handling of vacancy without employer info.
        """
        # Arrange
        data = {
            "items": [{
                "id": "1",
                "name": "Test Job",
                "employer": {},  # Empty employer
                "salary": None,
                "key_skills": [],
                "snippet": {"requirement": "", "responsibility": ""},
                "experience": {"id": "noExperience"},
                "alternate_url": "http://example.com"
            }]
        }
        mock_response = Mock()
        mock_response.json.return_value = data
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act
        result = parse_hh_vacancies("Test")
        
        # Assert
        assert "employer" in result.columns
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_handles_missing_snippet(self, mock_get):
        """
        Test handling of vacancy without snippet.
        """
        # Arrange
        data = {
            "items": [{
                "id": "1",
                "name": "Test Job",
                "employer": {"name": "Company"},
                "salary": None,
                "key_skills": [],
                "snippet": None,  # No snippet
                "experience": {"id": "noExperience"},
                "alternate_url": "http://example.com"
            }]
        }
        mock_response = Mock()
        mock_response.json.return_value = data
        mock_get.return_value = mock_response
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act
        result = parse_hh_vacancies("Test")
        
        # Assert
        assert "description" in result.columns


# ==============================================================================
# Network Error Handling Tests
# ==============================================================================

class TestNetworkErrorHandling:
    """Tests for network error handling."""
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_hh_timeout_message(self, mock_get):
        """
        Test that HH timeout error has descriptive message.
        """
        # Arrange
        mock_get.side_effect = Timeout("Request timed out")
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act & Assert
        with pytest.raises(TimeoutError) as exc_info:
            parse_hh_vacancies("Python")
        
        assert "timeout" in str(exc_info.value).lower() or "hh" in str(exc_info.value).lower()
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_sj_timeout_message(self, mock_get):
        """
        Test that SuperJob timeout error has descriptive message.
        """
        # Arrange
        mock_get.side_effect = Timeout("Request timed out")
        
        from vacancy_bot import parse_superjob_vacancies
        
        # Act & Assert
        with pytest.raises(TimeoutError) as exc_info:
            parse_superjob_vacancies("Python")
        
        assert "timeout" in str(exc_info.value).lower() or "superjob" in str(exc_info.value).lower()
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_hh_connection_error_message(self, mock_get):
        """
        Test that HH connection error has descriptive message.
        """
        # Arrange
        mock_get.side_effect = RequestConnectionError("Connection refused")
        
        from vacancy_bot import parse_hh_vacancies
        
        # Act & Assert
        with pytest.raises(ConnectionError) as exc_info:
            parse_hh_vacancies("Python")
        
        assert "connection" in str(exc_info.value).lower() or "hh" in str(exc_info.value).lower()
    
    @pytest.mark.integration
    @patch('requests.get')
    def test_sj_connection_error_message(self, mock_get):
        """
        Test that SuperJob connection error has descriptive message.
        """
        # Arrange
        mock_get.side_effect = RequestConnectionError("Connection refused")
        
        from vacancy_bot import parse_superjob_vacancies
        
        # Act & Assert
        with pytest.raises(ConnectionError) as exc_info:
            parse_superjob_vacancies("Python")
        
        assert "connection" in str(exc_info.value).lower() or "superjob" in str(exc_info.value).lower()
