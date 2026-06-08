"""Tests for connector_map.py — verify Appendix A character definitions."""

from diagram_sanitizer.connector_map import (
    CONNECTOR_MAP,
    SINGLE_LINE_CHARS,
    DOUBLE_LINE_CHARS,
    BOX_CORNER_CHARS,
    T_JUNCTION_CHARS,
    CROSS_CHARS,
    ARROW_HEAD_CHARS,
    FULL_ARROW_CHARS,
    CIRCLE_CHARS,
    DIAGONAL_CHARS,
    ASCII_CONNECTOR_CHARS,
    ALL_CONNECTORS,
    HORIZONTAL_CHARS,
    VERTICAL_CHARS,
    SINGLE_TO_DOUBLE,
    DOUBLE_TO_SINGLE,
    STRICT,
    AT_LEAST_ONE,
    LOOSE,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    OPPOSITE,
    get_direction_delta,
    get_char_style,
    is_connector,
    get_expected_directions,
)


class TestConnectorMapCompleteness:
    """Ensure every character from Appendix A is present."""

    def test_all_single_line_present(self):
        for ch in SINGLE_LINE_CHARS:
            assert ch in CONNECTOR_MAP, f"Missing single-line char: {ch}"

    def test_all_double_line_present(self):
        for ch in DOUBLE_LINE_CHARS:
            assert ch in CONNECTOR_MAP, f"Missing double-line char: {ch}"

    def test_all_arrow_heads_present(self):
        for ch in ARROW_HEAD_CHARS:
            assert ch in CONNECTOR_MAP, f"Missing arrow head: {ch}"

    def test_all_full_arrows_present(self):
        for ch in FULL_ARROW_CHARS:
            assert ch in CONNECTOR_MAP, f"Missing full arrow: {ch}"

    def test_all_circles_present(self):
        for ch in CIRCLE_CHARS:
            assert ch in CONNECTOR_MAP, f"Missing circle: {ch}"

    def test_all_diagonals_present(self):
        for ch in DIAGONAL_CHARS:
            assert ch in CONNECTOR_MAP, f"Missing diagonal: {ch}"

    def test_all_ascii_present(self):
        for ch in ASCII_CONNECTOR_CHARS:
            assert ch in CONNECTOR_MAP, f"Missing ASCII connector: {ch}"

    def test_all_connectors_union_matches_map(self):
        assert ALL_CONNECTORS == frozenset(CONNECTOR_MAP.keys())


class TestConnectorDefinitions:
    """Verify correct directions and modes for each connector type."""

    # ── Horizontal lines ──
    def test_horizontal_line_single(self):
        cdef = CONNECTOR_MAP["─"]
        assert cdef.mode == AT_LEAST_ONE
        assert LEFT in cdef.directions
        assert RIGHT in cdef.directions
        assert UP not in cdef.directions
        assert DOWN not in cdef.directions

    def test_horizontal_line_double(self):
        cdef = CONNECTOR_MAP["═"]
        assert cdef.mode == AT_LEAST_ONE
        assert LEFT in cdef.directions
        assert RIGHT in cdef.directions

    def test_horizontal_line_ascii(self):
        cdef = CONNECTOR_MAP["-"]
        assert cdef.mode == AT_LEAST_ONE
        assert LEFT in cdef.directions
        assert RIGHT in cdef.directions

    # ── Vertical lines ──
    def test_vertical_line_single(self):
        cdef = CONNECTOR_MAP["│"]
        assert cdef.mode == AT_LEAST_ONE
        assert UP in cdef.directions
        assert DOWN in cdef.directions

    def test_vertical_line_double(self):
        cdef = CONNECTOR_MAP["║"]
        assert cdef.mode == AT_LEAST_ONE
        assert UP in cdef.directions
        assert DOWN in cdef.directions

    def test_vertical_line_ascii(self):
        cdef = CONNECTOR_MAP["|"]
        assert cdef.mode == AT_LEAST_ONE
        assert UP in cdef.directions
        assert DOWN in cdef.directions

    # ── Corners ──
    def test_top_left_corner(self):
        cdef = CONNECTOR_MAP["┌"]
        assert cdef.mode == STRICT
        assert cdef.directions == frozenset({RIGHT, DOWN})

    def test_top_right_corner(self):
        cdef = CONNECTOR_MAP["┐"]
        assert cdef.mode == STRICT
        assert cdef.directions == frozenset({LEFT, DOWN})

    def test_bottom_left_corner(self):
        cdef = CONNECTOR_MAP["└"]
        assert cdef.mode == STRICT
        assert cdef.directions == frozenset({RIGHT, UP})

    def test_bottom_right_corner(self):
        cdef = CONNECTOR_MAP["┘"]
        assert cdef.mode == STRICT
        assert cdef.directions == frozenset({LEFT, UP})

    # ── T-junctions ──
    def test_t_right(self):
        cdef = CONNECTOR_MAP["├"]
        assert cdef.mode == STRICT
        assert cdef.directions == frozenset({UP, DOWN, RIGHT})

    def test_t_left(self):
        cdef = CONNECTOR_MAP["┤"]
        assert cdef.mode == STRICT
        assert cdef.directions == frozenset({UP, DOWN, LEFT})

    def test_t_down(self):
        cdef = CONNECTOR_MAP["┬"]
        assert cdef.mode == STRICT
        assert cdef.directions == frozenset({LEFT, RIGHT, DOWN})

    def test_t_up(self):
        cdef = CONNECTOR_MAP["┴"]
        assert cdef.mode == STRICT
        assert cdef.directions == frozenset({LEFT, RIGHT, UP})

    # ── Cross ──
    def test_cross(self):
        cdef = CONNECTOR_MAP["┼"]
        assert cdef.mode == STRICT
        assert cdef.directions == frozenset({UP, DOWN, LEFT, RIGHT})

    # ── Arrow heads ──
    def test_arrow_head_right(self):
        cdef = CONNECTOR_MAP["▶"]
        assert cdef.mode == STRICT
        assert cdef.directions == frozenset({LEFT})

    def test_arrow_head_left(self):
        cdef = CONNECTOR_MAP["◀"]
        assert cdef.mode == STRICT
        assert cdef.directions == frozenset({RIGHT})

    def test_arrow_head_down(self):
        cdef = CONNECTOR_MAP["▼"]
        assert cdef.mode == STRICT
        assert cdef.directions == frozenset({UP})

    def test_arrow_head_up(self):
        cdef = CONNECTOR_MAP["▲"]
        assert cdef.mode == STRICT
        assert cdef.directions == frozenset({DOWN})

    # ── Full arrows ──
    def test_full_arrow_right(self):
        cdef = CONNECTOR_MAP["→"]
        assert cdef.mode == AT_LEAST_ONE
        assert LEFT in cdef.directions
        assert RIGHT in cdef.directions

    # ── Circles ──
    def test_circle(self):
        for ch in ("●", "○"):
            cdef = CONNECTOR_MAP[ch]
            assert cdef.mode == LOOSE

    # ── Diagonals ──
    def test_diagonal(self):
        for ch in ("╲", "╱"):
            cdef = CONNECTOR_MAP[ch]
            assert cdef.mode == LOOSE

    # ── ASCII junction ──
    def test_ascii_junction(self):
        cdef = CONNECTOR_MAP["+"]
        assert cdef.mode == LOOSE
        assert cdef.directions == frozenset({UP, DOWN, LEFT, RIGHT})


class TestStyleMapping:
    """Verify style unification tables."""

    def test_single_to_double_mapping(self):
        assert SINGLE_TO_DOUBLE["┌"] == "╔"
        assert SINGLE_TO_DOUBLE["┐"] == "╗"
        assert SINGLE_TO_DOUBLE["└"] == "╚"
        assert SINGLE_TO_DOUBLE["┘"] == "╝"
        assert SINGLE_TO_DOUBLE["─"] == "═"
        assert SINGLE_TO_DOUBLE["│"] == "║"
        assert SINGLE_TO_DOUBLE["├"] == "╠"
        assert SINGLE_TO_DOUBLE["┤"] == "╣"
        assert SINGLE_TO_DOUBLE["┬"] == "╦"
        assert SINGLE_TO_DOUBLE["┴"] == "╩"
        assert SINGLE_TO_DOUBLE["┼"] == "╬"

    def test_double_to_single_mapping(self):
        assert DOUBLE_TO_SINGLE["╔"] == "┌"
        assert DOUBLE_TO_SINGLE["╗"] == "┐"
        assert DOUBLE_TO_SINGLE["╚"] == "└"
        assert DOUBLE_TO_SINGLE["╝"] == "┘"

    def test_bidirectional_consistency(self):
        for single, double in SINGLE_TO_DOUBLE.items():
            assert DOUBLE_TO_SINGLE[double] == single

    def test_style_mapping_covers_all_box_chars(self):
        all_box = SINGLE_LINE_CHARS | DOUBLE_LINE_CHARS
        mapped_single = set(SINGLE_TO_DOUBLE.keys())
        mapped_double = set(DOUBLE_TO_SINGLE.keys())
        assert all_box <= (mapped_single | mapped_double)


class TestCharacterSets:
    """Verify character classification sets don't overlap incorrectly."""

    def test_single_and_double_disjoint(self):
        assert SINGLE_LINE_CHARS.isdisjoint(DOUBLE_LINE_CHARS)

    def test_box_corners_subset_of_all(self):
        assert BOX_CORNER_CHARS <= ALL_CONNECTORS

    def test_t_junctions_subset_of_all(self):
        assert T_JUNCTION_CHARS <= ALL_CONNECTORS

    def test_crosses_subset_of_all(self):
        assert CROSS_CHARS <= ALL_CONNECTORS

    def test_arrow_heads_disjoint_from_full_arrows(self):
        assert ARROW_HEAD_CHARS.isdisjoint(FULL_ARROW_CHARS)

    def test_horizontal_chars(self):
        assert "─" in HORIZONTAL_CHARS
        assert "═" in HORIZONTAL_CHARS
        assert "-" in HORIZONTAL_CHARS
        assert "│" not in HORIZONTAL_CHARS

    def test_vertical_chars(self):
        assert "│" in VERTICAL_CHARS
        assert "║" in VERTICAL_CHARS
        assert "|" in VERTICAL_CHARS
        assert "─" not in VERTICAL_CHARS


class TestUtilityFunctions:

    def test_opposite_directions(self):
        assert OPPOSITE[UP] == DOWN
        assert OPPOSITE[DOWN] == UP
        assert OPPOSITE[LEFT] == RIGHT
        assert OPPOSITE[RIGHT] == LEFT

    def test_direction_delta(self):
        assert get_direction_delta(UP) == (-1, 0)
        assert get_direction_delta(DOWN) == (1, 0)
        assert get_direction_delta(LEFT) == (0, -1)
        assert get_direction_delta(RIGHT) == (0, 1)

    def test_get_char_style(self):
        assert get_char_style("┌") == "single"
        assert get_char_style("╔") == "double"
        assert get_char_style("A") is None
        assert get_char_style(" ") is None

    def test_is_connector(self):
        assert is_connector("┌") is True
        assert is_connector("╔") is True
        assert is_connector("▶") is True
        assert is_connector("●") is True
        assert is_connector("+") is True
        assert is_connector("A") is False
        assert is_connector(" ") is False

    def test_get_expected_directions(self):
        dirs = get_expected_directions("┌")
        assert dirs == frozenset({RIGHT, DOWN})

        dirs = get_expected_directions("─")
        assert dirs == frozenset({LEFT, RIGHT})

        assert get_expected_directions("X") is None
