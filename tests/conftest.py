"""Shared test fixtures for diagram-sanitizer."""

import pytest


# ─── Valid diagrams ───────────────────────────────────────────────────────

@pytest.fixture
def valid_empty_box():
    """A simple valid box with no issues."""
    return "┌───┐\n│   │\n└───┘\n"


@pytest.fixture
def valid_labeled_box():
    """A valid box with a text label inside."""
    return "┌───────┐\n│ Hello │\n└───────┘\n"


@pytest.fixture
def valid_tree():
    """A simple valid tree diagram."""
    return "  ┌─ Result\n──┤\n  └─ Error\n"


@pytest.fixture
def valid_flowchart():
    """A multi-box flowchart."""
    return (
        "┌──────┐     ┌──────┐\n"
        "│ Start│────▶│ End  │\n"
        "└──────┘     └──────┘\n"
    )


# ─── Problematic diagrams ─────────────────────────────────────────────────

@pytest.fixture
def orphan_vbar():
    """A standalone vertical bar with no connections."""
    return "some text\n  │\nmore text\n"


@pytest.fixture
def orphan_hbar():
    """A standalone horizontal bar with no connections."""
    return "text ─── text\n"


@pytest.fixture
def orphan_corner_fragment():
    """A partial box corner with no matching side."""
    return "  └─\n"


@pytest.fixture
def orphan_component():
    """A small connected component disconnected from the main diagram."""
    return "┌───┐     ┌─┐\n│ A │     └─┘\n└───┘\n"


@pytest.fixture
def box_width_mismatch():
    """Box with different top and bottom widths."""
    return "┌───┐\n│ X │\n└─┘\n"


@pytest.fixture
def box_width_mismatch_wide():
    """Box where bottom is wider than top."""
    return "┌─┐\n│X│\n└───┘\n"


@pytest.fixture
def single_cell_gap():
    """A box with a single-cell gap in the bottom edge."""
    return "┌─┐\n│ │\n└ ┘\n"


@pytest.fixture
def multi_cell_gap():
    """A gap larger than 1 cell — not auto-fixable."""
    return "┌───┐\n│   │\n└   ┘\n"


@pytest.fixture
def mixed_style():
    """Diagram mixing single-line and double-line characters."""
    return "┌─┐\n║X║\n└─┘\n"


@pytest.fixture
def dangling_cross():
    """A cross with only 3 connected directions."""
    return "  │\n──┼\n"


@pytest.fixture
def broken_arrow_head():
    """Arrow head pointing at empty space."""
    return "text ▶\n"


@pytest.fixture
def nested_boxes():
    """A box containing another box inside."""
    return "┌───────┐\n│ ┌───┐ │\n│ └───┘ │\n└───────┘\n"


@pytest.fixture
def ascii_only():
    """Diagram using only ASCII connectors."""
    return "+---+\n| A |\n+---+\n"


@pytest.fixture
def mixed_unicode_ascii():
    """Diagram mixing Unicode and ASCII connectors."""
    return "┌───┐\n| X |\n+───┘\n"


@pytest.fixture
def circle_label():
    """A circle used as a node label marker."""
    return "┌──●──┐\n│ Node│\n└─────┘\n"


@pytest.fixture
def circle_near_vbar():
    """A circle exactly 1 cell away from a vertical bar."""
    return "│ ●\n"


@pytest.fixture
def tabs_in_input():
    """Input with tab characters."""
    return "\t┌─┐\n\t└─┘\n"


@pytest.fixture
def ansi_input():
    """Input with ANSI escape codes."""
    return "\x1b[31m┌─┐\x1b[0m\n\x1b[32m└─┘\x1b[0m\n"


@pytest.fixture
def bom_input():
    """Input starting with UTF-8 BOM."""
    return "\ufeff┌─┐\n└─┘\n"


@pytest.fixture
def crlf_input():
    """Input with Windows-style line endings."""
    return "┌─┐\r\n└─┘\r\n"


@pytest.fixture
def trailing_whitespace():
    """Input with trailing whitespace."""
    return "┌─┐   \n└─┘  \n"


@pytest.fixture
def very_wide_diagram():
    """A diagram wider than 200 columns."""
    inner = "─" * 250
    return f"┌{inner}┐\n└{'─' * 250}┘\n"


@pytest.fixture
def all_horizontal_lines():
    """Diagram consisting entirely of horizontal lines."""
    return "────\n\n────\n"


@pytest.fixture
def all_vertical_lines():
    """Diagram consisting entirely of vertical lines."""
    return "│\n│\n \n│\n│\n"


@pytest.fixture
def orphan_full_arrow():
    """A full arrow with no connections on either side."""
    return "text → text\n"


@pytest.fixture
def crossed_lines_no_junction():
    """Lines that cross without a junction character."""
    return "  │\n── ──\n  │\n"


@pytest.fixture
def three_sided_box():
    """A box with only three sides — missing bottom."""
    return "┌──┐\n│  │\n"


@pytest.fixture
def overlapping_components():
    """Two components that share cells."""
    return "┌───┐\n│┌─┐│\n│└─┘│\n└───┘\n"
