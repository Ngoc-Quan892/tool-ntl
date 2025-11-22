#!/bin/bash
# Development environment setup script

set -e

echo "🚀 Setting up Baccarat Predictor Pro development environment..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 20+"
    exit 1
fi

# Backend setup
echo "📦 Setting up backend..."
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
cd ..

# Frontend setup
echo "📦 Setting up frontend..."
cd frontend
npm install
cd ..

echo "✅ Development environment ready!"
echo ""
echo "To start development:"
echo "  Backend:  cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
echo ""
echo "Or use Docker: docker-compose up"

