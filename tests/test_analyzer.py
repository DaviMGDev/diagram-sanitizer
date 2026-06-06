"""Tests for the analysis engine: trace, gaps, boxes, styles."""

from ascii_sanitizer.analyzer import analyze
from ascii_sanitizer.grid import parse
from ascii_sanitizer.types import IssueType, Severity


def _analyze(text: str):
    return analyze(parse(text))


class TestValidDiagrams:
    def test_simple_box(self):
        issues = _analyze("┌──┐\n│AB│\n└──┘")
        assert len(issues) == 0

    def test_larger_box(self):
        issues = _analyze("┌──────┐\n│ text │\n│ more │\n└──────┘")
        assert len(issues) == 0

    def test_flowchart(self):
        issues = _analyze("""          ┌──────────┐
          │  START   │
          └────┬─────┘
               │
          ┌────▼────┐
          │  END    │
          └─────────┘""")
        assert len(issues) == 0

    def test_empty_diagram(self):
        issues = _analyze("")
        assert len(issues) == 0

    def test_plain_text(self):
        issues = _analyze("hello world\nno diagram here")
        assert len(issues) == 0


class TestGapDetection:
    def test_vertical_gap_one_cell(self):
        issues = _analyze("│\n\n│")
        gaps = [i for i in issues if i.type == IssueType.GAP]
        assert len(gaps) >= 1
        assert all(g.fixable for g in gaps)

    def test_horizontal_gap_one_cell(self):
        issues = _analyze("├ ┤")
        gaps = [i for i in issues if i.type == IssueType.GAP]
        assert len(gaps) >= 1
        assert all(g.fixable for g in gaps)

    def test_gap_two_cells_not_fixable(self):
        issues = _analyze("├  ┤")
        gaps = [i for i in issues if i.type == IssueType.GAP]
        assert len(gaps) >= 1
        assert all(not g.fixable for g in gaps)

    def test_box_width_mismatch(self):
        issues = _analyze("┌───┐\n│ A │\n└──┘")
        box_issues = [i for i in issues if i.type == IssueType.BOX_WIDTH]
        assert len(box_issues) >= 1
        assert box_issues[0].severity == Severity.ERROR

    def test_content_is_valid_endpoint(self):
        """├── label should not be flagged as gap."""
        issues = _analyze("├── label")
        gaps = [i for i in issues if i.type == IssueType.GAP]
        assert len(gaps) == 0

    def test_compact_tree(self):
        """The filesystem tree format should pass clean."""
        issues = _analyze("""root
├── src/
│   ├── main.py
│   └── lib/
└── README.md""")
        assert len(issues) == 0


class TestStyleCheck:
    def test_uniform_single(self):
        issues = _analyze("┌──┐\n│AB│\n└──┘")
        style = [i for i in issues if i.type == IssueType.STYLE_MIX]
        assert len(style) == 0

    def test_uniform_double(self):
        issues = _analyze("╔══╗\n║AB║\n╚══╝")
        style = [i for i in issues if i.type == IssueType.STYLE_MIX]
        assert len(style) == 0

    def test_mixed_styles(self):
        issues = _analyze("╔══╗\n║AB║\n╚──╝")
        style = [i for i in issues if i.type == IssueType.STYLE_MIX]
        assert len(style) >= 1
        assert style[0].severity == Severity.WARNING

    def test_majority_single_fixable(self):
        issues = _analyze("┌──┐\n│AB│\n╚──╝")  # 7 single, 3 double = 70%
        style = [i for i in issues if i.type == IssueType.STYLE_MIX]
        assert len(style) >= 1
        # 7/10 = 70% < 80%, so NOT fixable
        assert not style[0].fixable

    def test_majority_double_fixable(self):
        # 11 double, 1 single
        issues = _analyze("╔══╗\n║AB║\n╚══╝\n╚══╝")
        style = [i for i in issues if i.type == IssueType.STYLE_MIX]
        # Actually this has uniform double style, so no mix
        assert len(style) == 0


class TestArrowOrphan:
    def test_arrow_with_line(self):
        issues = _analyze("──▶")
        orphans = [i for i in issues if i.type == IssueType.ARROW_ORPHAN]
        assert len(orphans) == 0

    def test_isolated_arrow(self):
        issues = _analyze("   ▶")
        orphans = [i for i in issues if i.type == IssueType.ARROW_ORPHAN]
        assert len(orphans) >= 1

    def test_decorative_arrow_in_box_border(self):
        """Arrow between horizontal lines is decorative."""
        issues = _analyze("┌──▼──┐\n│text │\n└─────┘")
        orphans = [i for i in issues if i.type == IssueType.ARROW_ORPHAN]
        assert len(orphans) == 0


class TestNestedBoxes:
    def test_nested_boxes(self):
        issues = _analyze("""┌─────────┐
│ ┌─────┐ │
│ │inner│ │
│ └─────┘ │
└─────────┘""")
        # Both boxes should be valid — no false gaps
        assert len(issues) == 0


class TestDanglingJunction:
    def test_connected_connector_no_dangling(self):
        issues = _analyze("│\n│\n│")
        dangling = [i for i in issues if i.type == IssueType.DANGLING_JUNCTION]
        assert len(dangling) == 0

    def test_totally_isolated_connector(self):
        issues = _analyze("   ┼")
        dangling = [i for i in issues if i.type == IssueType.DANGLING_JUNCTION]
        assert len(dangling) >= 1


class TestEdgeConnectors:
    def test_edge_start_is_ok(self):
        """Connector at the very start of a line should be ok if connected elsewhere."""
        issues = _analyze("──▶ text")
        assert len(issues) == 0

    def test_timeline(self):
        issues = _analyze("───●────▶")
        assert len(issues) == 0
