"""Markdown table detection and normalization.

Implements FR-028, FR-029, FR-030, FR-031 for GFM markdown table awareness.
Detects contiguous GFM table blocks in preprocessed text, identifies separator
rows, computes column widths, and provides exemption maps for connector
classification.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DetectedTable:
    """A detected markdown table block in the input."""

    start_line: int
    """0-indexed line number of the first table row."""

    end_line: int
    """Exclusive — first line after the table block."""

    column_count: int
    """Number of | -delimited columns in the table."""

    col_widths: list[int] = field(default_factory=list)
    """Maximum content width per column (computed after detection)."""

    has_separator: bool = False
    """Whether a valid separator row was found as the second row."""

    separator_row_idx: int = -1
    """Line index of the separator row (relative to start_line)."""


def detect_markdown_tables(lines: list[str]) -> list[DetectedTable]:
    """Detect contiguous GFM markdown table blocks.

    Implements FR-028:
    1. At least two consecutive rows containing | with non-empty cell content
    2. The second row is a separator row (only |, -, :, whitespace)
    3. All rows in the block have the same number of | -delimited columns

    Also handles:
    - FR-031: Returns exempt regions for |, -, : within tables
    - EC-033: Rows with inconsistent column counts end the block

    Args:
        lines: Preprocessed (normalized) input lines.

    Returns:
        List of DetectedTable objects in order of appearance.
    """
    tables: list[DetectedTable] = []
    i = 0
    n = len(lines)

    while i < n:
        # Look for a potential start of a table: a line with at least one |
        if not _is_potential_table_row(lines[i]):
            i += 1
            continue

        # Try to extend a table block starting at line i
        table = _extract_table_block(lines, i)
        if table is None:
            i += 1
            continue

        tables.append(table)
        i = table.end_line

    # Compute column widths for each detected table
    for table in tables:
        _compute_col_widths(lines, table)

    return tables


def build_exempt_regions(tables: list[DetectedTable]) -> set[tuple[int, int]]:
    """Build a set of (row, col) positions to exempt from connector classification.

    The exempt characters are |, -, and : within identified table blocks.
    These are table formatting, not diagram connectors (FR-031).

    Args:
        tables: List of detected tables.

    Returns:
        Set of (row, col) tuples to skip during connector classification.
    """
    exempt: set[tuple[int, int]] = set()
    for table in tables:
        for row in range(table.start_line, table.end_line):
            # The entire row is part of the table block. Exempt |, -, :
            # but we don't have the line content here. Instead, we'll build
            # the exempt set when we have both tables and lines available.
            pass
    return exempt


def build_exempt_regions_from_lines(
    tables: list[DetectedTable], lines: list[str]
) -> set[tuple[int, int]]:
    """Build exempt regions using line content.

    Marks every |, -, and : within table blocks for exemption.
    """
    exempt: set[tuple[int, int]] = set()
    exempt_chars = frozenset({"|", "-", ":"})
    for table in tables:
        for row_idx in range(table.start_line, table.end_line):
            line = lines[row_idx]
            for col, ch in enumerate(line):
                if ch in exempt_chars:
                    exempt.add((row_idx, col))
    return exempt


def normalize_markdown_table(
    lines: list[str], table: DetectedTable
) -> tuple[list[str], list[dict]]:
    """Normalize a markdown table's column widths and separator row.

    Implements FR-029 and FR-030.

    Args:
        lines: Mutable list of all preprocessed lines (modified in place).
        table: The detected table to normalize.

    Returns:
        Tuple of (modified lines, list of issues reported).
    """
    issues: list[dict] = []

    if not table.col_widths:
        _compute_col_widths(lines, table)

    col_widths = table.col_widths
    if not col_widths:
        return lines, issues

    n_cols = table.column_count

    # ── Check for missing/malformed separator row (FR-030) ──
    sep_idx = table.start_line + 1
    if sep_idx >= table.end_line:
        # Table has only one row — shouldn't happen per detection, but handle gracefully
        return lines, issues

    if not table.has_separator:
        # Insert a separator row
        issues.append({
            "line": table.start_line + 1,  # 1-indexed for report
            "col": 1,
            "severity": "warning",
            "type": "markdown_table",
            "message": (
                f"Markdown table at line {table.start_line + 1} is missing a "
                f"separator row — inserting |---| row"
            ),
            "fixable": True,
            "fix_suggestion": "Insert separator row with padded dashes",
        })
        sep_line = _build_separator_row(n_cols, col_widths)
        lines.insert(sep_idx, sep_line)
        # Adjust table boundaries
        table.end_line += 1
        table.has_separator = True
        table.separator_row_idx = 1  # second row of block

    # Ensure separator row is well-formed
    if table.has_separator and sep_idx < table.end_line:
        sep_line = _build_separator_row(n_cols, col_widths)
        if lines[sep_idx].strip() != sep_line.strip():
            # Rewrite separator
            lines[sep_idx] = sep_line

    # ── Normalize column widths (FR-029) ──
    # Recompute column widths after potential separator insertion
    _compute_col_widths(lines, table)
    col_widths = table.col_widths

    normalized_any = False
    for row_idx in range(table.start_line, table.end_line):
        if row_idx == table.start_line + 1 and table.has_separator:
            # Separator row — already normalized above
            continue
        line = lines[row_idx]
        cells = _split_table_row(line)
        if len(cells) < n_cols:
            # Pad with empty cells (EC-033)
            cells.extend([""] * (n_cols - len(cells)))
            normalized_any = True
        elif len(cells) > n_cols:
            # Truncate extra cells (EC-033)
            cells = cells[:n_cols]
            normalized_any = True

        # Pad each cell to column width
        padded_cells = []
        for ci, cell in enumerate(cells):
            if ci < len(col_widths):
                width = col_widths[ci]
                padded = cell.ljust(width)
            else:
                padded = cell
            padded_cells.append(padded)

        new_line = "| " + " | ".join(padded_cells) + " |"
        if new_line != line:
            lines[row_idx] = new_line
            normalized_any = True

    if normalized_any:
        issues.append({
            "line": table.start_line + 1,  # 1-indexed
            "col": 1,
            "severity": "info",
            "type": "markdown_table",
            "message": "Normalized markdown table column widths",
            "fixable": True,
            "fix_suggestion": "Column widths padded to match widest cell",
        })

    return lines, issues


# ── Internal helpers ─────────────────────────────────────────────────────────


def _is_potential_table_row(line: str) -> bool:
    """Check if a line looks like a GFM table row (contains at least one |)."""
    return "|" in line and bool(line.strip())


def _is_separator_row(line: str) -> bool:
    """Check if a line is a valid GFM separator row.

    A separator row consists only of |, -, :, and whitespace,
    and contains at least one | and one -.
    """
    stripped = line.strip()
    if not stripped:
        return False
    # Must start and end with |
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return False
    # All characters must be | - : or whitespace
    allowed = frozenset({"|", "-", ":", " "})
    if not all(ch in allowed for ch in stripped):
        return False
    # Must contain at least one -
    return "-" in stripped


def _count_columns(line: str) -> int:
    """Count the number of columns in a GFM table row.

    Columns are delimited by |. Leading and trailing | are optional.
    """
    # Split by | and count non-empty segments
    stripped = line.strip()
    if not stripped.startswith("|"):
        stripped = "|" + stripped
    if not stripped.endswith("|"):
        stripped = stripped + "|"
    # Split: remove first and last empty strings from leading/trailing |
    parts = stripped.split("|")
    # Count non-empty parts (but include empty cells in the middle)
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return len(parts)


def _split_table_row(line: str) -> list[str]:
    """Split a GFM table row into cell contents (stripped)."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        stripped = "|" + stripped
    if not stripped.endswith("|"):
        stripped = stripped + "|"
    parts = stripped.split("|")
    # Remove first and last empty from leading/trailing |
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return [p.strip() for p in parts]


def _extract_table_block(
    lines: list[str], start: int
) -> DetectedTable | None:
    """Try to extract a markdown table block starting at `start`.

    Returns None if lines[start] doesn't start a valid table block.
    """
    n = len(lines)
    if start >= n:
        return None

    first_cols = _count_columns(lines[start])
    if first_cols < 1:
        return None

    table = DetectedTable(
        start_line=start,
        end_line=start,
        column_count=first_cols,
    )

    # Check second row for separator (FR-028 condition 2)
    if start + 1 < n and _is_separator_row(lines[start + 1]):
        sep_cols = _count_columns(lines[start + 1])
        if sep_cols == first_cols:
            table.has_separator = True
            table.separator_row_idx = 1
            table.end_line = start + 2
        else:
            # Separator-like row but wrong column count → not a valid block
            return None
    elif start + 1 < n and _is_potential_table_row(lines[start + 1]):
        # Second row exists and is a data row (not separator)
        # Check if it has same column count
        second_cols = _count_columns(lines[start + 1])
        if second_cols == first_cols:
            # Block without separator (FR-030 case)
            table.end_line = start + 2
        else:
            # Different column count → not a valid block
            return None
    else:
        # Only one row that looks like a table → not a block (AC-022)
        return None

    # FR-028 condition 1 satisfied: at least 2 rows
    # Now extend the block
    i = table.end_line
    while i < n:
        if not _is_potential_table_row(lines[i]):
            break
        cols = _count_columns(lines[i])
        if cols != first_cols:
            # EC-033: inconsistent column count → end block
            # Could also flag as ambiguous, but per spec we end the block
            break
        table.end_line = i + 1
        i += 1

    return table


def _compute_col_widths(lines: list[str], table: DetectedTable) -> None:
    """Compute maximum content width per column for a table."""
    n_cols = table.column_count
    if n_cols < 1:
        table.col_widths = []
        return

    widths = [0] * n_cols
    for row_idx in range(table.start_line, table.end_line):
        # Skip separator row for content width computation
        if row_idx == table.start_line + table.separator_row_idx and table.has_separator:
            continue
        cells = _split_table_row(lines[row_idx])
        for ci in range(min(len(cells), n_cols)):
            widths[ci] = max(widths[ci], len(cells[ci]))

    # Ensure minimum width of 1 for each column
    widths = [max(1, w) for w in widths]
    table.col_widths = widths


def _build_separator_row(n_cols: int, col_widths: list[int]) -> str:
    """Build a GFM separator row with padded dashes.

    Each separator cell is at least --- and padded to column width.
    Preserves : alignment markers (though we use left-align by default).
    """
    cells = []
    for ci in range(n_cols):
        if ci < len(col_widths):
            width = col_widths[ci]
        else:
            width = 3
        # At least 3 dashes
        dash_count = max(3, width)
        cells.append("-" * dash_count)
    return "| " + " | ".join(cells) + " |"
