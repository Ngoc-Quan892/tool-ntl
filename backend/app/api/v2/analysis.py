"""
Analysis API endpoints.

Endpoints for statistics, pattern analysis, and edge calculations.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v2.base import NotFoundError, SuccessResponse, get_database_session
from app.core.engine import EnhancedShoe, Outcome
from app.core.roadmap import generate_roadmaps
from app.models.database import GameResult
from app.models.schemas import (
    EdgeCalculationResponse,
    PatternAnalysisResponse,
    StatisticsResponse,
    ShoeAnalysisRequest,
    ShoeAnalysisResponse,
    HypothesisTestRequest,
    HypothesisTestResponse,
    PatternSignificanceRequest,
    PatternSignificanceResponse,
    StatisticalTestResult,
)
from app.core.statistics import (
    comprehensive_statistical_analysis,
    chi_square_goodness_of_fit,
    runs_test,
    binomial_test,
    pattern_significance_test,
    autocorrelation,
    calculate_entropy,
    bayesian_win_probability,
    confidence_interval,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


def get_shoe(request: Request, shoe_id: Optional[str] = None) -> EnhancedShoe:
    """Get shoe by ID or return default."""
    if shoe_id:
        shoes = getattr(request.app.state, "shoes", {})
        if shoe_id not in shoes:
            raise NotFoundError("Shoe", shoe_id)
        return shoes[shoe_id]
    
    # Return default shoe
    if not hasattr(request.app.state, "default_shoe"):
        request.app.state.default_shoe = EnhancedShoe(decks=8)
    return request.app.state.default_shoe


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    request: Request,
    db: Session = Depends(get_database_session),
    shoe_id: Optional[str] = Query(None, description="Shoe ID (uses default if not provided)"),
) -> StatisticsResponse:
    """
    Get shoe statistics.
    
    Args:
        request: FastAPI request
        db: Database session
        shoe_id: Optional shoe ID
        
    Returns:
        Shoe statistics
    """
    if shoe_id:
        # Get statistics from specific shoe
        shoe = get_shoe(request, shoe_id)
        stats = shoe.get_statistics()
        
        return StatisticsResponse(
            total_hands=stats.get("total_hands", 0),
            banker_wins=stats.get("banker_wins", 0),
            player_wins=stats.get("player_wins", 0),
            ties=stats.get("ties", 0),
            banker_pct=stats.get("banker_pct", 0.0),
            player_pct=stats.get("player_pct", 0.0),
            tie_pct=stats.get("tie_pct", 0.0),
            max_banker_streak=stats.get("max_banker_streak", 0),
            max_player_streak=stats.get("max_player_streak", 0),
            natural_count=stats.get("natural_count", 0),
            natural_pct=stats.get("natural_pct", 0.0),
            banker_deviation=stats.get("banker_deviation", 0.0),
            player_deviation=stats.get("player_deviation", 0.0),
        )
    else:
        # Get statistics from database
        results = db.query(GameResult).all()
        
        if not results:
            return StatisticsResponse(
                total_hands=0,
                banker_wins=0,
                player_wins=0,
                ties=0,
                banker_pct=0.0,
                player_pct=0.0,
                tie_pct=0.0,
                max_banker_streak=0,
                max_player_streak=0,
                natural_count=0,
                natural_pct=0.0,
                banker_deviation=0.0,
                player_deviation=0.0,
            )
        
        outcomes = [r.result for r in results]
        banker_wins = outcomes.count("B")
        player_wins = outcomes.count("P")
        ties = outcomes.count("T")
        total = len(outcomes)
        no_tie = banker_wins + player_wins
        
        # Calculate streaks
        max_banker_streak = _calculate_max_streak(outcomes, "B")
        max_player_streak = _calculate_max_streak(outcomes, "P")
        
        # Theoretical probabilities
        from app.core.engine import THEORETICAL_PROB
        
        return StatisticsResponse(
            total_hands=total,
            banker_wins=banker_wins,
            player_wins=player_wins,
            ties=ties,
            banker_pct=round(banker_wins / no_tie * 100, 2) if no_tie > 0 else 0.0,
            player_pct=round(player_wins / no_tie * 100, 2) if no_tie > 0 else 0.0,
            tie_pct=round(ties / total * 100, 2) if total > 0 else 0.0,
            max_banker_streak=max_banker_streak,
            max_player_streak=max_player_streak,
            natural_count=0,  # Would need to track this
            natural_pct=0.0,
            banker_deviation=round(
                (banker_wins / no_tie - THEORETICAL_PROB["BANKER"]) * 100, 2
            ) if no_tie > 0 else 0.0,
            player_deviation=round(
                (player_wins / no_tie - THEORETICAL_PROB["PLAYER"]) * 100, 2
            ) if no_tie > 0 else 0.0,
        )


@router.get("/patterns", response_model=PatternAnalysisResponse)
async def get_pattern_analysis(
    request: Request,
    db: Session = Depends(get_database_session),
    shoe_id: Optional[str] = Query(None, description="Shoe ID"),
    limit: int = Query(100, ge=10, le=1000, description="Number of hands to analyze"),
) -> PatternAnalysisResponse:
    """
    Get pattern analysis.
    
    Args:
        request: FastAPI request
        db: Database session
        shoe_id: Optional shoe ID
        limit: Number of hands to analyze
        
    Returns:
        Pattern analysis
    """
    # Get history
    if shoe_id:
        shoe = get_shoe(request, shoe_id)
        history = [h.result.value for h in shoe.hand_history[-limit:]]
    else:
        results = (
            db.query(GameResult)
            .order_by(GameResult.timestamp.desc())
            .limit(limit)
            .all()
        )
        history = [r.result for r in reversed(results)]
    
    if not history:
        return PatternAnalysisResponse(
            detected_patterns=[],
            pattern_frequency={},
            streak_analysis={},
            sequence_analysis={},
        )
    
    # Detect patterns
    patterns = _detect_patterns(history)
    
    # Pattern frequency
    pattern_freq = Counter()
    for pattern in patterns:
        pattern_freq[pattern["type"]] += 1
    
    # Streak analysis
    streak_analysis = _analyze_streaks(history)
    
    # Sequence analysis
    sequence_analysis = _analyze_sequences(history)
    
    return PatternAnalysisResponse(
        detected_patterns=patterns[:20],  # Top 20 patterns
        pattern_frequency=dict(pattern_freq),
        streak_analysis=streak_analysis,
        sequence_analysis=sequence_analysis,
    )


@router.get("/edge", response_model=EdgeCalculationResponse)
async def get_edge_calculation(
    request: Request,
    shoe_id: Optional[str] = Query(None, description="Shoe ID (uses default if not provided)"),
) -> EdgeCalculationResponse:
    """
    Get edge calculations for current shoe state.
    
    Args:
        request: FastAPI request
        shoe_id: Optional shoe ID
        
    Returns:
        Edge calculations
    """
    shoe = get_shoe(request, shoe_id)
    edge = shoe.calculate_edge()
    
    return EdgeCalculationResponse(**edge)


def _calculate_max_streak(outcomes: List[str], target: str) -> int:
    """Calculate maximum streak length."""
    max_streak = 0
    current_streak = 0
    
    for outcome in outcomes:
        if outcome == target:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    
    return max_streak


def _detect_patterns(history: List[str]) -> List[Dict]:
    """Detect patterns in history."""
    patterns = []
    
    # Streak patterns
    current_streak = 1
    last_result = history[0] if history else None
    
    for i in range(1, len(history)):
        if history[i] == last_result and history[i] != "T":
            current_streak += 1
        else:
            if current_streak >= 3:
                patterns.append({
                    "type": "streak",
                    "pattern": last_result * current_streak,
                    "length": current_streak,
                    "position": i - current_streak,
                })
            current_streak = 1
            last_result = history[i]
    
    # Alternation patterns
    alternations = 0
    for i in range(1, min(10, len(history))):
        if history[i] != history[i-1] and history[i] != "T" and history[i-1] != "T":
            alternations += 1
    
    if alternations >= 5:
        patterns.append({
            "type": "alternation",
            "pattern": "Alternating",
            "length": alternations,
            "position": 0,
        })
    
    return patterns


def _analyze_streaks(history: List[str]) -> Dict:
    """Analyze streaks in history."""
    banker_streaks = []
    player_streaks = []
    
    current_banker = 0
    current_player = 0
    
    for result in history:
        if result == "B":
            current_banker += 1
            current_player = 0
            if current_banker >= 2:
                banker_streaks.append(current_banker)
        elif result == "P":
            current_player += 1
            current_banker = 0
            if current_player >= 2:
                player_streaks.append(current_player)
        else:
            current_banker = 0
            current_player = 0
    
    return {
        "banker_streaks": {
            "count": len(banker_streaks),
            "average": sum(banker_streaks) / len(banker_streaks) if banker_streaks else 0,
            "max": max(banker_streaks) if banker_streaks else 0,
        },
        "player_streaks": {
            "count": len(player_streaks),
            "average": sum(player_streaks) / len(player_streaks) if player_streaks else 0,
            "max": max(player_streaks) if player_streaks else 0,
        },
    }


def _analyze_sequences(history: List[str]) -> Dict:
    """Analyze sequences in history."""
    # Remove ties for sequence analysis
    no_ties = [h for h in history if h != "T"]
    
    if len(no_ties) < 3:
        return {"common_sequences": [], "sequence_frequency": {}}
    
    # Find common 3-hand sequences
    sequences = Counter()
    for i in range(len(no_ties) - 2):
        seq = "".join(no_ties[i:i+3])
        sequences[seq] += 1
    
    return {
        "common_sequences": [
            {"sequence": seq, "count": count}
            for seq, count in sequences.most_common(10)
        ],
        "sequence_frequency": dict(sequences),
    }


@router.post("/analyze/shoe", response_model=ShoeAnalysisResponse)
async def analyze_shoe(
    request: Request,
    payload: ShoeAnalysisRequest,
    db: Session = Depends(get_database_session),
) -> ShoeAnalysisResponse:
    """
    Perform comprehensive statistical analysis on a shoe.
    
    This endpoint runs 10+ statistical tests including:
    - Chi-square goodness of fit
    - Runs test
    - Entropy analysis
    - Autocorrelation
    - Binomial tests
    - Pattern significance
    - Bayesian inference
    - And more...
    
    Args:
        request: FastAPI request
        payload: Analysis request with optional shoe_id
        db: Database session
        
    Returns:
        Comprehensive statistical analysis results
    """
    # Get outcomes from shoe or database
    if payload.shoe_id:
        shoe = get_shoe(request, payload.shoe_id)
        outcomes = [h.result.value for h in shoe.hand_history]
        numeric_data = None
        if payload.include_numeric_data:
            # Extract numeric data (e.g., counts, scores)
            numeric_data = [i for i in range(len(outcomes))]  # Placeholder
    else:
        # Get from database
        results = db.query(GameResult).order_by(GameResult.timestamp.asc()).all()
        outcomes = [r.result for r in results]
        numeric_data = None
        if payload.include_numeric_data:
            numeric_data = [i for i in range(len(outcomes))]  # Placeholder
    
    if not outcomes:
        return ShoeAnalysisResponse(
            shoe_id=payload.shoe_id,
            total_samples=0,
            tests={},
            summary={"message": "No data available for analysis"}
        )
    
    # Perform comprehensive analysis
    analysis_results = comprehensive_statistical_analysis(
        outcomes,
        numeric_data=numeric_data
    )
    
    # Convert test results to StatisticalTestResult format
    formatted_tests = {}
    for test_name, test_result in analysis_results.get("tests", {}).items():
        formatted_tests[test_name] = StatisticalTestResult(
            test=test_result.get("test", test_name),
            statistic=test_result.get("statistic"),
            p_value=test_result.get("p_value"),
            significant=test_result.get("significant"),
            interpretation=test_result.get("interpretation", ""),
            additional_data={k: v for k, v in test_result.items() 
                           if k not in ["test", "statistic", "p_value", "significant", "interpretation"]}
        )
    
    # Create summary
    summary = {
        "total_tests": len(formatted_tests),
        "significant_tests": sum(1 for t in formatted_tests.values() if t.significant),
        "total_samples": analysis_results.get("total_samples", len(outcomes)),
        "banker_count": outcomes.count("B"),
        "player_count": outcomes.count("P"),
        "tie_count": outcomes.count("T"),
    }
    
    return ShoeAnalysisResponse(
        shoe_id=payload.shoe_id,
        total_samples=analysis_results.get("total_samples", len(outcomes)),
        tests=formatted_tests,
        summary=summary
    )


@router.get("/hypothesis/test", response_model=HypothesisTestResponse)
async def hypothesis_test(
    request: Request,
    test_type: str = Query(..., description="Type of test: chi_square, runs, binomial, autocorrelation"),
    shoe_id: Optional[str] = Query(None, description="Shoe ID (uses default if not provided)"),
    lag: int = Query(1, ge=1, le=20, description="Lag for autocorrelation test"),
    expected_prob: float = Query(0.5, ge=0.0, le=1.0, description="Expected probability for binomial test"),
    db: Session = Depends(get_database_session),
) -> HypothesisTestResponse:
    """
    Perform a specific hypothesis test.
    
    Available tests:
    - chi_square: Chi-square goodness of fit test
    - runs: Runs test for randomness
    - binomial: Binomial test for proportion
    - autocorrelation: Autocorrelation test
    
    Args:
        request: FastAPI request
        test_type: Type of test to perform
        shoe_id: Optional shoe ID
        lag: Lag for autocorrelation test
        expected_prob: Expected probability for binomial test
        db: Database session
        
    Returns:
        Hypothesis test results with p-value and interpretation
    """
    # Get data
    if shoe_id:
        shoe = get_shoe(request, shoe_id)
        outcomes = [h.result.value for h in shoe.hand_history]
    else:
        results = db.query(GameResult).order_by(GameResult.timestamp.asc()).all()
        outcomes = [r.result for r in results]
    
    if not outcomes:
        return HypothesisTestResponse(
            test_type=test_type,
            result=StatisticalTestResult(
                test=test_type,
                interpretation="No data available"
            )
        )
    
    # Remove ties for some tests
    no_ties = [o for o in outcomes if o != 'T']
    
    # Perform test based on type
    test_result = None
    
    if test_type == "chi_square":
        banker_count = outcomes.count('B')
        player_count = outcomes.count('P')
        tie_count = outcomes.count('T')
        total = len(outcomes)
        
        expected_b = 0.458597 * total
        expected_p = 0.446247 * total
        expected_t = 0.095156 * total
        
        test_result = chi_square_goodness_of_fit(
            [banker_count, player_count, tie_count],
            [expected_b, expected_p, expected_t]
        )
    
    elif test_type == "runs":
        if len(no_ties) < 2:
            test_result = {
                "test": "runs_test",
                "statistic": 0.0,
                "p_value": 1.0,
                "significant": False,
                "interpretation": "Insufficient data"
            }
        else:
            test_result = runs_test(no_ties)
    
    elif test_type == "binomial":
        if len(no_ties) == 0:
            test_result = {
                "test": "binomial_test",
                "p_value": 1.0,
                "significant": False,
                "interpretation": "No data"
            }
        else:
            banker_wins = no_ties.count('B')
            test_result = binomial_test(
                banker_wins,
                len(no_ties),
                expected_prob=expected_prob
            )
    
    elif test_type == "autocorrelation":
        if len(no_ties) < lag + 1:
            test_result = {
                "test": "autocorrelation",
                "lag": lag,
                "autocorrelation": 0.0,
                "significant": False,
                "interpretation": "Insufficient data"
            }
        else:
            numeric_outcomes = [1 if o == 'B' else 0 for o in no_ties]
            test_result = autocorrelation(numeric_outcomes, lag=lag)
    
    else:
        return HypothesisTestResponse(
            test_type=test_type,
            result=StatisticalTestResult(
                test=test_type,
                interpretation=f"Unknown test type: {test_type}"
            )
        )
    
    # Format result
    result = StatisticalTestResult(
        test=test_result.get("test", test_type),
        statistic=test_result.get("statistic") or test_result.get("autocorrelation"),
        p_value=test_result.get("p_value"),
        significant=test_result.get("significant"),
        interpretation=test_result.get("interpretation", ""),
        additional_data={k: v for k, v in test_result.items() 
                        if k not in ["test", "statistic", "p_value", "significant", "interpretation", "autocorrelation"]}
    )
    
    # Get confidence interval if available
    conf_interval = None
    if "confidence_interval_95" in test_result:
        conf_interval = tuple(test_result["confidence_interval_95"])
    elif "credible_interval_95" in test_result:
        conf_interval = tuple(test_result["credible_interval_95"])
    
    return HypothesisTestResponse(
        test_type=test_type,
        result=result,
        confidence_interval=conf_interval
    )


@router.get("/patterns/significance", response_model=PatternSignificanceResponse)
async def pattern_significance(
    request: Request,
    pattern_type: str = Query(..., description="Pattern type: streak, sequence, alternation"),
    shoe_id: Optional[str] = Query(None, description="Shoe ID (uses default if not provided)"),
    min_streak_length: int = Query(3, ge=2, le=10, description="Minimum streak length"),
    sequence_length: int = Query(3, ge=2, le=5, description="Sequence length for sequence patterns"),
    db: Session = Depends(get_database_session),
) -> PatternSignificanceResponse:
    """
    Test significance of patterns in shoe data.
    
    Args:
        request: FastAPI request
        pattern_type: Type of pattern to test
        shoe_id: Optional shoe ID
        min_streak_length: Minimum streak length for streak patterns
        sequence_length: Sequence length for sequence patterns
        db: Database session
        
    Returns:
        Pattern significance analysis with p-value
    """
    # Get data
    if shoe_id:
        shoe = get_shoe(request, shoe_id)
        outcomes = [h.result.value for h in shoe.hand_history]
    else:
        results = db.query(GameResult).order_by(GameResult.timestamp.asc()).all()
        outcomes = [r.result for r in results]
    
    if not outcomes:
        return PatternSignificanceResponse(
            pattern_type=pattern_type,
            pattern_count=0,
            total_hands=0,
            observed_frequency=0.0,
            p_value=1.0,
            significant=False,
            interpretation="No data available"
        )
    
    # Remove ties
    no_ties = [o for o in outcomes if o != 'T']
    total_hands = len(no_ties)
    
    if total_hands == 0:
        return PatternSignificanceResponse(
            pattern_type=pattern_type,
            pattern_count=0,
            total_hands=0,
            observed_frequency=0.0,
            p_value=1.0,
            significant=False,
            interpretation="No valid data (only ties)"
        )
    
    pattern_count = 0
    expected_frequency = None
    
    if pattern_type == "streak":
        # Count streaks of minimum length
        current_streak = 1
        for i in range(1, len(no_ties)):
            if no_ties[i] == no_ties[i-1]:
                current_streak += 1
            else:
                if current_streak >= min_streak_length:
                    pattern_count += 1
                current_streak = 1
        if current_streak >= min_streak_length:
            pattern_count += 1
        
        # Expected frequency (approximation)
        # Probability of streak of length n: p^n * (1-p) for each outcome
        p_banker = 0.458597
        p_player = 0.446247
        expected_freq_banker = p_banker ** min_streak_length * (1 - p_banker)
        expected_freq_player = p_player ** min_streak_length * (1 - p_player)
        expected_frequency = expected_freq_banker + expected_freq_player
    
    elif pattern_type == "sequence":
        # Count specific sequences
        target_sequence = "B" * sequence_length  # Example: BBB
        for i in range(len(no_ties) - sequence_length + 1):
            if "".join(no_ties[i:i+sequence_length]) == target_sequence:
                pattern_count += 1
        
        # Expected frequency
        p_banker = 0.458597
        expected_frequency = p_banker ** sequence_length
    
    elif pattern_type == "alternation":
        # Count alternating patterns (BPBP or PBPB)
        alternations = 0
        for i in range(1, len(no_ties)):
            if no_ties[i] != no_ties[i-1]:
                alternations += 1
        pattern_count = alternations
        
        # Expected frequency (approximately 50% alternation)
        expected_frequency = 0.5
    
    else:
        return PatternSignificanceResponse(
            pattern_type=pattern_type,
            pattern_count=0,
            total_hands=total_hands,
            observed_frequency=0.0,
            p_value=1.0,
            significant=False,
            interpretation=f"Unknown pattern type: {pattern_type}"
        )
    
    if expected_frequency is None:
        expected_frequency = 0.1  # Default
    
    # Perform significance test
    test_result = pattern_significance_test(
        pattern_count,
        total_hands,
        expected_frequency
    )
    
    observed_frequency = pattern_count / total_hands if total_hands > 0 else 0.0
    
    return PatternSignificanceResponse(
        pattern_type=pattern_type,
        pattern_count=pattern_count,
        total_hands=total_hands,
        observed_frequency=round(observed_frequency, 6),
        expected_frequency=expected_frequency,
        p_value=test_result.get("p_value", 1.0),
        significant=test_result.get("significant", False),
        interpretation=test_result.get("interpretation", ""),
        confidence_interval=test_result.get("confidence_interval_95")
    )

