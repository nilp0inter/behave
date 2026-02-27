#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

for plan in plans/*/; do
    plan_name=$(basename "$plan")
    echo "=========================================="
    echo "  PLAN: $plan_name"
    echo "=========================================="
    python -m behave --params-config-dir "$plan" --no-capture features/
    echo
done
