#!/usr/bin/env bash
set -euo pipefail

echo "==> Running security scans"

# Python: run safety and bandit if available
if command -v pip >/dev/null 2>&1; then
  if pip show safety >/dev/null 2>&1; then
    echo "Running safety check for Python requirements"
    safety check || true
  else
    echo "Installing safety"
    pip install --user safety || true
    safety check || true
  fi
  if pip show bandit >/dev/null 2>&1; then
    echo "Running bandit scan"
    bandit -r backend/app || true
  else
    echo "Installing bandit"
    pip install --user bandit || true
    bandit -r backend/app || true
  fi
fi

# Node: run npm audit
if [ -d "frontend" ]; then
  echo "Running npm audit (frontend)"
  cd frontend
  npm ci || true
  npm audit --audit-level=moderate || true
  cd - >/dev/null
fi

echo "==> Security scans completed"
