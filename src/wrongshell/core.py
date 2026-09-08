"""Deterministic, non-executing shell translation for copied commands."""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from typing import Literal

Shell = Literal["powershell", "bash", "zsh", "posix", "cmd", "unknown"]
Severity = Literal["info", "warning", "danger"]
Status = Literal["ready", "review", "manual"]

_SHELLS = {"auto", "powershell", "bash", "zsh", "posix", "cmd", "unknown"}
_POSIX_SHELLS = {"bash", "zsh", "posix"}
_CLI_SHIMS = {"npm", "npx", "pnpm", "yarn"}


@dataclass(frozen=True, slots=True)
class Change:
    """One explainable text transformation or warning."""

    code: str
    severity: Severity
    title: str
    before: str
    after: str
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Segment:
    """A command-shaped segment split at visible shell boundaries."""

    line: int
    text: str
    executable: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CommandReport:
    """A reviewable report. WrongShell never runs the input."""

    original: str
    translated: str
    source_shell: Shell
    target_shell: Shell
    status: Status
    segments: tuple[Segment, ...]
    changes: tuple[Change, ...]
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "original": self.original,
            "translated": self.translated,
            "source_shell": self.source_shell,
            "target_shell": self.target_shell,
            "status": self.status,
            "segments": [segment.to_dict() for segment in self.segments],
            "changes": [change.to_dict() for change in self.changes],
            "blockers": list(self.blockers),
            "executed": False,
        }


def _validate_shell(value: str, option: str) -> Shell | Literal["auto"]:
    normalized = value.lower()
    if normalized not in _SHELLS:
        choices = ", ".join(sorted(_SHELLS - {"auto"}))
        raise ValueError(f"{option} must be one of: auto, {choices}")
    return normalized  # type: ignore[return-value]


def detect_target_shell(requested: str = "auto") -> Shell:
    """Choose a target shell from an explicit value or conservative local hints."""

    validated = _validate_shell(requested, "target shell")
    if validated != "auto":
        return validated

    if os.name == "nt":
        if os.environ.get("PSModulePath") or os.environ.get("WT_SESSION"):
            return "powershell"
        return "cmd"

    shell = os.environ.get("SHELL", "").lower()
    if shell.endswith("/zsh"):
        return "zsh"
    if shell.endswith("/bash"):
        return "bash"
    return "posix"


def guess_source_shell(command: str) -> Shell:
    """Guess only from visible syntax; unknown input is treated as POSIX-like."""

    if re.search(r"(?im)^\s*(?:\$env:|Get-[A-Za-z]+|Set-[A-Za-z]+|Remove-[A-Za-z]+)", command):
        return "powershell"
    if re.search(r"(?im)^\s*(?:export|source|sudo|rm|cp|mv|mkdir\s+-p)\b", command):
        return "bash"
    if re.search(r"(?im)^\s*(?:@echo\s+off|set\s+[A-Za-z_][A-Za-z0-9_]*=)", command):
        return "cmd"
    return "posix"


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _powershell_string(value: str) -> str:
    escaped = value.replace("`", "``").replace('"', '`"')
    return f'"{escaped}"'


def _replace_prefix(line: str, mapping: dict[str, str]) -> tuple[str, str, str] | None:
    pattern = r"^(?P<indent>\s*)(?P<command>[A-Za-z][A-Za-z0-9_.-]*)(?P<rest>(?:\s+.*)?)$"
    match = re.match(pattern, line)
    if match is None:
        return None
    command = match.group("command")
    replacement = mapping.get(command.lower())
    if replacement is None:
        return None
    new_line = f"{match.group('indent')}{replacement}{match.group('rest')}"
    return new_line, command, replacement


def _translate_to_powershell(command: str, source_shell: Shell) -> tuple[str, list[Change]]:
    changes: list[Change] = []
    lines: list[str] = []
    posix_mapping = {
        "rm": "Remove-Item",
        "cp": "Copy-Item",
        "mv": "Move-Item",
        "cat": "Get-Content",
        "grep": "Select-String",
        "which": "Get-Command",
        "pwd": "Get-Location",
    }

    for line in command.splitlines():
        current = line
        export_match = re.match(
            r"^(?P<indent>\s*)export\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)="
            r"(?P<value>[^;&|]*)(?P<tail>\s*(?:(?:&&|\|\||[;|]).*)?)$",
            current,
        )
        if export_match:
            value = _unquote(export_match.group("value").strip())
            replacement = (
                f"{export_match.group('indent')}$env:{export_match.group('name')}="
                f"{_powershell_string(value)}{export_match.group('tail')}"
            )
            changes.append(
                Change(
                    code="POSIX-EXPORT",
                    severity="info",
                    title="Make the environment assignment explicit",
                    before=current.strip(),
                    after=replacement.strip(),
                    reason="PowerShell uses $env:NAME instead of the POSIX export syntax.",
                )
            )
            current = replacement

        rm_force = re.match(r"^(?P<indent>\s*)rm\s+-rf\s+(?P<path>.+)$", current)
        if rm_force:
            replacement = (
                f"{rm_force.group('indent')}Remove-Item -Recurse -Force {rm_force.group('path')}"
            )
            changes.append(
                Change(
                    code="POSIX-DELETE",
                    severity="danger",
                    title="Translate recursive deletion",
                    before=current.strip(),
                    after=replacement.strip(),
                    reason="This keeps the destructive intent; review the path before running it.",
                )
            )
            current = replacement
        elif source_shell in _POSIX_SHELLS:
            prefix_change = _replace_prefix(current, posix_mapping)
            if prefix_change:
                current, before_command, after_command = prefix_change
                changes.append(
                    Change(
                        code="POSIX-COMMAND",
                        severity="info",
                        title=f"Translate {before_command} for PowerShell",
                        before=before_command,
                        after=after_command,
                        reason="The command name is expressed using a PowerShell cmdlet.",
                    )
                )

        shim_pattern = r"(^|[;&|]\s*)(npm|npx|pnpm|yarn)(?!\.cmd)(?=\s|$)"

        def replace_shim(match: re.Match[str]) -> str:
            tool = match.group(2)
            return f"{match.group(1)}{tool}.cmd"

        replaced = re.sub(shim_pattern, replace_shim, current, flags=re.IGNORECASE)
        if replaced != current:
            changes.append(
                Change(
                    code="PS-NPM-SHIM",
                    severity="info",
                    title="Use the Windows command shim",
                    before=current.strip(),
                    after=replaced.strip(),
                    reason=(
                        "PowerShell can resolve npm.ps1 first. The .cmd shim avoids changing "
                        "execution policy just to run a package command."
                    ),
                )
            )
            current = replaced

        lines.append(current)

    return "\n".join(lines), changes


def _translate_to_posix(command: str, source_shell: Shell) -> tuple[str, list[Change]]:
    changes: list[Change] = []
    lines: list[str] = []
    reverse_mapping = {
        "Get-ChildItem": "ls",
        "Get-Content": "cat",
        "Get-Location": "pwd",
        "Get-Command": "which",
        "Copy-Item": "cp",
        "Move-Item": "mv",
    }

    for line in command.splitlines():
        current = line
        env_match = re.match(
            r"^(?P<indent>\s*)\$env:(?P<name>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*)$", current
        )
        if env_match:
            value = env_match.group("value").strip()
            value_text = value if value else '""'
            replacement = (
                f"{env_match.group('indent')}export {env_match.group('name')}={value_text}"
            )
            changes.append(
                Change(
                    code="PS-ENV",
                    severity="info",
                    title="Make the environment assignment portable",
                    before=current.strip(),
                    after=replacement.strip(),
                    reason="POSIX shells use export NAME=value for environment variables.",
                )
            )
            current = replacement

        remove_match = re.match(
            r"^(?P<indent>\s*)Remove-Item\s+-Recurse\s+-Force\s+(?P<path>.+)$",
            current,
            flags=re.IGNORECASE,
        )
        if remove_match:
            replacement = f"{remove_match.group('indent')}rm -rf {remove_match.group('path')}"
            changes.append(
                Change(
                    code="PS-DELETE",
                    severity="danger",
                    title="Translate recursive deletion",
                    before=current.strip(),
                    after=replacement.strip(),
                    reason="This keeps the destructive intent; review the path before running it.",
                )
            )
            current = replacement
        else:
            prefix_change = _replace_prefix(current, reverse_mapping)
            if prefix_change:
                current, before_command, after_command = prefix_change
                changes.append(
                    Change(
                        code="PS-COMMAND",
                        severity="info",
                        title=f"Translate {before_command} for POSIX",
                        before=before_command,
                        after=after_command,
                        reason="The command name is expressed using a common POSIX utility.",
                    )
                )

        shim_pattern = r"(^|[;&|]\s*)(npm|npx|pnpm|yarn)\.cmd(?![A-Za-z0-9_.-])"

        def remove_shim(match: re.Match[str]) -> str:
            return f"{match.group(1)}{match.group(2)}"

        replaced = re.sub(shim_pattern, remove_shim, current, flags=re.IGNORECASE)
        if replaced != current:
            changes.append(
                Change(
                    code="PS-NPM-SHIM-REVERSE",
                    severity="info",
                    title="Remove the Windows-only command shim",
                    before=current.strip(),
                    after=replaced.strip(),
                    reason="POSIX shells normally invoke the package-manager command directly.",
                )
            )
            current = replaced

        lines.append(current)

    return "\n".join(lines), changes


def _segments(command: str) -> tuple[Segment, ...]:
    result: list[Segment] = []
    separators = re.compile(r"\s*(?:&&|\|\||[;|])\s*")
    for line_number, line in enumerate(command.splitlines(), start=1):
        for piece in separators.split(line):
            text = piece.strip()
            if not text:
                continue
            executable_match = re.match(r"(?:[.&!]\s*)?(?:[\"']([^\"']+)[\"']|(\S+))", text)
            executable = (
                "unknown"
                if executable_match is None
                else (executable_match.group(1) or executable_match.group(2))
            )
            result.append(Segment(line=line_number, text=text, executable=executable))
    return tuple(result)


def _risk_changes(command: str) -> tuple[list[Change], list[str]]:
    changes: list[Change] = []
    blockers: list[str] = []
    patterns: tuple[tuple[str, str, Severity, str, str], ...] = (
        (
            r"(?i)\brm\s+-rf\b|\bRemove-Item\b[^\n]*(?:-Recurse|-Force)",
            "destructive filesystem deletion",
            "danger",
            "Destructive operation",
            "Confirm the exact path and whether a backup exists.",
        ),
        (
            r"(?i)\bgit\s+(?:reset\s+--hard|clean\s+-[^\n]*f)\b",
            "destructive Git cleanup",
            "danger",
            "Destructive Git operation",
            "Confirm the worktree and uncommitted changes before running it.",
        ),
        (
            r"(?i)\b(?:curl|wget|Invoke-WebRequest|iwr)\b[^\n]*(?:\||;)\s*(?:bash|sh|zsh|iex|Invoke-Expression)\b",
            "remote content piped into execution",
            "danger",
            "Remote-to-execution boundary",
            "Download and inspect the content separately before executing anything.",
        ),
        (
            r"(?i)(?:\.env(?:\b|/)|~[/\\]\.ssh|\.aws[/\\]credentials|\b(?:printenv|env)\b)",
            "credential-like or environment data access",
            "warning",
            "Sensitive-data access signal",
            "Check whether the command can expose credentials in its output.",
        ),
        (
            r"(?i)\b(?:curl|wget|Invoke-WebRequest|iwr)\b",
            "network request",
            "warning",
            "Network boundary",
            "Confirm the destination and what data leaves the machine.",
        ),
    )
    for pattern, code_suffix, severity, title, reason in patterns:
        if re.search(pattern, command):
            code = f"REVIEW-{re.sub(r'[^A-Z0-9]+', '-', code_suffix.upper()).strip('-')}"
            changes.append(
                Change(
                    code=code,
                    severity=severity,
                    title=title,
                    before=code_suffix,
                    after="review required",
                    reason=reason,
                )
            )

    if re.search(r"\$\([^\n]*\)|`[^`\n]+`", command):
        blockers.append(
            "Command substitution is present; WrongShell will not guess its meaning across shells."
        )
    if re.search(r"(?m)^\s*(?:eval|Invoke-Expression|iex)\b", command, flags=re.IGNORECASE):
        blockers.append("Dynamic evaluation is present; translate it manually.")
    return changes, blockers


def inspect_command(
    command: str,
    *,
    source_shell: str = "auto",
    target_shell: str = "auto",
) -> CommandReport:
    """Translate a command without executing it and return an explainable report."""

    original = command.strip("\r\n")
    if not original.strip():
        raise ValueError("command input is empty")

    source_value = _validate_shell(source_shell, "source shell")
    source: Shell = guess_source_shell(original) if source_value == "auto" else source_value
    target = detect_target_shell(target_shell)

    if target == "powershell":
        translated, translation_changes = _translate_to_powershell(original, source)
    elif target in _POSIX_SHELLS:
        translated, translation_changes = _translate_to_posix(original, source)
    else:
        translated, translation_changes = original, []

    risk_changes, blockers = _risk_changes(original)
    changes = tuple(translation_changes + risk_changes)
    if blockers:
        status: Status = "manual"
    elif any(change.severity == "danger" for change in changes):
        status = "review"
    else:
        status = "ready"

    return CommandReport(
        original=original,
        translated=translated,
        source_shell=source,
        target_shell=target,
        status=status,
        segments=_segments(original),
        changes=changes,
        blockers=tuple(blockers),
    )
