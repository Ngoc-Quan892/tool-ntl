# Installation Guide

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (optional, recommended)

## Quick Start with Docker

```bash
docker-compose up --build
```

## Manual Installation

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Development Setup

Run the setup script:

```bash
bash scripts/setup_dev.sh
```

## Verification

- Backend: http://localhost:8000/docs
- Frontend: http://localhost:5173

## Troubleshooting

See README.md for common issues.

