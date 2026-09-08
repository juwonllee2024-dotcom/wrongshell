# Security policy

## Scope

WrongShell is a local command translator. It should inspect text and print a
report only. It must not execute input, spawn a shell, make a network request,
write a file, or read the clipboard implicitly.

The parser is heuristic. It is not a sandbox, malware detector, or guarantee
that a command is safe. A `READY` report means only that no known blocker or
danger signal was found by this version.

## Reporting a vulnerability

Please do not include real credentials, private commands, or sensitive paths in
a public issue. Open a private GitHub security advisory when available, or
contact the repository owner through the GitHub profile. Include the smallest
non-sensitive reproduction, expected behavior, actual behavior, and version.

## Safe use

Inspect commands before running them. Review all paths, URLs, redirects, pipes,
and generated text yourself. Do not publish a report if its original command
contains secrets.
