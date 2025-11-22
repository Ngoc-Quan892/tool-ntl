"""
Comprehensive statistical analysis module for Baccarat data.

This module provides:
- Chi-square tests
- Runs test
- Entropy analysis
- Bayesian inference
- Autocorrelation
- And 10+ additional statistical tests
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

try:
    from scipy import stats
    from scipy.stats import chi2, norm, binom, poisson
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    # Fallback implementations will be used


# ==================== CHI-SQUARE TESTS ====================

def chi_square_goodness_of_fit(
    observed: List[int],
    expected: List[float],
    degrees_of_freedom: Optional[int] = None
) -> Dict[str, Any]:
    """
    Chi-square goodness of fit test.
    
    Tests if observed frequencies match expected frequencies.
    
    Args:
        observed: Observed frequencies
        expected: Expected frequencies
        degrees_of_freedom: Optional degrees of freedom (default: len(observed) - 1)
        
    Returns:
        Dictionary with test statistic, p-value, and interpretation
    """
    if len(observed) != len(expected):
        raise ValueError("Observed and expected must have same length")
    
    # Remove zero expected values
    valid_indices = [i for i, e in enumerate(expected) if e > 0]
    observed = [observed[i] for i in valid_indices]
    expected = [expected[i] for i in valid_indices]
    
    if not observed:
        return {
            "test": "chi_square_goodness_of_fit",
            "statistic": 0.0,
            "p_value": 1.0,
            "degrees_of_freedom": 0,
            "significant": False,
            "interpretation": "No valid data"
        }
    
    # Calculate chi-square statistic
    chi_square = sum((o - e) ** 2 / e for o, e in zip(observed, expected))
    
    # Degrees of freedom
    df = degrees_of_freedom if degrees_of_freedom is not None else len(observed) - 1
    
    # Calculate p-value
    if SCIPY_AVAILABLE:
        p_value = 1 - chi2.cdf(chi_square, df)
    else:
        # Approximate using normal distribution for large df
        if df > 30:
            z = (chi_square - df) / math.sqrt(2 * df)
            p_value = 1 - norm.cdf(z)
        else:
            # Simple approximation
            p_value = max(0.0, min(1.0, 1 - (chi_square / (df + chi_square))))
    
    return {
        "test": "chi_square_goodness_of_fit",
        "statistic": round(chi_square, 4),
        "p_value": round(p_value, 6),
        "degrees_of_freedom": df,
        "significant": p_value < 0.05,
        "interpretation": "Data matches expected distribution" if p_value >= 0.05 else "Data deviates from expected distribution"
    }


def chi_square_independence(
    contingency_table: List[List[int]]
) -> Dict[str, Any]:
    """
    Chi-square test of independence.
    
    Tests if two categorical variables are independent.
    
    Args:
        contingency_table: 2D array of observed frequencies
        
    Returns:
        Dictionary with test statistic, p-value, and interpretation
    """
    table = np.array(contingency_table)
    row_sums = table.sum(axis=1)
    col_sums = table.sum(axis=0)
    total = table.sum()
    
    if total == 0:
        return {
            "test": "chi_square_independence",
            "statistic": 0.0,
            "p_value": 1.0,
            "degrees_of_freedom": 0,
            "significant": False,
            "interpretation": "No data"
        }
    
    # Calculate expected frequencies
    expected = np.outer(row_sums, col_sums) / total
    
    # Calculate chi-square statistic
    chi_square = np.sum((table - expected) ** 2 / (expected + 1e-10))
    
    # Degrees of freedom
    df = (table.shape[0] - 1) * (table.shape[1] - 1)
    
    # Calculate p-value
    if SCIPY_AVAILABLE:
        p_value = 1 - chi2.cdf(chi_square, df)
    else:
        if df > 30:
            z = (chi_square - df) / math.sqrt(2 * df)
            p_value = 1 - norm.cdf(z)
        else:
            p_value = max(0.0, min(1.0, 1 - (chi_square / (df + chi_square))))
    
    return {
        "test": "chi_square_independence",
        "statistic": round(float(chi_square), 4),
        "p_value": round(p_value, 6),
        "degrees_of_freedom": df,
        "significant": p_value < 0.05,
        "interpretation": "Variables are independent" if p_value >= 0.05 else "Variables are dependent"
    }


# ==================== RUNS TEST ====================

def runs_test(sequence: List[str], median_split: bool = False) -> Dict[str, Any]:
    """
    Runs test for randomness.
    
    Tests if a sequence is random by counting runs (consecutive identical values).
    
    Args:
        sequence: Sequence of outcomes (e.g., ['B', 'P', 'B', ...])
        median_split: If True, split by median value; if False, use mode
        
    Returns:
        Dictionary with test statistic, p-value, and interpretation
    """
    if len(sequence) < 2:
        return {
            "test": "runs_test",
            "statistic": 0.0,
            "p_value": 1.0,
            "runs": 0,
            "expected_runs": 0.0,
            "significant": False,
            "interpretation": "Insufficient data"
        }
    
    # Convert to binary sequence
    if median_split:
        # Split by median
        values = [ord(s) for s in sequence]
        median_val = np.median(values)
        binary = [1 if v >= median_val else 0 for v in values]
    else:
        # Use most common value as split
        counter = Counter(sequence)
        mode = counter.most_common(1)[0][0]
        binary = [1 if s == mode else 0 for s in sequence]
    
    n1 = sum(binary)  # Count of 1s
    n2 = len(binary) - n1  # Count of 0s
    n = len(binary)
    
    if n1 == 0 or n2 == 0:
        return {
            "test": "runs_test",
            "statistic": 0.0,
            "p_value": 1.0,
            "runs": 1,
            "expected_runs": 1.0,
            "significant": False,
            "interpretation": "No variation in data"
        }
    
    # Count runs
    runs = 1
    for i in range(1, len(binary)):
        if binary[i] != binary[i-1]:
            runs += 1
    
    # Expected runs
    expected_runs = (2 * n1 * n2) / n + 1
    
    # Variance
    variance = (2 * n1 * n2 * (2 * n1 * n2 - n)) / (n * n * (n - 1))
    
    if variance <= 0:
        return {
            "test": "runs_test",
            "statistic": 0.0,
            "p_value": 1.0,
            "runs": runs,
            "expected_runs": expected_runs,
            "significant": False,
            "interpretation": "Cannot calculate variance"
        }
    
    # Z-score
    z_score = (runs - expected_runs) / math.sqrt(variance)
    
    # P-value (two-tailed)
    if SCIPY_AVAILABLE:
        p_value = 2 * (1 - norm.cdf(abs(z_score)))
    else:
        # Normal approximation
        p_value = 2 * (1 - _normal_cdf(abs(z_score)))
    
    return {
        "test": "runs_test",
        "statistic": round(z_score, 4),
        "p_value": round(p_value, 6),
        "runs": runs,
        "expected_runs": round(expected_runs, 2),
        "n1": n1,
        "n2": n2,
        "significant": p_value < 0.05,
        "interpretation": "Sequence appears random" if p_value >= 0.05 else "Sequence shows non-random pattern"
    }


# ==================== ENTROPY ANALYSIS ====================

def calculate_entropy(sequence: List[str], base: float = 2.0) -> Dict[str, Any]:
    """
    Calculate Shannon entropy of a sequence.
    
    Higher entropy indicates more randomness/unpredictability.
    
    Args:
        sequence: Sequence of outcomes
        base: Logarithm base (2 for bits, e for nats)
        
    Returns:
        Dictionary with entropy value and interpretation
    """
    if not sequence:
        return {
            "test": "entropy",
            "entropy": 0.0,
            "max_entropy": 0.0,
            "normalized_entropy": 0.0,
            "interpretation": "No data"
        }
    
    # Count frequencies
    counter = Counter(sequence)
    n = len(sequence)
    
    # Calculate entropy
    entropy = 0.0
    for count in counter.values():
        if count > 0:
            p = count / n
            entropy -= p * math.log(p, base)
    
    # Maximum entropy (uniform distribution)
    max_entropy = math.log(len(counter), base) if counter else 0.0
    
    # Normalized entropy (0 to 1)
    normalized = entropy / max_entropy if max_entropy > 0 else 0.0
    
    return {
        "test": "entropy",
        "entropy": round(entropy, 4),
        "max_entropy": round(max_entropy, 4),
        "normalized_entropy": round(normalized, 4),
        "unique_values": len(counter),
        "interpretation": "High randomness" if normalized > 0.8 else "Low randomness" if normalized < 0.5 else "Moderate randomness"
    }


# ==================== BAYESIAN INFERENCE ====================

def bayesian_inference(
    prior_prob: float,
    likelihood: float,
    evidence: float
) -> Dict[str, Any]:
    """
    Bayesian inference using Bayes' theorem.
    
    P(A|B) = P(B|A) * P(A) / P(B)
    
    Args:
        prior_prob: Prior probability P(A)
        likelihood: Likelihood P(B|A)
        evidence: Evidence P(B)
        
    Returns:
        Dictionary with posterior probability and interpretation
    """
    if evidence == 0:
        return {
            "test": "bayesian_inference",
            "posterior": 0.0,
            "prior": prior_prob,
            "likelihood": likelihood,
            "interpretation": "Invalid evidence"
        }
    
    posterior = (likelihood * prior_prob) / evidence
    
    return {
        "test": "bayesian_inference",
        "posterior": round(posterior, 6),
        "prior": prior_prob,
        "likelihood": likelihood,
        "evidence": evidence,
        "interpretation": f"Posterior probability: {posterior:.2%}"
    }


def bayesian_win_probability(
    wins: int,
    total: int,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0
) -> Dict[str, Any]:
    """
    Bayesian estimation of win probability using Beta distribution.
    
    Args:
        wins: Number of wins
        total: Total number of trials
        prior_alpha: Prior alpha parameter (default: 1 for uniform prior)
        prior_beta: Prior beta parameter (default: 1 for uniform prior)
        
    Returns:
        Dictionary with posterior mean, credible interval, etc.
    """
    if total == 0:
        return {
            "test": "bayesian_win_probability",
            "posterior_mean": 0.5,
            "credible_interval_95": (0.0, 1.0),
            "interpretation": "No data"
        }
    
    # Posterior parameters
    alpha_post = prior_alpha + wins
    beta_post = prior_beta + (total - wins)
    
    # Posterior mean
    posterior_mean = alpha_post / (alpha_post + beta_post)
    
    # 95% credible interval (approximate)
    if SCIPY_AVAILABLE:
        from scipy.stats import beta
        lower = beta.ppf(0.025, alpha_post, beta_post)
        upper = beta.ppf(0.975, alpha_post, beta_post)
    else:
        # Approximation
        std = math.sqrt((alpha_post * beta_post) / ((alpha_post + beta_post) ** 2 * (alpha_post + beta_post + 1)))
        lower = max(0.0, posterior_mean - 1.96 * std)
        upper = min(1.0, posterior_mean + 1.96 * std)
    
    return {
        "test": "bayesian_win_probability",
        "posterior_mean": round(posterior_mean, 6),
        "credible_interval_95": (round(lower, 6), round(upper, 6)),
        "alpha": alpha_post,
        "beta": beta_post,
        "wins": wins,
        "total": total,
        "interpretation": f"Win probability: {posterior_mean:.2%} (95% CI: {lower:.2%} - {upper:.2%})"
    }


# ==================== AUTOCORRELATION ====================

def autocorrelation(
    sequence: List[float],
    lag: int = 1,
    max_lags: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calculate autocorrelation at specified lag(s).
    
    Measures correlation between values at different time points.
    
    Args:
        sequence: Sequence of numeric values
        lag: Single lag to calculate, or if max_lags is provided, calculate up to max_lags
        max_lags: If provided, calculate autocorrelation for lags 1 to max_lags
        
    Returns:
        Dictionary with autocorrelation values and interpretation
    """
    if len(sequence) < 2:
        return {
            "test": "autocorrelation",
            "lag": lag,
            "autocorrelation": 0.0,
            "significant": False,
            "interpretation": "Insufficient data"
        }
    
    arr = np.array(sequence)
    mean = np.mean(arr)
    
    if max_lags:
        # Calculate for multiple lags
        autocorrs = {}
        for l in range(1, min(max_lags + 1, len(sequence) // 2)):
            if l >= len(sequence):
                break
            shifted = arr[l:]
            original = arr[:-l]
            numerator = np.sum((original - mean) * (shifted - mean))
            denominator = np.sum((arr - mean) ** 2)
            if denominator > 0:
                autocorrs[l] = numerator / denominator
            else:
                autocorrs[l] = 0.0
        
        # Test significance (approximate)
        n = len(sequence)
        significant_lags = []
        for l, ac in autocorrs.items():
            # Standard error for autocorrelation
            se = 1.0 / math.sqrt(n)
            if abs(ac) > 1.96 * se:  # 95% confidence
                significant_lags.append(l)
        
        return {
            "test": "autocorrelation",
            "autocorrelations": {str(k): round(v, 4) for k, v in autocorrs.items()},
            "significant_lags": significant_lags,
            "interpretation": f"Significant autocorrelation at lags: {significant_lags}" if significant_lags else "No significant autocorrelation"
        }
    else:
        # Single lag
        if lag >= len(sequence):
            return {
                "test": "autocorrelation",
                "lag": lag,
                "autocorrelation": 0.0,
                "significant": False,
                "interpretation": "Lag too large"
            }
        
        shifted = arr[lag:]
        original = arr[:-lag]
        numerator = np.sum((original - mean) * (shifted - mean))
        denominator = np.sum((arr - mean) ** 2)
        
        if denominator > 0:
            autocorr = numerator / denominator
        else:
            autocorr = 0.0
        
        # Test significance
        n = len(sequence)
        se = 1.0 / math.sqrt(n)
        significant = abs(autocorr) > 1.96 * se
        
        return {
            "test": "autocorrelation",
            "lag": lag,
            "autocorrelation": round(autocorr, 4),
            "significant": significant,
            "interpretation": "Significant autocorrelation detected" if significant else "No significant autocorrelation"
        }


# ==================== ADDITIONAL STATISTICAL TESTS ====================

def kolmogorov_smirnov_test(
    data: List[float],
    distribution: str = "uniform",
    params: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Kolmogorov-Smirnov test for distribution.
    
    Tests if data follows a specified distribution.
    
    Args:
        data: Sample data
        distribution: Distribution name ("uniform", "normal")
        params: Distribution parameters
        
    Returns:
        Dictionary with test statistic, p-value, and interpretation
    """
    if len(data) < 2:
        return {
            "test": "kolmogorov_smirnov",
            "statistic": 0.0,
            "p_value": 1.0,
            "significant": False,
            "interpretation": "Insufficient data"
        }
    
    sorted_data = sorted(data)
    n = len(sorted_data)
    
    if distribution == "uniform":
        # Test against uniform [0, 1]
        # Normalize data to [0, 1]
        min_val = min(data)
        max_val = max(data)
        if max_val == min_val:
            return {
                "test": "kolmogorov_smirnov",
                "statistic": 0.0,
                "p_value": 1.0,
                "significant": False,
                "interpretation": "No variation in data"
            }
        normalized = [(x - min_val) / (max_val - min_val) for x in sorted_data]
        
        # Calculate KS statistic
        ks_stat = 0.0
        for i, val in enumerate(normalized):
            expected = (i + 1) / n
            diff1 = abs(val - expected)
            diff2 = abs(val - i / n) if i > 0 else val
            ks_stat = max(ks_stat, diff1, diff2)
    
    elif distribution == "normal":
        if not params:
            mean = np.mean(data)
            std = np.std(data)
        else:
            mean = params.get("mean", np.mean(data))
            std = params.get("std", np.std(data))
        
        if std == 0:
            return {
                "test": "kolmogorov_smirnov",
                "statistic": 0.0,
                "p_value": 1.0,
                "significant": False,
                "interpretation": "No variation in data"
            }
        
        # Normalize to standard normal
        normalized = [(x - mean) / std for x in sorted_data]
        
        # Calculate KS statistic against standard normal
        if SCIPY_AVAILABLE:
            from scipy.stats import norm
            ks_stat = 0.0
            for i, val in enumerate(normalized):
                expected = norm.cdf(val)
                diff1 = abs((i + 1) / n - expected)
                diff2 = abs(i / n - expected) if i > 0 else abs(expected)
                ks_stat = max(ks_stat, diff1, diff2)
        else:
            ks_stat = 0.0  # Simplified
    
    else:
        return {
            "test": "kolmogorov_smirnov",
            "statistic": 0.0,
            "p_value": 1.0,
            "significant": False,
            "interpretation": f"Unknown distribution: {distribution}"
        }
    
    # Approximate p-value
    if SCIPY_AVAILABLE:
        from scipy.stats import kstest
        if distribution == "uniform":
            result = kstest(data, "uniform", args=(min(data), max(data) - min(data)))
            p_value = result.pvalue
        else:
            result = kstest(data, "norm", args=(mean, std))
            p_value = result.pvalue
    else:
        # Approximation
        p_value = max(0.0, min(1.0, 2 * math.exp(-2 * n * ks_stat ** 2)))
    
    return {
        "test": "kolmogorov_smirnov",
        "statistic": round(ks_stat, 4),
        "p_value": round(p_value, 6),
        "distribution": distribution,
        "significant": p_value < 0.05,
        "interpretation": f"Data follows {distribution} distribution" if p_value >= 0.05 else f"Data does not follow {distribution} distribution"
    }


def binomial_test(
    successes: int,
    trials: int,
    expected_prob: float = 0.5
) -> Dict[str, Any]:
    """
    Binomial test for proportion.
    
    Tests if observed proportion differs from expected.
    
    Args:
        successes: Number of successes
        trials: Total number of trials
        expected_prob: Expected probability of success
        
    Returns:
        Dictionary with p-value and confidence interval
    """
    if trials == 0:
        return {
            "test": "binomial_test",
            "p_value": 1.0,
            "observed_proportion": 0.0,
            "expected_proportion": expected_prob,
            "confidence_interval_95": (0.0, 1.0),
            "significant": False,
            "interpretation": "No data"
        }
    
    observed_prop = successes / trials
    
    # Calculate p-value (two-tailed)
    if SCIPY_AVAILABLE:
        try:
            from scipy.stats import binomtest
            result = binomtest(successes, trials, expected_prob, alternative='two-sided')
            p_value = result.pvalue
        except ImportError:
            # Fallback
            if trials * expected_prob > 5 and trials * (1 - expected_prob) > 5:
                z = (observed_prop - expected_prob) / math.sqrt(expected_prob * (1 - expected_prob) / trials)
                p_value = 2 * (1 - _normal_cdf(abs(z)))
            else:
                p_value = 0.05  # Placeholder
    else:
        # Approximation using normal distribution
        if trials * expected_prob > 5 and trials * (1 - expected_prob) > 5:
            z = (observed_prop - expected_prob) / math.sqrt(expected_prob * (1 - expected_prob) / trials)
            p_value = 2 * (1 - _normal_cdf(abs(z)))
        else:
            # Exact binomial (simplified)
            p_value = 0.05  # Placeholder
    
    # Confidence interval (95%)
    if SCIPY_AVAILABLE:
        from scipy.stats import beta
        alpha = 0.05
        lower = beta.ppf(alpha / 2, successes, trials - successes + 1)
        upper = beta.ppf(1 - alpha / 2, successes + 1, trials - successes)
    else:
        # Normal approximation
        se = math.sqrt(observed_prop * (1 - observed_prop) / trials)
        lower = max(0.0, observed_prop - 1.96 * se)
        upper = min(1.0, observed_prop + 1.96 * se)
    
    return {
        "test": "binomial_test",
        "p_value": round(p_value, 6),
        "observed_proportion": round(observed_prop, 4),
        "expected_proportion": expected_prob,
        "successes": successes,
        "trials": trials,
        "confidence_interval_95": (round(lower, 6), round(upper, 6)),
        "significant": p_value < 0.05,
        "interpretation": f"Proportion matches expected ({expected_prob:.2%})" if p_value >= 0.05 else f"Proportion differs from expected ({expected_prob:.2%})"
    }


def mann_whitney_u_test(
    group1: List[float],
    group2: List[float]
) -> Dict[str, Any]:
    """
    Mann-Whitney U test (non-parametric test for two groups).
    
    Tests if two groups have different distributions.
    
    Args:
        group1: First group of values
        group2: Second group of values
        
    Returns:
        Dictionary with U statistic, p-value, and interpretation
    """
    if len(group1) < 2 or len(group2) < 2:
        return {
            "test": "mann_whitney_u",
            "u_statistic": 0.0,
            "p_value": 1.0,
            "significant": False,
            "interpretation": "Insufficient data"
        }
    
    if SCIPY_AVAILABLE:
        from scipy.stats import mannwhitneyu
        result = mannwhitneyu(group1, group2, alternative='two-sided')
        u_stat = result.statistic
        p_value = result.pvalue
    else:
        # Simplified calculation
        combined = [(x, 1) for x in group1] + [(x, 2) for x in group2]
        combined.sort()
        
        rank = 1
        ranks = []
        for i, (val, group) in enumerate(combined):
            if i > 0 and combined[i-1][0] == val:
                # Tie
                rank_sum = sum(j + 1 for j in range(i - len([x for x in combined[:i] if x[0] == val]), i + 1))
                avg_rank = rank_sum / len([x for x in combined if x[0] == val])
                ranks.append((avg_rank, group))
            else:
                ranks.append((rank, group))
                rank += 1
        
        r1 = sum(r for r, g in ranks if g == 1)
        n1 = len(group1)
        n2 = len(group2)
        u1 = n1 * n2 + n1 * (n1 + 1) / 2 - r1
        u2 = n1 * n2 - u1
        u_stat = min(u1, u2)
        
        # Approximate p-value using normal distribution
        mean_u = n1 * n2 / 2
        var_u = n1 * n2 * (n1 + n2 + 1) / 12
        z = (u_stat - mean_u) / math.sqrt(var_u)
        p_value = 2 * (1 - _normal_cdf(abs(z)))
    
    return {
        "test": "mann_whitney_u",
        "u_statistic": round(float(u_stat), 4),
        "p_value": round(p_value, 6),
        "significant": p_value < 0.05,
        "interpretation": "Groups have similar distributions" if p_value >= 0.05 else "Groups have different distributions"
    }


def ljung_box_test(
    residuals: List[float],
    lags: int = 10
) -> Dict[str, Any]:
    """
    Ljung-Box test for autocorrelation in residuals.
    
    Tests if residuals are independently distributed.
    
    Args:
        residuals: Residual values
        lags: Number of lags to test
        
    Returns:
        Dictionary with Q statistic, p-value, and interpretation
    """
    if len(residuals) < lags + 1:
        return {
            "test": "ljung_box",
            "q_statistic": 0.0,
            "p_value": 1.0,
            "lags": lags,
            "significant": False,
            "interpretation": "Insufficient data"
        }
    
    n = len(residuals)
    mean_res = np.mean(residuals)
    var_res = np.var(residuals)
    
    if var_res == 0:
        return {
            "test": "ljung_box",
            "q_statistic": 0.0,
            "p_value": 1.0,
            "lags": lags,
            "significant": False,
            "interpretation": "No variation in residuals"
        }
    
    # Calculate Q statistic
    q_stat = 0.0
    for k in range(1, min(lags + 1, n)):
        autocorr_k = autocorrelation(residuals, lag=k)
        if isinstance(autocorr_k, dict) and "autocorrelation" in autocorr_k:
            r_k = autocorr_k["autocorrelation"]
            q_stat += (r_k ** 2) / (n - k)
    
    q_stat = n * (n + 2) * q_stat
    
    # P-value (chi-square distribution with lags degrees of freedom)
    if SCIPY_AVAILABLE:
        p_value = 1 - chi2.cdf(q_stat, lags)
    else:
        p_value = max(0.0, min(1.0, 1 - (q_stat / (lags + q_stat))))
    
    return {
        "test": "ljung_box",
        "q_statistic": round(q_stat, 4),
        "p_value": round(p_value, 6),
        "lags": lags,
        "degrees_of_freedom": lags,
        "significant": p_value < 0.05,
        "interpretation": "No autocorrelation in residuals" if p_value >= 0.05 else "Autocorrelation detected in residuals"
    }


def jarque_bera_test(data: List[float]) -> Dict[str, Any]:
    """
    Jarque-Bera test for normality.
    
    Tests if data follows a normal distribution.
    
    Args:
        data: Sample data
        
    Returns:
        Dictionary with JB statistic, p-value, and interpretation
    """
    if len(data) < 3:
        return {
            "test": "jarque_bera",
            "jb_statistic": 0.0,
            "p_value": 1.0,
            "skewness": 0.0,
            "kurtosis": 0.0,
            "significant": False,
            "interpretation": "Insufficient data"
        }
    
    arr = np.array(data)
    n = len(arr)
    mean = np.mean(arr)
    std = np.std(arr)
    
    if std == 0:
        return {
            "test": "jarque_bera",
            "jb_statistic": 0.0,
            "p_value": 1.0,
            "skewness": 0.0,
            "kurtosis": 0.0,
            "significant": False,
            "interpretation": "No variation in data"
        }
    
    # Calculate skewness
    skewness = np.mean(((arr - mean) / std) ** 3)
    
    # Calculate kurtosis
    kurtosis = np.mean(((arr - mean) / std) ** 4) - 3
    
    # Jarque-Bera statistic
    jb = (n / 6) * (skewness ** 2 + (kurtosis ** 2) / 4)
    
    # P-value (chi-square with 2 degrees of freedom)
    if SCIPY_AVAILABLE:
        p_value = 1 - chi2.cdf(jb, 2)
    else:
        p_value = max(0.0, min(1.0, 1 - (jb / (2 + jb))))
    
    return {
        "test": "jarque_bera",
        "jb_statistic": round(jb, 4),
        "p_value": round(p_value, 6),
        "skewness": round(skewness, 4),
        "kurtosis": round(kurtosis, 4),
        "significant": p_value < 0.05,
        "interpretation": "Data is normally distributed" if p_value >= 0.05 else "Data is not normally distributed"
    }


def confidence_interval(
    data: List[float],
    confidence: float = 0.95
) -> Dict[str, Any]:
    """
    Calculate confidence interval for mean.
    
    Args:
        data: Sample data
        confidence: Confidence level (default: 0.95 for 95%)
        
    Returns:
        Dictionary with mean, confidence interval, and interpretation
    """
    if not data:
        return {
            "test": "confidence_interval",
            "mean": 0.0,
            "confidence": confidence,
            "interval": (0.0, 0.0),
            "interpretation": "No data"
        }
    
    arr = np.array(data)
    n = len(arr)
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)  # Sample standard deviation
    
    if n < 2:
        return {
            "test": "confidence_interval",
            "mean": round(mean, 4),
            "confidence": confidence,
            "interval": (round(mean, 4), round(mean, 4)),
            "interpretation": "Insufficient data for interval"
        }
    
    # Standard error
    se = std / math.sqrt(n)
    
    # Critical value
    alpha = 1 - confidence
    if SCIPY_AVAILABLE:
        from scipy.stats import t
        critical = t.ppf(1 - alpha / 2, n - 1)
    else:
        # Use normal approximation for large n
        if n > 30:
            critical = 1.96 if confidence == 0.95 else 2.576 if confidence == 0.99 else 1.645
        else:
            critical = 2.0  # Approximation
    
    margin = critical * se
    lower = mean - margin
    upper = mean + margin
    
    return {
        "test": "confidence_interval",
        "mean": round(mean, 4),
        "std": round(std, 4),
        "confidence": confidence,
        "interval": (round(lower, 6), round(upper, 6)),
        "margin_of_error": round(margin, 6),
        "sample_size": n,
        "interpretation": f"Mean: {mean:.4f} ({confidence*100:.0f}% CI: {lower:.4f} - {upper:.4f})"
    }


def pattern_significance_test(
    pattern_count: int,
    total_hands: int,
    expected_frequency: float
) -> Dict[str, Any]:
    """
    Test significance of a pattern occurrence.
    
    Args:
        pattern_count: Number of times pattern occurred
        total_hands: Total number of hands
        expected_frequency: Expected frequency of pattern
        
    Returns:
        Dictionary with p-value, significance, and interpretation
    """
    if total_hands == 0:
        return {
            "test": "pattern_significance",
            "pattern_count": 0,
            "total_hands": 0,
            "observed_frequency": 0.0,
            "expected_frequency": expected_frequency,
            "p_value": 1.0,
            "significant": False,
            "interpretation": "No data"
        }
    
    observed_freq = pattern_count / total_hands
    expected_count = expected_frequency * total_hands
    
    # Use binomial test
    if SCIPY_AVAILABLE:
        from scipy.stats import binom
        if observed_freq > expected_frequency:
            p_value = 1 - binom.cdf(pattern_count - 1, total_hands, expected_frequency)
        else:
            p_value = binom.cdf(pattern_count, total_hands, expected_frequency)
        p_value = min(1.0, 2 * p_value)  # Two-tailed
    else:
        # Normal approximation
        z = (pattern_count - expected_count) / math.sqrt(expected_count * (1 - expected_frequency))
        p_value = 2 * (1 - _normal_cdf(abs(z)))
    
    return {
        "test": "pattern_significance",
        "pattern_count": pattern_count,
        "total_hands": total_hands,
        "observed_frequency": round(observed_freq, 6),
        "expected_frequency": expected_frequency,
        "p_value": round(p_value, 6),
        "significant": p_value < 0.05,
        "interpretation": "Pattern frequency is significant" if p_value < 0.05 else "Pattern frequency is not significant"
    }


# ==================== HELPER FUNCTIONS ====================

def _normal_cdf(x: float) -> float:
    """Cumulative distribution function for standard normal distribution."""
    # Approximation using error function
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def binom_test(x: int, n: int, p: float, alternative: str = 'two-sided') -> float:
    """Binomial test (scipy fallback)."""
    if SCIPY_AVAILABLE:
        from scipy.stats import binomtest
        result = binomtest(x, n, p, alternative=alternative)
        return result.pvalue
    else:
        # Approximation
        if n * p > 5 and n * (1 - p) > 5:
            z = (x / n - p) / math.sqrt(p * (1 - p) / n)
            if alternative == 'two-sided':
                return 2 * (1 - _normal_cdf(abs(z)))
            elif alternative == 'greater':
                return 1 - _normal_cdf(z)
            else:
                return _normal_cdf(z)
        return 0.05  # Placeholder


# ==================== COMPREHENSIVE ANALYSIS ====================

def comprehensive_statistical_analysis(
    outcomes: List[str],
    numeric_data: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Perform comprehensive statistical analysis on baccarat outcomes.
    
    Args:
        outcomes: List of outcomes ('B', 'P', 'T')
        numeric_data: Optional numeric data (e.g., counts, scores)
        
    Returns:
        Dictionary with all statistical test results
    """
    results = {
        "total_samples": len(outcomes),
        "tests": {}
    }
    
    if not outcomes:
        return results
    
    # Remove ties for some tests
    no_ties = [o for o in outcomes if o != 'T']
    
    # 1. Chi-square goodness of fit
    banker_count = outcomes.count('B')
    player_count = outcomes.count('P')
    tie_count = outcomes.count('T')
    total = len(outcomes)
    
    if total > 0:
        expected_b = 0.458597 * total
        expected_p = 0.446247 * total
        expected_t = 0.095156 * total
        
        results["tests"]["chi_square_goodness_of_fit"] = chi_square_goodness_of_fit(
            [banker_count, player_count, tie_count],
            [expected_b, expected_p, expected_t]
        )
    
    # 2. Runs test
    if len(no_ties) >= 2:
        results["tests"]["runs_test"] = runs_test(no_ties)
    
    # 3. Entropy
    results["tests"]["entropy"] = calculate_entropy(outcomes)
    
    # 4. Autocorrelation
    if len(no_ties) >= 3:
        # Convert to numeric for autocorrelation
        numeric_outcomes = [1 if o == 'B' else 0 for o in no_ties]
        results["tests"]["autocorrelation"] = autocorrelation(numeric_outcomes, max_lags=5)
    
    # 5. Binomial test for banker proportion
    if len(no_ties) > 0:
        banker_wins = no_ties.count('B')
        results["tests"]["binomial_test_banker"] = binomial_test(
            banker_wins,
            len(no_ties),
            expected_prob=0.458597
        )
    
    # 6. Pattern significance (streaks)
    if len(no_ties) >= 10:
        # Count streaks of 3 or more
        streak_count = 0
        current_streak = 1
        for i in range(1, len(no_ties)):
            if no_ties[i] == no_ties[i-1]:
                current_streak += 1
            else:
                if current_streak >= 3:
                    streak_count += 1
                current_streak = 1
        if current_streak >= 3:
            streak_count += 1
        
        # Expected frequency of streaks >= 3
        expected_freq = 0.1  # Approximation
        results["tests"]["pattern_significance_streaks"] = pattern_significance_test(
            streak_count,
            len(no_ties),
            expected_freq
        )
    
    # 7. Confidence intervals
    if numeric_data and len(numeric_data) > 0:
        results["tests"]["confidence_interval"] = confidence_interval(numeric_data)
        results["tests"]["jarque_bera"] = jarque_bera_test(numeric_data)
    
    # 8. Bayesian win probability
    if len(no_ties) > 0:
        banker_wins = no_ties.count('B')
        results["tests"]["bayesian_win_probability"] = bayesian_win_probability(
            banker_wins,
            len(no_ties)
        )
    
    # 9. Kolmogorov-Smirnov test (if numeric data)
    if numeric_data and len(numeric_data) >= 2:
        results["tests"]["kolmogorov_smirnov"] = kolmogorov_smirnov_test(
            numeric_data,
            distribution="uniform"
        )
    
    # 10. Ljung-Box test (if we can create residuals)
    if len(no_ties) >= 10:
        # Create sequence of differences
        numeric_seq = [1 if o == 'B' else -1 for o in no_ties]
        mean_seq = np.mean(numeric_seq)
        residuals = [x - mean_seq for x in numeric_seq]
        results["tests"]["ljung_box"] = ljung_box_test(residuals, lags=5)
    
    return results

