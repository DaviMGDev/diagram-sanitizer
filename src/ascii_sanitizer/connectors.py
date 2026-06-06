"""Connector character classification and direction expectations.

Maps every Unicode box-drawing, arrow, and circle character to the
cardinal directions in which it expects a connection. Based on
Appendix A of the SPEC.md.
"""

from __future__ import annotations

from enum import Enum, auto


class Dir(Enum):
    """Cardinal direction."""
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


# ---- Single-line box-drawing characters ----

_SINGLE_LINE: dict[str, set[Dir]] = {
    "─": {Dir.LEFT, Dir.RIGHT},
    "│": {Dir.UP, Dir.DOWN},
    "┌": {Dir.RIGHT, Dir.DOWN},
    "┐": {Dir.LEFT, Dir.DOWN},
    "└": {Dir.RIGHT, Dir.UP},
    "┘": {Dir.LEFT, Dir.UP},
    "├": {Dir.UP, Dir.DOWN, Dir.RIGHT},
    "┤": {Dir.UP, Dir.DOWN, Dir.LEFT},
    "┬": {Dir.LEFT, Dir.RIGHT, Dir.DOWN},
    "┴": {Dir.LEFT, Dir.RIGHT, Dir.UP},
    "┼": {Dir.UP, Dir.DOWN, Dir.LEFT, Dir.RIGHT},
}

# ---- Double-line box-drawing characters ----

_DOUBLE_LINE: dict[str, set[Dir]] = {
    "═": {Dir.LEFT, Dir.RIGHT},
    "║": {Dir.UP, Dir.DOWN},
    "╔": {Dir.RIGHT, Dir.DOWN},
    "╗": {Dir.LEFT, Dir.DOWN},
    "╚": {Dir.RIGHT, Dir.UP},
    "╝": {Dir.LEFT, Dir.UP},
    "╠": {Dir.UP, Dir.DOWN, Dir.RIGHT},
    "╣": {Dir.UP, Dir.DOWN, Dir.LEFT},
    "╦": {Dir.LEFT, Dir.RIGHT, Dir.DOWN},
    "╩": {Dir.LEFT, Dir.RIGHT, Dir.UP},
    "╬": {Dir.UP, Dir.DOWN, Dir.LEFT, Dir.RIGHT},
}

# ---- Arrow heads ----

_ARROW_HEADS: dict[str, set[Dir]] = {
    "▶": {Dir.LEFT},   # Right-pointing head expects line from left
    "◀": {Dir.RIGHT},  # Left-pointing head expects line from right
    "▼": {Dir.UP},     # Down-pointing head expects line from above
    "▲": {Dir.DOWN},   # Up-pointing head expects line from below
}

# ---- Full arrows (continuation expected in both directions) ----

_FULL_ARROWS: dict[str, set[Dir]] = {
    "→": {Dir.LEFT, Dir.RIGHT},
    "←": {Dir.LEFT, Dir.RIGHT},
    "↑": {Dir.UP, Dir.DOWN},
    "↓": {Dir.UP, Dir.DOWN},
}

# ---- Circles (loose — any direction is acceptable) ----

_CIRCLES: dict[str, set[Dir]] = {
    "●": {Dir.UP, Dir.DOWN, Dir.LEFT, Dir.RIGHT},
    "○": {Dir.UP, Dir.DOWN, Dir.LEFT, Dir.RIGHT},
}

# ---- Diagonal lines (loose) ----

_DIAGONALS: dict[str, set[Dir]] = {
    "╲": set(),
    "╱": set(),
}

# ---- ASCII fallbacks ----

_ASCII: dict[str, set[Dir]] = {
    "+": {Dir.UP, Dir.DOWN, Dir.LEFT, Dir.RIGHT},
    "-": {Dir.LEFT, Dir.RIGHT},
    "|": {Dir.UP, Dir.DOWN},
}

# ---- Complete map ----

CONNECTOR_MAP: dict[str, set[Dir]] = {}
CONNECTOR_MAP.update(_SINGLE_LINE)
CONNECTOR_MAP.update(_DOUBLE_LINE)
CONNECTOR_MAP.update(_ARROW_HEADS)
CONNECTOR_MAP.update(_FULL_ARROWS)
CONNECTOR_MAP.update(_CIRCLES)
CONNECTOR_MAP.update(_DIAGONALS)
CONNECTOR_MAP.update(_ASCII)

# ---- Character sets for quick classification ----

SINGLE_LINE_CHARS: frozenset[str] = frozenset(_SINGLE_LINE)
DOUBLE_LINE_CHARS: frozenset[str] = frozenset(_DOUBLE_LINE)
ARROW_HEAD_CHARS: frozenset[str] = frozenset(_ARROW_HEADS)
FULL_ARROW_CHARS: frozenset[str] = frozenset(_FULL_ARROWS)
CIRCLE_CHARS: frozenset[str] = frozenset(_CIRCLES)
DIAGONAL_CHARS: frozenset[str] = frozenset(_DIAGONALS)
ASCII_CHARS: frozenset[str] = frozenset(_ASCII)

# Box-drawing characters (single + double)
BOX_DRAWING_CHARS: frozenset[str] = frozenset(_SINGLE_LINE) | frozenset(_DOUBLE_LINE)

# All connector characters
ALL_CONNECTORS: frozenset[str] = frozenset(CONNECTOR_MAP)


# ---- Single ↔ Double line character mapping (for style unification) ----

_SINGLE_TO_DOUBLE: dict[str, str] = {
    "─": "═", "│": "║", "┌": "╔", "┐": "╗",
    "└": "╚", "┘": "╝", "├": "╠", "┤": "╣",
    "┬": "╦", "┴": "╩", "┼": "╬",
}

_DOUBLE_TO_SINGLE: dict[str, str] = {v: k for k, v in _SINGLE_TO_DOUBLE.items()}

_SINGLE_TO_DOUBLE.update(_DOUBLE_TO_SINGLE)  # bidirectional map


def to_single_line(char: str) -> str:
    """Convert a double-line char to single-line, or return unchanged."""
    return _DOUBLE_TO_SINGLE.get(char, char)


def to_double_line(char: str) -> str:
    """Convert a single-line char to double-line, or return unchanged."""
    return _SINGLE_TO_DOUBLE.get(char, char)


# ---- Lookup functions ----

def is_connector(char: str) -> bool:
    """Check if a character is a recognized connector."""
    return char in CONNECTOR_MAP


def expected_directions(char: str) -> set[Dir]:
    """Get the set of directions a connector expects connections in."""
    return CONNECTOR_MAP.get(char, set())


def is_single_line(char: str) -> bool:
    """Check if a character is a single-line box-drawing character."""
    return char in SINGLE_LINE_CHARS


def is_double_line(char: str) -> bool:
    """Check if a character is a double-line box-drawing character."""
    return char in DOUBLE_LINE_CHARS


def is_horizontal(char: str) -> bool:
    """Check if a character expects horizontal connections (─, ═)."""
    return char in ("─", "═", "-")


def is_vertical(char: str) -> bool:
    """Check if a character expects vertical connections (│, ║)."""
    return char in ("│", "║", "|")
