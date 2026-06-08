"""CLI entry point for diagram-sanitizer — powered by Click."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from typing import TextIO

import click

from diagram_sanitizer import __version__, sanitize


def _read_input(file_arg: str | None) -> str:
    """Read diagram text from a file argument or stdin.

    Follows the spec (AC-012):
    - ``-`` → read from stdin
    - ``None`` + stdin is a pipe → read from stdin
    - ``None`` + stdin is a terminal → trigger help (handled by Click)
    - any other string → open as file path
    """
    if file_arg == "-":
        return sys.stdin.read()
    if file_arg is not None:
        with open(file_arg, encoding="utf-8", errors="replace") as f:
            return f.read()
    # file_arg is None — Click will have already shown help if stdin is a TTY,
    # but if we reach here stdin is a pipe
    return sys.stdin.read()


def _write_output(
    text: str, file_arg: str | None, in_place: bool, output: TextIO | None = None
) -> None:
    """Write corrected diagram to the appropriate destination."""
    if in_place and file_arg and file_arg != "-":
        # Atomic file replacement (FR-024)
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(file_arg) or ".",
            prefix=".das-",
            suffix=".tmp",
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmpf:
                tmpf.write(text)
            os.replace(tmp_path, file_arg)
        except Exception:
            os.unlink(tmp_path)
            raise
    elif output:
        output.write(text)
    else:
        click.echo(text)


def _format_report(report: dict, fmt: str) -> str:
    """Serialize the report dict to the requested format."""
    if fmt == "json":
        return json.dumps(report, indent=2, ensure_ascii=False)
    # text format
    lines: list[str] = []
    lines.append(f"Status: {report['status'].upper()}")
    lines.append(f"Issues: {len(report['issues'])}")
    lines.append("")
    for i, issue in enumerate(report["issues"], 1):
        lines.append(
            f"  [{i}] {issue['severity'].upper()}: {issue['type']}"
        )
        lines.append(f"      Line {issue['line']}, Col {issue['col']}")
        if issue.get("end_line"):
            loc = f" → Line {issue['end_line']}"
            if issue.get("end_col"):
                loc += f", Col {issue['end_col']}"
            lines.append(f"      {loc}")
        lines.append(f"      {issue['message']}")
        if issue.get("fixable"):
            lines.append(f"      [FIXABLE] {issue.get('fix_suggestion', '')}")
        lines.append("")
    if report.get("corrected_diagram"):
        lines.append("--- Corrected Diagram ---")
        lines.append(report["corrected_diagram"])
    return "\n".join(lines)


def _exit_with_status(status: str) -> None:
    """Exit with the appropriate code per FR-023."""
    if status == "error":
        sys.exit(2)
    elif status == "warning":
        sys.exit(1)
    else:
        sys.exit(0)


@click.command()
@click.argument("file", required=False, default=None)
@click.option(
    "--check", is_flag=True,
    help="Exit non-zero if issues exist (no output).",
)
@click.option(
    "--fix", is_flag=True,
    help="Output corrected diagram to stdout.",
)
@click.option(
    "--in-place", is_flag=True,
    help="Overwrite input file with corrected diagram (requires --fix).",
)
@click.option(
    "--format", "output_format",
    type=click.Choice(["json", "text"]),
    default="json",
    help="Output format (default: json).",
)
@click.option(
    "--tab-width", type=int, default=4,
    help="Spaces per tab (default: 4).",
)
@click.version_option(version=__version__, prog_name="diagram-sanitizer")
def main(
    file: str | None,
    check: bool,
    fix: bool,
    in_place: bool,
    output_format: str,
    tab_width: int,
) -> None:
    """Validate and auto-correct structural errors in ASCII diagrams.

    Reads from FILE or stdin (use '-' to explicitly read from stdin).
    Outputs a JSON report by default.
    """
    # Validate flag combinations
    if in_place and not fix:
        raise click.UsageError("--in-place requires --fix")
    if in_place and (file is None or file == "-"):
        raise click.UsageError("--in-place requires a file path (not stdin)")

    diagram = _read_input(file)

    # Determine mode from flags
    if check:
        mode = "check"
    elif fix:
        mode = "fix"
    else:
        mode = "auto"

    # Run the sanitizer engine
    report = sanitize(diagram, {"tab_width": tab_width, "mode": mode})

    # --check mode: exit code only, no output (FR-023)
    if check:
        _exit_with_status(report["status"])

    # --fix mode: output corrected diagram (or null if none)
    if fix:
        corrected = report.get("corrected_diagram")
        if corrected:
            _write_output(corrected, file, in_place)
        _exit_with_status(report["status"])

    # Default: output report
    formatted = _format_report(report, output_format)
    click.echo(formatted)
    _exit_with_status(report["status"])


if __name__ == "__main__":
    main()
