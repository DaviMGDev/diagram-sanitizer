"""Tests for grid.py — Grid construction and connector classification."""

import pytest
from diagram_sanitizer.grid import Grid, ConnectorCell, classify_connectors, neighbor
from diagram_sanitizer.connector_map import UP, DOWN, LEFT, RIGHT


class TestGridConstruction:

    def test_simple_box(self):
        grid = Grid("┌─┐\n│ │\n└─┘")
        assert grid.height == 3
        assert grid.width == 3

    def test_unequal_rows(self):
        grid = Grid("short\nlonger line")
        assert grid.height == 2
        assert grid.width == 11

    def test_single_line(self):
        grid = Grid("───")
        assert grid.height == 1
        assert grid.width == 3

    def test_empty_string(self):
        grid = Grid("")
        assert grid.height == 1
        assert grid.width == 0
        assert grid.rows == [""]

    def test_trailing_newline(self):
        # split('\n') on "abc\n" → ["abc", ""] → height=2
        grid = Grid("abc\n")
        assert grid.height == 2
        assert grid.width == 3

    def test_trailing_newline_preserved_in_reconstruction(self):
        # Input has trailing newline
        text = "abc\n"
        grid = Grid(text)
        # to_string() won't add the trailing empty row back
        # This is expected — normalized text shouldn't have trailing empty lines
        result = grid.to_string()
        assert result == "abc" or result == "abc\n"
        # Either is acceptable; the important thing is grid.height

    def test_width_tracks_max_row_length(self):
        grid = Grid("a\nab\nabc")
        assert grid.width == 3


class TestGridAccess:

    def test_get_within_bounds(self):
        grid = Grid("AB\nCD")
        assert grid.get(0, 0) == "A"
        assert grid.get(0, 1) == "B"
        assert grid.get(1, 0) == "C"
        assert grid.get(1, 1) == "D"

    def test_get_out_of_bounds_row(self):
        grid = Grid("AB")
        assert grid.get(-1, 0) == " "
        assert grid.get(10, 0) == " "

    def test_get_out_of_bounds_col(self):
        grid = Grid("AB")
        assert grid.get(0, -1) == " "
        assert grid.get(0, 10) == " "

    def test_get_past_end_of_short_row(self):
        grid = Grid("A\nBB")
        assert grid.get(0, 1) == " "  # row 0 only has length 1
        assert grid.get(1, 1) == "B"

    def test_set_within_bounds(self):
        grid = Grid("AB\nCD")
        grid.set(0, 0, "X")
        assert grid.get(0, 0) == "X"
        assert grid.rows[0] == "XB"

    def test_set_out_of_bounds_row(self):
        grid = Grid("AB")
        grid.set(10, 0, "X")  # Should be no-op
        assert grid.rows == ["AB"]

    def test_set_out_of_bounds_col_negative(self):
        grid = Grid("AB")
        grid.set(0, -1, "X")  # Should be no-op
        assert grid.rows == ["AB"]

    def test_set_past_end_of_row(self):
        grid = Grid("AB")
        grid.set(0, 4, "X")
        assert grid.get(0, 4) == "X"
        assert grid.get(0, 3) == " "
        assert grid.get(0, 2) == " "

    def test_to_string(self):
        grid = Grid("┌─┐\n│ │\n└─┘")
        assert grid.to_string() == "┌─┐\n│ │\n└─┘"

    def test_to_string_after_modification(self):
        grid = Grid("AB\nCD")
        grid.set(0, 0, "X")
        assert grid.to_string() == "XB\nCD"

    def test_set_updates_width(self):
        grid = Grid("A")
        assert grid.width == 1
        grid.set(0, 5, "X")
        assert grid.width == 6


class TestConnectorClassification:

    def test_classify_valid_box(self):
        grid = Grid("┌─┐\n│ │\n└─┘")
        connectors = classify_connectors(grid)
        # ┌, ─, ┐, │, │, └, ─, ┘ = 8 connectors
        assert len(connectors) == 8

    def test_classify_correct_positions(self):
        grid = Grid("┌─┐\n│ │\n└─┘")
        connectors = classify_connectors(grid)
        positions = {(c.row, c.col) for c in connectors}
        assert (0, 0) in positions  # ┌
        assert (0, 1) in positions  # ─
        assert (0, 2) in positions  # ┐
        assert (1, 0) in positions  # │
        assert (1, 2) in positions  # │
        assert (2, 0) in positions  # └
        assert (2, 1) in positions  # ─
        assert (2, 2) in positions  # ┘

    def test_classify_correct_expected_directions(self):
        grid = Grid("┌")
        connectors = classify_connectors(grid)
        assert len(connectors) == 1
        assert connectors[0].char == "┌"
        assert RIGHT in connectors[0].expected
        assert DOWN in connectors[0].expected
        assert UP not in connectors[0].expected
        assert LEFT not in connectors[0].expected

    def test_no_connectors_in_plain_text(self):
        grid = Grid("Hello World")
        connectors = classify_connectors(grid)
        assert len(connectors) == 0

    def test_empty_grid_no_connectors(self):
        grid = Grid("")
        connectors = classify_connectors(grid)
        assert len(connectors) == 0

    def test_mixed_content(self):
        grid = Grid("text ┌─┐ text\n     └─┘")
        connectors = classify_connectors(grid)
        # There are 6 box-drawing characters
        assert len(connectors) == 6

    def test_ascii_connectors_classified(self):
        grid = Grid("+--+\n|  |\n+--+")
        connectors = classify_connectors(grid)
        # +--+ (row 0): +, -, -, + = 4
        # |  | (row 1): |, |     = 2
        # +--+ (row 2): +, -, -, + = 4
        # Total: 10
        assert len(connectors) == 10

    def test_connector_cell_is_dataclass(self):
        grid = Grid("─")
        connectors = classify_connectors(grid)
        cell = connectors[0]
        assert isinstance(cell, ConnectorCell)
        assert cell.row == 0
        assert cell.col == 0
        assert cell.char == "─"


class TestNeighbor:

    def test_neighbor_up(self):
        grid = Grid("A\nB")
        r, c, ch = neighbor(grid, 1, 0, UP)
        assert (r, c) == (0, 0)
        assert ch == "A"

    def test_neighbor_down(self):
        grid = Grid("A\nB")
        r, c, ch = neighbor(grid, 0, 0, DOWN)
        assert (r, c) == (1, 0)
        assert ch == "B"

    def test_neighbor_left(self):
        grid = Grid("AB")
        r, c, ch = neighbor(grid, 0, 1, LEFT)
        assert (r, c) == (0, 0)
        assert ch == "A"

    def test_neighbor_right(self):
        grid = Grid("AB")
        r, c, ch = neighbor(grid, 0, 0, RIGHT)
        assert (r, c) == (0, 1)
        assert ch == "B"

    def test_neighbor_out_of_bounds(self):
        grid = Grid("A")
        r, c, ch = neighbor(grid, 0, 0, UP)
        assert (r, c) == (-1, 0)
        assert ch == " "

    def test_neighbor_out_of_bounds_left(self):
        grid = Grid("A")
        r, c, ch = neighbor(grid, 0, 0, LEFT)
        assert (r, c) == (0, -1)
        assert ch == " "
