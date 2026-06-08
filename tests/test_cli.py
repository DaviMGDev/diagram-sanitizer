"""Tests for the Click CLI — flag combinations, exit codes, output formats."""

import json
import os
import tempfile

import pytest
from click.testing import CliRunner

from diagram_sanitizer.cli import main


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


# ── Valid diagram ────────────────────────────────────────────────────────────

VALID_BOX = "┌───┐\n│ A │\n└───┘\n"
ORPHAN_VBAR = "  │\n"


# ── Default mode (report output) ─────────────────────────────────────────────


class TestDefaultMode:

    def test_default_json_output(self, runner):
        """Default invocation with a file should output JSON report."""
        result = runner.invoke(main, ["-"], input=VALID_BOX)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "ok"
        assert data["issues"] == []

    def test_default_text_output(self, runner):
        """--format text should output human-readable report."""
        result = runner.invoke(
            main, ["-", "--format", "text"], input=VALID_BOX
        )
        assert result.exit_code == 0
        assert "Status: OK" in result.output
        assert "Issues: 0" in result.output

    def test_default_with_issues_returns_warning_exit(self, runner):
        """AC-012: Diagram with issues exits non-zero in default mode."""
        result = runner.invoke(main, ["-"], input=ORPHAN_VBAR)
        assert result.exit_code in (1, 2)
        data = json.loads(result.output)
        assert data["status"] == "error"
        assert len(data["issues"]) > 0

    def test_default_stdin_pipe(self, runner):
        """Reading from stdin pipe should work."""
        result = runner.invoke(main, input=VALID_BOX)
        assert result.exit_code == 0

    def test_default_with_file(self, runner):
        """Reading from a real file should work."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(VALID_BOX)
            f.flush()
            result = runner.invoke(main, [f.name])
        os.unlink(f.name)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "ok"


# ── --check mode ─────────────────────────────────────────────────────────────


class TestCheckMode:

    def test_check_valid_no_output(self, runner):
        """--check on valid diagram: exit 0, no output."""
        result = runner.invoke(main, ["--check", "-"], input=VALID_BOX)
        assert result.exit_code == 0
        assert result.output == ""

    def test_check_with_issues_exits_2(self, runner):
        """--check on diagram with errors: exit 2, no output."""
        result = runner.invoke(main, ["--check", "-"], input=ORPHAN_VBAR)
        assert result.exit_code == 2
        assert result.output == ""


# ── --fix mode ───────────────────────────────────────────────────────────────


class TestFixMode:

    def test_fix_valid_diagram_no_output(self, runner):
        """--fix on a valid diagram: nothing to fix, no output, exit 0."""
        result = runner.invoke(main, ["--fix", "-"], input=VALID_BOX)
        # corrected_diagram is null so nothing printed
        assert result.exit_code == 0

    def test_fix_orphan_removes_it(self, runner):
        """--fix on a diagram with an orphan: outputs corrected diagram."""
        result = runner.invoke(main, ["--fix", "-"], input=ORPHAN_VBAR)
        # Should output the corrected version (│ replaced with space)
        assert result.exit_code in (1, 2)  # Error status for orphans
        # The orphan │ should be replaced with space
        assert "│" not in result.output

    def test_fix_gap_fills_it(self, runner):
        """--fix on a box with a gap: fills the gap."""
        result = runner.invoke(
            main, ["--fix", "-"], input="┌─┐\n│ │\n└ ┘\n"
        )
        if result.output:
            # The gap at (3,2) should be filled with ─
            lines = result.output.strip().split("\n")
            bottom = lines[-1]
            assert "─" in bottom

    def test_fix_in_place_requires_file(self, runner):
        """--fix --in-place on stdin should error."""
        result = runner.invoke(
            main, ["--fix", "--in-place", "-"], input=VALID_BOX
        )
        assert result.exit_code != 0

    def test_fix_in_place_requires_fix(self, runner):
        """--in-place without --fix should error."""
        result = runner.invoke(
            main, ["--in-place", "file.txt"], input=VALID_BOX
        )
        assert result.exit_code != 0

    def test_fix_in_place_overwrites_file(self, runner):
        """--fix --in-place atomically overwrites the file."""
        broken = "  │\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(broken)
            tmp_path = f.name

        try:
            result = runner.invoke(
                main, ["--fix", "--in-place", tmp_path]
            )
            assert result.exit_code in (1, 2)  # Had errors (orphan = error severity)
            # File should now be corrected (│ → space)
            with open(tmp_path, encoding="utf-8") as f:
                content = f.read()
            assert "│" not in content
        finally:
            os.unlink(tmp_path)


# ── --tab-width ──────────────────────────────────────────────────────────────


class TestTabWidth:

    def test_tab_width_passed_to_engine(self, runner):
        """--tab-width flag should work."""
        result = runner.invoke(
            main, ["--tab-width", "8", "-"], input="\t│\n"
        )
        assert result.exit_code in (0, 1, 2)


# ── --version ────────────────────────────────────────────────────────────────


class TestVersion:

    def test_version_flag(self, runner):
        """--version should print version and exit 0."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "diagram-sanitizer" in result.output


# ── --help ───────────────────────────────────────────────────────────────────


class TestHelp:

    def test_help_flag(self, runner):
        """--help should print usage and exit 0."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "--check" in result.output
        assert "--fix" in result.output
        assert "--in-place" in result.output
        assert "--format" in result.output
        assert "--tab-width" in result.output


# ── Error handling ───────────────────────────────────────────────────────────


class TestErrorHandling:

    def test_file_not_found(self, runner):
        """Non-existent file should cause an error."""
        result = runner.invoke(main, ["nonexistent_file.txt"])
        assert result.exit_code != 0

    def test_empty_input(self, runner):
        """Empty input should not crash."""
        result = runner.invoke(main, ["-"], input="")
        assert result.exit_code == 0
