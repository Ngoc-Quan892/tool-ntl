"""
Pydantic schemas for API validation, request/response payloads, and WebSocket messages.

This module contains all Pydantic models used for:
- API request/response validation
- WebSocket message schemas
- Data serialization
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, validator

ResultLiteral = Literal["B", "P", "T"]
StatusLiteral = Literal["pending", "running", "completed", "failed", "cancelled"]


class AddResultRequest(BaseModel):
    result: ResultLiteral


class PredictionResponse(BaseModel):
    recommend: Literal["B", "P"]
    confidence: float
    edge_pct: float
    pattern: str
    true_count: float
    next_suggested: Literal["B", "P"]
    timestamp: datetime


class AddResultResponse(BaseModel):
    success: bool
    total_hands: int
    prediction: PredictionResponse


class HistoryEntry(BaseModel):
    id: int
    result: ResultLiteral
    prediction: dict
    shoe_number: int
    hand_number: int
    timestamp: datetime


class HistoryResponse(BaseModel):
    total: int
    items: List[HistoryEntry]


class StatsResponse(BaseModel):
    total_hands: int
    banker_wins: int
    player_wins: int
    ties: int
    banker_streak: int
    player_streak: int
    current_shoe: int
    accuracy: float


class RoadmapResponse(BaseModel):
    big_road: List[List[Optional[dict]]]
    big_eye_boy: List[List[Optional[dict]]]
    small_road: List[List[Optional[dict]]]
    cockroach_pig: List[List[Optional[dict]]]


class SimulationRequest(BaseModel):
    shoes: int = Field(ge=1, le=10_000)
    hands_per_shoe: int = Field(ge=1, le=100)


class SimulationStatus(BaseModel):
    task_id: str
    status: str
    total_shoes: int
    completed_shoes: int
    results: Optional[dict]


class ResetResponse(BaseModel):
    success: bool


class ExportFormat(BaseModel):
    format: Literal["csv", "json"] = "json"


# WebSocket Message Schemas
class WebSocketMessage(BaseModel):
    """Base WebSocket message schema."""
    type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Optional[Dict[str, Any]] = None


class PredictionUpdateMessage(WebSocketMessage):
    """WebSocket message for prediction updates."""
    type: Literal["prediction_update"] = "prediction_update"
    data: PredictionResponse


class ResultAddedMessage(WebSocketMessage):
    """WebSocket message when a new result is added."""
    type: Literal["result_added"] = "result_added"
    data: AddResultResponse


class SimulationUpdateMessage(WebSocketMessage):
    """WebSocket message for simulation progress updates."""
    type: Literal["simulation_update"] = "simulation_update"
    data: SimulationStatus


class ErrorMessage(WebSocketMessage):
    """WebSocket error message."""
    type: Literal["error"] = "error"
    data: Dict[str, Any] = Field(..., description="Error details with 'message' and optional 'code'")


class HeartbeatMessage(WebSocketMessage):
    """WebSocket heartbeat message."""
    type: Literal["heartbeat"] = "heartbeat"
    data: Optional[Dict[str, Any]] = None


# Request/Response Schemas with enhanced validation
class AddResultRequest(BaseModel):
    """Request schema for adding a game result."""
    result: ResultLiteral = Field(..., description="Game result: B (Banker), P (Player), or T (Tie)")
    shoe_number: Optional[int] = Field(None, ge=1, description="Optional shoe number")
    hand_number: Optional[int] = Field(None, ge=1, description="Optional hand number within shoe")

    @validator("result")
    def validate_result(cls, v):
        """Validate result is one of the allowed values."""
        if v not in ["B", "P", "T"]:
            raise ValueError("Result must be 'B', 'P', or 'T'")
        return v


class PredictionResponse(BaseModel):
    """Response schema for prediction data."""
    recommend: Literal["B", "P"] = Field(..., description="Recommended bet: B (Banker) or P (Player)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level between 0 and 1")
    edge_pct: float = Field(..., description="Calculated edge percentage")
    pattern: str = Field(..., description="Detected pattern description")
    true_count: float = Field(..., description="True count from card counting")
    next_suggested: Literal["B", "P"] = Field(..., description="Next suggested bet")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Prediction timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "recommend": "B",
                "confidence": 0.75,
                "edge_pct": 2.5,
                "pattern": "Banker streak",
                "true_count": 1.2,
                "next_suggested": "B",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class AddResultResponse(BaseModel):
    """Response schema after adding a result."""
    success: bool = Field(..., description="Whether the operation was successful")
    total_hands: int = Field(..., ge=0, description="Total number of hands after adding")
    prediction: PredictionResponse = Field(..., description="Updated prediction after adding result")
    message: Optional[str] = Field(None, description="Optional success message")


class HistoryEntry(BaseModel):
    """Schema for a single history entry."""
    id: int = Field(..., description="Entry ID")
    result: ResultLiteral = Field(..., description="Game result")
    prediction: Optional[Dict[str, Any]] = Field(None, description="Prediction data at time of result")
    shoe_number: int = Field(..., ge=1, description="Shoe number")
    hand_number: Optional[int] = Field(None, ge=1, description="Hand number within shoe")
    timestamp: datetime = Field(..., description="When the result was recorded")
    true_count: Optional[float] = Field(None, description="True count at time of result")
    edge: Optional[float] = Field(None, description="Calculated edge at time of result")


class HistoryResponse(BaseModel):
    """Response schema for history queries."""
    total: int = Field(..., ge=0, description="Total number of entries")
    items: List[HistoryEntry] = Field(..., description="List of history entries")
    page: Optional[int] = Field(None, ge=1, description="Current page number (if paginated)")
    page_size: Optional[int] = Field(None, ge=1, description="Number of items per page (if paginated)")


class StatsResponse(BaseModel):
    """Response schema for session statistics."""
    total_hands: int = Field(..., ge=0, description="Total number of hands")
    banker_wins: int = Field(..., ge=0, description="Number of banker wins")
    player_wins: int = Field(..., ge=0, description="Number of player wins")
    ties: int = Field(..., ge=0, description="Number of ties")
    banker_streak: int = Field(..., description="Current banker streak (can be negative)")
    player_streak: int = Field(..., description="Current player streak (can be negative)")
    current_shoe: int = Field(..., ge=1, description="Current shoe number")
    accuracy: float = Field(..., ge=0.0, le=1.0, description="Prediction accuracy (0-1)")
    banker_percentage: float = Field(..., ge=0.0, le=100.0, description="Banker win percentage")
    player_percentage: float = Field(..., ge=0.0, le=100.0, description="Player win percentage")
    tie_percentage: float = Field(..., ge=0.0, le=100.0, description="Tie percentage")


class RoadmapResponse(BaseModel):
    """Response schema for roadmap data."""
    big_road: List[List[Optional[Dict[str, Any]]]] = Field(..., description="Big Road grid")
    big_eye_boy: List[List[Optional[Dict[str, Any]]]] = Field(..., description="Big Eye Boy grid")
    small_road: List[List[Optional[Dict[str, Any]]]] = Field(..., description="Small Road grid")
    cockroach_pig: List[List[Optional[Dict[str, Any]]]] = Field(..., description="Cockroach Pig grid")


class SimulationRequest(BaseModel):
    """Request schema for simulation runs."""
    shoes: int = Field(..., ge=1, le=10_000, description="Number of shoes to simulate")
    hands_per_shoe: int = Field(..., ge=1, le=100, description="Number of hands per shoe")
    strategy: Optional[str] = Field(None, description="Optional strategy name to test")


class SimulationStatus(BaseModel):
    """Response schema for simulation status."""
    task_id: str = Field(..., description="Unique task identifier")
    status: StatusLiteral = Field(..., description="Current simulation status")
    total_shoes: int = Field(..., ge=0, description="Total number of shoes")
    completed_shoes: int = Field(..., ge=0, description="Number of completed shoes")
    results: Optional[Dict[str, Any]] = Field(None, description="Simulation results summary")
    started_at: Optional[datetime] = Field(None, description="When simulation started")
    completed_at: Optional[datetime] = Field(None, description="When simulation completed")
    progress_pct: float = Field(..., ge=0.0, le=100.0, description="Progress percentage")

    @validator("progress_pct", always=True)
    def calculate_progress(cls, v, values):
        """Calculate progress percentage from completed/total shoes."""
        if "total_shoes" in values and "completed_shoes" in values:
            total = values.get("total_shoes", 0)
            completed = values.get("completed_shoes", 0)
            if total > 0:
                return round((completed / total) * 100, 2)
        return v if v is not None else 0.0


class ResetResponse(BaseModel):
    """Response schema for reset operations."""
    success: bool = Field(..., description="Whether reset was successful")
    message: Optional[str] = Field(None, description="Optional message about reset operation")


class ExportFormat(BaseModel):
    """Request schema for data export."""
    format: Literal["csv", "json"] = Field("json", description="Export format")
    include_predictions: bool = Field(True, description="Include prediction data in export")
    date_from: Optional[datetime] = Field(None, description="Start date for export")
    date_to: Optional[datetime] = Field(None, description="End date for export")


# ==================== V2 API SCHEMAS ====================

# Shoe Management Schemas
class CreateShoeRequest(BaseModel):
    """Request to create a new shoe."""
    decks: int = Field(8, ge=1, le=16, description="Number of decks in shoe")
    reshuffle_point: Optional[int] = Field(None, ge=10, le=50, description="Cards remaining before reshuffle")


class ShoeStateResponse(BaseModel):
    """Response with shoe state information."""
    shoe_id: str = Field(..., description="Unique shoe identifier")
    decks: int = Field(..., description="Number of decks")
    cards_remaining: int = Field(..., description="Cards remaining in shoe")
    cards_dealt: int = Field(..., description="Total cards dealt")
    decks_remaining: float = Field(..., description="Decks remaining")
    hands_played: int = Field(..., description="Number of hands played")
    reshuffled_count: int = Field(..., description="Number of times reshuffled")
    running_count_b: float = Field(..., description="Running count for banker")
    running_count_p: float = Field(..., description="Running count for player")
    true_count_b: float = Field(..., description="True count for banker")
    true_count_p: float = Field(..., description="True count for player")
    edge: Dict[str, Any] = Field(..., description="Edge calculations")
    composition: Dict[str, Dict[str, Any]] = Field(..., description="Card composition by rank")
    high_card_count: int = Field(..., description="High card count")
    low_card_count: int = Field(..., description="Low card count")
    high_low_ratio: float = Field(..., description="High/low card ratio")
    created_at: str = Field(..., description="Shoe creation timestamp")
    needs_reshuffle: bool = Field(..., description="Whether shoe needs reshuffling")


class ResetShoeResponse(BaseModel):
    """Response after resetting a shoe."""
    success: bool = Field(..., description="Whether reset was successful")
    shoe_id: str = Field(..., description="Shoe identifier")
    message: str = Field(..., description="Status message")


# Hand Playing Schemas
class PlayHandRequest(BaseModel):
    """Request to play a hand."""
    shoe_id: Optional[str] = Field(None, description="Shoe ID (optional, uses default if not provided)")
    result: Optional[ResultLiteral] = Field(None, description="Manual result (optional, auto-plays if not provided)")


class HandResponse(BaseModel):
    """Response with hand information."""
    hand_id: str = Field(..., description="Unique hand identifier")
    shoe_id: str = Field(..., description="Shoe identifier")
    hand_number: int = Field(..., description="Hand number in shoe")
    result: ResultLiteral = Field(..., description="Hand result")
    banker_total: int = Field(..., description="Banker total")
    player_total: int = Field(..., description="Player total")
    is_natural: bool = Field(..., description="Whether hand was natural")
    banker_cards: List[Dict[str, str]] = Field(..., description="Banker cards")
    player_cards: List[Dict[str, str]] = Field(..., description="Player cards")
    timestamp: datetime = Field(..., description="Hand timestamp")


class HandHistoryResponse(BaseModel):
    """Response with hand history."""
    total: int = Field(..., description="Total number of hands")
    items: List[HandResponse] = Field(..., description="List of hands")
    page: Optional[int] = Field(None, description="Current page")
    page_size: Optional[int] = Field(None, description="Page size")


# Prediction Schemas
class PredictRequest(BaseModel):
    """Request for prediction."""
    shoe_id: Optional[str] = Field(None, description="Shoe ID (optional)")


class AccuracyMetricsResponse(BaseModel):
    """Response with accuracy metrics."""
    total_predictions: int = Field(..., description="Total predictions made")
    correct_predictions: int = Field(..., description="Correct predictions")
    accuracy: float = Field(..., ge=0.0, le=100.0, description="Accuracy percentage")
    banker_accuracy: float = Field(..., ge=0.0, le=100.0, description="Banker prediction accuracy")
    player_accuracy: float = Field(..., ge=0.0, le=100.0, description="Player prediction accuracy")
    recent_accuracy: float = Field(..., ge=0.0, le=100.0, description="Recent accuracy (last 50 hands)")
    confidence_distribution: Dict[str, int] = Field(..., description="Distribution of confidence levels")


class ConfidenceScoresResponse(BaseModel):
    """Response with confidence scores."""
    current_confidence: float = Field(..., ge=0.0, le=1.0, description="Current prediction confidence")
    average_confidence: float = Field(..., ge=0.0, le=1.0, description="Average confidence")
    confidence_history: List[float] = Field(..., description="Confidence history")
    confidence_by_outcome: Dict[str, float] = Field(..., description="Average confidence by outcome")


# Analysis Schemas
class StatisticsResponse(BaseModel):
    """Response with shoe statistics."""
    total_hands: int = Field(..., description="Total hands played")
    banker_wins: int = Field(..., description="Banker wins")
    player_wins: int = Field(..., description="Player wins")
    ties: int = Field(..., description="Ties")
    banker_pct: float = Field(..., description="Banker win percentage")
    player_pct: float = Field(..., description="Player win percentage")
    tie_pct: float = Field(..., description="Tie percentage")
    max_banker_streak: int = Field(..., description="Maximum banker streak")
    max_player_streak: int = Field(..., description="Maximum player streak")
    natural_count: int = Field(..., description="Number of naturals")
    natural_pct: float = Field(..., description="Natural percentage")
    banker_deviation: float = Field(..., description="Deviation from theoretical banker probability")
    player_deviation: float = Field(..., description="Deviation from theoretical player probability")


class PatternAnalysisResponse(BaseModel):
    """Response with pattern analysis."""
    detected_patterns: List[Dict[str, Any]] = Field(..., description="Detected patterns")
    pattern_frequency: Dict[str, int] = Field(..., description="Pattern frequency")
    streak_analysis: Dict[str, Any] = Field(..., description="Streak analysis")
    sequence_analysis: Dict[str, Any] = Field(..., description="Sequence analysis")


class EdgeCalculationResponse(BaseModel):
    """Response with edge calculations."""
    edge_banker_raw: float = Field(..., description="Raw banker edge")
    edge_banker_after_commission: float = Field(..., description="Banker edge after commission")
    edge_player: float = Field(..., description="Player edge")
    max_edge: float = Field(..., description="Maximum edge")
    has_positive_edge: bool = Field(..., description="Whether positive edge exists")
    recommendation: str = Field(..., description="Betting recommendation")
    reason: str = Field(..., description="Reason for recommendation")
    true_count_b: float = Field(..., description="True count for banker")
    true_count_p: float = Field(..., description="True count for player")


# Statistical Analysis Schemas
class StatisticalTestResult(BaseModel):
    """Result of a single statistical test."""
    test: str = Field(..., description="Test name")
    statistic: Optional[float] = Field(None, description="Test statistic")
    p_value: Optional[float] = Field(None, description="P-value")
    significant: Optional[bool] = Field(None, description="Whether result is significant")
    interpretation: str = Field(..., description="Interpretation of results")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="Additional test-specific data")


class ShoeAnalysisRequest(BaseModel):
    """Request for comprehensive shoe analysis."""
    shoe_id: Optional[str] = Field(None, description="Shoe ID (uses default if not provided)")
    include_numeric_data: bool = Field(False, description="Include numeric data analysis")


class ShoeAnalysisResponse(BaseModel):
    """Response with comprehensive statistical analysis of a shoe."""
    shoe_id: Optional[str] = Field(None, description="Shoe identifier")
    total_samples: int = Field(..., description="Total number of samples analyzed")
    tests: Dict[str, StatisticalTestResult] = Field(..., description="Results of statistical tests")
    summary: Dict[str, Any] = Field(..., description="Summary statistics")


class HypothesisTestRequest(BaseModel):
    """Request for hypothesis testing."""
    test_type: str = Field(..., description="Type of test (chi_square, runs, binomial, etc.)")
    data: List[str] = Field(..., description="Data to test")
    expected_values: Optional[List[float]] = Field(None, description="Expected values for goodness of fit")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional test parameters")


class HypothesisTestResponse(BaseModel):
    """Response with hypothesis test results."""
    test_type: str = Field(..., description="Type of test performed")
    result: StatisticalTestResult = Field(..., description="Test result")
    confidence_interval: Optional[Tuple[float, float]] = Field(None, description="95% confidence interval if applicable")


class PatternSignificanceRequest(BaseModel):
    """Request for pattern significance testing."""
    pattern_type: str = Field(..., description="Type of pattern (streak, sequence, etc.)")
    pattern_data: List[str] = Field(..., description="Pattern data")
    expected_frequency: Optional[float] = Field(None, description="Expected frequency of pattern")


class PatternSignificanceResponse(BaseModel):
    """Response with pattern significance analysis."""
    pattern_type: str = Field(..., description="Type of pattern analyzed")
    pattern_count: int = Field(..., description="Number of pattern occurrences")
    total_hands: int = Field(..., description="Total number of hands")
    observed_frequency: float = Field(..., description="Observed frequency")
    expected_frequency: Optional[float] = Field(None, description="Expected frequency")
    p_value: float = Field(..., description="P-value")
    significant: bool = Field(..., description="Whether pattern is statistically significant")
    interpretation: str = Field(..., description="Interpretation of results")
    confidence_interval: Optional[Tuple[float, float]] = Field(None, description="95% confidence interval")
