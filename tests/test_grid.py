"""Tests for grid parsing and reconstruction."""

from ascii_sanitizer.grid import get_cell, grid_dimensions, parse, reconstruct, set_cell


class TestParse:
    def test_simple(self):
        grid = parse("abc\ndef")
        assert grid == [["a", "b", "c"], ["d", "e", "f"]]

    def test_empty(self):
        grid = parse("")
        assert grid == []

    def test_whitespace_only(self):
        grid = parse("   ")
        assert grid == [[" ", " ", " "]]

    def test_single_line(self):
        grid = parse("hello")
        assert grid == [["h", "e", "l", "l", "o"]]

    def test_padding(self):
        grid = parse("a\nbb\nccc")
        assert len(grid[0]) == 3
        assert grid[0] == ["a", " ", " "]
        assert grid[1] == ["b", "b", " "]
        assert grid[2] == ["c", "c", "c"]

    def test_crlf_normalization(self):
        grid = parse("a\r\nb\nc")
        assert grid == [["a"], ["b"], ["c"]]
        assert len(grid) == 3

    def test_tab_expansion(self):
        grid = parse("a\tb", tab_width=4)
        assert "".join(grid[0]) == "a   b"

    def test_tab_expansion_alignment(self):
        grid = parse("\t\ta\nab\t\tc", tab_width=4)
        # First line: two tabs (8) + 'a' = 9.
        # Second line: ab (2) + tab to 4 (2) + tab (4) + c (1) = 9
        assert len(grid[0]) == 9
        assert grid[0] == [" "] * 8 + ["a"]
        assert grid[1] == ["a", "b", " ", " ", " ", " ", " ", " ", "c"]

    def test_empty_lines(self):
        grid = parse("a\n\nb")
        assert len(grid) == 3
        # Empty line gets padded to max width (1 in this case)
        assert grid[1] == [" "]


class TestReconstruct:
    def test_simple(self):
        grid = [["a", "b"], ["c", "d"]]
        assert reconstruct(grid) == "ab\ncd"

    def test_trailing_spaces_stripped(self):
        grid = [["a", " ", " "], ["b", "c", " "]]
        assert reconstruct(grid) == "a\nbc"

    def test_trailing_empty_lines(self):
        grid = [["a"], [" "], ["b"], [" "], [" "]]
        assert reconstruct(grid) == "a\n\nb"

    def test_roundtrip(self):
        diagram = "┌──┐\n│A │\n└──┘"
        grid = parse(diagram)
        assert reconstruct(grid) == diagram


class TestCellAccess:
    def test_get_cell(self):
        grid = [["a", "b"], ["c", "d"]]
        assert get_cell(grid, 0, 0) == "a"
        assert get_cell(grid, 1, 1) == "d"
        assert get_cell(grid, 2, 0) is None
        assert get_cell(grid, 0, 2) is None

    def test_set_cell(self):
        grid = [["a", "b"], ["c", "d"]]
        set_cell(grid, 0, 0, "X")
        assert grid[0][0] == "X"
        set_cell(grid, 5, 5, "Z")  # No-op
        assert len(grid) == 2


class TestDimensions:
    def test_empty(self):
        assert grid_dimensions([]) == (0, 0)

    def test_normal(self):
        grid = [["a", "b"], ["c", "d"]]
        assert grid_dimensions(grid) == (2, 2)
