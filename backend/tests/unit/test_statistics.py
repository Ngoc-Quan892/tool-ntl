"""
Unit tests for statistics module.
"""
import pytest
import numpy as np
from app.core.statistics import (
    chi_square_goodness_of_fit,
    runs_test,
    calculate_entropy,
    bayesian_win_probability,
    autocorrelation,
    binomial_test,
    pattern_significance_test,
    confidence_interval,
    comprehensive_statistical_analysis,
)


class TestChiSquareTests:
    """Tests for chi-square tests."""
    
    def test_chi_square_goodness_of_fit(self):
        """Test chi-square goodness of fit."""
        observed = [50, 30, 20]
        expected = [50, 30, 20]
        result = chi_square_goodness_of_fit(observed, expected)
        
        assert result["test"] == "chi_square_goodness_of_fit"
        assert result["statistic"] == 0.0
        assert result["p_value"] > 0.9
        assert result["significant"] is False
    
    def test_chi_square_with_deviation(self):
        """Test chi-square with deviation."""
        observed = [60, 25, 15]
        expected = [50, 30, 20]
        result = chi_square_goodness_of_fit(observed, expected)
        
        assert result["statistic"] > 0
        assert "p_value" in result
        assert "interpretation" in result


class TestRunsTest:
    """Tests for runs test."""
    
    def test_runs_test_random_sequence(self):
        """Test runs test with random sequence."""
        sequence = ["B", "P", "B", "P", "B", "P", "B", "P"]
        result = runs_test(sequence)
        
        assert result["test"] == "runs_test"
        assert result["runs"] > 0
        assert "p_value" in result
        assert "significant" in result
    
    def test_runs_test_streak(self):
        """Test runs test with streak."""
        sequence = ["B", "B", "B", "B", "P", "P", "P"]
        result = runs_test(sequence)
        
        assert result["runs"] == 2
        assert result["significant"] is True  # Non-random
    
    def test_runs_test_empty(self):
        """Test runs test with empty sequence."""
        result = runs_test([])
        assert result["interpretation"] == "Insufficient data"


class TestEntropy:
    """Tests for entropy analysis."""
    
    def test_entropy_uniform(self):
        """Test entropy with uniform distribution."""
        sequence = ["B", "P", "B", "P", "B", "P"]
        result = calculate_entropy(sequence)
        
        assert result["test"] == "entropy"
        assert result["entropy"] > 0
        assert result["normalized_entropy"] > 0
        assert result["normalized_entropy"] <= 1.0
    
    def test_entropy_single_value(self):
        """Test entropy with single value."""
        sequence = ["B", "B", "B", "B"]
        result = calculate_entropy(sequence)
        
        assert result["entropy"] == 0.0
        assert result["normalized_entropy"] == 0.0


class TestBayesianInference:
    """Tests for Bayesian inference."""
    
    def test_bayesian_win_probability(self):
        """Test Bayesian win probability."""
        result = bayesian_win_probability(wins=30, total=50)
        
        assert result["test"] == "bayesian_win_probability"
        assert 0 <= result["posterior_mean"] <= 1
        assert len(result["credible_interval_95"]) == 2
        assert result["credible_interval_95"][0] < result["credible_interval_95"][1]
    
    def test_bayesian_no_data(self):
        """Test Bayesian with no data."""
        result = bayesian_win_probability(wins=0, total=0)
        assert result["posterior_mean"] == 0.5


class TestAutocorrelation:
    """Tests for autocorrelation."""
    
    def test_autocorrelation_single_lag(self):
        """Test autocorrelation with single lag."""
        sequence = [1, 0, 1, 0, 1, 0, 1, 0]
        result = autocorrelation(sequence, lag=1)
        
        assert result["test"] == "autocorrelation"
        assert "autocorrelation" in result
        assert -1 <= result["autocorrelation"] <= 1
    
    def test_autocorrelation_multiple_lags(self):
        """Test autocorrelation with multiple lags."""
        sequence = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
        result = autocorrelation(sequence, max_lags=3)
        
        assert "autocorrelations" in result
        assert len(result["autocorrelations"]) > 0


class TestBinomialTest:
    """Tests for binomial test."""
    
    def test_binomial_test(self):
        """Test binomial test."""
        result = binomial_test(successes=30, trials=50, expected_prob=0.5)
        
        assert result["test"] == "binomial_test"
        assert 0 <= result["p_value"] <= 1
        assert "confidence_interval_95" in result
        assert len(result["confidence_interval_95"]) == 2


class TestPatternSignificance:
    """Tests for pattern significance."""
    
    def test_pattern_significance(self):
        """Test pattern significance."""
        result = pattern_significance_test(
            pattern_count=10,
            total_hands=100,
            expected_frequency=0.05
        )
        
        assert result["test"] == "pattern_significance"
        assert "p_value" in result
        assert "significant" in result


class TestConfidenceInterval:
    """Tests for confidence interval."""
    
    def test_confidence_interval(self):
        """Test confidence interval calculation."""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = confidence_interval(data, confidence=0.95)
        
        assert result["test"] == "confidence_interval"
        assert "mean" in result
        assert "interval" in result
        assert result["interval"][0] < result["mean"] < result["interval"][1]


class TestComprehensiveAnalysis:
    """Tests for comprehensive statistical analysis."""
    
    def test_comprehensive_analysis(self):
        """Test comprehensive analysis."""
        outcomes = ["B", "P", "B", "B", "P", "T", "B", "P", "B", "B"] * 10
        result = comprehensive_statistical_analysis(outcomes)
        
        assert "total_samples" in result
        assert "tests" in result
        assert len(result["tests"]) > 5  # Should have multiple tests
    
    def test_comprehensive_analysis_empty(self):
        """Test comprehensive analysis with empty data."""
        result = comprehensive_statistical_analysis([])
        assert result["total_samples"] == 0
        assert len(result["tests"]) == 0

