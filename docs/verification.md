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
| diff whitespace check | pass: `git diff --cached --check` |
| package hash | pass: SHA-256 recorded below |

## Published build

The following artifacts were built from source commit
`2115033682461c535daf04f1e9f6e93c7a8681f6` and published in
[v0.1.0](https://github.com/juwonllee2024-dotcom/wrongshell/releases/tag/v0.1.0):

```text
wrongshell-0.1.0-py3-none-any.whl  5d0669ecfaaf4c3cc12c754945d0c71d2d30bd1e5e6d8056dccd6ec45e72998e
wrongshell-0.1.0.tar.gz            15aa6a56866f68286702ecfbc19ee9f902ee82be807bd1cea7ad2b2099bfe6f8
```

## Remote verification

- GitHub Actions matrix: [run 34247604100](https://github.com/juwonllee2024-dotcom/wrongshell/actions/runs/34247604100)
- Release: [WrongShell v0.1.0](https://github.com/juwonllee2024-dotcom/wrongshell/releases/tag/v0.1.0)

## Manual scenario

Input: `npm ci` with target `powershell`.

Expected: `npm.cmd ci`, a `PS-NPM-SHIM` explanation, status `READY`, and no
process execution. A destructive example must return `REVIEW`; unknown command
substitution must return `MANUAL`.
