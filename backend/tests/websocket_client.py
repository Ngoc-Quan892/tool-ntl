"""
WebSocket test client with auto-reconnection and heartbeat.

Usage:
    python -m tests.websocket_client --endpoint predictions
    python -m tests.websocket_client --endpoint stats
    python -m tests.websocket_client --endpoint shoe --shoe-id <shoe_id>
"""
import argparse
import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from typing import Optional

import websockets
from websockets.exceptions import ConnectionClosed, InvalidURI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WebSocketClient:
    """WebSocket client with auto-reconnection and heartbeat."""

    def __init__(
        self,
        url: str,
        reconnect_interval: int = 5,
        heartbeat_interval: int = 30,
    ):
        self.url = url
        self.reconnect_interval = reconnect_interval
        self.heartbeat_interval = heartbeat_interval
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.reconnect_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.message_count = 0

    async def connect(self) -> bool:
        """Connect to WebSocket server."""
        try:
            logger.info(f"Connecting to {self.url}...")
            self.websocket = await websockets.connect(self.url)
            logger.info(f"Connected to {self.url}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        self.running = False
        
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass
            self.websocket = None
        
        logger.info("Disconnected")

    async def send_message(self, message: dict) -> None:
        """Send a message to the server."""
        if not self.websocket:
            logger.warning("Cannot send message: not connected")
            return
        
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    async def receive_messages(self) -> None:
        """Receive and handle messages from server."""
        if not self.websocket:
            return
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.message_count += 1
                    await self.handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON: {message}")
        except ConnectionClosed:
            logger.warning("Connection closed by server")
            if self.running:
                await self.reconnect()
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            if self.running:
                await self.reconnect()

    async def handle_message(self, message: dict) -> None:
        """Handle incoming message."""
        msg_type = message.get("type", "unknown")
        timestamp = message.get("timestamp", datetime.utcnow().isoformat())
        
        logger.info(f"📨 [{msg_type}] {timestamp}")
        
        if msg_type == "connected":
            logger.info(f"  Connection ID: {message.get('connection_id')}")
            logger.info(f"  Room: {message.get('room')}")
        elif msg_type == "heartbeat":
            logger.debug("  Heartbeat received")
        elif msg_type == "pong":
            logger.debug("  Pong received")
        elif msg_type == "prediction_update":
            data = message.get("data", {})
            logger.info(f"  Prediction: {data.get('recommend')} (confidence: {data.get('confidence', 0):.2%})")
        elif msg_type == "stats_update":
            data = message.get("data", {})
            logger.info(f"  Stats: {data.get('total_hands', 0)} hands, "
                       f"accuracy: {data.get('accuracy', 0):.2f}%")
        elif msg_type == "shoe_state":
            data = message.get("data", {})
            logger.info(f"  Shoe: {data.get('cards_remaining', 0)} cards remaining, "
                       f"{data.get('hands_played', 0)} hands played")
        elif msg_type == "error":
            logger.error(f"  Error: {message.get('message')}")
        else:
            logger.info(f"  Data: {json.dumps(message, indent=2)}")

    async def heartbeat_loop(self) -> None:
        """Send heartbeat messages periodically."""
        while self.running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                if self.websocket and self.running:
                    await self.send_message({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    logger.debug("Sent heartbeat (ping)")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    async def reconnect(self) -> None:
        """Reconnect to server."""
        logger.info(f"Reconnecting in {self.reconnect_interval} seconds...")
        await asyncio.sleep(self.reconnect_interval)
        
        if self.running:
            success = await self.connect()
            if success:
                # Restart message receiving
                asyncio.create_task(self.receive_messages())
                # Restart heartbeat
                if self.heartbeat_task:
                    self.heartbeat_task.cancel()
                self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())

    async def run(self) -> None:
        """Run the client."""
        self.running = True
        
        # Connect
        success = await self.connect()
        if not success:
            logger.error("Failed to connect, exiting")
            return
        
        # Start heartbeat
        self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())
        
        # Start receiving messages
        try:
            await self.receive_messages()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            await self.disconnect()
            logger.info(f"Total messages received: {self.message_count}")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="WebSocket test client")
    parser.add_argument(
        "--endpoint",
        choices=["predictions", "stats", "shoe"],
        required=True,
        help="WebSocket endpoint to connect to",
    )
    parser.add_argument(
        "--shoe-id",
        help="Shoe ID (required for shoe endpoint)",
    )
    parser.add_argument(
        "--url",
        default="ws://localhost:8000",
        help="Base WebSocket URL",
    )
    parser.add_argument(
        "--reconnect-interval",
        type=int,
        default=5,
        help="Reconnection interval in seconds",
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=int,
        default=30,
        help="Heartbeat interval in seconds",
    )
    
    args = parser.parse_args()
    
    # Build URL
    if args.endpoint == "shoe":
        if not args.shoe_id:
            logger.error("--shoe-id is required for shoe endpoint")
            sys.exit(1)
        url = f"{args.url}/ws/shoe/{args.shoe_id}"
    elif args.endpoint == "predictions":
        url = f"{args.url}/ws/predictions"
    elif args.endpoint == "stats":
        url = f"{args.url}/ws/stats"
    else:
        logger.error(f"Unknown endpoint: {args.endpoint}")
        sys.exit(1)
    
    # Create client
    client = WebSocketClient(
        url=url,
        reconnect_interval=args.reconnect_interval,
        heartbeat_interval=args.heartbeat_interval,
    )
    
    # Handle signals
    def signal_handler(sig, frame):
        logger.info("Received signal, shutting down...")
        client.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run client
    try:
        await client.run()
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

