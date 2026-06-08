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

FIX_ORDER = ["orphan", "arrow_orphan", "gap", "box_width", "style_mix"]


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
    if fix_type in ("orphan", "arrow_orphan"):
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
    - Collect widths from ALL horizontal borders (top, internal rows with
      T-junctions, bottom)
    - Compute modal width (most frequent). On tie, use narrower (conservative)
    - Normalize all horizontal borders to the modal width
    """
    # Track which boxes we've already processed (by top-left corner)
    processed: set[tuple[int, int]] = set()

    for issue in issues:
        tl_row = issue["line"] - 1
        tl_col = issue["col"] - 1
        if (tl_row, tl_col) in processed:
            continue
        processed.add((tl_row, tl_col))

        # Find the box corners in the grid
        tl_char = grid.get(tl_row, tl_col)
        if tl_char not in ("┌", "╔"):
            continue

        # Find top-right corner
        tr_col = _find_matching_right_corner(grid, tl_row, tl_col, tl_char)
        if tr_col is None:
            continue
        top_w = tr_col - tl_col - 1

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
        br_col = _find_matching_right_corner(grid, bl_row, tl_col, grid.get(bl_row, tl_col))
        if br_col is None:
            continue
        bottom_w = br_col - tl_col - 1

        # ── Collect all horizontal border widths (FR-017) ──
        # Include top, bottom, and any internal separator rows
        # (rows with T-junctions at the left column, e.g., ├──┤ or ╠══╣)
        widths: dict[int, int] = {}  # width -> count
        # Top
        widths[top_w] = widths.get(top_w, 0) + 1
        # Bottom
        widths[bottom_w] = widths.get(bottom_w, 0) + 1
        # Internal separator rows
        for r in range(tl_row + 1, bl_row):
            ch = grid.get(r, tl_col)
            if ch in ("├", "╠"):
                irc = _find_matching_right_corner(grid, r, tl_col, ch)
                if irc is not None:
                    w = irc - tl_col - 1
                    widths[w] = widths.get(w, 0) + 1

        if not widths:
            continue

        # Compute modal width; on tie, use narrower (FR-017)
        max_count = max(widths.values())
        candidates = [w for w, c in widths.items() if c == max_count]
        target_width = min(candidates)  # narrower wins on tie

        if all(w == target_width for w in widths):
            continue  # Already consistent

        # ── Normalize all borders to target width ──
        is_double = tl_char in ("╔", "╗")
        h_line = "═" if is_double else "─"
        right_corner_map = {
            "┌": "┐", "╔": "╗",
            "├": "┤", "╠": "╣",
            "└": "┘", "╚": "╝",
        }

        # Fix top border
        _normalize_border(
            grid, tl_row, tl_col, tr_col, target_width, h_line,
            right_corner_map.get(tl_char, "┐")
        )

        # Fix bottom border
        bl_char = grid.get(bl_row, tl_col)
        _normalize_border(
            grid, bl_row, tl_col, br_col, target_width, h_line,
            right_corner_map.get(bl_char, "┘")
        )

        # Fix internal separator rows
        for r in range(tl_row + 1, bl_row):
            ch = grid.get(r, tl_col)
            if ch in ("├", "╠"):
                irc = _find_matching_right_corner(grid, r, tl_col, ch)
                if irc is not None and irc - tl_col - 1 != target_width:
                    _normalize_border(
                        grid, r, tl_col, irc, target_width, h_line,
                        right_corner_map.get(ch, "┤")
                    )


def _find_matching_right_corner(
    grid: "Grid", row: int, left_col: int, left_char: str
) -> int | None:
    """Find the matching right-side corner on the same row."""
    right_chars = {"┌": "┐", "╔": "╗", "├": "┤", "╠": "╣", "└": "┘", "╚": "╝"}
    expected_right = right_chars.get(left_char)
    if expected_right is None:
        return None
    for c in range(left_col + 1, grid.width):
        ch = grid.get(row, c)
        if ch == expected_right:
            return c
    return None


def _normalize_border(
    grid: "Grid", row: int, left_col: int, old_right_col: int | None,
    target_width: int, h_line: str, right_corner: str
) -> None:
    """Normalize a single horizontal border to target_width."""
    # Clear existing border cells and right corner
    if old_right_col is not None:
        for c in range(left_col + 1, old_right_col + 1):
            grid.set(row, c, " ")

    # Draw new border at target width
    new_right_col = left_col + target_width + 1
    for c in range(left_col + 1, new_right_col):
        grid.set(row, c, h_line)
    grid.set(row, new_right_col, right_corner)


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
