# Developer Guide - Baccarat Predictor Pro

Hướng dẫn cho developers muốn contribute hoặc integrate với Baccarat Predictor Pro.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Architecture](#architecture)
- [API Development](#api-development)
- [Frontend Development](#frontend-development)
- [Testing](#testing)
- [Contributing](#contributing)
- [Code Style](#code-style)

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **PostgreSQL 15+** (hoặc SQLite cho development)
- **Redis** (optional, cho caching)
- **Docker** (optional, cho containerized development)

### Quick Start

```bash
# Clone repository
git clone <repository-url>
cd "Tool NTL"

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install

# Run development servers
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

## 📁 Project Structure

```
Tool NTL/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   │   ├── v1/         # Legacy API
│   │   │   └── v2/         # Current API
│   │   ├── core/           # Core engine logic
│   │   ├── ml/             # Machine Learning
│   │   ├── models/         # Database models
│   │   ├── services/       # Services (cache, monitoring)
│   │   └── utils/          # Utilities
│   ├── tests/              # Tests
│   └── requirements.txt
├── frontend/                # React TypeScript frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom hooks
│   │   ├── stores/         # State management
│   │   └── lib/            # Utilities
│   └── package.json
├── deployment/              # Deployment configs
├── docs/                    # Documentation
└── ml-training/            # ML training scripts
```

## 🛠️ Development Setup

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup database
# For SQLite (development)
export DATABASE_URL=sqlite:///./data/baccarat.db

# For PostgreSQL (production-like)
export DATABASE_URL=postgresql://user:password@localhost:5432/baccarat

# Run migrations
alembic upgrade head

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

### Docker Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🏗️ Architecture

### Backend Architecture

```
┌─────────────────┐
│   FastAPI App   │
├─────────────────┤
│  API Routes v2  │
│  WebSocket      │
│  Middleware     │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│ Core  │ │  ML   │
│Engine │ │Model  │
└───┬───┘ └───┬───┘
    │         │
┌───▼─────────▼───┐
│   Database      │
│   (PostgreSQL)  │
└─────────────────┘
```

### Frontend Architecture

```
┌─────────────────┐
│  React App      │
├─────────────────┤
│  Components     │
│  Hooks          │
│  Stores         │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│  API  │ │ WebSocket│
│Client │ │ Client   │
└───┬───┘ └───┬───┘
    │         │
┌───▼─────────▼───┐
│   Backend API   │
└─────────────────┘
```

## 🔌 API Development

### Adding New Endpoint

1. **Create route file** (if new module):
```python
# backend/app/api/v2/new_feature.py
from fastapi import APIRouter
from app.models.schemas import YourSchema

router = APIRouter(prefix="/new-feature", tags=["new-feature"])

@router.post("/action")
async def new_action(data: YourSchema):
    # Implementation
    return {"success": True}
```

2. **Register router** in `main.py`:
```python
from app.api.v2.new_feature import router as new_feature_router

app.include_router(new_feature_router, prefix="/api/v2")
```

3. **Add schema** in `app/models/schemas.py`:
```python
class YourSchema(BaseModel):
    field: str
```

### Using Cache

```python
from app.services.cache import cache_manager, cached

# Manual caching
value = await cache_manager.get("key")
await cache_manager.set("key", value, ttl=300)

# Decorator caching
@cached(ttl=300, key_prefix="predictions")
async def get_prediction():
    return compute_prediction()
```

### Database Queries

```python
from app.models.database import get_db
from sqlalchemy.orm import Session

@router.get("/items")
async def get_items(db: Session = Depends(get_db)):
    # Use optimized queries
    items = db.query(Model).limit(100).all()
    return items
```

## 🎨 Frontend Development

### Adding New Component

```typescript
// src/components/NewComponent.tsx
import React from 'react';

export const NewComponent: React.FC = () => {
  return <div>New Component</div>;
};
```

### Using State Management

```typescript
// Using Zustand
import { useGameStore } from '@/stores/gameStore';

const MyComponent = () => {
  const { shoes, addShoe } = useGameStore();
  // Use store
};
```

### API Calls

```typescript
// Using React Query
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

const MyComponent = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['shoes'],
    queryFn: () => api.get('/api/v2/shoes'),
  });
};
```

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/unit/test_predictor.py

# Run integration tests
pytest tests/integration/
```

### Frontend Tests

```bash
cd frontend

# Run unit tests
npm test

# Run with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e
```

### Writing Tests

**Backend:**
```python
# tests/unit/test_feature.py
import pytest
from app.core.feature import Feature

def test_feature():
    feature = Feature()
    result = feature.method()
    assert result == expected
```

**Frontend:**
```typescript
// src/components/__tests__/Component.test.tsx
import { render, screen } from '@testing-library/react';
import { Component } from '../Component';

test('renders component', () => {
  render(<Component />);
  expect(screen.getByText('Hello')).toBeInTheDocument();
});
```

## 🤝 Contributing

### Workflow

1. **Fork repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes**
4. **Write tests**
5. **Run tests**: Ensure all pass
6. **Commit**: `git commit -m "Add amazing feature"`
7. **Push**: `git push origin feature/amazing-feature`
8. **Create Pull Request**

### Commit Messages

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Formatting
- `refactor:` Code refactoring
- `test:` Tests
- `chore:` Maintenance

### Pull Request Checklist

- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All tests pass
- [ ] No linter errors

## 📝 Code Style

### Python

- Follow PEP 8
- Use type hints
- Docstrings cho functions
- Black formatting
- isort cho imports

```python
def function_name(param: str) -> dict:
    """
    Function description.
    
    Args:
        param: Parameter description
        
    Returns:
        Return description
    """
    return {}
```

### TypeScript

- Use TypeScript strict mode
- ESLint rules
- Prettier formatting
- Functional components

```typescript
interface Props {
  title: string;
}

export const Component: React.FC<Props> = ({ title }) => {
  return <div>{title}</div>;
};
```

## 🔗 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [API Documentation](./API_COMPLETE.md)

## 📞 Support

- GitHub Issues: For bugs và feature requests
- Discussions: For questions
- Email: For security issues

