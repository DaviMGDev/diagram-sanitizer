"""CLI for ascii-sanitizer."""

from __future__ import annotations

import json
import sys

import click

from . import sanitize
from .report import format_text


@click.command()
@click.argument("file", type=click.Path(dir_okay=False), required=False)
@click.option("--check", is_flag=True, help="Exit non-zero if issues exist (no output)")
@click.option("--fix", is_flag=True, help="Output corrected diagram to stdout")
@click.option("--in-place", is_flag=True, help="Overwrite input file with corrected diagram")
@click.option(
    "--format", "output_format",
    type=click.Choice(["json", "text"]),
    default="json",
    help="Output format (default: json)",
)
@click.option(
    "--tab-width", type=int, default=4,
    help="Tab replacement width (default: 4)",
)
def main(
    file: str | None,
    check: bool,
    fix: bool,
    in_place: bool,
    output_format: str,
    tab_width: int,
) -> None:
    """Validate and auto-fix structural errors in ASCII diagrams.

    Reads from FILE or stdin. Outputs a JSON report by default.
    """
    # Read input: file path, "-" for stdin, or stdin if no file given
    if file and file != "-":
        try:
            with open(file, encoding="utf-8") as f:
                diagram = f.read()
        except FileNotFoundError:
            click.echo(f"Error: File '{file}' does not exist.", err=True)
            sys.exit(1)
    else:
        diagram = sys.stdin.read()

    # Run sanitizer
    report = sanitize(diagram, tab_width=tab_width)

    if check:
        # Exit non-zero if issues found
        if report.status == "error":
            sys.exit(2)
        elif report.status == "warning":
            sys.exit(1)
        else:
            sys.exit(0)

    if (fix or in_place) and report.corrected_diagram:
        if in_place and file and file != "-":
            with open(file, "w", encoding="utf-8") as f:
                f.write(report.corrected_diagram)
            click.echo(f"Fixed {len(report.issues)} issue(s) in '{file}'", err=True)
        else:
            click.echo(report.corrected_diagram)
        return

    # Output report
    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        click.echo(format_text(report))

    # Set exit code
    if report.status == "error":
        sys.exit(2)
    elif report.status == "warning":
        sys.exit(1)


if __name__ == "__main__":
    main()
