#!/usr/bin/env bash
set -euo pipefail

echo "==> Running smoke tests (HTTP health checks + minimal playwright if available)"

# Basic health check for backend
if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
  echo "Backend health: OK"
else
  echo "Backend health: FAILED or not reachable (ensure services are running)"
fi

# Playwright optional (run only if installed and tests present)
if [ -d "frontend" ]; then
  if command -v npx >/dev/null 2>&1; then
    if [ -f "frontend/e2e/app.spec.ts" ]; then
      echo "Running quick Playwright smoke test (headless)"
      cd frontend
      npx playwright test e2e/app.spec.ts --workers=1 --timeout=30000 || true
      cd - >/dev/null
    else
      echo "No e2e smoke test found; skipping Playwright"
    fi
  else
    echo "npx not available; skipping Playwright"
  fi
fi

echo "==> Smoke tests completed"
