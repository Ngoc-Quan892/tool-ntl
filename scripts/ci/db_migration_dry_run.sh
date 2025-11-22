#!/usr/bin/env bash
set -euo pipefail

echo "==> Running DB migration dry-run (generate SQL with alembic)"

if [ -d "backend" ]; then
  cd backend
  if [ -f "alembic.ini" ]; then
    echo "Generating SQL for alembic upgrade head"
    alembic upgrade --sql head > /tmp/alembic_upgrade.sql || true
    echo "SQL generated at /tmp/alembic_upgrade.sql"
  else
    echo "No alembic.ini found in backend; skipping"
  fi
  cd - >/dev/null
else
  echo "No backend directory; skipping migration dry-run"
fi

echo "==> Migration dry-run completed"
