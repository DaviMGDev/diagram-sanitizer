"""Tests for fixer.py — fix application in priority order."""

import pytest
from diagram_sanitizer.grid import Grid
from diagram_sanitizer.fixer import apply_fixes


class TestApplyFixes:

    def test_no_fixable_issues_returns_none(self):
        """FR-025: No fixable issues → corrected_diagram is None."""
        grid = Grid("┌─┐\n└─┘")
        issues = []  # No issues
        result = apply_fixes(grid, issues)
        assert result is None

    def test_all_issues_not_fixable_returns_none(self):
        """All issues have fixable=False."""
        grid = Grid("text")
        issues = [
            {"type": "gap", "line": 1, "col": 1, "fixable": False,
             "severity": "error", "message": "ambiguous gap"},
        ]
        result = apply_fixes(grid, issues)
        assert result is None

    def test_returns_string_when_fixable_issues(self):
        """At least one fixable issue → returns string."""
        grid = Grid("  │\n")
        issues = [
            {"type": "orphan", "line": 1, "col": 3, "fixable": True,
             "severity": "error", "message": "orphan vertical bar"},
        ]
        result = apply_fixes(grid, issues)
        assert isinstance(result, str)

    def test_orphan_removal_replaces_with_space(self):
        """FR-010: Orphan replaced with space."""
        grid = Grid("  │\n")
        issues = [
            {"type": "orphan", "line": 1, "col": 3, "fixable": True,
             "severity": "error", "message": "orphan vertical bar"},
        ]
        result = apply_fixes(grid, issues)
        assert result == "   \n"  # Three spaces
        assert "│" not in result

    def test_gap_fill_inserts_line_char(self):
        """FR-016: Single-cell gap filled with appropriate char."""
        grid = Grid("┌─┐\n│ │\n└ ┘")
        issues = [
            {"type": "gap", "line": 3, "col": 2, "fixable": True,
             "severity": "error", "message": "gap between bottom corners",
             "fix_suggestion": "Insert '─' at (3,2)"},
        ]
        result = apply_fixes(grid, issues)
        # Bottom row should now be "└─┘"
        assert "└─┘" in result or "└─┘" == result.split("\n")[2]

    def test_multiple_fixes_applied(self):
        """Multiple fixable issues are all applied."""
        grid = Grid("  │\n┌ ┐\n└─┘")
        issues = [
            # Orphan vertical bar
            {"type": "orphan", "line": 1, "col": 3, "fixable": True,
             "severity": "error", "message": "orphan"},
            # Gap in top border
            {"type": "gap", "line": 2, "col": 2, "fixable": True,
             "severity": "error", "message": "gap in top border",
             "fix_suggestion": "Insert '─' at (2,2)"},
        ]
        result = apply_fixes(grid, issues)
        # Orphan removed, gap filled
        lines = result.split("\n")
        assert lines[0].strip() == "" or lines[0] == "   "  # Orphan removed
        assert "─" in lines[1]  # Gap filled

    def test_fix_order_preserved(self):
        """Orphan removal happens before gap fill (FR-027 step 10)."""
        # A gap pointing at an orphan — orphan should be removed first
        grid = Grid("┌─┐\n│ │\n└ │")  # │ at (2,2) is an orphan, └ at (2,0)
        issues = [
            # Orphan should be first in fix order
            {"type": "orphan", "line": 3, "col": 3, "fixable": True,
             "severity": "error", "message": "orphan"},
            {"type": "gap", "line": 3, "col": 2, "fixable": True,
             "severity": "error", "message": "gap",
             "fix_suggestion": "Insert '─' at (3,2)"},
        ]
        result = apply_fixes(grid, issues)
        # Orphan removed (│→space), gap filled (space→─)
        lines = result.split("\n")
        bottom = lines[2]
        # Should be └─  (gap filled, orphan removed → space)
        assert bottom.startswith("└─")

    def test_box_width_normalization(self):
        """FR-017: Box border normalized — modal width with conservative tie-breaking."""
        # Top=3, internal row=3, bottom=1 → modal=3 unambiguous (count 2 vs 1)
        grid = Grid("┌───┐\n├───┤\n│ X │\n└─┘")
        issues = [
            {"type": "box_width", "line": 1, "col": 1, "fixable": True,
             "severity": "error",
             "message": "Box width mismatch: top border spans 3 cell(s), bottom border spans 1 cell(s)",
             "fix_suggestion": "Normalize box width to 3",
             "end_line": 4, "end_col": 4},
        ]
        result = apply_fixes(grid, issues)
        # Bottom should now span same width as top (modal width = 3)
        assert "└───┘" in result

    def test_style_unification(self):
        """FR-018: Style unified to majority when >80%."""
        # 10 single-line + 1 double-line → 90% single → unify
        grid = Grid("┌─────┐\n│  ║  │\n└─────┘")
        issues = [
            {"type": "style_mix", "line": 1, "col": 1, "fixable": True,
             "severity": "warning",
             "message": "Style inconsistency: component mixes single-line (10) and double-line (1)",
             "fix_suggestion": "Unify component to single-line style (91% majority)",
             "end_line": 3, "end_col": 7},
        ]
        result = apply_fixes(grid, issues)
        # The double ║ should be converted to │
        assert "║" not in result
        assert "│" in result


class TestFixEdgeCases:

    def test_fix_on_empty_grid(self):
        grid = Grid("")
        issues = [
            {"type": "orphan", "line": 1, "col": 1, "fixable": True,
             "severity": "error", "message": "test"},
        ]
        result = apply_fixes(grid, issues)
        assert isinstance(result, str)

    def test_orphan_at_grid_edge(self):
        grid = Grid("│\n")
        issues = [
            {"type": "orphan", "line": 1, "col": 1, "fixable": True,
             "severity": "error", "message": "orphan"},
        ]
        result = apply_fixes(grid, issues)
        assert result == " \n"
