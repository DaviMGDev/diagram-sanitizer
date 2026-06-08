"""Pipeline orchestrator — the sanitize() entry point.

Orchestrates all 12 pipeline stages and produces the JSON report.
"""

from __future__ import annotations

from diagram_sanitizer.preprocessor import preprocess
from diagram_sanitizer.markdown import (
    detect_markdown_tables,
    build_exempt_regions_from_lines,
    normalize_markdown_table,
)
from diagram_sanitizer.grid import Grid, classify_connectors
from diagram_sanitizer.components import find_components
from diagram_sanitizer.detectors import (
    detect_orphans,
    detect_gaps,
    detect_box_widths,
    detect_style_mix,
    detect_cross_arrow_circle,
    detect_missing_sides,
    detect_overlaps,
    detect_mixed_arrows,
)
from diagram_sanitizer.fixer import apply_fixes

# ── Default options ──────────────────────────────────────────────────────────

DEFAULT_OPTIONS: dict = {
    "tab_width": 4,
    "max_grid_width": 400,
    "mode": "auto",
}

# ── Issue ID prefixes ────────────────────────────────────────────────────────

_ID_PREFIX: dict[str, str] = {
    "gap": "GAP",
    "box_width": "BOX",
    "style_mix": "STYLE",
    "dangling_junction": "DANGL",
    "orphan": "ORPH",
    "arrow_orphan": "ARRW",
    "missing_side": "SIDE",
    "overlap": "OVERL",
    "markdown_table": "MDTBL",
    "encoding": "ENCOD",
}


# ── Main entry point ─────────────────────────────────────────────────────────


def sanitize(diagram: str, options: dict | None = None) -> dict:
    """Validate and auto-correct an ASCII diagram.

    This is the main library entry point (FR-020). It accepts a raw UTF-8
    diagram string and returns a report dict matching the spec's data model.

    Args:
        diagram: Raw UTF-8 diagram string.
        options: Optional configuration dict:
            - tab_width (int): Spaces per tab, default 4.
            - max_grid_width (int): Max columns before warning, default 400.
            - mode (str): "check", "fix", or "auto" (default).

    Returns:
        A dict with keys: status, issues, corrected_diagram.
    """
    # Merge options with defaults
    opts = dict(DEFAULT_OPTIONS)
    if options:
        opts.update(options)

    # ── Step 1: Preprocessing ──
    normalized = preprocess(diagram, tab_width=opts["tab_width"])

    # ── Check for replacement characters (NFR-006) ──
    if "�" in normalized:
        all_issues: list[dict] = [
            {
                "line": 1,
                "col": 1,
                "severity": "warning",
                "type": "encoding",
                "message": "Input contains invalid UTF-8 sequences (replaced with U+FFFD)",
                "fixable": False,
            }
        ]
    else:
        all_issues = []

    # ── Step 2: Markdown table detection (FR-028) ──
    lines = normalized.split("\n")
    detected_tables = detect_markdown_tables(lines)
    exempt_regions = build_exempt_regions_from_lines(detected_tables, lines)

    # ── Step 3-4: Grid construction + connector classification ──
    grid = Grid(normalized)
    connectors = classify_connectors(grid, exempt_regions=exempt_regions)

    # Handle empty / no-connector inputs (EC-001, EC-002, EC-003)
    if not connectors:
        status = _compute_status(all_issues)
        for issue in all_issues:
            prefix = _ID_PREFIX.get(issue["type"], "ISSUE")
            issue["id"] = f"{prefix}-{issue['line']}-{issue['col']}"
        return {
            "status": status,
            "issues": all_issues,
            "corrected_diagram": None,
        }

    # ── Step 4: Connected component analysis ──
    components = find_components(connectors, grid)

    # ── Steps 5-9: Detection stages ──
    all_issues.extend(detect_orphans(grid, connectors, components))
    all_issues.extend(detect_gaps(grid, connectors))
    all_issues.extend(detect_box_widths(grid, components))
    all_issues.extend(detect_missing_sides(grid, components))
    all_issues.extend(detect_style_mix(components))
    all_issues.extend(detect_cross_arrow_circle(grid, connectors, components))
    all_issues.extend(detect_overlaps(components))
    all_issues.extend(detect_mixed_arrows(connectors, components))

    # ── Deduplicate issues (EC-027) ──
    issues = _deduplicate(all_issues)

    # ── Add issue IDs ──
    for issue in issues:
        prefix = _ID_PREFIX.get(issue["type"], "ISSUE")
        issue["id"] = f"{prefix}-{issue['line']}-{issue['col']}"

    # ── Compute status ──
    status = _compute_status(issues)

    # ── Step 10: Fix application ──
    mode = opts.get("mode", "auto")
    corrected_diagram = None
    if mode in ("fix", "auto"):
        corrected_diagram = apply_fixes(grid, issues)

    # ── Step 10b: Markdown table normalization (FR-029, FR-030) ──
    # Runs after diagram fixes so orphan removal doesn't affect table content
    if detected_tables and corrected_diagram is not None:
        table_lines = corrected_diagram.split("\n")
        table_issues: list[dict] = []
        for table in detected_tables:
            table_lines, ti = normalize_markdown_table(table_lines, table)
            table_issues.extend(ti)
        if table_issues:
            corrected_diagram = "\n".join(table_lines)
            # Re-apply IDs to table issues and merge
            for ti in table_issues:
                if "id" not in ti:
                    prefix = _ID_PREFIX.get(ti["type"], "ISSUE")
                    ti["id"] = f"{prefix}-{ti['line']}-{ti['col']}"
            issues.extend(table_issues)
            # Recompute status after adding table issues
            status = _compute_status(issues)

    # ── Step 11: Build report ──
    return {
        "status": status,
        "issues": issues,
        "corrected_diagram": corrected_diagram,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────


def _deduplicate(issues: list[dict]) -> list[dict]:
    """Deduplicate issues by (type, line, col) keeping earliest occurrence.

    EC-027: Two issues are duplicates if they share the same type, line,
    and col. Keep the one from the earliest pipeline stage (first in list).
    """
    seen: set[tuple[str, int, int]] = set()
    result: list[dict] = []
    for issue in issues:
        key = (issue["type"], issue["line"], issue["col"])
        if key not in seen:
            seen.add(key)
            result.append(issue)
    return result


def _compute_status(issues: list[dict]) -> str:
    """Compute overall status from issue severities.

    FR-023: "error" if any errors, "warning" if only warnings, "ok" if none.
    """
    has_error = any(i["severity"] == "error" for i in issues)
    has_warning = any(i["severity"] == "warning" for i in issues)
    has_info = any(i["severity"] == "info" for i in issues)

    if has_error:
        return "error"
    elif has_warning:
        return "warning"
    elif has_info:
        return "warning"  # Info-only also yields warning status
    else:
        return "ok"
