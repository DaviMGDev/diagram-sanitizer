"""Tests for preprocessor.py — input normalization."""

from diagram_sanitizer.preprocessor import preprocess


class TestBOMStripping:

    def test_bom_at_start_is_removed(self):
        text = "\ufeff┌─┐\n└─┘"
        result = preprocess(text)
        assert not result.startswith("\ufeff")
        assert result.startswith("┌─┐")

    def test_no_bom_passes_through(self):
        text = "┌─┐\n└─┘"
        result = preprocess(text)
        assert result == "┌─┐\n└─┘"

    def test_bom_in_middle_not_removed(self):
        text = "text \ufeff more"
        result = preprocess(text)
        assert "\ufeff" in result


class TestANSIRemoval:

    def test_simple_ansi_colors_removed(self):
        text = "\x1b[31mRed\x1b[0m"
        result = preprocess(text)
        assert result == "Red"

    def test_ansi_in_diagram_removed(self):
        text = "\x1b[31m┌─┐\x1b[0m\n\x1b[32m└─┘\x1b[0m"
        result = preprocess(text)
        assert result == "┌─┐\n└─┘"

    def test_ansi_with_semicolons_removed(self):
        text = "\x1b[1;31mBold Red\x1b[0m"
        result = preprocess(text)
        assert result == "Bold Red"

    def test_no_ansi_passes_through(self):
        text = "normal text"
        result = preprocess(text)
        assert result == "normal text"


class TestTabExpansion:

    def test_tab_expands_to_spaces(self):
        text = "\ttext"
        result = preprocess(text, tab_width=4)
        assert result == "    text"

    def test_tab_multiple_tabs(self):
        text = "\t\ttext"
        result = preprocess(text, tab_width=2)
        assert result == "    text"

    def test_tab_custom_width(self):
        text = "\ttext"
        result = preprocess(text, tab_width=8)
        assert result == "        text"

    def test_tab_default_width_is_4(self):
        text = "\ttext"
        result = preprocess(text)
        assert result == "    text"


class TestLineEndingNormalization:

    def test_crlf_to_lf(self):
        text = "line1\r\nline2"
        result = preprocess(text)
        assert result == "line1\nline2"
        assert "\r" not in result

    def test_cr_to_lf(self):
        text = "line1\rline2"
        result = preprocess(text)
        assert result == "line1\nline2"

    def test_mixed_endings(self):
        text = "a\r\nb\rc\nd"
        result = preprocess(text)
        assert result == "a\nb\nc\nd"
        assert "\r" not in result

    def test_lf_only_unchanged(self):
        text = "line1\nline2"
        result = preprocess(text)
        assert result == "line1\nline2"


class TestTrailingWhitespaceTrimming:

    def test_trailing_spaces_removed(self):
        text = "line1   \nline2  "
        result = preprocess(text)
        assert result == "line1\nline2"

    def test_trailing_tabs_removed(self):
        text = "line1\t\nline2"
        result = preprocess(text)
        # tabs are expanded first, then trailing spaces trimmed
        assert result == "line1\nline2"

    def test_no_trailing_whitespace_passes_through(self):
        text = "line1\nline2"
        result = preprocess(text)
        assert result == "line1\nline2"


class TestCombinedNormalization:

    def test_all_normalizations_applied(self):
        text = "\ufeff\x1b[31m┌─┐\x1b[0m  \r\n\t└─┘  \r"
        result = preprocess(text, tab_width=4)
        # trailing \r normalizes to \n, giving trailing newline
        assert result == "┌─┐\n    └─┘\n"
        assert "\r" not in result
        assert "\ufeff" not in result
        assert "\x1b" not in result

    def test_empty_string(self):
        result = preprocess("")
        assert result == ""

    def test_whitespace_only(self):
        result = preprocess("   \n\t\n  ")
        assert result == "\n\n"
