# WebSocket Documentation

Tài liệu đầy đủ cho WebSocket implementation với real-time updates.

## Overview

WebSocket implementation cung cấp real-time updates cho:
- Shoe state changes
- Prediction updates
- Statistics changes

## Architecture

### WebSocket Manager

`websocket_manager.py` cung cấp:
- **Connection Management**: Quản lý connections với metadata
- **Room-based Broadcasting**: Gửi messages đến các rooms cụ thể
- **Message Queuing**: Lưu messages cho clients reconnect
- **Heartbeat Mechanism**: Giữ connections alive và detect dead connections
- **Auto-cleanup**: Tự động dọn dẹp dead connections và old messages

### Connection Lifecycle

1. **Connect**: Client kết nối và được assign vào một room
2. **Heartbeat**: Server gửi heartbeat mỗi 30 giây
3. **Message Exchange**: Client và server trao đổi messages
4. **Reconnect**: Client tự động reconnect nếu disconnect
5. **Cleanup**: Server tự động cleanup dead connections

## Endpoints

### 1. `/ws/shoe/{shoe_id}`

Live updates cho một shoe cụ thể.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/shoe/{shoe_id}');
```

**Messages Received:**
- `connected` - Khi kết nối thành công
- `shoe_state` - Trạng thái shoe hiện tại
- `heartbeat` - Heartbeat messages
- `error` - Error messages

**Messages Sent:**
- `ping` - Heartbeat ping
- `subscribe` - Subscribe to specific events

**Example:**
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'shoe_state') {
        console.log('Shoe state:', data.data);
    }
};
```

### 2. `/ws/predictions`

Real-time prediction updates.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/predictions');
```

**Messages Received:**
- `connected` - Khi kết nối thành công
- `prediction_update` - Prediction updates (khi có thay đổi)
- `heartbeat` - Heartbeat messages

**Update Frequency:**
- Checks every 2 seconds
- Sends update if prediction changed significantly (>5% confidence change)

**Example:**
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'prediction_update') {
        console.log('Prediction:', data.data);
    }
};
```

### 3. `/ws/stats`

Live statistics updates.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/stats');
```

**Messages Received:**
- `connected` - Khi kết nối thành công
- `stats_update` - Statistics updates (khi có thay đổi)
- `heartbeat` - Heartbeat messages

**Update Frequency:**
- Checks every 3 seconds
- Sends update if total hands changed

**Example:**
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'stats_update') {
        console.log('Stats:', data.data);
    }
};
```

## Message Format

### Standard Message Structure

```json
{
  "type": "message_type",
  "data": {},
  "timestamp": "2024-01-01T00:00:00",
  "connection_id": "uuid",
  "room": "room_name"
}
```

### Message Types

#### `connected`
Sent when client successfully connects.

```json
{
  "type": "connected",
  "connection_id": "uuid",
  "room": "predictions",
  "timestamp": "2024-01-01T00:00:00"
}
```

#### `heartbeat`
Sent periodically to keep connection alive.

```json
{
  "type": "heartbeat",
  "timestamp": "2024-01-01T00:00:00"
}
```

#### `prediction_update`
Prediction data update.

```json
{
  "type": "prediction_update",
  "data": {
    "recommend": "B",
    "confidence": 0.75,
    "edge_pct": 2.5,
    "pattern": "Banker streak",
    "true_count": 1.2,
    "next_suggested": "B",
    "timestamp": "2024-01-01T00:00:00"
  },
  "timestamp": "2024-01-01T00:00:00"
}
```

#### `stats_update`
Statistics update.

```json
{
  "type": "stats_update",
  "data": {
    "total_hands": 100,
    "banker_wins": 46,
    "player_wins": 44,
    "ties": 10,
    "accuracy": 55.0
  },
  "timestamp": "2024-01-01T00:00:00"
}
```

#### `shoe_state`
Shoe state information.

```json
{
  "type": "shoe_state",
  "shoe_id": "uuid",
  "data": {
    "cards_remaining": 416,
    "hands_played": 0,
    "true_count_b": 0.0,
    "true_count_p": 0.0
  },
  "timestamp": "2024-01-01T00:00:00"
}
```

#### `error`
Error message.

```json
{
  "type": "error",
  "message": "Error description",
  "timestamp": "2024-01-01T00:00:00"
}
```

## Client Implementation

### Python Test Client

```bash
# Connect to predictions endpoint
python -m tests.websocket_client --endpoint predictions

# Connect to stats endpoint
python -m tests.websocket_client --endpoint stats

# Connect to shoe endpoint
python -m tests.websocket_client --endpoint shoe --shoe-id <shoe_id>
```

### JavaScript/HTML Test Client

Mở file `backend/tests/websocket_test.html` trong browser để test WebSocket connections.

### Auto-Reconnection

Clients tự động reconnect nếu connection bị mất:
- Reconnect interval: 5 seconds (configurable)
- Max reconnection attempts: Unlimited
- Queued messages: Last 10 messages sent on reconnect

### Heartbeat

- Server sends heartbeat every 30 seconds
- Client should respond with `ping` messages
- Dead connections detected after 3 missed heartbeats

## Configuration

Settings trong `app/core/config.py`:

```python
WS_HEARTBEAT_INTERVAL: int = 30  # Seconds
WS_MAX_CONNECTIONS: int = 100
```

## Room-based Broadcasting

Messages có thể được broadcast đến:
- **Specific Room**: `broadcast_to_room(room, message)`
- **All Connections**: `broadcast_to_all(message)`
- **Specific Connection**: `send_to_connection(connection_id, message)`

## Message Queuing

- Messages được queue per room
- Last 50 messages per room
- Messages older than 1 hour are cleaned up
- Reconnecting clients receive last 10 messages

## Statistics

Manager cung cấp statistics:

```python
stats = ws_manager.get_stats()
# Returns:
# {
#   "total_connections": 100,
#   "active_connections": 50,
#   "total_messages_sent": 1000,
#   "total_messages_failed": 5,
#   "rooms": 3,
#   "rooms_detail": {
#     "predictions": 20,
#     "stats": 15,
#     "shoe_123": 5
#   }
# }
```

## Error Handling

### Connection Errors
- Automatic reconnection
- Dead connection cleanup
- Error messages sent to client

### Message Errors
- Invalid JSON ignored
- Failed sends logged
- Dead connections removed

## Best Practices

1. **Always handle reconnection**: Implement auto-reconnect logic
2. **Respond to heartbeats**: Send ping messages periodically
3. **Handle errors gracefully**: Check message types and handle errors
4. **Limit message rate**: Don't send too many messages too quickly
5. **Clean up on disconnect**: Close connections properly

## Testing

### Manual Testing

1. Start server: `uvicorn app.main:app --reload`
2. Open `backend/tests/websocket_test.html` in browser
3. Connect to different endpoints
4. Observe real-time updates

### Automated Testing

```bash
# Run Python test client
python -m tests.websocket_client --endpoint predictions

# Test with multiple clients
for i in {1..5}; do
    python -m tests.websocket_client --endpoint predictions &
done
```

## Troubleshooting

### Connection Fails
- Check server is running
- Verify WebSocket URL is correct
- Check firewall/network settings

### No Messages Received
- Verify endpoint is correct
- Check server logs for errors
- Ensure heartbeat is working

### High Memory Usage
- Message queues are limited (50 per room)
- Old messages are cleaned up automatically
- Dead connections are removed

## Performance

- Supports 100+ concurrent connections
- Low latency (<100ms for message delivery)
- Efficient room-based broadcasting
- Automatic cleanup of dead connections

