# Copernicus Podcast API Test Suite

## Overview

This directory contains the test suite for the Copernicus Podcast API. The tests are organized into unit tests and integration tests.

## Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── README.md               # This file
├── unit/                   # Unit tests
│   ├── __init__.py
│   └── test_canonical_service.py
├── integration/            # Integration tests
│   └── __init__.py
└── test_admin_router.py    # Admin router endpoint tests
```

## Running Tests

### Run all tests
```bash
cd cloud-run-backend
pytest
```

### Run unit tests only
```bash
pytest tests/unit/
```

### Run integration tests only
```bash
pytest tests/integration/
```

### Run with verbose output
```bash
pytest -v
```

### Run specific test file
```bash
pytest tests/unit/test_canonical_service.py
```

### Run specific test
```bash
pytest tests/unit/test_canonical_service.py::TestCanonicalService::test_is_canonical_filename_feature
```

## Test Coverage

### Unit Tests
- **CanonicalService**: Tests for canonical filename generation and validation
  - Feature format validation (ever-{category}-{6 digits})
  - News format validation (news-{category}-{date}-{serial})
  - Category extraction

### Integration Tests
- **Admin Router**: Tests for admin API endpoints
  - Endpoint structure validation
  - Authentication requirements
  - Router registration

## Adding New Tests

1. **Unit Tests**: Add to `tests/unit/` directory
   - Test individual service methods
   - Use mocks for external dependencies
   - Keep tests fast and isolated

2. **Integration Tests**: Add to `tests/integration/` directory
   - Test API endpoints
   - Test service interactions
   - Use TestClient for FastAPI endpoints

3. **Fixtures**: Add shared fixtures to `conftest.py`
   - Mock database clients
   - Mock GCS clients
   - Sample data fixtures

## Test Markers

Tests can be marked with:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow running tests

Run marked tests:
```bash
pytest -m unit
pytest -m integration
pytest -m "not slow"
```

## Configuration

Test configuration is in `pytest.ini` at the project root.

## Dependencies

Test dependencies are in `requirements.txt`:
- pytest
- pytest-asyncio
- pytest-mock
- httpx

## Notes

- Tests use mocks for external services (Firestore, GCS, etc.)
- No actual database connections required for unit tests
- Integration tests may require mock services or test environment

