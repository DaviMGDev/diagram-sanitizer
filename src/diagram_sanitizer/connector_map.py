"""Connector character definitions — Appendix A of the spec.

Maps every recognized connector character to its expected connection
directions and connection mode. Also provides character classification
sets and style-unification lookup tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet

# ── Direction constants ────────────────────────────────────────────────────

UP = "up"
DOWN = "down"
LEFT = "left"
RIGHT = "right"

ALL_DIRECTIONS: FrozenSet[str] = frozenset({UP, DOWN, LEFT, RIGHT})

OPPOSITE: dict[str, str] = {
    UP: DOWN,
    DOWN: UP,
    LEFT: RIGHT,
    RIGHT: LEFT,
}

# ── Connection modes ────────────────────────────────────────────────────────

STRICT = "strict"
"""All listed directions MUST have a connection (corners, T-junctions, arrow heads)."""

AT_LEAST_ONE = "at_least_one"
"""At least ONE of the listed directions must connect (line segments — endpoints valid)."""

LOOSE = "loose"
"""Any direction accepted; disconnected → warning only (+, circles, diagonals)."""


# ── ConnectorDef ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ConnectorDef:
    """Definition of a single connector character's expected connectivity."""

    directions: FrozenSet[str]
    """The set of directions this character expects connections in."""
    mode: str
    """How strictly those directions are enforced: 'strict', 'at_least_one', or 'loose'."""


# ── Helper to build the map ─────────────────────────────────────────────────

def _d(*dirs: str) -> FrozenSet[str]:
    """Shorthand for creating a frozen set of directions."""
    return frozenset(dirs)


# ── Connector character map ─────────────────────────────────────────────────

CONNECTOR_MAP: dict[str, ConnectorDef] = {
    # ─ Single-line box drawing ─
    "─": ConnectorDef(_d(LEFT, RIGHT), AT_LEAST_ONE),
    "│": ConnectorDef(_d(UP, DOWN), AT_LEAST_ONE),
    "┌": ConnectorDef(_d(RIGHT, DOWN), STRICT),
    "┐": ConnectorDef(_d(LEFT, DOWN), STRICT),
    "└": ConnectorDef(_d(RIGHT, UP), STRICT),
    "┘": ConnectorDef(_d(LEFT, UP), STRICT),
    "├": ConnectorDef(_d(UP, DOWN, RIGHT), STRICT),
    "┤": ConnectorDef(_d(UP, DOWN, LEFT), STRICT),
    "┬": ConnectorDef(_d(LEFT, RIGHT, DOWN), STRICT),
    "┴": ConnectorDef(_d(LEFT, RIGHT, UP), STRICT),
    "┼": ConnectorDef(_d(UP, DOWN, LEFT, RIGHT), STRICT),
    # ─ Double-line box drawing ─
    "═": ConnectorDef(_d(LEFT, RIGHT), AT_LEAST_ONE),
    "║": ConnectorDef(_d(UP, DOWN), AT_LEAST_ONE),
    "╔": ConnectorDef(_d(RIGHT, DOWN), STRICT),
    "╗": ConnectorDef(_d(LEFT, DOWN), STRICT),
    "╚": ConnectorDef(_d(RIGHT, UP), STRICT),
    "╝": ConnectorDef(_d(LEFT, UP), STRICT),
    "╠": ConnectorDef(_d(UP, DOWN, RIGHT), STRICT),
    "╣": ConnectorDef(_d(UP, DOWN, LEFT), STRICT),
    "╦": ConnectorDef(_d(LEFT, RIGHT, DOWN), STRICT),
    "╩": ConnectorDef(_d(LEFT, RIGHT, UP), STRICT),
    "╬": ConnectorDef(_d(UP, DOWN, LEFT, RIGHT), STRICT),
    # ─ Arrow heads ─
    "▶": ConnectorDef(_d(LEFT), STRICT),
    "◀": ConnectorDef(_d(RIGHT), STRICT),
    "▼": ConnectorDef(_d(UP), STRICT),
    "▲": ConnectorDef(_d(DOWN), STRICT),
    # ─ Full arrows (continuation in both directions) ─
    "→": ConnectorDef(_d(LEFT, RIGHT), AT_LEAST_ONE),
    "←": ConnectorDef(_d(LEFT, RIGHT), AT_LEAST_ONE),
    "↑": ConnectorDef(_d(UP, DOWN), AT_LEAST_ONE),
    "↓": ConnectorDef(_d(UP, DOWN), AT_LEAST_ONE),
    # ─ Circles ─
    "●": ConnectorDef(ALL_DIRECTIONS, LOOSE),
    "○": ConnectorDef(ALL_DIRECTIONS, LOOSE),
    # ─ Diagonals ─
    "╲": ConnectorDef(ALL_DIRECTIONS, LOOSE),  # Chebyshev distance 1
    "╱": ConnectorDef(ALL_DIRECTIONS, LOOSE),
    # ─ ASCII fallbacks ─
    "+": ConnectorDef(ALL_DIRECTIONS, LOOSE),
    "-": ConnectorDef(_d(LEFT, RIGHT), AT_LEAST_ONE),
    "|": ConnectorDef(_d(UP, DOWN), AT_LEAST_ONE),
}

# ── Character classification sets ───────────────────────────────────────────

SINGLE_LINE_CHARS: FrozenSet[str] = frozenset(
    "─│┌┐└┘├┤┬┴┼"
)

DOUBLE_LINE_CHARS: FrozenSet[str] = frozenset(
    "═║╔╗╚╝╠╣╦╩╬"
)

BOX_CORNER_CHARS: FrozenSet[str] = frozenset(
    "┌┐└┘╔╗╚╝"
)

T_JUNCTION_CHARS: FrozenSet[str] = frozenset(
    "├┤┬┴╠╣╦╩"
)

CROSS_CHARS: FrozenSet[str] = frozenset(
    "┼╬"
)

ARROW_HEAD_CHARS: FrozenSet[str] = frozenset(
    "▶◀▼▲"
)

FULL_ARROW_CHARS: FrozenSet[str] = frozenset(
    "→←↑↓"
)

CIRCLE_CHARS: FrozenSet[str] = frozenset(
    "●○"
)

DIAGONAL_CHARS: FrozenSet[str] = frozenset(
    "╲╱"
)

ASCII_CONNECTOR_CHARS: FrozenSet[str] = frozenset(
    "+-|"
)

# All connector characters combined
ALL_CONNECTORS: FrozenSet[str] = frozenset(CONNECTOR_MAP.keys())

# Line-type characters (horizontal or vertical lines, including ASCII)
HORIZONTAL_CHARS: FrozenSet[str] = frozenset("─═-")
VERTICAL_CHARS: FrozenSet[str] = frozenset("│║|")

# ── Style unification mapping ───────────────────────────────────────────────

# Single-line → Double-line
SINGLE_TO_DOUBLE: dict[str, str] = {
    "─": "═",
    "│": "║",
    "┌": "╔",
    "┐": "╗",
    "└": "╚",
    "┘": "╝",
    "├": "╠",
    "┤": "╣",
    "┬": "╦",
    "┴": "╩",
    "┼": "╬",
}

# Double-line → Single-line
DOUBLE_TO_SINGLE: dict[str, str] = {v: k for k, v in SINGLE_TO_DOUBLE.items()}


def get_direction_delta(direction: str) -> tuple[int, int]:
    """Return (row_delta, col_delta) for a cardinal direction."""
    return {
        UP: (-1, 0),
        DOWN: (1, 0),
        LEFT: (0, -1),
        RIGHT: (0, 1),
    }[direction]


def get_char_style(char: str) -> str | None:
    """Return 'single', 'double', or None if not a box-drawing char."""
    if char in SINGLE_LINE_CHARS:
        return "single"
    if char in DOUBLE_LINE_CHARS:
        return "double"
    return None


def is_connector(char: str) -> bool:
    """Check if a character is a recognized connector."""
    return char in CONNECTOR_MAP


def get_expected_directions(char: str) -> FrozenSet[str] | None:
    """Get expected connection directions for a connector character, or None."""
    cdef = CONNECTOR_MAP.get(char)
    return cdef.directions if cdef else None
