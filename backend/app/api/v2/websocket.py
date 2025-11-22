"""
WebSocket endpoints for v2 API.

Endpoints:
- /ws/shoe/{shoe_id} - Live shoe updates
- /ws/predictions - Real-time predictions
- /ws/stats - Live statistics
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from app.api.websocket_manager import ws_manager
from app.core.engine import EnhancedShoe
from app.core.predictor import Predictor

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


def get_shoe(request: Request, shoe_id: Optional[str] = None) -> Optional[EnhancedShoe]:
    """Get shoe by ID or return default."""
    if shoe_id:
        shoes = getattr(request.app.state, "shoes", {})
        return shoes.get(shoe_id)
    
    return getattr(request.app.state, "default_shoe", None)


def get_predictor(request: Request) -> Predictor:
    """Get predictor from app state."""
    if not hasattr(request.app.state, "predictor"):
        request.app.state.predictor = Predictor()
    return request.app.state.predictor


@router.websocket("/ws/shoe/{shoe_id}")
async def websocket_shoe_updates(
    websocket: WebSocket,
    shoe_id: str,
    request: Request,
):
    """
    WebSocket endpoint for live shoe updates.
    
    Sends updates when:
    - Shoe state changes
    - New hand is played
    - Shoe is reset
    """
    connection = await ws_manager.connect(websocket, room=f"shoe_{shoe_id}")
    
    try:
        # Send initial shoe state
        shoe = get_shoe(request, shoe_id)
        if shoe:
            state = shoe.get_state()
            await ws_manager.send_to_connection(
                connection.connection_id,
                {
                    "type": "shoe_state",
                    "shoe_id": shoe_id,
                    "data": state,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        else:
            await ws_manager.send_to_connection(
                connection.connection_id,
                {
                    "type": "error",
                    "message": f"Shoe {shoe_id} not found",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages (heartbeat, commands, etc.)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                try:
                    message = json.loads(data)
                    message_type = message.get("type")
                    
                    if message_type == "ping":
                        # Respond to ping
                        await ws_manager.send_to_connection(
                            connection.connection_id,
                            {
                                "type": "pong",
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        )
                    elif message_type == "subscribe":
                        # Subscribe to specific events
                        events = message.get("events", [])
                        # Could implement event filtering here
                        await ws_manager.send_to_connection(
                            connection.connection_id,
                            {
                                "type": "subscribed",
                                "events": events,
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        )
                        
                except json.JSONDecodeError:
                    # Invalid JSON, ignore
                    pass
                    
            except asyncio.TimeoutError:
                # Timeout is fine, just continue
                pass
                
    except WebSocketDisconnect:
        ws_manager.disconnect(connection.connection_id)
        logger.info(f"WebSocket disconnected: shoe_{shoe_id}")


@router.websocket("/ws/predictions")
async def websocket_predictions(
    websocket: WebSocket,
    request: Request,
):
    """
    WebSocket endpoint for real-time predictions.
    
    Sends prediction updates when:
    - New prediction is generated
    - Prediction confidence changes significantly
    """
    connection = await ws_manager.connect(websocket, room="predictions")
    
    try:
        # Send initial prediction
        predictor = get_predictor(request)
        prediction = predictor.predict()
        prediction["timestamp"] = datetime.utcnow()
        
        await ws_manager.send_to_connection(
            connection.connection_id,
            {
                "type": "prediction_update",
                "data": prediction,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        
        # Track last prediction for change detection
        last_prediction = prediction
        
        # Keep connection alive and send updates
        while True:
            try:
                # Check for prediction changes periodically
                await asyncio.sleep(2)  # Check every 2 seconds
                
                current_prediction = predictor.predict()
                current_prediction["timestamp"] = datetime.utcnow()
                
                # Send update if prediction changed significantly
                if (
                    current_prediction["recommend"] != last_prediction["recommend"]
                    or abs(current_prediction["confidence"] - last_prediction["confidence"]) > 0.05
                ):
                    await ws_manager.send_to_connection(
                        connection.connection_id,
                        {
                            "type": "prediction_update",
                            "data": current_prediction,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    last_prediction = current_prediction
                
                # Handle incoming messages
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                    message = json.loads(data)
                    
                    if message.get("type") == "ping":
                        await ws_manager.send_to_connection(
                            connection.connection_id,
                            {
                                "type": "pong",
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        )
                except (asyncio.TimeoutError, json.JSONDecodeError):
                    # No message or invalid JSON, continue
                    pass
                    
            except asyncio.CancelledError:
                break
                
    except WebSocketDisconnect:
        ws_manager.disconnect(connection.connection_id)
        logger.info("WebSocket disconnected: predictions")


@router.websocket("/ws/stats")
async def websocket_stats(
    websocket: WebSocket,
    request: Request,
):
    """
    WebSocket endpoint for live statistics.
    
    Sends statistics updates when:
    - Statistics change
    - New hand is played
    - Session is reset
    """
    connection = await ws_manager.connect(websocket, room="stats")
    
    try:
        # Send initial stats
        app_state = getattr(request.app.state, "app_state", None)
        if app_state:
            from app.utils.helpers import compute_stats
            
            stats = compute_stats(app_state)
            await ws_manager.send_to_connection(
                connection.connection_id,
                {
                    "type": "stats_update",
                    "data": stats,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        
        # Track last stats for change detection
        last_total_hands = 0
        if app_state:
            from app.utils.helpers import compute_stats
            stats = compute_stats(app_state)
            last_total_hands = stats.get("total_hands", 0)
        
        # Keep connection alive and send updates
        while True:
            try:
                # Check for stats changes periodically
                await asyncio.sleep(3)  # Check every 3 seconds
                
                if app_state:
                    current_stats = compute_stats(app_state)
                    
                    # Send update if stats changed
                    if current_stats.get("total_hands", 0) != last_total_hands:
                        await ws_manager.send_to_connection(
                            connection.connection_id,
                            {
                                "type": "stats_update",
                                "data": current_stats,
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        )
                        last_total_hands = current_stats.get("total_hands", 0)
                
                # Handle incoming messages
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                    message = json.loads(data)
                    
                    if message.get("type") == "ping":
                        await ws_manager.send_to_connection(
                            connection.connection_id,
                            {
                                "type": "pong",
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        )
                except (asyncio.TimeoutError, json.JSONDecodeError):
                    # No message or invalid JSON, continue
                    pass
                    
            except asyncio.CancelledError:
                break
                
    except WebSocketDisconnect:
        ws_manager.disconnect(connection.connection_id)
        logger.info("WebSocket disconnected: stats")

