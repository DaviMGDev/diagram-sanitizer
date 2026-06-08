"""Connected component analysis using union-find (disjoint set).

Clusters connector cells into connected components based on the
bidirectional connectivity rules defined in the spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from diagram_sanitizer.grid import ConnectorCell, Grid, neighbor
from diagram_sanitizer.connector_map import (
    CONNECTOR_MAP,
    OPPOSITE,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    DIAGONAL_CHARS,
)


@dataclass
class Component:
    """A connected component of connector cells."""

    id: int
    cells: list[ConnectorCell]
    size: int = 0

    def __post_init__(self) -> None:
        self.size = len(self.cells)


# ── Union-Find ───────────────────────────────────────────────────────────────


class UnionFind:
    """Disjoint-set data structure with path compression and union by rank."""

    def __init__(self, n: int) -> None:
        self.parent: list[int] = list(range(n))
        self.rank: list[int] = [0] * n

    def find(self, x: int) -> int:
        """Find the root of element x with path compression."""
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> None:
        """Union the sets containing x and y."""
        rx = self.find(x)
        ry = self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            self.parent[rx] = ry
        elif self.rank[rx] > self.rank[ry]:
            self.parent[ry] = rx
        else:
            self.parent[ry] = rx
            self.rank[rx] += 1


# ── Connectivity check ───────────────────────────────────────────────────────


def _are_directly_connected(
    cell_a: ConnectorCell, cell_b: ConnectorCell, direction_a_to_b: str
) -> bool:
    """Check if two adjacent cells are directly connected per the spec.

    Two connectors are directly connected if:
    - cell_a expects connection in direction_a_to_b toward cell_b, AND
    - cell_b expects connection in the OPPOSITE direction toward cell_a.
    """
    cdef_a = CONNECTOR_MAP.get(cell_a.char)
    cdef_b = CONNECTOR_MAP.get(cell_b.char)
    if cdef_a is None or cdef_b is None:
        return False

    opposite = OPPOSITE[direction_a_to_b]
    return direction_a_to_b in cdef_a.directions and opposite in cdef_b.directions


def _check_diagonal_connection(
    cell: ConnectorCell, grid: Grid
) -> list[tuple[int, int]]:
    """Check Chebyshev distance 1 neighbors for diagonal characters.

    Returns list of (row, col) of connected diagonal neighbors.
    """
    connected: list[tuple[int, int]] = []
    if cell.char not in DIAGONAL_CHARS:
        return connected

    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = cell.row + dr, cell.col + dc
            ch = grid.get(nr, nc)
            if ch in DIAGONAL_CHARS:
                connected.append((nr, nc))
    return connected


# ── Main function ────────────────────────────────────────────────────────────


def find_components(
    connectors: list[ConnectorCell], grid: Grid
) -> list[Component]:
    """Cluster connectors into connected components.

    Uses union-find with the bidirectional connectivity rule.
    Two adjacent connectors are unioned if each expects connection
    toward the other.

    Components are returned sorted by size descending (largest first).

    Args:
        connectors: List of all connector cells in row-major order.
        grid: The 2D character grid.

    Returns:
        List of Component objects sorted by size descending.
    """
    n = len(connectors)

    if n == 0:
        return []

    # Build a lookup: (row, col) → connector index
    pos_to_idx: dict[tuple[int, int], int] = {
        (c.row, c.col): i for i, c in enumerate(connectors)
    }

    uf = UnionFind(n)

    cardinal_dirs = [UP, DOWN, LEFT, RIGHT]

    for i, cell in enumerate(connectors):
        # Check cardinal neighbors
        for direction in cardinal_dirs:
            nr, nc, nch = neighbor(grid, cell.row, cell.col, direction)
            if (nr, nc) in pos_to_idx:
                j = pos_to_idx[(nr, nc)]
                neighbor_cell = connectors[j]
                if _are_directly_connected(cell, neighbor_cell, direction):
                    uf.union(i, j)

        # Check diagonal neighbors for diagonal characters
        for nr, nc in _check_diagonal_connection(cell, grid):
            if (nr, nc) in pos_to_idx:
                j = pos_to_idx[(nr, nc)]
                uf.union(i, j)

    # Group by root
    groups: dict[int, list[ConnectorCell]] = {}
    for i, cell in enumerate(connectors):
        root = uf.find(i)
        groups.setdefault(root, []).append(cell)

    # Build Component objects
    components = [
        Component(id=idx, cells=cells)
        for idx, (_, cells) in enumerate(groups.items())
    ]

    # Sort by size descending
    components.sort(key=lambda c: c.size, reverse=True)

    return components
