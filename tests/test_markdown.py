"""Tests for markdown.py — GFM table detection and normalization."""

import pytest
from diagram_sanitizer.markdown import (
    detect_markdown_tables,
    build_exempt_regions_from_lines,
    normalize_markdown_table,
    DetectedTable,
    _is_potential_table_row,
    _is_separator_row,
    _count_columns,
    _split_table_row,
    _build_separator_row,
)


class TestTableRowDetection:

    def test_potential_table_row_with_pipes(self):
        assert _is_potential_table_row("| A | B |") is True

    def test_potential_table_row_without_leading_pipe(self):
        assert _is_potential_table_row("A | B") is True

    def test_no_pipe_not_table(self):
        assert _is_potential_table_row("just text") is False

    def test_empty_line_not_table(self):
        assert _is_potential_table_row("") is False
        assert _is_potential_table_row("   ") is False


class TestSeparatorRowDetection:

    def test_valid_separator(self):
        assert _is_separator_row("|---|---|") is True

    def test_separator_with_colons(self):
        assert _is_separator_row("|:---|:---:|") is True

    def test_separator_with_whitespace(self):
        assert _is_separator_row("  | --- | --- |  ") is True

    def test_not_separator_no_dash(self):
        assert _is_separator_row("| A | B |") is False

    def test_not_separator_missing_pipe(self):
        assert _is_separator_row("---|---") is False  # missing leading |

    def test_empty_not_separator(self):
        assert _is_separator_row("") is False


class TestColumnCounting:

    def test_two_columns(self):
        assert _count_columns("| A | B |") == 2

    def test_three_columns(self):
        assert _count_columns("| A | B | C |") == 3

    def test_no_leading_trailing_pipes(self):
        assert _count_columns("A | B") == 2

    def test_single_column(self):
        assert _count_columns("| A |") == 1


class TestSplitTableRow:

    def test_basic_split(self):
        cells = _split_table_row("| A | B |")
        assert cells == ["A", "B"]

    def test_split_strips_whitespace(self):
        cells = _split_table_row("|  A  |  B  |")
        assert cells == ["A", "B"]

    def test_split_empty_cells(self):
        cells = _split_table_row("| A | | C |")
        assert cells == ["A", "", "C"]

    def test_split_no_leading_trailing_pipes(self):
        cells = _split_table_row("A | B")
        assert cells == ["A", "B"]


class TestBuildSeparatorRow:

    def test_basic_separator(self):
        sep = _build_separator_row(2, [3, 5])
        assert "---" in sep
        assert "-----" in sep

    def test_minimum_three_dashes(self):
        sep = _build_separator_row(2, [1, 2])
        # Each cell should have at least 3 dashes
        parts = sep.split("|")
        for p in parts:
            p = p.strip()
            if p:
                assert len(p) >= 3


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════


class TestDetectMarkdownTables:

    def test_simple_table_detected(self):
        """EC-031: valid markdown table is detected."""
        lines = ["| A | B |", "|---|---|", "| 1 | 2 |"]
        tables = detect_markdown_tables(lines)
        assert len(tables) == 1
        table = tables[0]
        assert table.start_line == 0
        assert table.end_line == 3
        assert table.column_count == 2
        assert table.has_separator is True

    def test_table_without_separator(self):
        """EC-032 case: table missing separator row."""
        lines = ["| A | B |", "| 1 | 2 |"]
        tables = detect_markdown_tables(lines)
        assert len(tables) == 1
        table = tables[0]
        assert table.has_separator is False

    def test_single_row_not_table(self):
        """AC-022: isolated single row is NOT treated as table."""
        lines = ["some text", "| A | B |", "more text"]
        tables = detect_markdown_tables(lines)
        assert len(tables) == 0

    def test_two_rows_different_columns_not_table(self):
        """Rows with different column counts don't form a table."""
        lines = ["| A | B |", "| 1 | 2 | 3 |"]
        tables = detect_markdown_tables(lines)
        assert len(tables) == 0

    def test_no_pipe_lines_not_detected(self):
        lines = ["just text", "more text"]
        tables = detect_markdown_tables(lines)
        assert len(tables) == 0

    def test_empty_input(self):
        tables = detect_markdown_tables([])
        assert len(tables) == 0

    def test_single_pipe_line_not_table(self):
        """One line with pipes but no second row."""
        lines = ["| A | B |"]
        tables = detect_markdown_tables(lines)
        assert len(tables) == 0

    def test_multi_row_table(self):
        """Table with more than 3 rows."""
        lines = [
            "| Name | Value |",
            "|------|-------|",
            "| foo  | 1     |",
            "| bar  | 2     |",
            "| baz  | 3     |",
        ]
        tables = detect_markdown_tables(lines)
        assert len(tables) == 1
        assert tables[0].end_line == 5

    def test_table_ends_at_non_table_line(self):
        """Table detection stops at non-table line."""
        lines = [
            "| A | B |",
            "|---|---|",
            "| 1 | 2 |",
            "",
            "more text",
        ]
        tables = detect_markdown_tables(lines)
        assert len(tables) == 1
        assert tables[0].end_line == 3  # stops at empty line

    def test_multiple_tables(self):
        """Two separate tables in the input."""
        lines = [
            "| A | B |",
            "|---|---|",
            "| 1 | 2 |",
            "",
            "| X | Y |",
            "|---|---|",
            "| 3 | 4 |",
        ]
        tables = detect_markdown_tables(lines)
        assert len(tables) == 2


class TestExemptRegions:

    def test_exempt_regions_include_pipes(self):
        lines = ["| A | B |", "|---|---|", "| 1 | 2 |"]
        tables = detect_markdown_tables(lines)
        exempt = build_exempt_regions_from_lines(tables, lines)
        # Row 0: col 0 (|), col 4 (|), col 8 (|)
        assert (0, 0) in exempt  # first |
        assert (0, 4) in exempt  # middle |
        assert (0, 8) in exempt  # last |
        assert (2, 0) in exempt  # first | of data row

    def test_exempt_regions_include_separator_dashes(self):
        lines = ["| A | B |", "|---|---|", "| 1 | 2 |"]
        tables = detect_markdown_tables(lines)
        exempt = build_exempt_regions_from_lines(tables, lines)
        # Row 1 has dashes — should be exempt
        assert (1, 2) in exempt  # -
        assert (1, 3) in exempt  # -


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestNormalizeMarkdownTable:

    def test_normalize_column_widths(self):
        """FR-029: column widths are normalized."""
        lines = ["| A | B |", "|---|---|", "| foo | bar |"]
        tables = detect_markdown_tables(lines)
        table = tables[0]
        result_lines, issues = normalize_markdown_table(list(lines), table)
        # All columns should be padded to match max width
        assert "foo" in result_lines[2]
        assert "bar" in result_lines[2]

    def test_insert_missing_separator(self):
        """FR-030: missing separator row is inserted."""
        lines = ["| A | B |", "| 1 | 2 |"]
        tables = detect_markdown_tables(lines)
        table = tables[0]
        result_lines, issues = normalize_markdown_table(list(lines), table)
        # A separator row should have been inserted
        assert len(result_lines) == 3
        assert any("---" in line for line in result_lines)
        assert any(i["type"] == "markdown_table" for i in issues)

    def test_separator_inserted_at_correct_position(self):
        """Separator goes as second row."""
        lines = ["| A | B |", "| 1 | 2 |"]
        tables = detect_markdown_tables(lines)
        table = tables[0]
        result_lines, issues = normalize_markdown_table(list(lines), table)
        # Result should be: header, separator, data
        assert "---" in result_lines[1]  # second row is separator

    def test_preserves_cell_content(self):
        """Cell text is never modified, only padded."""
        lines = ["| Hello | World |", "|---|---|"]
        tables = detect_markdown_tables(lines)
        table = tables[0]
        result_lines, issues = normalize_markdown_table(list(lines), table)
        assert "Hello" in result_lines[0]
        assert "World" in result_lines[0]
