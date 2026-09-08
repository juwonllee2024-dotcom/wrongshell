# Product research

Date: 2026-09-08

## Problem observed

People copy commands from AI chats into a different shell than the answer
assumed. The failure is often not the package or the code; it is shell parsing,
command resolution, quoting, environment syntax, or a platform-specific shim.
The concrete trigger for this MVP was Windows PowerShell refusing to load
`npm.ps1` under an execution policy while `npm.cmd` remained available.

## Confirmed facts

- PowerShell parses input into tokens and chooses how to interpret them in
  expression or argument mode. See the [Microsoft parsing guide](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_parsing).
- ShellCheck documents that its advice depends on the target shell and asks
  users to identify that shell. See [ShellCheck SC2148](https://www.shellcheck.net/wiki/SC2148).
- Current public projects already cover model-based command review and
  pre-execution agent gatekeeping, including [command-review](https://github.com/ondrejnov/command-review),
  [sh-guard](https://github.com/aryanbhosale/sh-guard), and
  [Kintsugi](https://github.com/arrowassassin/kintsugi). That makes a generic
  “AI safety dashboard” a weak direction.
- A public discussion describes the repeated terminal-to-browser-to-AI
  copy/paste loop and another reports concern about secrets in agent context:
  [terminal/AI loop](https://www.reddit.com/r/commandline/comments/1sex1fu/removed/),
  [agent secrets](https://www.reddit.com/r/AskNetsec/comments/1vstngw/ai-coding-agents-are-writing-pasted-secrets-to/).

## Innovation hypothesis

If a tool shows a deterministic, shell-specific translation before the command
is run, Windows developers can recover from AI-generated Bash instructions
without weakening PowerShell policy or asking a model a second time.

## One difference

WrongShell is a **shell-compatibility lens**, not an agent gate, model wrapper,
or execution sandbox: every change is a small visible text diff with a reason,
and uncertainty becomes `MANUAL`.

## Seven-day experiment

Recruit ten developers who use both an AI chat and PowerShell or WSL. Give each
five real but non-sensitive command blocks. Measure:

1. whether they encounter a shell mismatch;
2. whether the report makes the mismatch understandable;
3. whether they use the translated command successfully;
4. whether they return for a second command block.

The survival signal is repeated successful use, not stars, clones, or a claimed
security score.

## Candidate review

| Candidate | Pain | Novelty | Build today | Shareability | Open source | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| WrongShell | 9 | 7 | 10 | 8 | 9 | selected |
| CommandGlass command storyboard | 9 | 5 | 10 | 7 | 9 | crowded safety/preflight space |
| TabHandoff cross-model transfer | 8 | 4 | 7 | 7 | 8 | commercial extensions and own relay overlap |
| PortLens port owner/reclaimer | 8 | 5 | 8 | 5 | 8 | basic utility overlaps existing local tools |

Scores are working hypotheses, not market measurements.
