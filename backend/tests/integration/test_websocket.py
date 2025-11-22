"""
Integration tests for WebSocket functionality.
"""
import pytest
import asyncio
import websockets
from app.main import create_app


@pytest.mark.asyncio
class TestWebSocket:
    """Tests for WebSocket connections."""
    
    async def test_websocket_connection(self):
        """Test WebSocket connection."""
        # This would require a running server
        # For now, we'll test the connection logic
        try:
            async with websockets.connect("ws://localhost:8000/ws") as ws:
                # Send a message
                await ws.send('{"type": "ping"}')
                # Wait for response
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                assert response is not None
        except (ConnectionRefusedError, OSError):
            # Server not running, skip test
            pytest.skip("WebSocket server not available")
    
    async def test_websocket_message_types(self):
        """Test different WebSocket message types."""
        try:
            async with websockets.connect("ws://localhost:8000/ws") as ws:
                # Test prediction update
                await ws.send('{"type": "get_prediction"}')
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                assert response is not None
        except (ConnectionRefusedError, OSError):
            pytest.skip("WebSocket server not available")

