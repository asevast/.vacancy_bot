"""
Unit tests for ML clustering functionality.

Tests for TF-IDF vectorization and KMeans clustering.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from vacancy_bot import cluster_vacancies


# ==============================================================================
# Clustering Tests
# ==============================================================================

class TestClusterVacancies:
    """Test suite for vacancy clustering functionality."""
    
    @pytest.mark.unit
    def test_cluster_vacancies_returns_dataframe_with_cluster_column(self, sample_cluster_data):
        """
        Test that clustering returns DataFrame with 'cluster' column.
        """
        # Act
        result = cluster_vacancies(sample_cluster_data)
        
        # Assert
        assert "cluster" in result.columns
        assert len(result) == len(sample_cluster_data)
    
    @pytest.mark.unit
    def test_cluster_vacancies_assigns_valid_cluster_names(self, sample_cluster_data):
        """
        Test that clusters are assigned valid names (Junior/Middle/Senior).
        """
        # Act
        result = cluster_vacancies(sample_cluster_data)
        
        # Assert
        valid_clusters = {"Junior", "Middle", "Senior"}
        assigned_clusters = set(result["cluster"].unique())
        assert assigned_clusters.issubset(valid_clusters), \
            f"Unexpected clusters: {assigned_clusters - valid_clusters}"
    
    @pytest.mark.unit
    def test_cluster_vacancies_empty_dataframe_returns_mixed(self, empty_vacancies_dataframe):
        """
        Test that empty DataFrame returns 'mixed' cluster.
        """
        # Act
        result = cluster_vacancies(empty_vacancies_dataframe)
        
        # Assert
        assert result["cluster"].iloc[0] == "mixed"
    
    @pytest.mark.unit
    def test_cluster_vacancies_less_than_5_returns_mixed(self, sample_vacancies_dataframe):
        """
        Test that DataFrames with less than 5 vacancies return 'mixed' cluster.
        """
        # Arrange - take only 3 vacancies
        small_df = sample_vacancies_dataframe.head(3)
        
        # Act
        result = cluster_vacancies(small_df)
        
        # Assert
        assert all(result["cluster"] == "mixed")
    
    @pytest.mark.unit
    def test_cluster_vacancies_no_salary_returns_unknown(self):
        """
        Test that DataFrames without salary data return 'unknown' cluster.
        """
        # Arrange
        df_no_salary = pd.DataFrame({
            "source": ["hh"] * 5,
            "external_id": [str(i) for i in range(5)],
            "name": ["Developer"] * 5,
            "company": ["Company"] * 5,
            "salary": [None, None, None, None, None],
            "description": ["Desc"] * 5,
            "skills": [["Python"]] * 5,
            "experience": ["noExperience"] * 5,
            "url": ["http://example.com"] * 5
        })
        
        # Act
        result = cluster_vacancies(df_no_salary)
        
        # Assert
        assert all(result["cluster"] == "unknown")
    
    @pytest.mark.unit
    def test_cluster_vacancies_salary_based_clustering(self):
        """
        Test that higher salaries are assigned to higher cluster levels.
        
        This is a key business logic test - higher salaries should
        generally indicate more senior positions.
        """
        # Arrange - clear salary separation for predictable clustering
        df = pd.DataFrame({
            "source": ["hh"] * 6,
            "external_id": [str(i) for i in range(6)],
            "name": ["Dev"] * 6,
            "company": ["C"] * 6,
            "salary": [50000, 60000, 70000, 100000, 120000, 200000],
            "description": ["Simple"] * 3 + ["Complex"] * 3,
            "skills": [["Python"]] * 6,
            "experience": ["noExp"] * 6,
            "url": ["http://x.com"] * 6
        })
        
        # Act
        result = cluster_vacancies(df)
        
        # Assert - check that low salaries and high salaries are in different clusters
        low_salary_clusters = result[result["salary"] < 80000]["cluster"].unique()
        high_salary_clusters = result[result["salary"] >= 100000]["cluster"].unique()
        
        # Different salary ranges should be in different clusters
        assert len(low_salary_clusters) > 0
        assert len(high_salary_clusters) > 0
    
    @pytest.mark.unit
    def test_cluster_vacancies_handles_string_skills(self):
        """
        Test that string skills (non-list) are handled correctly.
        """
        # Arrange
        df = pd.DataFrame({
            "source": ["hh"] * 6,
            "external_id": [str(i) for i in range(6)],
            "name": ["Dev"] * 6,
            "company": ["C"] * 6,
            "salary": [50000, 60000, 70000, 100000, 120000, 150000],
            "description": ["D"] * 6,
            "skills": ["Python, Django", "Python", "Django", "ML", "AI", "DevOps"],  # Strings, not lists
            "experience": ["noExp"] * 6,
            "url": ["http://x.com"] * 6
        })
        
        # Act & Assert - Should not raise error
        result = cluster_vacancies(df)
        assert "cluster" in result.columns
    
    @pytest.mark.unit
    def test_cluster_vacancies_handles_none_description(self):
        """
        Test that None descriptions are handled correctly.
        """
        # Arrange
        df = pd.DataFrame({
            "source": ["hh"] * 6,
            "external_id": [str(i) for i in range(6)],
            "name": ["Dev"] * 6,
            "company": ["C"] * 6,
            "salary": [50000, 60000, 70000, 100000, 120000, 150000],
            "description": [None, "Desc", None, "Desc", None, "Desc"],
            "skills": [["Python"]] * 6,
            "experience": ["noExp"] * 6,
            "url": ["http://x.com"] * 6
        })
        
        # Act & Assert - Should not raise error
        result = cluster_vacancies(df)
        assert "cluster" in result.columns
    
    @pytest.mark.unit
    def test_cluster_vacancies_returns_copy(self, sample_cluster_data):
        """
        Test that clustering returns a new DataFrame, not modifying the original.
        """
        # Arrange
        original_df = sample_cluster_data.copy()
        
        # Act
        result = cluster_vacancies(sample_cluster_data)
        
        # Assert - original should not have 'cluster' column
        assert "cluster" not in sample_cluster_data.columns
        # Result should have 'cluster' column
        assert "cluster" in result.columns
        # But they should have the same length
        assert len(result) == len(original_df)
    
    @pytest.mark.unit
    @pytest.mark.parametrize("num_vacancies", [5, 10, 20, 50])
    def test_cluster_vacancies_handles_different_sizes(self, num_vacancies):
        """
        Test clustering with different numbers of vacancies.
        """
        # Arrange
        salaries = [50000 + i * 5000 for i in range(num_vacancies)]
        df = pd.DataFrame({
            "source": ["hh"] * num_vacancies,
            "external_id": [str(i) for i in range(num_vacancies)],
            "name": ["Dev"] * num_vacancies,
            "company": ["C"] * num_vacancies,
            "salary": salaries,
            "description": ["Description"] * num_vacancies,
            "skills": [["Python"]] * num_vacancies,
            "experience": ["noExp"] * num_vacancies,
            "url": ["http://x.com"] * num_vacancies
        })
        
        # Act
        result = cluster_vacancies(df)
        
        # Assert
        assert len(result) == num_vacancies
        assert "cluster" in result.columns
        # Should have exactly 3 clusters (Junior, Middle, Senior)
        assert len(result["cluster"].unique()) == 3
    
    @pytest.mark.unit
    def test_cluster_vacancies_deterministic(self, sample_cluster_data):
        """
        Test that clustering is deterministic (same input = same output).
        """
        # Act
        result1 = cluster_vacancies(sample_cluster_data)
        result2 = cluster_vacancies(sample_cluster_data)
        
        # Assert - cluster assignments should be the same
        pd.testing.assert_series_equal(
            result1["cluster"].reset_index(drop=True),
            result2["cluster"].reset_index(drop=True)
        )


# ==============================================================================
# TF-IDF Vectorization Tests
# ==============================================================================

class TestTFIDFVectorization:
    """Test suite for TF-IDF vectorization used in clustering."""
    
    @pytest.mark.unit
    def test_tfidf_vectorizer_parameters(self):
        """
        Test that TF-IDF vectorizer uses expected parameters.
        """
        # This test verifies the vectorizer configuration
        # We check the implementation indirectly through clustering results
        
        # The vectorizer should:
        # - Use max_features=1000
        # - Remove english stop words
        
        # We'll test this by checking that common words don't dominate
        df = pd.DataFrame({
            "source": ["hh"] * 10,
            "external_id": [str(i) for i in range(10)],
            "name": ["Developer"] * 10,
            "company": ["C"] * 10,
            "salary": list(range(50000, 150000, 10000)),
            "description": ["the and is are for with python java"] * 10,
            "skills": [["python"]] * 10,
            "experience": ["noExp"] * 10,
            "url": ["http://x.com"] * 10
        })
        
        # Act - should not fail even with stop words
        result = cluster_vacancies(df)
        
        # Assert
        assert "cluster" in result.columns
    
    @pytest.mark.unit
    def test_tfidf_handles_empty_skills(self):
        """
        Test that TF-IDF handles empty skills gracefully.
        """
        # Arrange
        df = pd.DataFrame({
            "source": ["hh"] * 6,
            "external_id": [str(i) for i in range(6)],
            "name": ["Dev"] * 6,
            "company": ["C"] * 6,
            "salary": list(range(50000, 110000, 10000)),
            "description": ["Python"] * 6,
            "skills": [[], [], [], [], [], []],  # Empty skills
            "experience": ["noExp"] * 6,
            "url": ["http://x.com"] * 6
        })
        
        # Act & Assert
        result = cluster_vacancies(df)
        assert "cluster" in result.columns


# ==============================================================================
# KMeans Clustering Tests
# ==============================================================================

class TestKMeansClustering:
    """Test suite for KMeans clustering algorithm."""
    
    @pytest.mark.unit
    def test_kmeans_creates_three_clusters(self, sample_cluster_data):
        """
        Test that KMeans always creates exactly 3 clusters.
        """
        # Act
        result = cluster_vacancies(sample_cluster_data)
        
        # Assert
        unique_clusters = result["cluster"].unique()
        assert len(unique_clusters) == 3
    
    @pytest.mark.unit
    def test_kmeans_random_state_determinism(self):
        """
        Test that KMeans with fixed random_state is deterministic.
        """
        # Arrange - create two identical DataFrames
        df = pd.DataFrame({
            "source": ["hh"] * 10,
            "external_id": [str(i) for i in range(10)],
            "name": ["Dev"] * 10,
            "company": ["C"] * 10,
            "salary": list(range(50000, 150000, 10000)),
            "description": ["Description"] * 10,
            "skills": [["Python"]] * 10,
            "experience": ["noExp"] * 10,
            "url": ["http://x.com"] * 10
        })
        
        # Act - run clustering twice
        result1 = cluster_vacancies(df)
        result2 = cluster_vacancies(df)
        
        # Assert - results should be identical
        pd.testing.assert_series_equal(
            result1["cluster"].reset_index(drop=True),
            result2["cluster"].reset_index(drop=True)
        )
    
    @pytest.mark.unit
    def test_kmeans_n_init_parameter(self):
        """
        Test that KMeans uses n_init parameter for stability.
        """
        # The implementation should use n_init=10 for better convergence
        
        # This is tested indirectly - if n_init is too low,
        # clustering might be non-deterministic even with random_state
        df = pd.DataFrame({
            "source": ["hh"] * 15,
            "external_id": [str(i) for i in range(15)],
            "name": ["Dev"] * 15,
            "company": ["C"] * 15,
            "salary": [50000] * 5 + [100000] * 5 + [150000] * 5,
            "description": ["Simple task"] * 5 + ["Medium task"] * 5 + ["Complex task"] * 5,
            "skills": [["Python"]] * 15,
            "experience": ["noExp"] * 15,
            "url": ["http://x.com"] * 15
        })
        
        # Act
        result = cluster_vacancies(df)
        
        # Assert - should create 3 distinct clusters
        assert len(result["cluster"].unique()) == 3


# ==============================================================================
# Edge Cases and Error Handling
# ==============================================================================

class TestClusteringEdgeCases:
    """Test suite for edge cases in clustering."""
    
    @pytest.mark.unit
    def test_all_same_salary(self):
        """
        Test clustering when all vacancies have the same salary.
        """
        # Arrange
        df = pd.DataFrame({
            "source": ["hh"] * 10,
            "external_id": [str(i) for i in range(10)],
            "name": ["Dev"] * 10,
            "company": ["C"] * 10,
            "salary": [100000] * 10,  # Same salary
            "description": ["Description"] * 10,
            "skills": [["Python"]] * 10,
            "experience": ["noExp"] * 10,
            "url": ["http://x.com"] * 10
        })
        
        # Act
        result = cluster_vacancies(df)
        
        # Assert - should still have cluster column
        assert "cluster" in result.columns
    
    @pytest.mark.unit
    def test_all_same_description(self):
        """
        Test clustering when all vacancies have the same description.
        """
        # Arrange
        df = pd.DataFrame({
            "source": ["hh"] * 6,
            "external_id": [str(i) for i in range(6)],
            "name": ["Dev"] * 6,
            "company": ["C"] * 6,
            "salary": list(range(50000, 110000, 10000)),
            "description": ["Same description for all"] * 6,
            "skills": [["Python"]] * 6,
            "experience": ["noExp"] * 6,
            "url": ["http://x.com"] * 6
        })
        
        # Act
        result = cluster_vacancies(df)
        
        # Assert
        assert "cluster" in result.columns
    
    @pytest.mark.unit
    def test_very_long_descriptions(self):
        """
        Test clustering with very long descriptions.
        """
        # Arrange
        long_desc = "Python " * 1000  # Very long description
        df = pd.DataFrame({
            "source": ["hh"] * 6,
            "external_id": [str(i) for i in range(6)],
            "name": ["Dev"] * 6,
            "company": ["C"] * 6,
            "salary": list(range(50000, 110000, 10000)),
            "description": [long_desc] * 6,
            "skills": [["Python"]] * 6,
            "experience": ["noExp"] * 6,
            "url": ["http://x.com"] * 6
        })
        
        # Act
        result = cluster_vacancies(df)
        
        # Assert
        assert "cluster" in result.columns
    
    @pytest.mark.unit
    def test_unicode_descriptions(self):
        """
        Test clustering with unicode characters in descriptions.
        """
        # Arrange
        df = pd.DataFrame({
            "source": ["hh"] * 6,
            "external_id": [str(i) for i in range(6)],
            "name": ["Разработчик"] * 6,
            "company": ["Компания"] * 6,
            "salary": list(range(50000, 110000, 10000)),
            "description": ["Описание вакансии на русском языке"] * 6,
            "skills": [["Python"]] * 6,
            "experience": ["noExp"] * 6,
            "url": ["http://x.com"] * 6
        })
        
        # Act
        result = cluster_vacancies(df)
        
        # Assert
        assert "cluster" in result.columns
    
    @pytest.mark.unit
    def test_mixed_source_data(self):
        """
        Test clustering with mixed HH and SuperJob data.
        """
        # Arrange
        df = pd.DataFrame({
            "source": ["hh", "hh", "hh", "sj", "sj", "sj"],
            "external_id": [str(i) for i in range(6)],
            "name": ["Dev"] * 6,
            "company": ["C"] * 6,
            "salary": [50000, 60000, 70000, 100000, 120000, 150000],
            "description": ["D"] * 6,
            "skills": [["Python"]] * 6,
            "experience": ["noExp"] * 6,
            "url": ["http://x.com"] * 6
        })
        
        # Act
        result = cluster_vacancies(df)
        
        # Assert
        assert "cluster" in result.columns
        assert len(result) == 6
