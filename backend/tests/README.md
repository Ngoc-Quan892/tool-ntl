# Backend Tests

Comprehensive test suite for the Baccarat Predictor backend.

## Test Structure

```
tests/
├── unit/              # Unit tests for individual modules
│   ├── test_statistics.py
│   ├── test_ml.py
│   ├── test_engine.py
│   └── test_predictor.py
├── integration/       # Integration tests
│   ├── test_api_integration.py
│   └── test_websocket.py
├── security/          # Security tests
│   └── test_security.py
└── performance/      # Performance and load tests
    └── test_load.py
```

## Running Tests

### All Tests
```bash
pytest
```

### By Category
```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# Security tests
pytest -m security

# Performance tests
pytest -m performance

# Skip slow tests
pytest -m "not slow"
```

### With Coverage
```bash
pytest --cov=app --cov-report=html
```

### Specific Test File
```bash
pytest tests/unit/test_statistics.py
```

## Coverage Target

- **Target**: >80% coverage
- **Current**: Check with `pytest --cov=app --cov-report=term-missing`

## Test Categories

- **Unit Tests**: Fast, isolated tests for individual functions/classes
- **Integration Tests**: Test API endpoints and database interactions
- **Security Tests**: SQL injection, XSS, input validation
- **Performance Tests**: Response times, concurrent requests, memory usage

## Writing New Tests

1. Place tests in appropriate directory
2. Use descriptive test names
3. Add appropriate markers (`@pytest.mark.unit`, etc.)
4. Aim for >80% coverage
5. Test both success and error cases

