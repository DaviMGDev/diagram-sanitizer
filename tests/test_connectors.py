"""Tests for connector classification and direction maps."""

from ascii_sanitizer.connectors import (
    Dir,
    expected_directions,
    is_connector,
    is_double_line,
    is_horizontal,
    is_single_line,
    is_vertical,
    to_double_line,
    to_single_line,
)


class TestClassification:
    def test_corner_is_connector(self):
        assert is_connector("┌")
        assert is_connector("┐")
        assert is_connector("└")
        assert is_connector("┘")

    def test_line_is_connector(self):
        assert is_connector("│")
        assert is_connector("─")

    def test_t_is_connector(self):
        assert is_connector("├")
        assert is_connector("┤")
        assert is_connector("┬")
        assert is_connector("┴")
        assert is_connector("┼")

    def test_double_line_is_connector(self):
        assert is_connector("╔")
        assert is_connector("═")
        assert is_connector("║")

    def test_arrow_is_connector(self):
        assert is_connector("▶")
        assert is_connector("▼")
        assert is_connector("→")

    def test_circle_is_connector(self):
        assert is_connector("●")
        assert is_connector("○")

    def test_ascii_is_connector(self):
        assert is_connector("+")
        assert is_connector("-")
        assert is_connector("|")

    def test_plain_text_not_connector(self):
        assert not is_connector("a")
        assert not is_connector(" ")
        assert not is_connector("!")

    def test_empty_string_not_connector(self):
        assert not is_connector("")


class TestDirections:
    def test_corner_directions(self):
        assert expected_directions("┌") == {Dir.RIGHT, Dir.DOWN}
        assert expected_directions("┐") == {Dir.LEFT, Dir.DOWN}
        assert expected_directions("└") == {Dir.RIGHT, Dir.UP}
        assert expected_directions("┘") == {Dir.LEFT, Dir.UP}

    def test_t_directions(self):
        assert expected_directions("├") == {Dir.UP, Dir.DOWN, Dir.RIGHT}
        assert expected_directions("┤") == {Dir.UP, Dir.DOWN, Dir.LEFT}
        assert expected_directions("┬") == {Dir.LEFT, Dir.RIGHT, Dir.DOWN}
        assert expected_directions("┴") == {Dir.LEFT, Dir.RIGHT, Dir.UP}
        assert expected_directions("┼") == {Dir.UP, Dir.DOWN, Dir.LEFT, Dir.RIGHT}

    def test_line_directions(self):
        assert expected_directions("─") == {Dir.LEFT, Dir.RIGHT}
        assert expected_directions("│") == {Dir.UP, Dir.DOWN}

    def test_arrow_head_directions(self):
        assert expected_directions("▶") == {Dir.LEFT}
        assert expected_directions("◀") == {Dir.RIGHT}
        assert expected_directions("▼") == {Dir.UP}
        assert expected_directions("▲") == {Dir.DOWN}

    def test_full_arrow_directions(self):
        assert expected_directions("→") == {Dir.LEFT, Dir.RIGHT}
        assert expected_directions("←") == {Dir.LEFT, Dir.RIGHT}

    def test_circle_directions(self):
        assert expected_directions("●") == {Dir.UP, Dir.DOWN, Dir.LEFT, Dir.RIGHT}
        assert expected_directions("○") == {Dir.UP, Dir.DOWN, Dir.LEFT, Dir.RIGHT}

    def test_unknown_char(self):
        assert expected_directions("x") == set()


class TestStyleChecks:
    def test_single_line(self):
        assert is_single_line("┌")
        assert is_single_line("─")
        assert not is_single_line("╔")
        assert not is_single_line("a")

    def test_double_line(self):
        assert is_double_line("╔")
        assert is_double_line("═")
        assert not is_double_line("┌")
        assert not is_double_line("a")

    def test_horizontal(self):
        assert is_horizontal("─")
        assert is_horizontal("═")
        assert not is_horizontal("│")

    def test_vertical(self):
        assert is_vertical("│")
        assert is_vertical("║")
        assert not is_vertical("─")


class TestConversion:
    def test_single_to_double(self):
        assert to_double_line("┌") == "╔"
        assert to_double_line("─") == "═"
        assert to_double_line("│") == "║"
        assert to_double_line("┼") == "╬"

    def test_double_to_single(self):
        assert to_single_line("╔") == "┌"
        assert to_single_line("═") == "─"
        assert to_single_line("║") == "│"
        assert to_single_line("╬") == "┼"

    def test_no_conversion(self):
        assert to_double_line("x") == "x"
        assert to_single_line("x") == "x"
