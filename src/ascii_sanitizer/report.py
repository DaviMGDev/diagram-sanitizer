"""Report generation: build JSON report from issues and corrected grid."""

from __future__ import annotations

from .grid import reconstruct
from .types import Issue, Report, Severity


def build_report(issues: list[Issue], corrected_grid: list[list[str]] | None) -> Report:
    """Build a Report from issues and an optional corrected grid."""
    # Determine overall status
    severities = {issue.severity for issue in issues}

    if Severity.ERROR in severities:
        status = "error"
    elif Severity.WARNING in severities:
        status = "warning"
    else:
        status = "ok"

    corrected_diagram = None
    if corrected_grid:
        corrected_diagram = reconstruct(corrected_grid)

    has_fixable = any(issue.fixable for issue in issues)
    if not has_fixable:
        corrected_diagram = None

    return Report(
        status=status,
        issues=sorted(issues, key=lambda i: (i.line, i.col)),
        corrected_diagram=corrected_diagram,
    )


def format_text(report: Report) -> str:
    """Format a report as human-readable text."""
    lines: list[str] = []
    lines.append(f"Status: {report.status.upper()}")
    lines.append(f"Issues: {len(report.issues)}")
    lines.append("")

    for i, issue in enumerate(report.issues, 1):
        lines.append(f"  [{i}] {issue.severity.value.upper()}: {issue.type.value}")
        lines.append(f"      Line {issue.line}, Col {issue.col}")
        if issue.end_line:
            loc = f" → Line {issue.end_line}"
            if issue.end_col:
                loc += f", Col {issue.end_col}"
            lines.append(f"      {loc}")
        lines.append(f"      {issue.message}")
        if issue.fixable:
            lines.append(f"      [FIXABLE] {issue.fix_suggestion}")
        lines.append("")

    if report.corrected_diagram:
        lines.append("--- Corrected Diagram ---")
        lines.append(report.corrected_diagram)

    return "\n".join(lines)
