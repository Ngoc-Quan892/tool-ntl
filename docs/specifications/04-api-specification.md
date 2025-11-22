# API Specification

## Base URL

- Development: `http://localhost:8000/api`
- Production: `https://api.baccarat-predictor.pro/api`

## Endpoints

### v1 (Legacy)

- `POST /api/v1/add` - Add game result
- `GET /api/v1/predict` - Get prediction
- `GET /api/v1/history` - Get history
- `GET /api/v1/roadmap` - Get roadmaps
- `GET /api/v1/stats` - Get statistics

### v2 (Modern)

- `POST /api/v2/shoes` - Create/manage shoes
- `POST /api/v2/hands` - Add hand result
- `GET /api/v2/predictions` - Get predictions
- `GET /api/v2/analysis` - Get analysis
- `POST /api/v2/simulation` - Run simulation

## WebSocket

- `ws://localhost:8000/ws` - Real-time updates

## Authentication

Currently open. Future: JWT tokens.

## Rate Limiting

- 100 requests/minute per IP
- WebSocket: 10 connections per IP

