"""2D character grid for ASCII diagram parsing and reconstruction."""

from __future__ import annotations


def parse(text: str, *, tab_width: int = 4) -> list[list[str]]:
    """Parse a string into a 2D grid of characters.

    - Normalizes \\r\\n → \\n
    - Expands tabs to spaces
    - Pads all rows to the same length
    - Trims trailing whitespace per row (but preserves
      interior spaces which are semantically meaningful in diagrams)
    """
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Handle empty input
    if not text:
        return []

    lines = text.split("\n")

    # Expand tabs
    lines = [_expand_tabs(line, tab_width) for line in lines]

    # Compute max width after tab expansion
    if lines:
        max_width = max(len(line) for line in lines)
    else:
        max_width = 0

    # Pad rows to max width
    grid = []
    for line in lines:
        row = list(line)
        row.extend([" "] * (max_width - len(row)))
        grid.append(row)

    return grid


def reconstruct(grid: list[list[str]]) -> str:
    """Reconstruct a string from a 2D grid.

    Trailing whitespace on each row is stripped before joining,
    since it is semantically meaningless in ASCII diagrams.
    """
    lines = []
    for row in grid:
        line = "".join(row).rstrip()
        lines.append(line)
    # Strip trailing empty lines
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _expand_tabs(line: str, tab_width: int) -> str:
    """Expand tab characters to spaces, preserving column alignment."""
    result = []
    col = 0
    for ch in line:
        if ch == "\t":
            spaces = tab_width - (col % tab_width)
            result.append(" " * spaces)
            col += spaces
        else:
            result.append(ch)
            col += 1
    return "".join(result)


def get_cell(grid: list[list[str]], row: int, col: int) -> str | None:
    """Get a cell from the grid, or None if out of bounds."""
    if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
        return grid[row][col]
    return None


def set_cell(grid: list[list[str]], row: int, col: int, char: str) -> None:
    """Set a cell in the grid. No-op if out of bounds."""
    if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
        grid[row][col] = char


def grid_dimensions(grid: list[list[str]]) -> tuple[int, int]:
    """Return (rows, cols) of the grid."""
    if not grid:
        return (0, 0)
    return (len(grid), len(grid[0]) if grid[0] else 0)
