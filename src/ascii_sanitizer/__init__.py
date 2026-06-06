"""ASCII Diagram Sanitizer — validate and auto-fix structural errors in ASCII diagrams."""

from __future__ import annotations

from .analyzer import analyze
from .fixer import apply_fixes
from .grid import parse
from .report import build_report, format_text
from .types import Issue, IssueType, Report, Severity

__version__ = "0.1.0"


def sanitize(diagram: str, *, tab_width: int = 4) -> Report:
    """Validate an ASCII diagram and auto-fix unambiguous errors.

    Args:
        diagram: The ASCII diagram as a UTF-8 string.
        tab_width: Number of spaces to expand tabs to.

    Returns:
        A Report object with attributes:
        - status: "ok", "warning", or "error"
        - issues: list of Issue objects
        - corrected_diagram: the fixed diagram string, or None
        Use report.to_dict() for JSON-serializable output.
    """
    # Parse into grid
    grid = parse(diagram, tab_width=tab_width)

    # Analyze
    issues = analyze(grid)

    # Build report
    report = build_report(issues, corrected_grid=None)

    if report.status != "ok":
        # Try to apply fixes
        corrected_grid = apply_fixes(grid, issues)
        report = build_report(issues, corrected_grid)

    return report


__all__ = [
    "sanitize",
    "Issue",
    "IssueType",
    "Report",
    "Severity",
    "format_text",
    "__version__",
]
