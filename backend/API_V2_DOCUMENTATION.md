# API v2 Documentation

Tài liệu đầy đủ cho API v2 của Baccarat Predictor Pro.

## Base URL

```
http://localhost:8000/api/v2
```

## Authentication

Hiện tại API không yêu cầu authentication. Trong production, sẽ thêm JWT authentication.

## Endpoints Overview

### Health Endpoints
- `GET /health` - Health check
- `GET /health/db` - Database health check

### Shoe Management (`/shoes`)
- `POST /shoes/create` - Tạo shoe mới
- `GET /shoes/{shoe_id}` - Lấy trạng thái shoe
- `POST /shoes/{shoe_id}/reset` - Reset shoe
- `DELETE /shoes/{shoe_id}` - Xóa shoe

### Hand Playing (`/hands`)
- `POST /hands/play` - Chơi một hand
- `GET /hands/history` - Lấy lịch sử hands
- `GET /hands/{hand_id}` - Lấy thông tin hand cụ thể

### Predictions (`/predictions`)
- `POST /predictions/predict` - Lấy prediction hiện tại
- `GET /predictions/accuracy` - Lấy accuracy metrics
- `GET /predictions/confidence` - Lấy confidence scores

### Analysis (`/analysis`)
- `GET /analysis/statistics` - Thống kê shoe
- `GET /analysis/patterns` - Phân tích patterns
- `GET /analysis/edge` - Tính toán edge

## Chi tiết Endpoints

### 1. Health Check

#### GET /health
Kiểm tra trạng thái API và dependencies.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "timestamp": null
}
```

#### GET /health/db
Kiểm tra trạng thái database.

**Response:**
```json
{
  "status": "healthy",
  "database_url": "configured",
  "pool_size": 5,
  "max_overflow": 10
}
```

### 2. Shoe Management

#### POST /shoes/create
Tạo một shoe mới.

**Request Body:**
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
    "shoe_id": "uuid",
    "decks": 8,
    "reshuffle_point": 20,
    "message": "Shoe created successfully"
  },
  "message": "Shoe created"
}
```

#### GET /shoes/{shoe_id}
Lấy trạng thái của một shoe.

**Response:**
```json
{
  "shoe_id": "uuid",
  "decks": 8,
  "cards_remaining": 416,
  "cards_dealt": 0,
  "decks_remaining": 8.0,
  "hands_played": 0,
  "reshuffled_count": 0,
  "running_count_b": 0.0,
  "running_count_p": 0.0,
  "true_count_b": 0.0,
  "true_count_p": 0.0,
  "edge": {...},
  "composition": {...},
  "high_card_count": 128,
  "low_card_count": 96,
  "high_low_ratio": 1.333,
  "created_at": "2024-01-01T00:00:00",
  "needs_reshuffle": false
}
```

#### POST /shoes/{shoe_id}/reset
Reset một shoe (reshuffle và xóa lịch sử).

**Response:**
```json
{
  "success": true,
  "shoe_id": "uuid",
  "message": "Shoe reset successfully"
}
```

#### DELETE /shoes/{shoe_id}
Xóa một shoe.

**Response:**
```json
{
  "success": true,
  "data": {
    "shoe_id": "uuid"
  },
  "message": "Shoe deleted successfully"
}
```

### 3. Hand Playing

#### POST /hands/play
Chơi một hand.

**Request Body:**
```json
{
  "shoe_id": null,
  "result": null
}
```

**Response:**
```json
{
  "hand_id": "uuid",
  "shoe_id": "uuid",
  "hand_number": 1,
  "result": "B",
  "banker_total": 8,
  "player_total": 5,
  "is_natural": false,
  "banker_cards": [
    {"rank": "K", "suit": "♠"},
    {"rank": "8", "suit": "♥"}
  ],
  "player_cards": [
    {"rank": "5", "suit": "♦"}
  ],
  "timestamp": "2024-01-01T00:00:00"
}
```

#### GET /hands/history
Lấy lịch sử hands với pagination.

**Query Parameters:**
- `page` (int, default: 1) - Số trang
- `page_size` (int, default: 50, max: 500) - Số items mỗi trang
- `shoe_id` (string, optional) - Lọc theo shoe ID

**Response:**
```json
{
  "total": 100,
  "items": [...],
  "page": 1,
  "page_size": 50
}
```

#### GET /hands/{hand_id}
Lấy thông tin một hand cụ thể.

**Response:**
Tương tự như response của `/hands/play`

### 4. Predictions

#### POST /predictions/predict
Lấy prediction hiện tại.

**Request Body:**
```json
{
  "shoe_id": null
}
```

**Response:**
```json
{
  "recommend": "B",
  "confidence": 0.75,
  "edge_pct": 2.5,
  "pattern": "Banker streak",
  "true_count": 1.2,
  "next_suggested": "B",
  "timestamp": "2024-01-01T00:00:00"
}
```

#### GET /predictions/accuracy
Lấy accuracy metrics.

**Query Parameters:**
- `shoe_id` (string, optional) - Lọc theo shoe ID

**Response:**
```json
{
  "total_predictions": 100,
  "correct_predictions": 55,
  "accuracy": 55.0,
  "banker_accuracy": 60.0,
  "player_accuracy": 50.0,
  "recent_accuracy": 58.0,
  "confidence_distribution": {
    "low": 20,
    "medium": 50,
    "high": 30
  }
}
```

#### GET /predictions/confidence
Lấy confidence scores.

**Query Parameters:**
- `limit` (int, default: 100, max: 1000) - Số results để phân tích

**Response:**
```json
{
  "current_confidence": 0.75,
  "average_confidence": 0.68,
  "confidence_history": [0.75, 0.70, 0.65, ...],
  "confidence_by_outcome": {
    "B": 0.70,
    "P": 0.65,
    "T": 0.50
  }
}
```

### 5. Analysis

#### GET /analysis/statistics
Lấy thống kê shoe.

**Query Parameters:**
- `shoe_id` (string, optional) - Shoe ID (dùng default nếu không có)

**Response:**
```json
{
  "total_hands": 100,
  "banker_wins": 46,
  "player_wins": 44,
  "ties": 10,
  "banker_pct": 51.11,
  "player_pct": 48.89,
  "tie_pct": 10.0,
  "max_banker_streak": 5,
  "max_player_streak": 4,
  "natural_count": 15,
  "natural_pct": 15.0,
  "banker_deviation": 0.0513,
  "player_deviation": 0.0426
}
```

#### GET /analysis/patterns
Phân tích patterns.

**Query Parameters:**
- `shoe_id` (string, optional) - Shoe ID
- `limit` (int, default: 100, min: 10, max: 1000) - Số hands để phân tích

**Response:**
```json
{
  "detected_patterns": [
    {
      "type": "streak",
      "pattern": "BBBB",
      "length": 4,
      "position": 10
    }
  ],
  "pattern_frequency": {
    "streak": 5,
    "alternation": 2
  },
  "streak_analysis": {
    "banker_streaks": {
      "count": 10,
      "average": 3.2,
      "max": 5
    },
    "player_streaks": {
      "count": 8,
      "average": 2.8,
      "max": 4
    }
  },
  "sequence_analysis": {
    "common_sequences": [
      {"sequence": "BBP", "count": 5}
    ],
    "sequence_frequency": {...}
  }
}
```

#### GET /analysis/edge
Tính toán edge cho shoe hiện tại.

**Query Parameters:**
- `shoe_id` (string, optional) - Shoe ID (dùng default nếu không có)

**Response:**
```json
{
  "edge_banker_raw": 1.234,
  "edge_banker_after_commission": -4.066,
  "edge_player": -1.240,
  "max_edge": -1.240,
  "has_positive_edge": false,
  "recommendation": "NO BET",
  "reason": "Both sides have negative expectation",
  "true_count_b": 0.0,
  "true_count_p": 0.0
}
```

## Error Responses

Tất cả endpoints trả về lỗi theo format chuẩn:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message",
    "detail": {}
  }
}
```

### Error Codes

- `NOT_FOUND` - Resource không tồn tại
- `VALIDATION_ERROR` - Lỗi validation
- `DATABASE_ERROR` - Lỗi database
- `HTTP_404` - Not found
- `HTTP_422` - Validation error
- `HTTP_500` - Internal server error

## Swagger Documentation

Truy cập Swagger UI tại:
```
http://localhost:8000/docs
```

## Postman Collection

Import file `backend/postman_collection.json` vào Postman để test tất cả endpoints.

## Testing

Chạy tests:
```bash
cd backend
pytest tests/test_api_v2.py -v
```

## Rate Limiting

Hiện tại không có rate limiting. Trong production sẽ thêm rate limiting.

## Versioning

API v2 sử dụng prefix `/api/v2`. API v1 vẫn hoạt động tại `/api`.

