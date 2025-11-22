# Frontend Tests

Comprehensive test suite for the Baccarat Predictor frontend.

## Test Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── __tests__/     # Component unit tests
│   └── test/
│       └── setup.ts       # Test setup
└── e2e/                   # End-to-end tests
    ├── app.spec.ts
    └── visual.spec.ts
```

## Running Tests

### Unit Tests (Vitest)
```bash
npm run test              # Run tests
npm run test:ui          # Run with UI
npm run test:coverage    # Run with coverage
```

### E2E Tests (Playwright)
```bash
npm run test:e2e         # Run E2E tests
npm run test:e2e:ui      # Run with UI
npm run test:visual      # Visual regression tests
```

## Test Categories

- **Component Tests**: Unit tests for React components
- **E2E Tests**: Full user flow tests
- **Visual Regression**: Screenshot comparison tests

## Coverage Target

- **Target**: >80% coverage
- Run: `npm run test:coverage`

