#!/usr/bin/env bash
# Smoke test for the TCG Scan FastAPI backend.
# Run this after starting the server to verify it responds correctly.

set -euo pipefail

BASE="${API_URL:-http://localhost:8001}"

echo "=== Smoke-testing API at $BASE ==="

# Health check
echo -n "GET /v1/health ... "
RESULT=$(curl -sf "$BASE/v1/health")
echo "$RESULT"
echo "$RESULT" | grep -q '"status":"ok"' || { echo "FAIL: unexpected response"; exit 1; }

echo ""
echo "All smoke tests passed."
