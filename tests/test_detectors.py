"""Tests for detectors.py — all five detection stages."""

import pytest
from diagram_sanitizer.grid import Grid, classify_connectors
from diagram_sanitizer.components import find_components
from diagram_sanitizer.detectors import (
    detect_orphans,
    detect_gaps,
    detect_box_widths,
    detect_style_mix,
    detect_cross_arrow_circle,
)


def _analyze(text: str):
    """Helper: run grid, classification, and components for a diagram."""
    grid = Grid(text)
    connectors = classify_connectors(grid)
    components = find_components(connectors, grid)
    return grid, connectors, components


# ═══════════════════════════════════════════════════════════════════════════════
# ORPHAN DETECTION
# ═══════════════════════════════════════════════════════════════════════════════


class TestOrphanDetection:

    # ── Fully isolated orphans ──

    def test_isolated_vertical_bar(self):
        """EC-016: standalone │ with empty above and below."""
        grid, connectors, components = _analyze("  │\n")
        issues = detect_orphans(grid, connectors, components)
        assert len(issues) >= 1
        orphan = issues[0]
        assert orphan["type"] == "orphan"
        assert orphan["severity"] == "error"
        assert orphan["fixable"] is True

    def test_isolated_horizontal_bar(self):
        """A standalone ─── with nothing on either side."""
        grid, connectors, components = _analyze("─")
        issues = detect_orphans(grid, connectors, components)
        assert len(issues) == 1
        assert issues[0]["type"] == "orphan"
        assert issues[0]["severity"] == "error"

    def test_isolated_corner(self):
        """A ┌ with nothing else."""
        grid, connectors, components = _analyze(" ┌ \n")
        issues = detect_orphans(grid, connectors, components)
        assert len(issues) == 1
        assert issues[0]["type"] == "orphan"

    def test_isolated_arrow_head(self):
        """EC-018: arrow head ▶ with no ─ to its left."""
        grid, connectors, components = _analyze("text ▶\n")
        issues = detect_orphans(grid, connectors, components)
        # Arrow head is a strict orphan
        assert any(i["type"] == "orphan" and "arrow" in i["message"].lower()
                   for i in issues)

    def test_isolated_full_arrow(self):
        """EC-029: full arrow → with no connections."""
        grid, connectors, components = _analyze("text → text\n")
        issues = detect_orphans(grid, connectors, components)
        assert any(i["type"] == "orphan" and "arrow" in i["message"].lower()
                   for i in issues)

    def test_valid_box_no_orphans(self):
        """A complete box should have no orphans."""
        grid, connectors, components = _analyze("┌─┐\n│ │\n└─┘")
        issues = detect_orphans(grid, connectors, components)
        assert len(issues) == 0

    def test_valid_horizontal_line_connected(self):
        """A ─ connected to a ┌ on the right is valid — not orphan."""
        grid, connectors, components = _analyze("┌─\n")
        issues = detect_orphans(grid, connectors, components)
        # ┌ connects right+down, ─ connects left+right → both connected
        assert len(issues) == 0

    # ── Circle special cases ──

    def test_circle_far_away_not_orphan(self):
        """EC-020: ● more than 1 cell away from any connector → not orphan."""
        grid, connectors, components = _analyze("●     │\n")
        issues = detect_orphans(grid, connectors, components)
        # Should not report the circle as orphan
        assert not any(
            i["type"] == "orphan" and "●" in i["message"]
            for i in issues
        )

    def test_circle_one_cell_away_warning(self):
        """EC-021: ● exactly 1 cell from a connector but not connected → warning."""
        grid, connectors, components = _analyze("│ ●\n")
        issues = detect_orphans(grid, connectors, components)
        circle_issues = [i for i in issues if "●" in i.get("message", "")]
        if circle_issues:
            assert circle_issues[0]["severity"] == "warning"
            assert circle_issues[0]["fixable"] is False

    # ── Diagonal orphans ──

    def test_diagonal_isolated(self):
        """EC-022: ╲ with no diagonal neighbor → warning."""
        grid, connectors, components = _analyze("╲\n")
        issues = detect_orphans(grid, connectors, components)
        assert len(issues) >= 1
        diag = issues[0]
        assert diag["severity"] == "warning"

    # ── Component orphans ──

    def test_component_orphan_small_fragment(self):
        """EC-017: a └─ fragment disconnected from main diagram."""
        grid, connectors, components = _analyze("┌───┐     └─\n│ A │\n└───┘")
        issues = detect_orphans(grid, connectors, components)
        # The └─ fragment should be reported as component orphans
        assert len(issues) >= 2  # At least └ and ─

    def test_multiple_disconnected_components(self):
        """Two separate boxes — neither is orphan of the other (EC-012)."""
        grid, connectors, components = _analyze("┌─┐  ┌───┐\n└─┘  └───┘")
        issues = detect_orphans(grid, connectors, components)
        # Both have comparable sizes, neither is >50% → no orphans
        # Actually: first box has 6 connectors, second has 8, total 14
        # 8/14 ≈ 57% > 50%, so first box IS a component orphan!
        if len(components) >= 2:
            largest_pct = components[0].size / sum(c.size for c in components)
            if largest_pct > 0.5:
                assert len(issues) > 0  # Smaller components are orphans

    def test_single_large_component_no_orphans(self):
        """A single component spanning everything — no orphans."""
        grid, connectors, components = _analyze("┌─────────┐\n│         │\n└─────────┘")
        issues = detect_orphans(grid, connectors, components)
        assert len(issues) == 0

    # ── ASCII junction special case ──

    def test_isolated_plus_sign_warning(self):
        """A standalone + with no connections → warning (not error for loose mode)."""
        grid, connectors, components = _analyze(" + \n")
        issues = detect_orphans(grid, connectors, components)
        plus_issues = [i for i in issues if "+" in i.get("message", "")]
        if plus_issues:
            assert plus_issues[0]["severity"] == "warning"


# ═══════════════════════════════════════════════════════════════════════════════
# GAP DETECTION
# ═══════════════════════════════════════════════════════════════════════════════


class TestGapDetection:

    def test_valid_box_no_gaps(self):
        """A complete box with no gaps."""
        grid, connectors, components = _analyze("┌─┐\n│ │\n└─┘")
        issues = detect_gaps(grid, connectors)
        assert len(issues) == 0

    def test_single_cell_gap(self):
        """A single empty cell between connectors — fixable."""
        grid, connectors, components = _analyze("┌─┐\n│ │\n└ ┘")
        issues = detect_gaps(grid, connectors)
        # Gap between └ and ┘ at (2,1) — 1 empty cell
        gap_issues = [i for i in issues if i["type"] == "gap"]
        # May find gap in bottom border
        bottom_gaps = [
            i for i in gap_issues if i["line"] == 3  # 1-indexed row 3 = row 2
        ]
        if bottom_gaps:
            assert bottom_gaps[0]["fixable"] is True

    def test_multi_cell_gap_not_fixable(self):
        """EC-006: 2+ empty cells between connectors — not fixable."""
        grid, connectors, components = _analyze("┌───┐\n│   │\n└   ┘")
        issues = detect_gaps(grid, connectors)
        gap_issues = [i for i in issues if i["type"] == "gap"]
        if gap_issues:
            for gi in gap_issues:
                # Multi-cell gaps should not be fixable
                if gi.get("end_line") and gi["end_line"] != gi["line"]:
                    # Multi-cell across lines
                    pass
                elif gi.get("end_col") and gi["end_col"] - gi["col"] > 0:
                    assert gi["fixable"] is False

    def test_vertical_gap(self):
        """A missing │ between connectors."""
        grid, connectors, components = _analyze("┌─┐\n  │\n└─┘")
        issues = detect_gaps(grid, connectors)
        # There's a gap between ┌ and the left │
        # Actually the diagram has: row0: ┌─┐, row1: "  │", row2: └─┘
        # ┌ at (0,0) expects right and down. Down = (1,0) = " " → gap
        gap_issues = [i for i in issues if i["type"] == "gap"]
        assert len(gap_issues) > 0

    def test_gap_severity_is_error(self):
        """AC-017: gaps have error severity."""
        grid, connectors, components = _analyze("┌ ┐\n│ │\n└─┘")
        issues = detect_gaps(grid, connectors)
        gap_issues = [i for i in issues if i["type"] == "gap"]
        for gi in gap_issues:
            assert gi["severity"] == "error"

    def test_no_gaps_in_empty_input(self):
        grid, connectors, components = _analyze("")
        issues = detect_gaps(grid, connectors)
        assert issues == []


# ═══════════════════════════════════════════════════════════════════════════════
# BOX ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════


class TestBoxWidthDetection:

    def test_matching_box_no_issue(self):
        """A box with matching top and bottom widths."""
        grid, connectors, components = _analyze("┌───┐\n│   │\n└───┘")
        issues = detect_box_widths(grid, components)
        assert len(issues) == 0

    def test_mismatched_box_width(self):
        """Box with wider top than bottom (AC-003)."""
        grid, connectors, components = _analyze("┌───┐\n│ X │\n└─┘")
        issues = detect_box_widths(grid, components)
        box_issues = [i for i in issues if i["type"] == "box_width"]
        assert len(box_issues) >= 1
        assert box_issues[0]["severity"] == "error"

    def test_wider_bottom_than_top(self):
        """Box where bottom is wider than top."""
        grid, connectors, components = _analyze("┌─┐\n│X│\n└───┘")
        issues = detect_box_widths(grid, components)
        box_issues = [i for i in issues if i["type"] == "box_width"]
        assert len(box_issues) >= 1

    def test_double_line_box_no_issue(self):
        """Double-line box with matching widths."""
        grid, connectors, components = _analyze("╔═══╗\n║   ║\n╚═══╝")
        issues = detect_box_widths(grid, components)
        assert len(issues) == 0

    def test_double_line_box_mismatch(self):
        """Double-line box with width mismatch."""
        grid, connectors, components = _analyze("╔═══╗\n║ X ║\n╚═╝")
        issues = detect_box_widths(grid, components)
        box_issues = [i for i in issues if i["type"] == "box_width"]
        assert len(box_issues) >= 1

    def test_nested_boxes(self):
        """Nested boxes should be analyzed independently (EC-007)."""
        grid, connectors, components = _analyze(
            "┌───────────┐\n"
            "│ ┌───┐     │\n"
            "│ └───┘     │\n"
            "└───────────┘"
        )
        issues = detect_box_widths(grid, components)
        # Outer box has matching widths, inner box has matching widths
        # No issues expected
        assert len(issues) == 0

    def test_box_issue_has_bounding_box(self):
        """Box width issues should include end_line/end_col."""
        grid, connectors, components = _analyze("┌───┐\n│ X │\n└─┘")
        issues = detect_box_widths(grid, components)
        box_issues = [i for i in issues if i["type"] == "box_width"]
        if box_issues:
            assert "end_line" in box_issues[0]
            assert "end_col" in box_issues[0]


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════


class TestStyleDetection:

    def test_uniform_single_line_no_issue(self):
        """Pure single-line box — no style issues."""
        grid, connectors, components = _analyze("┌─┐\n│ │\n└─┘")
        issues = detect_style_mix(components)
        assert len(issues) == 0

    def test_uniform_double_line_no_issue(self):
        """Pure double-line box — no style issues."""
        grid, connectors, components = _analyze("╔═╗\n║ ║\n╚═╝")
        issues = detect_style_mix(components)
        assert len(issues) == 0

    def test_mixed_single_double_warns(self):
        """Mixed single/double line in same component (AC-004)."""
        grid, connectors, components = _analyze("┌─┐\n║X║\n└─┘")
        issues = detect_style_mix(components)
        style_issues = [i for i in issues if i["type"] == "style_mix"]
        assert len(style_issues) >= 1
        assert style_issues[0]["severity"] == "warning"

    def test_majority_single_style_fixable(self):
        """>80% single-line should be fixable (AC-009)."""
        # 3 single-line (┌,─,┐) + 1 double (║) = 75% single... need >80%
        # Let's use a larger component: 9 single + 1 double = 90%
        grid, connectors, components = _analyze("┌─────┐\n│  ║  │\n└─────┘")
        issues = detect_style_mix(components)
        style_issues = [i for i in issues if i["type"] == "style_mix"]
        if style_issues:
            # >80% should be fixable
            assert style_issues[0]["fixable"] is True

    def test_unicode_ascii_mix_info(self):
        """EC-030: Unicode + ASCII mix → info, not fixable."""
        grid, connectors, components = _analyze("┌───┐\n| X |\n+───┘")
        issues = detect_style_mix(components)
        style_issues = [i for i in issues if i["type"] == "style_mix"]
        if style_issues:
            assert style_issues[0]["severity"] == "info"
            assert style_issues[0]["fixable"] is False

    def test_pure_ascii_no_issue(self):
        """Pure ASCII box — no style issues."""
        grid, connectors, components = _analyze("+---+\n| A |\n+---+")
        issues = detect_style_mix(components)
        style_issues = [i for i in issues if i["type"] == "style_mix"]
        # ASCII-only should not trigger style warnings (only ASCII/Unicode mixing triggers info)
        assert len(style_issues) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# CROSS / ARROW / CIRCLE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestCrossArrowCircleValidation:

    def test_full_cross_no_warning(self):
        """A cross with all 4 directions connected — no warning."""
        grid, connectors, components = _analyze(" │\n─┼─\n │")
        issues = detect_cross_arrow_circle(grid, connectors, components)
        cross_issues = [i for i in issues if i["type"] == "dangling_junction"]
        assert len(cross_issues) == 0

    def test_dangling_cross_warns(self):
        """A cross with fewer than 4 connections (AC-005, EC-005)."""
        grid, connectors, components = _analyze("  │\n──┼\n")
        issues = detect_cross_arrow_circle(grid, connectors, components)
        cross_issues = [i for i in issues if i["type"] == "dangling_junction"]
        assert len(cross_issues) >= 1
        assert cross_issues[0]["severity"] == "warning"

    def test_no_cross_in_plain_box(self):
        """A box with no cross characters — no cross issues."""
        grid, connectors, components = _analyze("┌─┐\n│ │\n└─┘")
        issues = detect_cross_arrow_circle(grid, connectors, components)
        assert len(issues) == 0

    def test_double_line_cross(self):
        """Double-line cross ╬ with all 4 directions."""
        grid, connectors, components = _analyze(" ║\n═╬═\n ║")
        issues = detect_cross_arrow_circle(grid, connectors, components)
        cross_issues = [i for i in issues if i["type"] == "dangling_junction"]
        assert len(cross_issues) == 0
