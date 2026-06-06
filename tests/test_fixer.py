"""Tests for the auto-fix engine."""

from ascii_sanitizer.analyzer import analyze
from ascii_sanitizer.fixer import apply_fixes
from ascii_sanitizer.grid import parse, reconstruct


def _fix(text: str) -> str:
    grid = parse(text)
    issues = analyze(grid)
    fixed = apply_fixes(grid, issues)
    return reconstruct(fixed)


class TestGapFill:
    def test_vertical_gap_fill(self):
        result = _fix("│\n\n│")
        assert result == "│\n│\n│"

    def test_horizontal_gap_fill(self):
        result = _fix("├ ┤")
        assert result == "├─┤"

    def test_gap_two_cells_not_fixed(self):
        result = _fix("├  ┤")
        # Should remain unchanged (2-cell gap not fixable)
        assert result == "├  ┤"

    def test_gap_content_preserved(self):
        """Fixing a gap should not modify surrounding content."""
        original = "text before\n│\n\n│\ntext after"
        result = _fix(original)
        assert "text before" in result
        assert "text after" in result
        assert "│\n│\n│" in result


class TestBoxWidth:
    def test_bottom_shorter_clear_modal(self):
        # Top=4, middle rows=4, bottom=2 → modal is 4
        result = _fix("┌────┐\n│ AB │\n│ XY │\n└──┘")
        assert "└────┘" in result

    def test_middle_row_fixed(self):
        # Top=4, middle=2, bottom=4 → modal is 4
        result = _fix("┌────┐\n├──┤\n└────┘")
        # Middle row should be extended
        lines = result.split("\n")
        assert len(lines[1]) >= 6  # "├────┤"

    def test_ambiguous_width_not_fixed(self):
        # 50/50 split — ambiguous, should not fix
        result = _fix("┌──┐\n│AB│\n└────┘")
        assert result is not None  # Still returns something
        # Bottom may or may not be shrunk, but top shouldn't be corrupted
        assert "│AB│" in result


class TestStyleUnification:
    def test_majority_single_unified(self):
        # Many rows with single-line, one with double → >90% single
        result = _fix("┌──┐\n│A │\n│B │\n│C │\n╚──╝")
        # Should unify to single-line
        assert "╚" not in result
        assert "└" in result  # converted from ╚ to └


class TestNoFalseFixes:
    def test_valid_diagram_unchanged(self):
        original = "┌──┐\n│AB│\n└──┘"
        result = _fix(original)
        assert result == original

    def test_flowchart_unchanged(self):
        original = """          ┌──────────┐
          │  START   │
          └────┬─────┘
               │
          ┌────▼────┐
          │  END    │
          └─────────┘"""
        result = _fix(original)
        assert result == original


class TestContentPreservation:
    def test_labels_preserved(self):
        original = "before\n┌──┐\n│A │\n└──┘\nafter"
        result = _fix(original)
        assert "before" in result
        assert "after" in result
        assert "│A │" in result or "│ A│" in result  # content preserved
