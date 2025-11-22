# Architecture Specification

## System Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend    │────▶│  Database  │
│  (React)    │◀────│  (FastAPI)   │◀────│ (SQLite/   │
│             │     │              │     │  PostgreSQL)│
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │    Redis     │
                    │   (Cache)    │
                    └──────────────┘
```

## Component Overview

### Backend
- **API Layer**: FastAPI with versioned endpoints (v1, v2)
- **Core Engine**: Prediction algorithms and card counting
- **ML Module**: Machine learning models and training
- **Services**: Caching, metrics, logging

### Frontend
- **Components**: Modular React components
- **State Management**: Zustand store
- **API Client**: Axios with React Query
- **Real-time**: WebSocket integration

## Data Flow

1. User adds result → Frontend → Backend API
2. Backend updates predictor → Generates prediction
3. Prediction broadcast via WebSocket → Frontend updates
4. Roadmap recalculated → Frontend displays

## Deployment

- **Development**: Docker Compose
- **Production**: Kubernetes with Nginx ingress

