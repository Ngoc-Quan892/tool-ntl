#!/usr/bin/env bash
set -euo pipefail

# Run Python detector and set outputs for GitHub Actions
PY=python3
if ! command -v $PY >/dev/null 2>&1; then
  PY=python
fi

RESULT=$( $PY scripts/ci/detect_major_bumps.py 2>/dev/null || echo '{"major_bump": true, "details": {"error":"detector-failed"}}' )

echo "Major bump detection result: $RESULT"
# Write to file for later steps
echo "$RESULT" > /tmp/major_bump_result.json

# Extract boolean value
MAJOR=$(echo "$RESULT" | $PY -c "import sys, json; print(json.load(sys.stdin)['major_bump'])")

# For GitHub Actions, print output format
if [ -n "${GITHUB_OUTPUT:-}" ]; then
  echo "major_bump=$MAJOR" >> $GITHUB_OUTPUT
fi

# Exit 0 always so workflow can continue; we use value to decide auto-merge
exit 0
