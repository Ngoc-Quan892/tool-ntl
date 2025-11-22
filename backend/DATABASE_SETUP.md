# Database Setup Guide

Hướng dẫn thiết lập và sử dụng database layer với PostgreSQL/SQLAlchemy.

## Cấu trúc

### 1. Database Manager (`app/models/database.py`)

Database manager với các tính năng:
- **Connection Pooling**: Quản lý pool kết nối với cấu hình từ settings
- **Session Management**: Context manager và dependency injection cho FastAPI
- **Health Check**: Kiểm tra trạng thái kết nối database
- **Migration Support**: Tích hợp với Alembic

**Sử dụng:**

```python
from app.models.database import db_manager, get_db

# Context manager
with db_manager.get_session() as session:
    # Sử dụng session
    pass

# FastAPI dependency
@app.get("/items")
def get_items(db: Session = Depends(get_db)):
    return db.query(Item).all()
```

### 2. Schemas (`app/models/schemas.py`)

Pydantic models cho:
- **API Request/Response**: Validation cho tất cả endpoints
- **WebSocket Messages**: Schemas cho real-time communication
- **Enhanced Validation**: Field validation với constraints

**WebSocket Message Types:**
- `PredictionUpdateMessage`: Cập nhật prediction
- `ResultAddedMessage`: Khi có result mới
- `SimulationUpdateMessage`: Cập nhật tiến trình simulation
- `ErrorMessage`: Thông báo lỗi
- `HeartbeatMessage`: Heartbeat message

### 3. Base API Router (`app/api/v2/base.py`)

Base router cho API v2 với:
- **Exception Handlers**: Xử lý lỗi chuẩn hóa
- **Dependency Injection**: Utilities cho database và request
- **Response Helpers**: Success và Paginated response helpers
- **Health Endpoints**: `/v2/health` và `/v2/health/db`

**Exception Types:**
- `APIException`: Base exception
- `NotFoundError`: Resource not found
- `RequestValidationError`: Validation errors
- `DatabaseError`: Database operation errors

## Migrations

### Setup

Alembic đã được cấu hình với:
- `alembic.ini`: Cấu hình Alembic
- `alembic/env.py`: Environment setup với database settings
- `alembic/versions/001_initial_migration.py`: Migration đầu tiên

### Chạy Migrations

```bash
# Tạo migration mới
cd backend
alembic revision --autogenerate -m "description"

# Chạy migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Xem lịch sử
alembic history

# Xem migration hiện tại
alembic current
```

### Migration đầu tiên

Migration `001_initial_migration.py` tạo:
- `game_results` table với indexes
- `simulation_runs` table với indexes

## Seed Data

### Chạy Seed Script

```bash
cd backend
python -m scripts.seed_data

# Với options
python -m scripts.seed_data --clear --game-results 200 --simulation-runs 10
```

**Options:**
- `--clear`: Xóa dữ liệu hiện có trước khi seed
- `--game-results N`: Số lượng game results (default: 100)
- `--simulation-runs N`: Số lượng simulation runs (default: 5)

## Database Models

### GameResult

Lưu trữ kết quả từng ván baccarat:
- `id`: Primary key
- `result`: B, P, hoặc T
- `prediction`: JSON prediction data
- `shoe_number`: Số shoe
- `hand_number`: Số hand trong shoe
- `timestamp`: Thời gian
- `true_count`: True count từ card counting
- `edge`: Calculated edge

### SimulationRun

Lưu trữ thông tin simulation runs:
- `id`: Primary key
- `task_id`: Unique task identifier
- `total_shoes`: Tổng số shoes
- `completed_shoes`: Số shoes đã hoàn thành
- `results`: JSON results summary
- `status`: pending, running, completed, failed
- `started_at`: Thời gian bắt đầu
- `completed_at`: Thời gian hoàn thành

## Configuration

Database settings trong `app/core/config.py`:

```python
DATABASE_URL: str = "postgresql://user:password@localhost:5432/baccarat"
DB_ECHO: bool = False  # Log SQL queries
DB_POOL_SIZE: int = 5
DB_MAX_OVERFLOW: int = 10
```

## Health Checks

### API Health Check

```bash
curl http://localhost:8000/api/v2/health
```

### Database Health Check

```bash
curl http://localhost:8000/api/v2/health/db
```

## Best Practices

1. **Luôn sử dụng migrations**: Không dùng `create_all()` trong production
2. **Sử dụng dependency injection**: Dùng `get_db()` cho FastAPI endpoints
3. **Context managers**: Sử dụng `db_manager.get_session()` cho background tasks
4. **Error handling**: Sử dụng custom exceptions từ `base.py`
5. **Connection pooling**: Đã được cấu hình tự động, không cần setup thêm

## Troubleshooting

### Database connection failed

1. Kiểm tra `DATABASE_URL` trong `.env` hoặc environment variables
2. Đảm bảo PostgreSQL đang chạy
3. Kiểm tra credentials và permissions

### Migration errors

1. Đảm bảo database đã được tạo
2. Kiểm tra `alembic.ini` có đúng path
3. Chạy `alembic current` để xem migration hiện tại

### Seed data errors

1. Đảm bảo migrations đã chạy (`alembic upgrade head`)
2. Kiểm tra database connection
3. Xem logs để biết lỗi cụ thể

