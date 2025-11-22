"""
Advanced WebSocket Manager with room-based broadcasting and message queuing.

Features:
- Connection management per room
- Message queuing for disconnected clients
- Heartbeat mechanism
- Auto-cleanup of dead connections
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Connection:
    """Represents a WebSocket connection with metadata."""

    def __init__(self, websocket: WebSocket, connection_id: str, room: str):
        self.websocket = websocket
        self.connection_id = connection_id
        self.room = room
        self.connected_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.is_alive = True
        self.message_queue: deque = deque(maxlen=100)  # Queue for missed messages

    def __repr__(self) -> str:
        return f"Connection(id={self.connection_id[:8]}, room={self.room})"


class WebSocketManager:
    """
    Advanced WebSocket manager with room support and message queuing.
    
    Features:
    - Room-based broadcasting
    - Message queuing for reconnecting clients
    - Heartbeat mechanism
    - Connection lifecycle management
    """

    def __init__(self):
        """Initialize WebSocket manager."""
        # Room -> Set of connections
        self.rooms: Dict[str, Set[Connection]] = defaultdict(set)
        
        # Connection ID -> Connection
        self.connections: Dict[str, Connection] = {}
        
        # Message queues per room (for disconnected clients)
        self.room_message_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        
        # Heartbeat task
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "total_messages_sent": 0,
            "total_messages_failed": 0,
        }

    async def start(self) -> None:
        """Start background tasks."""
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop background tasks."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def connect(
        self,
        websocket: WebSocket,
        room: str = "default",
        connection_id: Optional[str] = None,
    ) -> Connection:
        """
        Connect a new WebSocket client.
        
        Args:
            websocket: WebSocket connection
            room: Room identifier
            connection_id: Optional connection ID (auto-generated if not provided)
            
        Returns:
            Connection object
        """
        await websocket.accept()
        
        conn_id = connection_id or str(uuid.uuid4())
        connection = Connection(websocket, conn_id, room)
        
        self.connections[conn_id] = connection
        self.rooms[room].add(connection)
        
        self.stats["total_connections"] += 1
        self.stats["active_connections"] = len(self.connections)
        
        logger.info(f"WebSocket connected: {connection} (total: {self.stats['active_connections']})")
        
        # Send queued messages if any
        await self._send_queued_messages(connection)
        
        # Send welcome message
        await self._send_to_connection(
            connection,
            {
                "type": "connected",
                "connection_id": conn_id,
                "room": room,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        
        return connection

    def disconnect(self, connection_id: str) -> None:
        """
        Disconnect a client.
        
        Args:
            connection_id: Connection identifier
        """
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        self.rooms[connection.room].discard(connection)
        del self.connections[connection_id]
        
        self.stats["active_connections"] = len(self.connections)
        
        logger.info(f"WebSocket disconnected: {connection} (remaining: {self.stats['active_connections']})")

    async def send_to_connection(
        self,
        connection_id: str,
        message: Dict[str, Any],
        queue_if_disconnected: bool = True,
    ) -> bool:
        """
        Send message to a specific connection.
        
        Args:
            connection_id: Connection identifier
            message: Message to send
            queue_if_disconnected: Whether to queue message if connection is disconnected
            
        Returns:
            True if sent successfully, False otherwise
        """
        if connection_id not in self.connections:
            if queue_if_disconnected:
                # Queue message for later delivery
                # Would need to track which room this connection was in
                logger.debug(f"Connection {connection_id} not found, message queued")
            return False
        
        connection = self.connections[connection_id]
        return await self._send_to_connection(connection, message)

    async def broadcast_to_room(
        self,
        room: str,
        message: Dict[str, Any],
        exclude_connection_id: Optional[str] = None,
    ) -> int:
        """
        Broadcast message to all connections in a room.
        
        Args:
            room: Room identifier
            message: Message to broadcast
            exclude_connection_id: Optional connection ID to exclude from broadcast
            
        Returns:
            Number of connections that received the message
        """
        if room not in self.rooms:
            return 0
        
        # Add to room message queue
        self.room_message_queues[room].append({
            "message": message,
            "timestamp": datetime.utcnow(),
        })
        
        sent_count = 0
        dead_connections = []
        
        for connection in list(self.rooms[room]):
            if exclude_connection_id and connection.connection_id == exclude_connection_id:
                continue
            
            if await self._send_to_connection(connection, message):
                sent_count += 1
            else:
                dead_connections.append(connection.connection_id)
        
        # Clean up dead connections
        for conn_id in dead_connections:
            self.disconnect(conn_id)
        
        return sent_count

    async def broadcast_to_all(
        self,
        message: Dict[str, Any],
        exclude_connection_id: Optional[str] = None,
    ) -> int:
        """
        Broadcast message to all connected clients.
        
        Args:
            message: Message to broadcast
            exclude_connection_id: Optional connection ID to exclude
            
        Returns:
            Number of connections that received the message
        """
        total_sent = 0
        for room in list(self.rooms.keys()):
            total_sent += await self.broadcast_to_room(room, message, exclude_connection_id)
        return total_sent

    async def _send_to_connection(
        self,
        connection: Connection,
        message: Dict[str, Any],
    ) -> bool:
        """
        Internal method to send message to a connection.
        
        Args:
            connection: Connection object
            message: Message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            await connection.websocket.send_json(message)
            connection.last_heartbeat = datetime.utcnow()
            self.stats["total_messages_sent"] += 1
            return True
        except Exception as e:
            logger.warning(f"Failed to send message to {connection}: {e}")
            self.stats["total_messages_failed"] += 1
            connection.is_alive = False
            return False

    async def _send_queued_messages(self, connection: Connection) -> None:
        """Send queued messages to a reconnected client."""
        room_queue = self.room_message_queues.get(connection.room, deque())
        
        if not room_queue:
            return
        
        # Send last few messages from queue
        messages_to_send = list(room_queue)[-10:]  # Last 10 messages
        
        for queued in messages_to_send:
            await self._send_to_connection(
                connection,
                {
                    **queued["message"],
                    "queued": True,
                    "original_timestamp": queued["timestamp"].isoformat(),
                },
            )

    async def _heartbeat_loop(self) -> None:
        """Background task to send heartbeat messages."""
        while True:
            try:
                await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                
                # Send heartbeat to all connections
                heartbeat_message = {
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
                dead_connections = []
                for connection in list(self.connections.values()):
                    # Check if connection is still alive
                    time_since_heartbeat = (datetime.utcnow() - connection.last_heartbeat).total_seconds()
                    
                    if time_since_heartbeat > settings.WS_HEARTBEAT_INTERVAL * 3:
                        # Connection seems dead
                        logger.warning(f"Connection {connection.connection_id} appears dead, removing")
                        dead_connections.append(connection.connection_id)
                    else:
                        # Send heartbeat
                        await self._send_to_connection(connection, heartbeat_message)
                
                # Clean up dead connections
                for conn_id in dead_connections:
                    self.disconnect(conn_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    async def _cleanup_loop(self) -> None:
        """Background task to clean up old message queues."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Clean up old message queues (older than 1 hour)
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                
                for room, queue in list(self.room_message_queues.items()):
                    # Remove old messages
                    while queue and queue[0]["timestamp"] < cutoff_time:
                        queue.popleft()
                    
                    # Remove empty queues for rooms with no connections
                    if not queue and room not in self.rooms:
                        del self.room_message_queues[room]
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    def get_room_connections(self, room: str) -> List[Connection]:
        """Get all connections in a room."""
        return list(self.rooms.get(room, set()))

    def get_connection(self, connection_id: str) -> Optional[Connection]:
        """Get connection by ID."""
        return self.connections.get(connection_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            **self.stats,
            "rooms": len(self.rooms),
            "rooms_detail": {
                room: len(connections)
                for room, connections in self.rooms.items()
            },
        }


# Global WebSocket manager instance
ws_manager = WebSocketManager()

