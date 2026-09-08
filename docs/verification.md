# Verification record

Date: 2026-09-08

## Test-first evidence

1. RED: `python -m unittest discover -s tests -v` failed before implementation
   because the `wrongshell` package did not exist.
2. GREEN: the same command passed after the first implementation.

## Required checks

The final commands and results are recorded below after a fresh run:

| Check | Result |
| --- | --- |
| bytecode compile | pass |
| unit/integration tests | pass: 9 tests |
| CLI smoke test | pass: `npm ci` -> `npm.cmd ci` |
| typecheck | pass: mypy strict |
| lint | pass: ruff check |
| format check | pass: ruff format --check |
| wheel/sdist build | pass: wheel and sdist |
| dependency audit | pass: no known vulnerabilities |
| diff whitespace check | recorded before commit |
| package hash | recorded in the release follow-up |

## Manual scenario

Input: `npm ci` with target `powershell`.

Expected: `npm.cmd ci`, a `PS-NPM-SHIM` explanation, status `READY`, and no
process execution. A destructive example must return `REVIEW`; unknown command
substitution must return `MANUAL`.
