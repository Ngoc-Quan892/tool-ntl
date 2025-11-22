.PHONY: test test-unit test-integration test-security test-performance test-coverage test-all help

help:
	@echo "Available test commands:"
	@echo "  make test              - Run all tests"
	@echo "  make test-unit         - Run unit tests only"
	@echo "  make test-integration  - Run integration tests only"
	@echo "  make test-security     - Run security tests only"
	@echo "  make test-performance  - Run performance tests only"
	@echo "  make test-coverage     - Run tests with coverage report"
	@echo "  make test-all          - Run all tests with coverage"

test:
	pytest

test-unit:
	pytest -m unit

test-integration:
	pytest -m integration

test-security:
	pytest -m security

test-performance:
	pytest -m performance

test-coverage:
	pytest --cov=app --cov-report=html --cov-report=term-missing

test-all:
	pytest --cov=app --cov-report=html --cov-report=term-missing --cov-report=json -v

lint:
	flake8 app tests --max-line-length=100 --exclude=__pycache__,migrations

format:
	black app tests
	isort app tests

