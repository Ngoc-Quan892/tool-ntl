"""
Hand Playing API endpoints.

Endpoints for playing hands and retrieving hand history.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v2.base import NotFoundError, PaginatedResponse, get_database_session
from app.core.engine import EnhancedShoe, Outcome
from app.models.database import GameResult
from app.models.schemas import (
    HandHistoryResponse,
    HandResponse,
    PlayHandRequest,
)

router = APIRouter(prefix="/hands", tags=["hands"])


def get_default_shoe(request: Request) -> EnhancedShoe:
    """Get or create default shoe from app state."""
    if not hasattr(request.app.state, "default_shoe"):
        request.app.state.default_shoe = EnhancedShoe(decks=8)
    return request.app.state.default_shoe


def get_shoe(request: Request, shoe_id: Optional[str] = None) -> EnhancedShoe:
    """Get shoe by ID or return default."""
    if shoe_id:
        shoes = getattr(request.app.state, "shoes", {})
        if shoe_id not in shoes:
            raise NotFoundError("Shoe", shoe_id)
        return shoes[shoe_id]
    return get_default_shoe(request)


@router.post("/play", response_model=HandResponse)
async def play_hand(
    request: Request,
    payload: PlayHandRequest,
    db: Session = Depends(get_database_session),
) -> HandResponse:
    """
    Play a single hand.
    
    If result is provided, records it. Otherwise, auto-plays the hand.
    
    Args:
        payload: Play hand request
        db: Database session
        
    Returns:
        Hand information
    """
    shoe = get_shoe(request, payload.shoe_id)
    
    if payload.result:
        # Manual result - create a simple hand record
        # In a real implementation, you'd track this properly
        hand = shoe.play_hand()  # Still play to get card info
        # Override result if provided
        if payload.result != hand.result.value:
            # Create a modified hand (simplified)
            hand.result = Outcome(payload.result)
    else:
        # Auto-play
        hand = shoe.play_hand()
    
    # Save to database
    db_obj = GameResult(
        result=hand.result.value,
        prediction=None,  # Would calculate prediction here
        shoe_number=1,  # Would track shoe number
        hand_number=hand.hand_number,
        true_count=0.0,  # Would get from shoe
        edge=0.0,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    
    # Convert to response
    return HandResponse(
        hand_id=hand.hand_id,
        shoe_id=hand.shoe_id,
        hand_number=hand.hand_number,
        result=hand.result.value,
        banker_total=hand.banker_total,
        player_total=hand.player_total,
        is_natural=hand.is_natural,
        banker_cards=[{"rank": c.rank, "suit": c.suit.value} for c in hand.banker_cards],
        player_cards=[{"rank": c.rank, "suit": c.suit.value} for c in hand.player_cards],
        timestamp=hand.timestamp,
    )


@router.get("/history", response_model=HandHistoryResponse)
async def get_hand_history(
    db: Session = Depends(get_database_session),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    shoe_id: Optional[str] = Query(None, description="Filter by shoe ID"),
) -> HandHistoryResponse:
    """
    Get hand history with pagination.
    
    Args:
        db: Database session
        page: Page number
        page_size: Items per page
        shoe_id: Optional shoe filter
        
    Returns:
        Paginated hand history
    """
    query = db.query(GameResult)
    
    # Filter by shoe if provided (would need shoe_id column in GameResult)
    # For now, just get all results
    
    total = query.count()
    offset = (page - 1) * page_size
    
    results = (
        query.order_by(GameResult.timestamp.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    
    items = [
        HandResponse(
            hand_id=f"hand_{r.id}",
            shoe_id=f"shoe_{r.shoe_number}",
            hand_number=r.hand_number or 0,
            result=r.result,
            banker_total=0,  # Would need to store this
            player_total=0,
            is_natural=False,
            banker_cards=[],
            player_cards=[],
            timestamp=r.timestamp,
        )
        for r in results
    ]
    
    return HandHistoryResponse(
        total=total,
        items=items,
        page=page,
        page_size=page_size,
    )


@router.get("/{hand_id}", response_model=HandResponse)
async def get_hand(
    hand_id: str,
    db: Session = Depends(get_database_session),
) -> HandResponse:
    """
    Get a specific hand by ID.
    
    Args:
        hand_id: Hand identifier (database ID)
        db: Database session
        
    Returns:
        Hand information
    """
    # Extract numeric ID from hand_id (format: "hand_123")
    try:
        db_id = int(hand_id.replace("hand_", ""))
    except ValueError:
        raise NotFoundError("Hand", hand_id)
    
    result = db.query(GameResult).filter(GameResult.id == db_id).first()
    
    if not result:
        raise NotFoundError("Hand", hand_id)
    
    return HandResponse(
        hand_id=f"hand_{result.id}",
        shoe_id=f"shoe_{result.shoe_number}",
        hand_number=result.hand_number or 0,
        result=result.result,
        banker_total=0,
        player_total=0,
        is_natural=False,
        banker_cards=[],
        player_cards=[],
        timestamp=result.timestamp,
    )

