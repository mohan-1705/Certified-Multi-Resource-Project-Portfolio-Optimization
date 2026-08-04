#!/usr/bin/env bash
set -euo pipefail

PYTHON=${PYTHON:-python}

# Generate the deterministic instance
$PYTHON data/generate_instance.py

# Solve the task and emit portfolio.json and certificate.json
$PYTHON solver.py

# Verify the generated portfolio and certificate
$PYTHON verify.py portfolio.json certificate.json

# Run the unit tests for verifier coverage
$PYTHON -m pytest tests/test_verify.py -q
