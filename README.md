# 🎰 Baccarat Predictor Pro

Advanced Baccarat analysis tool with ML prediction, card counting, and professional casino roadmaps.

## ✨ Features

- 🧠 **Multi-algorithm Ensemble Prediction** - Pattern detection, Bayesian inference, and card counting
- 📊 **4 Professional Roadmaps** - Big Road, Big Eye Boy, Small Road, Cockroach Pig
- 🃏 **Real Card Counting** - EOR (Effect of Removal) values for accurate edge calculation
- 📈 **Real-time Updates** - WebSocket for live predictions and alerts
- 🚀 **Mass Simulation** - Test strategies with 10,000+ shoes
- 💾 **Data Persistence** - SQLite/PostgreSQL with export capabilities
- 🎨 **Modern UI** - Dark casino-themed interface with animations

## 🚀 Quick Start

### With Docker (Recommended)

```bash
docker-compose up --build
```

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000/docs

### Manual Setup

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## 📚 Documentation

- [Installation Guide](docs/user-guide/installation.md)
- [Quick Start](docs/user-guide/quick-start.md)
- [Advanced Usage](docs/user-guide/advanced-usage.md)
- [API Documentation](docs/api/README.md)
- [Architecture](docs/specifications/02-architecture.md)

## 🧪 Testing

### Test Structure

```
backend/tests/
├── conftest.py                # Shared fixtures & utilities
├── test_fixtures.py           # Fixture validation
├── test_database.py           # Database contract tests
├── test_model_training.py     # ML training validation
├── test_predictions.py        # Prediction quality/correctness
├── test_integration.py        # Service-level integrations
├── performance/test_performance.py   # Performance & stress
└── test_final_integration.py  # Production-style scenarios
```

### Running Tests

**Quick suite (backend):**
```bash
cd backend
pytest tests/ -v
```

**Coverage run:**
```bash
cd backend
pytest tests/ --cov=app --cov-report=html
```

**Performance focus:**
```bash
cd backend
pytest tests/performance/test_performance.py -v --duration=10
```

**Integration only:**
```bash
cd backend
pytest tests/test_integration.py tests/test_final_integration.py -v
```

Frontend tests remain unchanged:
```bash
cd frontend
npm test
```

### Test Markers

- `@pytest.mark.asyncio` – async tests
- `@pytest.mark.slow` – long-running suites
- `@pytest.mark.integration` – integration/system coverage
- `@pytest.mark.unit` – traditional unit tests

### Coverage Goals

- **Overall**: 85‑95%
- **Core Services**: ≥90%
- **Database Layer**: ≥85%
- **Utils**: ≥85%

### Performance Benchmarks

- Training: < 30s for ≥100K records
- Prediction latency: < 100ms average (<200ms P95)
- Throughput: > 100 req/s under concurrency
- Memory: < 500MB RSS during training spikes

## 📊 Project Status

See [PROGRESS.md](PROGRESS.md) for detailed implementation progress.

## 🛠️ Development

```bash
# Setup development environment
bash scripts/setup_dev.sh

# Check progress
python scripts/show_progress.py

# Resume from checkpoint
python scripts/resume.py
```

## 📖 API Endpoints

### Core Endpoints

- `POST /api/add` - Add game result
- `GET /api/predict` - Get current prediction
- `GET /api/history` - Get result history
- `GET /api/roadmap` - Get all roadmaps
- `GET /api/stats` - Get session statistics
- `POST /api/simulate` - Run simulation
- `POST /api/reset` - Reset session

### WebSocket

- `ws://localhost:8000/ws` - Real-time prediction updates

## 🏗️ Project Structure

```
baccarat-predictor-pro/
├── backend/          # FastAPI backend
├── frontend/         # React + TypeScript frontend
├── docs/             # Documentation
├── ml-training/      # ML model training
├── deployment/       # Docker & K8s configs
└── scripts/          # Utility scripts
```

## 🔧 Configuration

Copy `backend/.env.example` to `backend/.env` and configure:

- `DATABASE_URL` - Database connection string
- `DEBUG` - Set to `False` in production
- `CORS_ORIGINS` - Allowed frontend origins

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🎯 Roadmap

- [x] Phase 0: Project structure and setup
- [ ] Phase 1: Core prediction engine
- [ ] Phase 2: Frontend implementation
- [ ] Phase 3: ML model integration
- [ ] Phase 4: Production deployment

## 📞 Support

For issues and questions, please open a GitHub issue.

---

**Built with ❤️ for Baccarat analysis**
