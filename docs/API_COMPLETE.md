# API Documentation - Complete Reference

Tài liệu đầy đủ cho Baccarat Predictor Pro API.

## 📋 Table of Contents

- [Overview](#overview)
- [Base URLs](#base-urls)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [API Versions](#api-versions)
- [Endpoints](#endpoints)
- [WebSocket](#websocket)
- [Error Handling](#error-handling)
- [Examples](#examples)

## 🌐 Overview

Baccarat Predictor Pro API cung cấp:

- Real-time game simulation với 8-deck shoe
- Professional card counting (EOR-based)
- Machine Learning predictions
- Statistical analysis
- Roadmap visualization
- WebSocket real-time updates

## 🔗 Base URLs

- **Development**: `http://localhost:8000`
- **Production**: `https://api.yourdomain.com`

## 🔐 Authentication

Hiện tại API không yêu cầu authentication. Trong production, sẽ thêm JWT authentication.

### Future Authentication (Planned)

```http
Authorization: Bearer <jwt_token>
```

## ⚡ Rate Limiting

- **API Requests**: 100 requests/minute per IP
- **WebSocket Connections**: 10 connections per IP
- **Burst**: 20 requests allowed in burst

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
```

## 📚 API Versions

### v1 (Legacy)
- Base: `/api`
- Status: Maintained for compatibility
- Deprecated: Use v2 for new integrations

### v2 (Current)
- Base: `/api/v2`
- Status: Active development
- Recommended for new integrations

## 🛠️ Endpoints

### Health Endpoints

#### `GET /health`
Root health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected"
}
```

#### `GET /api/v2/health`
API health check.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### `GET /api/v2/health/db`
Database-specific health check.

**Response:**
```json
{
  "status": "healthy",
  "database_url": "postgresql://...",
  "pool_size": 10,
  "max_overflow": 20
}
```

### Shoe Management

#### `POST /api/v2/shoes/create`
Tạo một shoe mới.

**Request:**
```json
{
  "decks": 8,
  "reshuffle_point": 20
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "shoe_id": "uuid-here",
    "decks": 8,
    "reshuffle_point": 20,
    "message": "Shoe created successfully"
  }
}
```

#### `GET /api/v2/shoes/{shoe_id}`
Lấy trạng thái của một shoe.

**Response:**
```json
{
  "success": true,
  "data": {
    "shoe_id": "uuid-here",
    "decks": 8,
    "cards_remaining": 312,
    "reshuffle_point": 20,
    "hands_played": 0
  }
}
```

#### `POST /api/v2/shoes/{shoe_id}/reset`
Reset một shoe (tạo lại với cards mới).

**Response:**
```json
{
  "success": true,
  "data": {
    "shoe_id": "uuid-here",
    "message": "Shoe reset successfully"
  }
}
```

#### `DELETE /api/v2/shoes/{shoe_id}`
Xóa một shoe.

**Response:**
```json
{
  "success": true,
  "message": "Shoe deleted successfully"
}
```

### Hand Playing

#### `POST /api/v2/hands/play`
Chơi một hand.

**Request:**
```json
{
  "shoe_id": "uuid-here",
  "result": "B"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "hand_id": "uuid-here",
    "result": "B",
    "shoe_id": "uuid-here",
    "hand_number": 1,
    "cards_remaining": 310,
    "true_count": 0.5,
    "edge": 0.02
  }
}
```

#### `GET /api/v2/hands/history`
Lấy lịch sử hands.

**Query Parameters:**
- `shoe_id` (optional): Filter by shoe
- `limit` (optional, default: 100): Number of results
- `offset` (optional, default: 0): Pagination offset

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "hand_id": "uuid-here",
        "result": "B",
        "shoe_id": "uuid-here",
        "hand_number": 1,
        "timestamp": "2024-01-01T00:00:00Z"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 100
  }
}
```

#### `GET /api/v2/hands/{hand_id}`
Lấy thông tin hand cụ thể.

**Response:**
```json
{
  "success": true,
  "data": {
    "hand_id": "uuid-here",
    "result": "B",
    "prediction": {
      "prediction": "B",
      "confidence": 0.75,
      "edge": 0.02
    },
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### Predictions

#### `POST /api/v2/predictions/predict`
Lấy prediction hiện tại.

**Request:**
```json
{
  "shoe_id": "uuid-here"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "prediction": "B",
    "confidence": 0.75,
    "edge": 0.02,
    "true_count": 0.5,
    "cards_remaining": 310,
    "ml_prediction": {
      "prediction": "B",
      "confidence": 0.72,
      "features": {}
    }
  }
}
```

#### `GET /api/v2/predictions/accuracy`
Lấy accuracy metrics.

**Query Parameters:**
- `shoe_id` (optional): Filter by shoe
- `limit` (optional): Number of recent predictions to analyze

**Response:**
```json
{
  "success": true,
  "data": {
    "total_predictions": 100,
    "correct": 75,
    "incorrect": 25,
    "accuracy": 0.75,
    "by_result": {
      "B": {"total": 50, "correct": 40, "accuracy": 0.8},
      "P": {"total": 40, "correct": 30, "accuracy": 0.75},
      "T": {"total": 10, "correct": 5, "accuracy": 0.5}
    }
  }
}
```

#### `GET /api/v2/predictions/confidence`
Lấy confidence scores.

**Response:**
```json
{
  "success": true,
  "data": {
    "average_confidence": 0.72,
    "high_confidence_count": 60,
    "medium_confidence_count": 30,
    "low_confidence_count": 10,
    "confidence_distribution": [0.5, 0.6, 0.7, 0.8, 0.9]
  }
}
```

### Analysis

#### `GET /api/v2/analysis/statistics`
Lấy thống kê shoe.

**Query Parameters:**
- `shoe_id` (required): Shoe ID

**Response:**
```json
{
  "success": true,
  "data": {
    "shoe_id": "uuid-here",
    "total_hands": 100,
    "banker_wins": 50,
    "player_wins": 40,
    "ties": 10,
    "banker_percentage": 0.5,
    "player_percentage": 0.4,
    "tie_percentage": 0.1,
    "true_count": 0.5,
    "edge": 0.02
  }
}
```

#### `GET /api/v2/analysis/patterns`
Phân tích patterns.

**Query Parameters:**
- `shoe_id` (required): Shoe ID
- `pattern_type` (optional): "streaks", "alternating", "clusters"

**Response:**
```json
{
  "success": true,
  "data": {
    "patterns": {
      "longest_banker_streak": 5,
      "longest_player_streak": 4,
      "alternating_count": 20,
      "clusters": [
        {"type": "banker", "count": 3, "positions": [10, 11, 12]}
      ]
    }
  }
}
```

#### `GET /api/v2/analysis/edge`
Tính toán edge.

**Query Parameters:**
- `shoe_id` (required): Shoe ID

**Response:**
```json
{
  "success": true,
  "data": {
    "edge": 0.02,
    "true_count": 0.5,
    "recommendation": "favorable",
    "confidence": 0.75
  }
}
```

### Metrics

#### `GET /api/v2/metrics/prometheus`
Prometheus metrics endpoint.

**Response:** Prometheus format metrics

#### `GET /api/v2/metrics`
Metrics dashboard.

**Response:**
```json
{
  "success": true,
  "data": {
    "cache": {
      "connected": true,
      "keys": 1000,
      "memory_usage": "10MB",
      "hits": 5000,
      "misses": 200
    },
    "database": {
      "connected": true,
      "pool_size": 10,
      "checked_out": 2
    },
    "websocket": {
      "active_connections": 10,
      "rooms": 3
    }
  }
}
```

## 🔌 WebSocket

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/v2');
```

### Events

#### Subscribe to Shoe Updates
```json
{
  "type": "subscribe",
  "channel": "shoe",
  "shoe_id": "uuid-here"
}
```

#### Subscribe to Predictions
```json
{
  "type": "subscribe",
  "channel": "predictions",
  "shoe_id": "uuid-here"
}
```

### Messages

#### Shoe Update
```json
{
  "type": "shoe_update",
  "data": {
    "shoe_id": "uuid-here",
    "cards_remaining": 310,
    "hands_played": 1
  }
}
```

#### Prediction Update
```json
{
  "type": "prediction_update",
  "data": {
    "prediction": "B",
    "confidence": 0.75,
    "edge": 0.02
  }
}
```

## ❌ Error Handling

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "ERR_404",
    "message": "Resource not found",
    "detail": "Shoe with ID 'uuid' not found"
  }
}
```

### Error Codes

- `ERR_400`: Bad Request
- `ERR_404`: Not Found
- `ERR_422`: Validation Error
- `ERR_500`: Internal Server Error

### Example Error Response

```json
{
  "success": false,
  "error": {
    "code": "ERR_422",
    "message": "Validation error",
    "detail": {
      "field": "decks",
      "message": "decks must be between 1 and 8"
    }
  }
}
```

## 📖 Examples

### Complete Workflow

```python
import requests

BASE_URL = "http://localhost:8000/api/v2"

# 1. Create a shoe
response = requests.post(f"{BASE_URL}/shoes/create", json={
    "decks": 8,
    "reshuffle_point": 20
})
shoe = response.json()["data"]
shoe_id = shoe["shoe_id"]

# 2. Get prediction
response = requests.post(f"{BASE_URL}/predictions/predict", json={
    "shoe_id": shoe_id
})
prediction = response.json()["data"]

# 3. Play a hand
response = requests.post(f"{BASE_URL}/hands/play", json={
    "shoe_id": shoe_id,
    "result": prediction["prediction"]
})
hand = response.json()["data"]

# 4. Get statistics
response = requests.get(f"{BASE_URL}/analysis/statistics", params={
    "shoe_id": shoe_id
})
stats = response.json()["data"]
```

### JavaScript Example

```javascript
const API_BASE = 'http://localhost:8000/api/v2';

// Create shoe
const createShoe = async () => {
  const response = await fetch(`${API_BASE}/shoes/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decks: 8, reshuffle_point: 20 })
  });
  return response.json();
};

// Get prediction
const getPrediction = async (shoeId) => {
  const response = await fetch(`${API_BASE}/predictions/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ shoe_id: shoeId })
  });
  return response.json();
};
```

## 📚 Interactive Documentation

- **Swagger UI**: `/docs` - Interactive API explorer
- **ReDoc**: `/redoc` - Alternative documentation view
- **OpenAPI Spec**: `/openapi.json` - Machine-readable API specification

## 🔗 Related Documentation

- [User Guide](../user-guide/quick-start.md)
- [Developer Guide](../DEVELOPER_GUIDE.md)
- [Deployment Guide](../deployment/DEPLOYMENT.md)

