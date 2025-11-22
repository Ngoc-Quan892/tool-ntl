"""
Shoe Management API endpoints.

Endpoints for creating, managing, and resetting shoes.
"""
from __future__ import annotations

import uuid
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.v2.base import NotFoundError, get_database_session, SuccessResponse
from app.core.engine import EnhancedShoe
from app.models.schemas import (
    CreateShoeRequest,
    ResetShoeResponse,
    ShoeStateResponse,
)

router = APIRouter(prefix="/shoes", tags=["shoes"])

# In-memory storage for shoes (in production, use database)
_shoes: Dict[str, EnhancedShoe] = {}


def get_shoe_manager(request: Request) -> Dict[str, EnhancedShoe]:
    """Get shoe manager from app state."""
    if not hasattr(request.app.state, "shoes"):
        request.app.state.shoes = {}
    return request.app.state.shoes


@router.post("/create", response_model=Dict)
async def create_shoe(
    request: Request,
    payload: CreateShoeRequest,
) -> Dict:
    """
    Create a new shoe.
    
    Args:
        payload: Shoe creation parameters
        
    Returns:
        Created shoe information
    """
    shoes = get_shoe_manager(request)
    
    shoe_id = str(uuid.uuid4())
    reshuffle_point = payload.reshuffle_point or 20
    
    shoe = EnhancedShoe(decks=payload.decks, reshuffle_point=reshuffle_point)
    # Override shoe_id to use our generated one
    shoe.shoe_id = shoe_id
    shoes[shoe_id] = shoe
    
    return SuccessResponse.create(
        {
            "shoe_id": shoe_id,
            "decks": payload.decks,
            "reshuffle_point": reshuffle_point,
            "message": "Shoe created successfully",
        },
        message="Shoe created",
    )


@router.get("/{shoe_id}", response_model=ShoeStateResponse)
async def get_shoe_state(
    request: Request,
    shoe_id: str,
) -> ShoeStateResponse:
    """
    Get current state of a shoe.
    
    Args:
        shoe_id: Shoe identifier
        
    Returns:
        Shoe state information
    """
    shoes = get_shoe_manager(request)
    
    if shoe_id not in shoes:
        raise NotFoundError("Shoe", shoe_id)
    
    shoe = shoes[shoe_id]
    state = shoe.get_state()
    
    return ShoeStateResponse(**state)


@router.post("/{shoe_id}/reset", response_model=ResetShoeResponse)
async def reset_shoe(
    request: Request,
    shoe_id: str,
) -> ResetShoeResponse:
    """
    Reset a shoe (reshuffle and clear history).
    
    Args:
        shoe_id: Shoe identifier
        
    Returns:
        Reset confirmation
    """
    shoes = get_shoe_manager(request)
    
    if shoe_id not in shoes:
        raise NotFoundError("Shoe", shoe_id)
    
    shoe = shoes[shoe_id]
    shoe.reset()
    
    return ResetShoeResponse(
        success=True,
        shoe_id=shoe_id,
        message="Shoe reset successfully",
    )


@router.delete("/{shoe_id}", response_model=Dict)
async def delete_shoe(
    request: Request,
    shoe_id: str,
) -> Dict:
    """
    Delete a shoe.
    
    Args:
        shoe_id: Shoe identifier
        
    Returns:
        Deletion confirmation
    """
    shoes = get_shoe_manager(request)
    
    if shoe_id not in shoes:
        raise NotFoundError("Shoe", shoe_id)
    
    del shoes[shoe_id]
    
    return SuccessResponse.create(
        {"shoe_id": shoe_id},
        message="Shoe deleted successfully",
    )

