#!/usr/bin/env bash
set -euo pipefail

echo "=== Running CIS Test Suites ==="

FAILED=0

echo ""
echo "--- Detection Service Tests ---"
cd services/detection
python -m pytest tests/ -v --tb=short || FAILED=1
cd ../..

echo ""
echo "--- Policy Engine Tests ---"
cd services/policy
python -m pytest tests/ -v --tb=short || FAILED=1
cd ../..

echo ""
echo "--- Review Queue Tests ---"
cd services/review
python -m pytest tests/ -v --tb=short || FAILED=1
cd ../..

echo ""
echo "--- Interceptor Tests ---"
cd services/interceptor
npm test || FAILED=1
cd ../..

echo ""
echo "--- Dashboard Tests ---"
cd services/dashboard
npm test || FAILED=1
cd ../..

echo ""
if [ $FAILED -eq 0 ]; then
    echo "=== All tests passed ==="
else
    echo "=== Some tests failed ==="
    exit 1
fi
