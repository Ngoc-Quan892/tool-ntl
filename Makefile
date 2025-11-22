.PHONY: help install dev test clean build docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install    - Install all dependencies"
	@echo "  make dev        - Start development servers"
	@echo "  make test       - Run all tests"
	@echo "  make build      - Build production artifacts"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make docker-up  - Start Docker containers"
	@echo "  make docker-down - Stop Docker containers"

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev:
	docker-compose up

test:
	cd backend && pytest
	cd frontend && npm test

build:
	cd backend && python -m build
	cd frontend && npm run build

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	rm -rf backend/dist backend/build
	rm -rf frontend/dist frontend/node_modules/.vite

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

