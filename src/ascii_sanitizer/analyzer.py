"""Core analysis engine: trace, gap detection, box checks, style checks."""

from __future__ import annotations

from collections import deque

from .connectors import (
    BOX_DRAWING_CHARS,
    DOUBLE_LINE_CHARS,
    SINGLE_LINE_CHARS,
    Dir,
    expected_directions,
    is_connector,
    is_double_line,
)
from .grid import get_cell, grid_dimensions
from .types import Issue, IssueType, Severity

# Direction vectors
_DIR_VECTORS: dict[Dir, tuple[int, int]] = {
    Dir.UP: (-1, 0),
    Dir.DOWN: (1, 0),
    Dir.LEFT: (0, -1),
    Dir.RIGHT: (0, 1),
}

# Characters that can appear in a vertical line trace
_VERTICAL_TRACE: frozenset[str] = frozenset(
    {"│", "║", "|", "├", "┤", "┼", "╠", "╣", "╬", "+"}
    | {"┬", "┴", "└", "┘", "╚", "╝", "┌", "┐", "╔", "╗"}
)

# Characters that can appear in a horizontal line trace
_HORIZONTAL_TRACE: frozenset[str] = frozenset(
    {"─", "═", "-", "┬", "┴", "┼", "╦", "╩", "╬", "+", "├", "┤"}
)


# ---- Trace result types ----

class TraceResult:
    """Result of tracing from a connector in one direction."""

    def __init__(self) -> None:
        self.connected: bool = False
        self.gap_length: int = 0
        self.dangling: bool = False
        self.end_row: int = -1
        self.end_col: int = -1
        self.end_char: str = ""
        self.content_end: bool = False


# ---- Main analysis entry point ----

def analyze(grid: list[list[str]]) -> list[Issue]:
    """Analyze a parsed grid and return all detected issues."""
    issues: list[Issue] = []

    rows, cols = grid_dimensions(grid)
    if rows == 0 or cols == 0:
        return issues

    # Collect all connectors
    connectors: list[tuple[int, int, str]] = []
    for r in range(rows):
        for c in range(cols):
            ch = grid[r][c]
            if is_connector(ch):
                connectors.append((r, c, ch))

    if not connectors:
        return issues  # No diagram characters found

    # 1. Connectivity trace
    issues.extend(_check_connectivity(grid, connectors, rows, cols))

    # 2. Box width check
    issues.extend(_check_boxes(grid, connectors, rows, cols))

    # 3. Style check
    issues.extend(_check_styles(grid, connectors, rows, cols))

    # 4. Arrow/circle orphan check
    issues.extend(_check_arrow_orphans(grid, connectors, rows, cols))

    # Deduplicate issues (same type, line, col)
    seen: set[tuple[str, int, int]] = set()
    unique: list[Issue] = []
    for issue in issues:
        key = (issue.type.value, issue.line, issue.col)
        if key not in seen:
            seen.add(key)
            unique.append(issue)

    return unique


# ---- Connectivity trace ----

def _check_connectivity(
    grid: list[list[str]],
    connectors: list[tuple[int, int, str]],
    rows: int, cols: int,
) -> list[Issue]:
    """Trace from each connector in expected directions and detect gaps."""
    issues: list[Issue] = []

    for r, c, ch in connectors:
        dirs = expected_directions(ch)
        # First pass: check if this connector has ANY valid connection
        has_any_connection = False
        trace_results: dict[Dir, TraceResult] = {}
        for d in dirs:
            result = _trace(grid, r, c, d, rows, cols)
            trace_results[d] = result
            # Connected means: adjacent connector, content endpoint,
            # or gap to connector (not dangling at edge)
            is_reachable = (
                result.connected
                or result.content_end
                or (result.gap_length > 0 and not result.dangling)
            )
            if is_reachable:
                has_any_connection = True

        # Only report dangling if the connector has NO connections at all
        if not has_any_connection:
            for d, result in trace_results.items():
                if result.dangling:
                    issues.append(Issue(
                        line=r + 1, col=c + 1,
                        severity=Severity.ERROR,
                        type=IssueType.DANGLING_JUNCTION,
                        message=f"Isolated connector '{ch}' at ({r + 1},{c + 1}): "
                                f"no connections in any direction",
                        fixable=False,
                    ))
                    break
            continue

        # Report gaps only for connected connectors
        for d, result in trace_results.items():
            if result.connected or result.content_end or result.dangling:
                continue
            if result.gap_length > 0:
                fixable = result.gap_length == 1
                line_char = _gap_fill_char(grid, r, c, d)
                if result.end_char:
                    msg = (
                        f"Disconnected line: '{ch}' at ({r + 1},{c + 1})"
                        f" has {result.gap_length} empty cell(s) to the"
                        f" {d.name.lower()} before '{result.end_char}'"
                        f" at ({result.end_row + 1},{result.end_col + 1})"
                    )
                else:
                    msg = (f"Disconnected line: '{ch}' at ({r + 1},{c + 1}) "
                           f"has {result.gap_length} empty cell(s) to the {d.name.lower()}")
                suggestion = None
                if fixable and line_char:
                    gr, gc = _step(r, c, d)
                    suggestion = (
                        f"Insert '{line_char}' at ({gr + 1},{gc + 1})"
                        f" to connect '{ch}' to '{result.end_char}'"
                    )

                issues.append(Issue(
                    line=r + 1, col=c + 1,
                    severity=Severity.ERROR,
                    type=IssueType.GAP,
                    message=msg,
                    fixable=fixable,
                    fix_suggestion=suggestion,
                    end_line=result.end_row + 1 if result.end_row >= 0 else None,
                    end_col=result.end_col + 1 if result.end_col >= 0 else None,
                ))

    return issues


def _trace(
    grid: list[list[str]], start_r: int, start_c: int,
    direction: Dir, rows: int, cols: int,
) -> TraceResult:
    """Trace from (start_r, start_c) in the given direction.

    Returns a TraceResult indicating whether the trace found a connector,
    a gap, or went out of bounds.
    """
    result = TraceResult()
    dr, dc = _DIR_VECTORS[direction]
    r, c = start_r + dr, start_c + dc
    gap_count = 0

    while 0 <= r < rows and 0 <= c < cols:
        ch = grid[r][c]

        if is_connector(ch):
            if gap_count == 0:
                result.connected = True
            else:
                result.gap_length = gap_count
                result.end_row = r
                result.end_col = c
                result.end_char = ch
            return result

        if ch != " ":
            # Content character (text, label, etc.) — always a valid endpoint.
            # Spaces between a connector and content are intentional formatting.
            result.content_end = True
            return result

        # Empty space
        gap_count += 1
        r += dr
        c += dc

    # Reached grid boundary without finding connector or content
    result.dangling = True
    result.gap_length = gap_count
    return result


def _step(r: int, c: int, direction: Dir) -> tuple[int, int]:
    """Return coordinates one step in the given direction."""
    dr, dc = _DIR_VECTORS[direction]
    return (r + dr, c + dc)


def _gap_fill_char(
    grid: list[list[str]], r: int, c: int, direction: Dir,
) -> str | None:
    """Determine which line character to use to fill a gap in the given direction."""
    ch = grid[r][c]
    if direction in (Dir.UP, Dir.DOWN):
        if is_double_line(ch):
            return "║"
        return "│"
    else:
        if is_double_line(ch):
            return "═"
        return "─"


# ---- Box detection ----

def _check_boxes(
    grid: list[list[str]],
    connectors: list[tuple[int, int, str]],
    rows: int, cols: int,
) -> list[Issue]:
    """Detect boxes and check for width mismatches between top and bottom borders."""
    issues: list[Issue] = []

    # Find all corners
    top_lefts = [(r, c) for r, c, ch in connectors if ch in ("┌", "╔")]
    {(r, c) for r, c, ch in connectors if ch in ("┐", "╗")}
    {(r, c) for r, c, ch in connectors if ch in ("└", "╚")}
    {(r, c) for r, c, ch in connectors if ch in ("┘", "╝")}

    # For each top-left, find matching top-right on same row
    for tl_r, tl_c in top_lefts:
        # Find rightmost ┐ (or ╗) on the same row, connected by horizontal line chars
        tr_c = _find_matching_corner_right(grid, tl_r, tl_c, rows, cols)
        if tr_c is None:
            continue

        top_width = tr_c - tl_c

        # Trace down from tl_c to find bottom-left corner
        bl_r, bl_char = _trace_vertical_down(grid, tl_r, tl_c, rows, cols)
        if bl_r is None or bl_char not in ("└", "╚"):
            continue

        # Check if there's a matching bottom-right on the same row
        br_c = _find_matching_corner_right(grid, bl_r, tl_c, rows, cols)
        if br_c is None:
            continue

        bottom_width = br_c - tl_c

        if top_width != bottom_width:
            # Determine canonical width — use the modal width (most frequent)
            internal_widths = _collect_box_border_widths(grid, tl_r, bl_r, tl_c, rows, cols)
            all_widths = [top_width, bottom_width] + internal_widths
            canonical = _modal_width(all_widths)
            fixable = canonical is not None
            suggestion = None
            if fixable:
                suggestion = (f"Normalize box borders to width {canonical} "
                              f"(top is {top_width}, bottom is {bottom_width})")

            issues.append(Issue(
                line=tl_r + 1, col=tl_c + 1,
                severity=Severity.ERROR,
                type=IssueType.BOX_WIDTH,
                message=(f"Box width mismatch: top border at row {tl_r + 1} has width {top_width}, "
                         f"bottom border at row {bl_r + 1} has width {bottom_width}"),
                fixable=fixable,
                fix_suggestion=suggestion,
                end_line=bl_r + 1,
                end_col=br_c + 1 if br_c else None,
            ))

    return issues


def _find_matching_corner_right(
    grid: list[list[str]], r: int, start_c: int, rows: int, cols: int,
) -> int | None:
    """From (r, start_c), look right for a matching corner
    (┐, ╗, ┤, ╣, ┘, ╝) connected by horizontal line characters."""
    for c in range(start_c + 1, cols):
        ch = grid[r][c]
        if ch in ("┐", "╗", "┤", "╣", "┘", "╝"):
            return c
        if ch not in _HORIZONTAL_TRACE and ch != " ":
            return None
        if ch == " ":
            return None
    return None


def _trace_vertical_down(
    grid: list[list[str]], start_r: int, c: int, rows: int, cols: int,
) -> tuple[int | None, str]:
    """Trace down from (start_r, c) following vertical line characters.

    Returns (row, char) where the trace ends, or (None, '') if it breaks.
    """
    r = start_r + 1
    while r < rows:
        ch = grid[r][c]
        if ch in _VERTICAL_TRACE:
            if ch in ("└", "╚", "┘", "╝", "┴", "╩"):
                return (r, ch)
            r += 1
        elif ch == " ":
            r += 1  # Allow single spaces? Actually no — space means break
            # But we should check if there's a continuation after a gap
            # For box detection, a 1-cell gap in the vertical trace is ok
            if r < rows and grid[r][c] in _VERTICAL_TRACE:
                # Skip single gap
                continue
            return (None, "")
        else:
            # Content character — break the trace
            return (None, "")
    return (None, "")


def _modal_width(widths: list[int]) -> int | None:
    """Return the modal (most frequent) width, or None if there's a tie."""
    if not widths:
        return None
    from collections import Counter
    c = Counter(w for w in widths if w > 0)
    if not c:
        return None
    # Check if there's a clear winner
    counts = c.most_common()
    if len(counts) == 1:
        return counts[0][0]
    if counts[0][1] > counts[1][1]:
        return counts[0][0]
    return None  # Tie — ambiguous


def _collect_box_border_widths(
    grid: list[list[str]], top_r: int, bot_r: int,
    left_c: int, rows: int, cols: int,
) -> list[int]:
    """Collect widths of all rows within a box (top_r to bot_r).

    Includes both horizontal-border rows (───) and content rows (with │ edges).
    """
    widths: list[int] = []
    for r in range(top_r, bot_r + 1):
        ch = grid[r][left_c]
        if ch not in _VERTICAL_TRACE:
            continue
        # Find the right edge on this row
        for c in range(left_c + 1, cols):
            rc = grid[r][c]
            if rc in ("┐", "╗", "┤", "╣", "┘", "╝", "│", "║", "|"):
                widths.append(c - left_c)
                break
            # Only break if we hit something that's clearly not part of the box
            if rc not in _HORIZONTAL_TRACE and rc != " ":
                # Content char — but the row might still have a right │ later
                # Don't break, keep scanning
                pass
    return widths


# ---- Style check ----

def _check_styles(
    grid: list[list[str]],
    connectors: list[tuple[int, int, str]],
    rows: int, cols: int,
) -> list[Issue]:
    """Check for mixed single/double line styles within connected components."""
    issues: list[Issue] = []

    # Build adjacency graph among box-drawing connectors
    connector_set: set[tuple[int, int]] = set()
    box_drawing_set: set[tuple[int, int]] = set()
    for r, c, ch in connectors:
        connector_set.add((r, c))
        if ch in BOX_DRAWING_CHARS:
            box_drawing_set.add((r, c))

    # BFS to find connected components
    visited: set[tuple[int, int]] = set()

    for start in box_drawing_set:
        if start in visited:
            continue

        # BFS within this component
        component: list[tuple[int, int]] = []
        queue = deque([start])
        visited.add(start)

        while queue:
            r, c = queue.popleft()
            component.append((r, c))
            ch = grid[r][c]
            dirs = expected_directions(ch)

            for d in dirs:
                dr, dc = _DIR_VECTORS[d]
                nr, nc = r + dr, c + dc
                if (nr, nc) in box_drawing_set and (nr, nc) not in visited:
                    # Check if adjacent cell is actually connected
                    nch = grid[nr][nc]
                    opposite = _opposite_dir(d)
                    if opposite in expected_directions(nch):
                        visited.add((nr, nc))
                        queue.append((nr, nc))

        # Count single vs double in this component
        single_count = sum(1 for r, c in component if grid[r][c] in SINGLE_LINE_CHARS)
        double_count = sum(1 for r, c in component if grid[r][c] in DOUBLE_LINE_CHARS)

        if single_count > 0 and double_count > 0:
            total = single_count + double_count
            single_pct = single_count / total
            double_pct = double_count / total

            fixable = single_pct > 0.8 or double_pct > 0.8
            majority = "single-line" if single_pct > double_pct else "double-line"

            r0, c0 = component[0]
            issues.append(Issue(
                line=r0 + 1, col=c0 + 1,
                severity=Severity.WARNING,
                type=IssueType.STYLE_MIX,
                message=(f"Mixed line styles in connected component: "
                         f"{single_count} single-line, {double_count} double-line chars "
                         f"({single_pct:.0%} / {double_pct:.0%})"),
                fixable=fixable,
                fix_suggestion=(f"Unify to {majority} style" if fixable else None),
            ))

    return issues


def _opposite_dir(d: Dir) -> Dir:
    """Return the opposite direction."""
    mapping = {Dir.UP: Dir.DOWN, Dir.DOWN: Dir.UP, Dir.LEFT: Dir.RIGHT, Dir.RIGHT: Dir.LEFT}
    return mapping[d]


# ---- Arrow / circle orphan check ----

def _check_arrow_orphans(
    grid: list[list[str]],
    connectors: list[tuple[int, int, str]],
    rows: int, cols: int,
) -> list[Issue]:
    """Check that arrow heads and circles have connecting lines.

    Skips arrow heads that appear between horizontal line characters
    (e.g., ┌────▼────┐) as these are decorative box elements.
    """
    from .connectors import ARROW_HEAD_CHARS, CIRCLE_CHARS

    issues: list[Issue] = []

    for r, c, ch in connectors:
        dirs = expected_directions(ch)
        if not dirs:
            continue

        # Skip decorative arrows (between horizontal line chars on either side)
        if ch in ARROW_HEAD_CHARS:
            left_ch = get_cell(grid, r, c - 1)
            right_ch = get_cell(grid, r, c + 1)
            if left_ch in ("─", "═", "-") and right_ch in ("─", "═", "-"):
                continue  # Decorative, between border chars

        # For each expected direction, check if there's at least one
        # connector or line character adjacent
        connected_any = False
        for d in dirs:
            dr, dc = _DIR_VECTORS[d]
            nr, nc = r + dr, c + dc
            adj = get_cell(grid, nr, nc)
            if adj and (is_connector(adj) or adj in ("─", "│", "═", "║", "-", "|")):
                connected_any = True
                break

        if not connected_any:
            if ch in ARROW_HEAD_CHARS:
                issues.append(Issue(
                    line=r + 1, col=c + 1,
                    severity=Severity.ERROR,
                    type=IssueType.ARROW_ORPHAN,
                    message=f"Arrow head '{ch}' at ({r + 1},{c + 1}) has no connecting line",
                    fixable=False,
                ))
            elif ch in CIRCLE_CHARS:
                issues.append(Issue(
                    line=r + 1, col=c + 1,
                    severity=Severity.WARNING,
                    type=IssueType.ARROW_ORPHAN,
                    message=f"Circle '{ch}' at ({r + 1},{c + 1}) has no connecting line",
                    fixable=False,
                ))

    return issues
