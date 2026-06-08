"""2D character grid for ASCII diagram analysis.

Provides the Grid class for representing a diagram as a row-major 2D
character array, plus connector classification functionality.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet

from diagram_sanitizer.connector_map import CONNECTOR_MAP, UP, DOWN, LEFT, RIGHT


@dataclass
class ConnectorCell:
    """A single connector cell in the diagram grid.

    Coordinates are 0-indexed (row, col).
    """

    row: int
    col: int
    char: str
    expected: FrozenSet[str]
    """The set of directions this character expects connections in."""


class Grid:
    """A 2D character grid for diagram analysis.

    Rows may have different lengths. Out-of-bounds access returns a space.
    Coordinates are 0-indexed.
    """

    def __init__(self, text: str) -> None:
        """Parse normalized text into a grid."""
        self.rows: list[str] = text.split("\n")
        self.height: int = len(self.rows)
        self.width: int = max((len(r) for r in self.rows), default=0)

    def get(self, row: int, col: int) -> str:
        """Get the character at (row, col), or ' ' if out of bounds."""
        if row < 0 or row >= self.height:
            return " "
        line = self.rows[row]
        if col < 0 or col >= len(line):
            return " "
        return line[col]

    def set(self, row: int, col: int, char: str) -> None:
        """Set the character at (row, col), extending the row if needed."""
        if row < 0 or row >= self.height:
            return
        line = self.rows[row]
        if col < 0:
            return
        if col >= len(line):
            # Extend row with spaces
            line = line + " " * (col - len(line) + 1)
        # Replace the character
        self.rows[row] = line[:col] + char + line[col + 1:]
        # Update width if needed
        self.width = max(self.width, len(self.rows[row]))

    def to_string(self) -> str:
        """Reconstruct the normalized diagram string with LF endings."""
        return "\n".join(self.rows)

    def __repr__(self) -> str:
        return f"Grid(height={self.height}, width={self.width})"


def classify_connectors(
    grid: Grid, exempt_regions: set[tuple[int, int]] | None = None
) -> list[ConnectorCell]:
    """Iterate the grid and identify all connector cells.

    Each connector cell is classified with its expected connection
    directions based on the connector map (Appendix A).

    Cells in exempt_regions are skipped (used for markdown table
    characters that should not be treated as connectors).

    Args:
        grid: The 2D character grid.
        exempt_regions: Optional set of (row, col) to skip.

    Returns:
        List of ConnectorCell objects in row-major order.
    """
    exempt = exempt_regions or set()
    connectors: list[ConnectorCell] = []
    for row in range(grid.height):
        line = grid.rows[row]
        for col, char in enumerate(line):
            if (row, col) in exempt:
                continue
            cdef = CONNECTOR_MAP.get(char)
            if cdef is not None:
                connectors.append(
                    ConnectorCell(
                        row=row,
                        col=col,
                        char=char,
                        expected=cdef.directions,
                    )
                )
    return connectors


def neighbor(grid: Grid, row: int, col: int, direction: str) -> tuple[int, int, str]:
    """Get the neighbor cell in the given cardinal direction.

    Returns:
        (neighbor_row, neighbor_col, neighbor_char) — the char is ' '
        if the neighbor is out of bounds.
    """
    dr, dc = _delta(direction)
    nr, nc = row + dr, col + dc
    return nr, nc, grid.get(nr, nc)


def _delta(direction: str) -> tuple[int, int]:
    """Return (row_delta, col_delta) for a cardinal direction."""
    return {
        UP: (-1, 0),
        DOWN: (1, 0),
        LEFT: (0, -1),
        RIGHT: (0, 1),
    }[direction]
