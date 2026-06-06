"""Auto-fix engine: gap filling, box width normalization, style unification.

Applies fixes in stages: box widths first (structural), then gaps (connectivity),
then styles (cosmetic). Re-analyzes between stages.
"""

from __future__ import annotations

from copy import deepcopy

from .analyzer import analyze
from .connectors import (
    BOX_DRAWING_CHARS,
    Dir,
    expected_directions,
    is_double_line,
    is_single_line,
    to_double_line,
    to_single_line,
)
from .grid import get_cell, grid_dimensions, set_cell
from .types import Issue, IssueType


def apply_fixes(grid: list[list[str]], issues: list[Issue]) -> list[list[str]]:
    """Apply all auto-fixes to a copy of the grid, in order of structural priority.

    Returns the fully-corrected grid.
    """
    fixed = deepcopy(grid)
    rows, cols = grid_dimensions(fixed)

    # Stage 1: Box width normalization (structural)
    box_issues = [i for i in issues if i.type == IssueType.BOX_WIDTH and i.fixable]
    for issue in box_issues:
        _fix_box_width(fixed, issue, rows, cols)

    # Stage 2: Re-analyze, then fix remaining gaps
    if box_issues:
        remaining = analyze(fixed)
        gap_issues = [i for i in remaining if i.type == IssueType.GAP and i.fixable]
    else:
        gap_issues = [i for i in issues if i.type == IssueType.GAP and i.fixable]

    for issue in gap_issues:
        _fix_gap(fixed, issue, rows, cols)

    # Stage 3: Re-analyze, then fix styles
    if gap_issues:
        remaining2 = analyze(fixed)
        style_issues = [i for i in remaining2 if i.type == IssueType.STYLE_MIX and i.fixable]
    else:
        style_issues = [i for i in issues if i.type == IssueType.STYLE_MIX and i.fixable]

    for issue in style_issues:
        _fix_style_mix(fixed, issue, rows, cols)

    return fixed


# ---- Gap filling ----

def _fix_gap(grid: list[list[str]], issue: Issue, rows: int, cols: int) -> None:
    """Fill a single-cell gap between two connectors."""
    r, c = issue.line - 1, issue.col - 1
    if issue.end_line is None or issue.end_col is None:
        return

    er, ec = issue.end_line - 1, issue.end_col - 1

    # Determine direction and fill character
    if r == er:
        fill_char = "─"
        if is_double_line(grid[r][c]) or is_double_line(grid[er][ec]):
            fill_char = "═"
    else:
        fill_char = "│"
        if is_double_line(grid[r][c]) or is_double_line(grid[er][ec]):
            fill_char = "║"

    # Fill the gap cell (should be exactly 1 cell based on fixable=True)
    dr = 1 if er > r else (-1 if er < r else 0)
    dc = 1 if ec > c else (-1 if ec < c else 0)

    mr, mc = r + dr, c + dc
    if 0 <= mr < rows and 0 <= mc < cols:
        if grid[mr][mc] == " ":
            set_cell(grid, mr, mc, fill_char)


# ---- Box width normalization ----

def _fix_box_width(grid: list[list[str]], issue: Issue, rows: int, cols: int) -> None:
    """Normalize box border widths to the canonical width."""
    if not issue.fix_suggestion:
        return

    import re
    match = re.search(r"width (\d+)", issue.fix_suggestion)
    if not match:
        return
    canonical = int(match.group(1))

    top_r = issue.line - 1
    left_c = issue.col - 1
    if issue.end_line is None:
        return
    bot_r = issue.end_line - 1

    # For each row between top_r and bot_r, find horizontal borders and normalize
    for r in range(top_r, bot_r + 1):
        ch = grid[r][left_c]
        if ch not in ("│", "║", "┌", "╔", "└", "╚", "├", "╠", "┼", "╬"):
            continue

        # Find the right edge on this row
        right_c = None
        for c in range(left_c + 1, cols):
            rc = grid[r][c]
            if rc in ("┐", "╗", "┤", "╣", "┘", "╝", "│", "║", "|"):
                right_c = c
                break
            non_line_chars = ("─", "═", "┬", "┴", "┼", "╦", "╩", "╬", "├", "┤")
            if rc == " " or (rc not in non_line_chars and rc != " "):
                # Check if content or truly end
                if rc != " ":
                    break
                if c - left_c > 5:  # reasonable gap, break
                    break

        if right_c is None:
            continue

        current_width = right_c - left_c

        if current_width == canonical:
            continue

        right_ch = grid[r][right_c]

        if current_width < canonical:
            # Extend: add horizontal line chars
            new_right = left_c + canonical

            # Ensure row is long enough
            while len(grid[r]) <= new_right:
                grid[r].append(" ")

            # Move the right corner to the new position
            grid[r][new_right] = right_ch
            if new_right != right_c:
                if right_ch in ("┐", "┘", "┤"):
                    grid[r][right_c] = "─"
                elif right_ch in ("╗", "╝", "╣"):
                    grid[r][right_c] = "═"
                else:
                    grid[r][right_c] = "─"

            # Fill the gap between old right_c and new_right with horizontal lines
            fill_char = "═" if right_ch in ("╗", "╝", "╣") else "─"
            for c in range(right_c, new_right):
                grid[r][c] = fill_char

        else:
            # Shrink: remove extra chars, move corner left
            new_right = left_c + canonical
            grid[r][new_right] = right_ch
            for c in range(new_right + 1, right_c + 1):
                if c < len(grid[r]):
                    grid[r][c] = " "


# ---- Style unification ----

def _fix_style_mix(grid: list[list[str]], issue: Issue, rows: int, cols: int) -> None:
    """Unify mixed single/double line styles within a connected component."""
    if not issue.fix_suggestion:
        return

    if "single-line" in issue.fix_suggestion:
        target_single = True
    elif "double-line" in issue.fix_suggestion:
        target_single = False
    else:
        return

    start_r, start_c = issue.line - 1, issue.col - 1

    # BFS to find all connected box-drawing characters
    from collections import deque
    visited: set[tuple[int, int]] = set()
    queue = deque([(start_r, start_c)])
    visited.add((start_r, start_c))

    while queue:
        r, c = queue.popleft()
        ch = grid[r][c]
        if ch not in BOX_DRAWING_CHARS:
            continue
        dirs = expected_directions(ch)
        for d in dirs:
            dr, dc = _dir_vector(d)
            nr, nc = r + dr, c + dc
            if (nr, nc) not in visited:
                nch = get_cell(grid, nr, nc)
                if nch and nch in BOX_DRAWING_CHARS:
                    opposite = _opposite_dir(d)
                    if opposite in expected_directions(nch):
                        visited.add((nr, nc))
                        queue.append((nr, nc))

    for r, c in visited:
        ch = grid[r][c]
        if target_single and is_double_line(ch):
            set_cell(grid, r, c, to_single_line(ch))
        elif not target_single and is_single_line(ch):
            set_cell(grid, r, c, to_double_line(ch))


# ---- Helpers ----

def _dir_vector(d: Dir) -> tuple[int, int]:
    mapping = {Dir.UP: (-1, 0), Dir.DOWN: (1, 0), Dir.LEFT: (0, -1), Dir.RIGHT: (0, 1)}
    return mapping[d]


def _opposite_dir(d: Dir) -> Dir:
    mapping = {Dir.UP: Dir.DOWN, Dir.DOWN: Dir.UP, Dir.LEFT: Dir.RIGHT, Dir.RIGHT: Dir.LEFT}
    return mapping[d]
