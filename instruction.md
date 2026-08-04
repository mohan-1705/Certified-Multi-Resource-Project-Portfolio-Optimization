# Certified Multi-Resource Project Portfolio Optimization

## Task Overview

This task requires solving a deterministic project portfolio optimization instance with multiple resource constraints, project dependencies, and pairwise synergies/conflicts. The solver must produce both a portfolio and an optimality certificate. The verifier independently validates the portfolio and the certificate.

## Required Files

- `solver.py`: builds and solves the optimization model, writes `portfolio.json` and `certificate.json`
- `verify.py`: verifies that `portfolio.json` and `certificate.json` are valid and the portfolio is optimal
- `data/instance.json`: deterministic instance data
- `tests/test_verify.py`: unit tests for verifier and certificate validation

## Running the Task

Execute the task by running:

```bash
bash solve.sh
```

This runs the instance generator, solver, verifier, and verifier unit tests.

## Validation

The task is complete if:

- `data/instance.json` is generated correctly
- `solver.py` produces `portfolio.json` and `certificate.json`
- `verify.py portfolio.json certificate.json` prints `VERIFIED`
- `python -m pytest tests/test_verify.py -q` passes

## Notes

The included `Dockerfile` builds a container that installs dependencies and executes `solve.sh` as the entrypoint.
