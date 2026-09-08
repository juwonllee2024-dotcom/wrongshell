"""Command-line interface for WrongShell."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from .core import CommandReport, inspect_command


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wrongshell",
        description="Translate a copied command for your shell. Never executes input.",
    )
    parser.add_argument(
        "command",
        nargs="*",
        help="command text; omit it to read stdin",
    )
    parser.add_argument("--file", type=Path, help="read command text from a local file")
    parser.add_argument(
        "--from-shell",
        default="auto",
        choices=["auto", "powershell", "bash", "zsh", "posix", "cmd", "unknown"],
        help="source shell syntax (default: auto)",
    )
    parser.add_argument(
        "--shell",
        "--to-shell",
        dest="target_shell",
        default="auto",
        choices=["auto", "powershell", "bash", "zsh", "posix", "cmd", "unknown"],
        help="target shell; auto detects the local shell",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="output format (default: text)",
    )
    return parser


def _read_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    command_parts = list(args.command)
    if command_parts and command_parts[0].lower() == "inspect":
        command_parts = command_parts[1:]
    if args.file and command_parts:
        parser.error("use either a command or --file, not both")
    if args.file:
        try:
            path = cast(Path, args.file)
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            parser.error(f"cannot read {args.file}: {exc}")
    if command_parts:
        return " ".join(command_parts)
    return sys.stdin.read()


def _shell_name(value: str) -> str:
    return {
        "powershell": "PowerShell",
        "bash": "Bash",
        "zsh": "Zsh",
        "posix": "POSIX shell",
        "cmd": "Command Prompt",
        "unknown": "Unknown shell",
    }.get(value, value)


def _format_text(report: CommandReport) -> str:
    lines = [
        "WRONGSHELL command report",
        f"Status: {report.status.upper()}",
        f"Source: {_shell_name(report.source_shell)}",
        f"Target: {_shell_name(report.target_shell)}",
        "",
        "Original:",
        report.original,
        "",
        "Translated (review before running):",
        report.translated,
    ]
    if report.segments:
        lines.extend(["", "Visible command segments:"])
        lines.extend(
            f"  line {segment.line}: {segment.executable} - {segment.text}"
            for segment in report.segments
        )
    if report.changes:
        lines.extend(["", "Why:"])
        lines.extend(
            f"  [{change.severity.upper()}] {change.code}: {change.reason}"
            for change in report.changes
        )
    if report.blockers:
        lines.extend(["", "Manual review required:"])
        lines.extend(f"  - {blocker}" for blocker in report.blockers)
    lines.extend(["", "Boundary: WrongShell never executes input or calls a network."])
    return "\n".join(lines)


def _format_markdown(report: CommandReport) -> str:
    lines = [
        "# WrongShell report",
        "",
        f"- Status: `{report.status}`",
        f"- Source: `{report.source_shell}`",
        f"- Target: `{report.target_shell}`",
        "",
        "## Original",
        "",
        "```text",
        report.original,
        "```",
        "",
        "## Translated",
        "",
        "```text",
        report.translated,
        "```",
    ]
    if report.changes:
        lines.extend(["", "## Review notes", ""])
        lines.extend(
            f"- **{change.code}** ({change.severity}): {change.reason}" for change in report.changes
        )
    if report.blockers:
        lines.extend(["", "## Manual review required", ""])
        lines.extend(f"- {blocker}" for blocker in report.blockers)
    lines.extend(["", "> WrongShell never executes input or calls a network."])
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    command = _read_command(args, parser)
    try:
        report = inspect_command(
            command,
            source_shell=args.from_shell,
            target_shell=args.target_shell,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    if args.format == "json":
        output = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    elif args.format == "markdown":
        output = _format_markdown(report)
    else:
        output = _format_text(report)
    print(output)
    return 0 if report.status == "ready" else 1
