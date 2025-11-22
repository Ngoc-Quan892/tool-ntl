#!/usr/bin/env bash
set -euo pipefail

echo "==> Starting automated dependency upgrade"

# Backend: upgrade outdated pip packages and update requirements.txt
if [ -d "backend" ]; then
  echo "--> Upgrading backend Python packages"
  python -m pip install --upgrade pip setuptools wheel || true
  cd backend
  # list outdated packages
  outdated=$(pip list --outdated --format=freeze 2>/dev/null | cut -d'=' -f1 || true)
  if [ -n "$outdated" ]; then
    echo "Updating: $outdated"
    pip install -U $outdated || true
  else
    echo "No outdated Python packages found"
  fi
  echo "Freezing requirements to backend/requirements.txt"
  pip freeze > requirements.txt
  cd - >/dev/null
fi

# Frontend: use npm-check-updates to bump package.json and install
if [ -d "frontend" ]; then
  echo "--> Upgrading frontend Node packages"
  cd frontend
  # Install npm-check-updates and run
  npx --yes npm-check-updates -u || true
  npm install || true
  cd - >/dev/null
fi

# Stage modified files so that create-pull-request action can commit them
echo "==> Finished upgrading dependencies"

echo "Files changed:"
git status --porcelain || true
