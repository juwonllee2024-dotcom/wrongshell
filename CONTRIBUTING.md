# Contributing to WrongShell

Thanks for helping make copied commands easier to review.

## Before opening a change

- Keep the runtime dependency-free and local-first.
- Never add command execution, implicit clipboard access, telemetry, or a
  network call to the MVP.
- Every new translation needs a focused test with the source and target shell
  stated explicitly.
- Unknown or ambiguous syntax should remain unchanged and receive a `MANUAL`
  result.

## Local checks

```powershell
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m build
python -m pip_audit --local
```

Please describe the user pain, the smallest behavior change, and the exact
verification commands in a pull request. Do not paste private command output.
