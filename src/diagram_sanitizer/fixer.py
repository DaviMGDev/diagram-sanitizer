"""Fix application stage — applies unambiguous corrections to a grid.

Fixes are applied in strict order:
1. Orphan removal (replace with space)
2. Gap fill (insert line character)
3. Box normalization (extend/shrink borders)
4. Style unification (replace minority-style chars)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from diagram_sanitizer.connector_map import (
    SINGLE_LINE_CHARS,
    DOUBLE_LINE_CHARS,
    SINGLE_TO_DOUBLE,
    DOUBLE_TO_SINGLE,
    HORIZONTAL_CHARS,
    VERTICAL_CHARS,
    CONNECTOR_MAP,
)

if TYPE_CHECKING:
    from diagram_sanitizer.grid import Grid


# ── Fix application order ────────────────────────────────────────────────────

FIX_ORDER = ["orphan", "gap", "box_width", "style_mix"]


def apply_fixes(grid: "Grid", issues: list[dict]) -> str | None:
    """Apply all fixable issues to the grid in priority order.

    Args:
        grid: The 2D character grid (will be modified in place).
        issues: List of issue dicts from detection stages.

    Returns:
        The corrected diagram string, or None if no fixable issues exist.
    """
    fixable_issues = [i for i in issues if i.get("fixable")]
    if not fixable_issues:
        return None

    # Group fixable issues by type
    by_type: dict[str, list[dict]] = {}
    for issue in fixable_issues:
        t = issue["type"]
        by_type.setdefault(t, []).append(issue)

    # Apply fixes in order
    for fix_type in FIX_ORDER:
        if fix_type in by_type:
            _apply_fix_type(grid, fix_type, by_type[fix_type])

    return grid.to_string()


def _apply_fix_type(grid: "Grid", fix_type: str, issues: list[dict]) -> None:
    """Apply a specific fix type to the grid."""
    if fix_type == "orphan":
        _fix_orphans(grid, issues)
    elif fix_type == "gap":
        _fix_gaps(grid, issues)
    elif fix_type == "box_width":
        _fix_box_widths(grid, issues)
    elif fix_type == "style_mix":
        _fix_style_mix(grid, issues)


# ── 1. Orphan removal ───────────────────────────────────────────────────────


def _fix_orphans(grid: "Grid", issues: list[dict]) -> None:
    """Replace orphan cells with spaces (FR-010)."""
    for issue in issues:
        # Issues use 1-indexed line/col — convert to 0-indexed
        row = issue["line"] - 1
        col = issue["col"] - 1
        ch = grid.get(row, col)
        if ch in CONNECTOR_MAP:
            grid.set(row, col, " ")


# ── 2. Gap fill ──────────────────────────────────────────────────────────────


def _fix_gaps(grid: "Grid", issues: list[dict]) -> None:
    """Fill single-cell gaps with the appropriate line character (FR-016)."""
    for issue in issues:
        row = issue["line"] - 1
        col = issue["col"] - 1

        # Determine fill character from the fix suggestion or direction
        suggestion = issue.get("fix_suggestion", "")
        fill_char = None

        # Try to extract character from suggestion: "Insert '│' at ..."
        if "Insert '" in suggestion:
            import re
            m = re.search(r"Insert '([^']+)'", suggestion)
            if m:
                fill_char = m.group(1)

        if not fill_char:
            # Fallback: determine from position context
            # Check if gap is horizontal or vertical
            end_line = issue.get("end_line", issue["line"])
            end_col = issue.get("end_col", issue["col"])
            if end_line == issue["line"]:
                fill_char = "─"
            else:
                fill_char = "│"

        # Only fill if the cell is empty
        if grid.get(row, col) == " ":
            grid.set(row, col, fill_char)


# ── 3. Box normalization ─────────────────────────────────────────────────────


def _fix_box_widths(grid: "Grid", issues: list[dict]) -> None:
    """Normalize box borders to match modal width (FR-017).

    Strategy:
    - Determine modal width from all horizontal borders of the box
    - Extend/shrink top and bottom borders to match
    - On width ties, use narrower width (conservative)
    """
    # Track which boxes we've already processed (by top-left corner)
    processed: set[tuple[int, int]] = set()

    for issue in issues:
        tl_row = issue["line"] - 1
        tl_col = issue["col"] - 1
        if (tl_row, tl_col) in processed:
            continue
        processed.add((tl_row, tl_col))

        # Parse the message to get widths
        msg = issue["message"]
        # "Box width mismatch: top border spans X cell(s), bottom border spans Y cell(s)"
        import re as _re
        nums = _re.findall(r"(\d+)", msg)
        if len(nums) < 2:
            continue

        top_w = int(nums[0])
        bottom_w = int(nums[1])

        # Modal width: use the narrower on tie (FR-017)
        # For a simple top-vs-bottom mismatch, use the one that matches the most internal rows
        # For now, use max width (extend to wider) as a reasonable default
        # Then apply tie-breaker: narrower wins on tie
        if top_w == bottom_w:
            continue  # No mismatch

        target_width = max(top_w, bottom_w)  # FIX later

        # Find the box corners in the grid
        tl_char = grid.get(tl_row, tl_col)
        if tl_char not in ("┌", "╔"):
            continue

        # Find top-right corner
        tr_col = tl_col + top_w + 1
        tr_char = grid.get(tl_row, tr_col)
        if tr_char not in ("┐", "╗"):
            continue

        # Find bottom-left corner
        bl_row = None
        for r in range(tl_row + 1, grid.height):
            ch = grid.get(r, tl_col)
            if ch in ("└", "╚"):
                bl_row = r
                break
        if bl_row is None:
            continue

        # Find bottom-right corner
        br_col = tl_col + bottom_w + 1
        br_char = grid.get(bl_row, br_col)
        if br_char not in ("┘", "╝"):
            continue

        # Normalize: extend or shrink bottom border to match target width
        # Extend bottom: add ─ between └ and ┘
        if bottom_w < target_width:
            # Fill the whole bottom border range (including old ┘ position)
            for fill_c in range(tl_col + 1, tl_col + target_width + 1):
                grid.set(bl_row, fill_c, "─")
            # Move ┘ to correct position
            grid.set(bl_row, tl_col + target_width + 1, tr_char.replace("╗", "╝").replace("┐", "┘"))
        elif bottom_w > target_width:
            # Shrink bottom: remove extra cells and move ┘ left
            for c in range(tl_col + target_width + 1, br_col + 1):
                grid.set(bl_row, c, " ")
            grid.set(bl_row, tl_col + target_width + 1, tr_char.replace("╗", "╝").replace("┐", "┘"))

        # Also fix top if needed
        if top_w < target_width:
            for fill_c in range(tl_col + 1, tl_col + target_width + 1):
                grid.set(tl_row, fill_c, "─")
            grid.set(tl_row, tl_col + target_width + 1, tr_char)
        elif top_w > target_width:
            for c in range(tl_col + target_width + 1, tr_col + 1):
                grid.set(tl_row, c, " ")
            grid.set(tl_row, tl_col + target_width + 1, tr_char)


# ── 4. Style unification ─────────────────────────────────────────────────────


def _fix_style_mix(grid: "Grid", issues: list[dict]) -> None:
    """Unify mixed single/double line styles when >80% majority (FR-018)."""
    for issue in issues:
        suggestion = issue.get("fix_suggestion", "")

        # Determine majority style from the suggestion
        if "single-line" in suggestion:
            majority = "single"
        elif "double-line" in suggestion:
            majority = "double"
        else:
            continue

        end_line = issue.get("end_line", issue["line"])
        end_col = issue.get("end_col", issue["col"])

        # Iterate the bounding box and convert minority chars
        for r in range(issue["line"] - 1, end_line):
            for c in range(issue["col"] - 1, end_col + 1):
                ch = grid.get(r, c)
                if majority == "single" and ch in DOUBLE_TO_SINGLE:
                    grid.set(r, c, DOUBLE_TO_SINGLE[ch])
                elif majority == "double" and ch in SINGLE_TO_DOUBLE:
                    grid.set(r, c, SINGLE_TO_DOUBLE[ch])
