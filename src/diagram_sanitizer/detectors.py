"""Detection stages — orphan, gap, box, style, cross/arrow/circle validation.

Each function returns a list of Issue dicts matching the spec's data model.
Coordinates in issues are 1-indexed (line, col) per the spec.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from diagram_sanitizer.connector_map import (
    CONNECTOR_MAP,
    OPPOSITE,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    STRICT,
    AT_LEAST_ONE,
    LOOSE,
    SINGLE_LINE_CHARS,
    DOUBLE_LINE_CHARS,
    BOX_CORNER_CHARS,
    CROSS_CHARS,
    ARROW_HEAD_CHARS,
    FULL_ARROW_CHARS,
    CIRCLE_CHARS,
    DIAGONAL_CHARS,
    ASCII_CONNECTOR_CHARS,
    HORIZONTAL_CHARS,
    VERTICAL_CHARS,
    get_char_style,
)

if TYPE_CHECKING:
    from diagram_sanitizer.grid import Grid, ConnectorCell
    from diagram_sanitizer.components import Component


# ── Issue helpers ────────────────────────────────────────────────────────────


def _issue(
    line: int,
    col: int,
    severity: str,
    type_: str,
    message: str,
    fixable: bool = False,
    fix_suggestion: str | None = None,
    end_line: int | None = None,
    end_col: int | None = None,
) -> dict:
    """Build an issue dict. Coordinates are 1-indexed."""
    issue: dict = {
        "line": line,
        "col": col,
        "severity": severity,
        "type": type_,
        "message": message,
        "fixable": fixable,
    }
    if fix_suggestion:
        issue["fix_suggestion"] = fix_suggestion
    if end_line is not None:
        issue["end_line"] = end_line
    if end_col is not None:
        issue["end_col"] = end_col
    return issue


def _to_1idx(row: int, col: int) -> tuple[int, int]:
    """Convert 0-indexed grid coords to 1-indexed line/col."""
    return row + 1, col + 1


# ── Connectivity helpers ─────────────────────────────────────────────────────


def _has_connection(
    connectors_by_pos: dict[tuple[int, int], "ConnectorCell"],
    cell: "ConnectorCell",
    direction: str,
    grid: "Grid",
) -> bool:
    """Check if cell has a direct connection in the given direction.

    A connection exists if there is an adjacent connector in that direction
    and both expect connection toward each other.
    """
    from diagram_sanitizer.grid import neighbor as _neighbor

    nr, nc, nch = _neighbor(grid, cell.row, cell.col, direction)
    if (nr, nc) not in connectors_by_pos:
        return False
    neighbor_cell = connectors_by_pos[(nr, nc)]
    cdef_a = CONNECTOR_MAP.get(cell.char)
    cdef_b = CONNECTOR_MAP.get(neighbor_cell.char)
    if cdef_a is None or cdef_b is None:
        return False
    opposite = OPPOSITE[direction]
    return direction in cdef_a.directions and opposite in cdef_b.directions


def _has_any_connection(
    connectors_by_pos: dict[tuple[int, int], "ConnectorCell"],
    cell: "ConnectorCell",
    grid: "Grid",
) -> bool:
    """Check if cell has ANY direct connection in any expected direction."""
    for direction in cell.expected:
        if direction in (UP, DOWN, LEFT, RIGHT):
            if _has_connection(connectors_by_pos, cell, direction, grid):
                return True
    return False


# ── Bounding box helpers ─────────────────────────────────────────────────────


def _bounding_box(cells: list["ConnectorCell"]) -> tuple[int, int, int, int]:
    """Return (min_row, max_row, min_col, max_col) in 0-indexed coords."""
    if not cells:
        return 0, 0, 0, 0
    min_r = min(c.row for c in cells)
    max_r = max(c.row for c in cells)
    min_c = min(c.col for c in cells)
    max_c = max(c.col for c in cells)
    return min_r, max_r, min_c, max_c


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ORPHAN DETECTION
# ═══════════════════════════════════════════════════════════════════════════════


def detect_orphans(
    grid: "Grid",
    connectors: "list[ConnectorCell]",
    components: "list[Component]",
) -> list[dict]:
    """Detect fully isolated orphans and component orphans.

    FR-008, FR-009, FR-011, AC-013, AC-014, EC-016–022, EC-029.
    """
    issues: list[dict] = []

    if not connectors or not components:
        return issues

    # Build position → connector lookup
    connectors_by_pos: dict[tuple[int, int], "ConnectorCell"] = {
        (c.row, c.col): c for c in connectors
    }

    # ── Fully isolated orphans (size 1, no direct connections) ──

    for cell in connectors:
        cdef = CONNECTOR_MAP.get(cell.char)
        if cdef is None:
            continue

        has_conn = _has_any_connection(connectors_by_pos, cell, grid)

        if has_conn:
            continue  # Not an orphan

        # Special handling for circles (FR-011, EC-020, EC-021)
        if cell.char in CIRCLE_CHARS:
            # Check if any connector exists within Chebyshev distance
            any_nearby = False
            very_nearby = False  # exactly distance 1
            for dr in (-2, -1, 0, 1, 2):
                for dc in (-2, -1, 0, 1, 2):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = cell.row + dr, cell.col + dc
                    if (nr, nc) in connectors_by_pos:
                        any_nearby = True
                        dist = max(abs(dr), abs(dc))
                        if dist == 1:
                            # Adjacent but not connected → warning (EC-021)
                            very_nearby = True
            if not any_nearby:
                # >1 cell away from any connector → intentional label, skip (EC-020)
                continue
            if very_nearby:
                # Exactly 1 cell away, not connecting → warning, don't auto-remove
                line, col = _to_1idx(cell.row, cell.col)
                issues.append(
                    _issue(
                        line, col, "warning", "orphan",
                        f"Circle '{cell.char}' is 1 cell from a connector but not connected — possible orphan",
                        fixable=False,
                    )
                )
                continue
            # Circle touching a connector? Then it would have has_conn=True and we'd skip.
            continue

        # Diagonals that are isolated → warning (EC-022)
        if cell.char in DIAGONAL_CHARS:
            line, col = _to_1idx(cell.row, cell.col)
            issues.append(
                _issue(
                    line, col, "warning", "orphan",
                    f"Diagonal '{cell.char}' has no connected diagonal neighbor",
                    fixable=True,
                    fix_suggestion=f"Remove diagonal '{cell.char}' at ({line},{col})",
                )
            )
            continue

        # ASCII junction (+) can't be fully isolated (loose mode accepts anything)
        if cell.char == "+":
            line, col = _to_1idx(cell.row, cell.col)
            issues.append(
                _issue(
                    line, col, "warning", "orphan",
                    f"ASCII junction '+' at ({line},{col}) has no connections — likely orphan",
                    fixable=True,
                    fix_suggestion=f"Remove '+' at ({line},{col})",
                )
            )
            continue

        # Arrow heads — broken arrow orphan (AC-015, EC-018)
        if cell.char in ARROW_HEAD_CHARS:
            line, col = _to_1idx(cell.row, cell.col)
            issues.append(
                _issue(
                    line, col, "error", "orphan",
                    f"Arrow head '{cell.char}' points at empty space — broken arrow",
                    fixable=True,
                    fix_suggestion=f"Remove arrow head '{cell.char}' at ({line},{col})",
                )
            )
            continue

        # Full arrows — orphan if no connections on either side (EC-029)
        if cell.char in FULL_ARROW_CHARS:
            line, col = _to_1idx(cell.row, cell.col)
            issues.append(
                _issue(
                    line, col, "error", "orphan",
                    f"Full arrow '{cell.char}' has no connections — broken arrow",
                    fixable=True,
                    fix_suggestion=f"Remove arrow '{cell.char}' at ({line},{col})",
                )
            )
            continue

        # Standard fully isolated orphan (error severity)
        line, col = _to_1idx(cell.row, cell.col)
        issues.append(
            _issue(
                line, col, "error", "orphan",
                f"Fully isolated connector '{cell.char}' at ({line},{col}) — no connections in expected directions",
                fixable=True,
                fix_suggestion=f"Replace '{cell.char}' at ({line},{col}) with space",
            )
        )

    # ── Component orphans (EC-012) ──

    if len(components) >= 2:
        largest_size = components[0].size
        total_connectors = sum(c.size for c in components)

        # >50% threshold for "clearly dominant" component
        if largest_size > total_connectors * 0.5:
            # All non-largest components are orphans
            for comp in components[1:]:
                min_r, max_r, min_c, max_c = _bounding_box(comp.cells)
                end_l, end_c = _to_1idx(max_r, max_c)
                for cell in comp.cells:
                    line, col = _to_1idx(cell.row, cell.col)
                    issues.append(
                        _issue(
                            line, col, "error", "orphan",
                            f"Component orphan: '{cell.char}' is part of a disconnected fragment (size {comp.size})",
                            fixable=True,
                            fix_suggestion=f"Remove '{cell.char}' at ({line},{col}) — part of orphan component",
                            end_line=end_l,
                            end_col=end_c,
                        )
                    )

    return issues


# ═══════════════════════════════════════════════════════════════════════════════
# 6. GAP DETECTION
# ═══════════════════════════════════════════════════════════════════════════════


def detect_gaps(
    grid: "Grid",
    connectors: "list[ConnectorCell]",
) -> list[dict]:
    """Ray-cast from each connector along expected directions to find gaps.

    FR-007, FR-016, AC-007, EC-006.
    """
    issues: list[dict] = []

    if not connectors:
        return issues

    connectors_by_pos: dict[tuple[int, int], "ConnectorCell"] = {
        (c.row, c.col): c for c in connectors
    }

    # Track which gaps we've already reported to avoid duplicates
    reported: set[tuple[int, int, str]] = set()

    cardinal = [UP, DOWN, LEFT, RIGHT]

    for cell in connectors:
        for direction in cardinal:
            if direction not in cell.expected:
                continue

            # Ray-cast in this direction
            dr, dc = {
                UP: (-1, 0),
                DOWN: (1, 0),
                LEFT: (0, -1),
                RIGHT: (0, 1),
            }[direction]

            r, c = cell.row + dr, cell.col + dc
            gap_cells: list[tuple[int, int]] = []

            while True:
                # Stop if we've left the grid entirely (grid.get returns " " for OOB)
                if r < 0 or r >= grid.height or c < 0 or c >= grid.width:
                    break
                ch = grid.get(r, c)
                if ch == " " or (ch not in CONNECTOR_MAP and ch != " "):
                    # Empty or non-connector — part of the gap
                    if ch == " ":
                        gap_cells.append((r, c))
                    r += dr
                    c += dc
                elif ch in CONNECTOR_MAP and (r, c) in connectors_by_pos:
                    # Found another connector
                    target = connectors_by_pos[(r, c)]
                    # Check bidirectional: does target expect connection back?
                    opposite = OPPOSITE[direction]
                    if opposite in target.expected:
                        # Valid connection exists, but we found a gap
                        if gap_cells:
                            gap_count = len(gap_cells)
                            # Determine if the gap is purely empty cells
                            # Skip gaps containing non-connector content
                            gap_line, gap_col = _to_1idx(
                                gap_cells[0][0], gap_cells[0][1]
                            )
                            end_l, end_c = _to_1idx(
                                gap_cells[-1][0], gap_cells[-1][1]
                            )

                            # Avoid duplicate reports (same gap from different direction)
                            gap_key = (gap_cells[0][0], gap_cells[0][1], direction)
                            if gap_key in reported:
                                break
                            reported.add(gap_key)

                            # Determine fill character
                            fill_char = _get_fill_char(direction, cell, target)
                            is_fixable = gap_count == 1 and fill_char is not None

                            msg = (
                                f"Connectivity gap: {gap_count} empty cell(s) "
                                f"between '{cell.char}' at ({cell.row + 1},{cell.col + 1}) "
                                f"and '{target.char}' at ({target.row + 1},{target.col + 1})"
                            )

                            fix_suggestion = None
                            if is_fixable and fill_char:
                                fix_suggestion = (
                                    f"Insert '{fill_char}' at ({gap_line},{gap_col})"
                                )

                            issues.append(
                                _issue(
                                    gap_line,
                                    gap_col,
                                    "error",
                                    "gap",
                                    msg,
                                    fixable=is_fixable,
                                    fix_suggestion=fix_suggestion,
                                    end_line=end_l,
                                    end_col=end_c,
                                )
                            )
                    break  # Stop ray at connector regardless
                else:
                    # Hit edge or non-connector content
                    break

    return issues


def _get_fill_char(
    direction: str, source: "ConnectorCell", target: "ConnectorCell"
) -> str | None:
    """Determine the fill character for a gap."""
    if direction in (UP, DOWN):
        # Vertical gap — prefer single vertical, match target's style
        if target.char in VERTICAL_CHARS:
            return target.char
        return "│"
    else:
        # Horizontal gap
        if target.char in HORIZONTAL_CHARS:
            return target.char
        return "─"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. BOX ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════


def detect_box_widths(
    grid: "Grid",
    components: "list[Component]",
) -> list[dict]:
    """Identify boxes and detect top/bottom border width mismatches.

    FR-012, AC-003, AC-008, FR-017, EC-023.
    """
    issues: list[dict] = []

    for comp in components:
        issues.extend(_detect_box_widths_in_component(grid, comp))

    return issues


def _detect_box_widths_in_component(
    grid: "Grid", comp: "Component"
) -> list[dict]:
    """Detect box width issues within a single component.

    Algorithm (FR-012):
    1. Find a top-left corner ┌
    2. Find closest top-right corner ┐ to its right on same row
    3. Find bottom-left corner └ at same column as ┌, on a row below
    4. Find bottom-right corner ┘ on same row as └ (to the right of └)
    5. Compare top span vs bottom span
    """
    issues: list[dict] = []

    for tl in comp.cells:
        if tl.char not in ("┌", "╔"):
            continue

        # Find matching top-right corner on same row (greedy: closest to the right)
        tr_candidates = [
            c for c in comp.cells
            if c.char in ("┐", "╗") and c.row == tl.row and c.col > tl.col
        ]
        if not tr_candidates:
            continue
        tr = min(tr_candidates, key=lambda c: c.col)
        top_width = tr.col - tl.col - 1

        # Find bottom-left corner at same column, below
        bl_candidates = [
            c for c in comp.cells
            if c.char in ("└", "╚") and c.col == tl.col and c.row > tl.row
        ]
        if not bl_candidates:
            continue
        bl = min(bl_candidates, key=lambda c: c.row)

        # Find bottom-right corner on same row as bl (to the right)
        br_candidates = [
            c for c in comp.cells
            if c.char in ("┘", "╝") and c.row == bl.row and c.col > bl.col
        ]
        if not br_candidates:
            continue
        br = min(br_candidates, key=lambda c: c.col)

        bottom_width = br.col - bl.col - 1

        if top_width != bottom_width:
            line, col = _to_1idx(tl.row, tl.col)
            end_l, end_c = _to_1idx(bl.row, br.col)
            is_fixable = True

            issues.append(
                _issue(
                    line,
                    col,
                    "error",
                    "box_width",
                    f"Box width mismatch: top border spans {top_width} cell(s), "
                    f"bottom border spans {bottom_width} cell(s)",
                    fixable=is_fixable,
                    fix_suggestion=(
                        f"Normalize box width to {max(top_width, bottom_width)}"
                    ),
                    end_line=end_l,
                    end_col=end_c,
                )
            )

    return issues


# ═══════════════════════════════════════════════════════════════════════════════
# 8. STYLE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════


def detect_style_mix(
    components: "list[Component]",
) -> list[dict]:
    """Detect mixed single/double line characters within components.

    FR-013, AC-004, AC-009, EC-030.
    """
    issues: list[dict] = []

    for comp in components:
        # Count styles (only box-drawing characters)
        single_count = sum(
            1 for c in comp.cells if c.char in SINGLE_LINE_CHARS
        )
        double_count = sum(
            1 for c in comp.cells if c.char in DOUBLE_LINE_CHARS
        )
        ascii_count = sum(
            1 for c in comp.cells if c.char in ASCII_CONNECTOR_CHARS
        )
        total_box = single_count + double_count

        # Unicode/ASCII mixing (EC-030) — info only
        if ascii_count > 0 and total_box > 0:
            line, col = _to_1idx(comp.cells[0].row, comp.cells[0].col)
            min_r, max_r, min_c, max_c = _bounding_box(comp.cells)
            end_l, end_c = _to_1idx(max_r, max_c)
            issues.append(
                _issue(
                    line, col, "info", "style_mix",
                    f"Component mixes Unicode box-drawing ({total_box} chars) with "
                    f"ASCII connectors ({ascii_count} chars) — cannot auto-convert",
                    fixable=False,
                    end_line=end_l,
                    end_col=end_c,
                )
            )
            continue  # Skip single/double check for mixed ASCII/Unicode

        # Single/double mixing
        if single_count > 0 and double_count > 0:
            line, col = _to_1idx(comp.cells[0].row, comp.cells[0].col)
            min_r, max_r, min_c, max_c = _bounding_box(comp.cells)
            end_l, end_c = _to_1idx(max_r, max_c)

            total = single_count + double_count
            single_pct = single_count / total if total > 0 else 0
            double_pct = double_count / total if total > 0 else 0

            # >80% threshold for fixability (AC-009)
            threshold = 0.8
            is_fixable = single_pct > threshold or double_pct > threshold
            majority_style = "single-line" if single_pct >= double_pct else "double-line"

            msg = (
                f"Style inconsistency: component mixes single-line ({single_count}) "
                f"and double-line ({double_count}) box-drawing characters"
            )

            fix_suggestion = None
            if is_fixable:
                fix_suggestion = (
                    f"Unify component to {majority_style} style "
                    f"({max(single_pct, double_pct):.0%} majority)"
                )

            issues.append(
                _issue(
                    line, col, "warning", "style_mix",
                    msg,
                    fixable=is_fixable,
                    fix_suggestion=fix_suggestion,
                    end_line=end_l,
                    end_col=end_c,
                )
            )

    return issues


# ═══════════════════════════════════════════════════════════════════════════════
# 9. CROSS / ARROW / CIRCLE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


def detect_cross_arrow_circle(
    grid: "Grid",
    connectors: "list[ConnectorCell]",
    components: "list[Component]",
) -> list[dict]:
    """Validate crosses, arrow heads, full arrows, and circles.

    FR-021, AC-005, AC-006, EC-005, EC-029.
    """
    issues: list[dict] = []

    connectors_by_pos: dict[tuple[int, int], "ConnectorCell"] = {
        (c.row, c.col): c for c in connectors
    }

    for cell in connectors:
        # ── Cross validation (FR-021, AC-005, EC-005) ──
        if cell.char in CROSS_CHARS:
            connected_count = 0
            for direction in (UP, DOWN, LEFT, RIGHT):
                if _has_connection(connectors_by_pos, cell, direction, grid):
                    connected_count += 1
            if connected_count < 4:
                line, col = _to_1idx(cell.row, cell.col)
                issues.append(
                    _issue(
                        line, col, "warning", "dangling_junction",
                        f"Cross '{cell.char}' has connections in only "
                        f"{connected_count}/4 directions — may be decorative",
                        fixable=False,
                    )
                )

        # ── Arrow head validation (AC-006, EC-018) ──
        # Already handled by orphan detection

        # ── Full arrow validation (EC-029) ──
        # Already handled by orphan detection

    return issues
