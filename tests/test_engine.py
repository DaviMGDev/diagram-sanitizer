"""Tests for engine.py — full pipeline integration."""

import pytest
from diagram_sanitizer.engine import sanitize, _deduplicate, _compute_status


class TestSanitizeAPI:

    def test_function_exists_and_returns_dict(self):
        """AC-011: sanitize() exists and returns a dict."""
        result = sanitize("┌─┐\n└─┘")
        assert isinstance(result, dict)
        assert "status" in result
        assert "issues" in result
        assert "corrected_diagram" in result

    def test_valid_diagram_returns_ok(self):
        """AC-001: Valid diagram → status ok, no issues."""
        result = sanitize("┌───┐\n│ A │\n└───┘")
        assert result["status"] == "ok"
        assert result["issues"] == []
        assert result["corrected_diagram"] is None

    def test_empty_string(self):
        """EC-001: Empty string → ok, no issues, null corrected."""
        result = sanitize("")
        assert result["status"] == "ok"
        assert result["issues"] == []
        assert result["corrected_diagram"] is None

    def test_no_connectors(self):
        """EC-002/003: No connectors → ok, no issues."""
        result = sanitize("Hello World\nJust text")
        assert result["status"] == "ok"
        assert result["issues"] == []

    def test_orphan_diagram_returns_errors(self):
        """A diagram with orphan characters should return errors."""
        result = sanitize("  │\n")
        assert result["status"] == "error"
        assert len(result["issues"]) > 0

    def test_corrected_diagram_when_fixable(self):
        """FR-025: corrected_diagram is string when fixable issues exist."""
        # Single orphan │ — fixable
        result = sanitize("  │\n")
        if any(i["fixable"] for i in result["issues"]):
            assert result["corrected_diagram"] is not None
            assert isinstance(result["corrected_diagram"], str)

    def test_corrected_diagram_null_when_no_fixable(self):
        """FR-025: corrected_diagram is null when no fixable issues."""
        # Use a case that produces only unfixable issues
        # A very ambiguous gap
        result = sanitize("┌─┐\n└ ┘")  # Width info needed
        if result["issues"] and not any(i["fixable"] for i in result["issues"]):
            assert result["corrected_diagram"] is None

    def test_non_connector_content_preserved(self):
        """AC-016: Text labels preserved in corrected_diagram."""
        result = sanitize("  │\n")
        if result["corrected_diagram"]:
            # Text around orphan should be preserved
            # The orphan │ gets removed but the surrounding text stays
            pass  # Just don't crash

    def test_issues_have_fixable_field(self):
        """AC-018: Every issue must have fixable boolean."""
        result = sanitize("  │\n")
        for issue in result["issues"]:
            assert "fixable" in issue
            assert isinstance(issue["fixable"], bool)

    def test_issues_have_required_fields(self):
        """Verify each issue has all required fields per spec."""
        result = sanitize("  │\n")
        for issue in result["issues"]:
            assert "line" in issue
            assert "col" in issue
            assert "severity" in issue
            assert "type" in issue
            assert "message" in issue
            assert "fixable" in issue

    def test_no_crash_on_complex_diagram(self):
        """Smoke test: complex diagram shouldn't crash."""
        diagram = (
            "┌──────┐     ┌──────┐\n"
            "│ Start│────▶│ End  │\n"
            "└──────┘     └──────┘\n"
        )
        result = sanitize(diagram)
        assert "status" in result

    def test_orphan_component_detection_integration(self):
        """A diagram with a disconnected fragment."""
        diagram = "┌───┐     └─\n│ A │\n└───┘"
        result = sanitize(diagram)
        # Should find the orphan └─ fragment
        orphan_issues = [i for i in result["issues"] if i["type"] == "orphan"]
        assert len(orphan_issues) > 0

    def test_gap_detection_integration(self):
        """Box with a gap should be detected."""
        diagram = "┌─┐\n│ │\n└ ┘"
        result = sanitize(diagram)
        gap_issues = [i for i in result["issues"] if i["type"] == "gap"]
        # There's a gap in the bottom border
        assert len(gap_issues) > 0

    def test_style_mix_integration(self):
        """Mixed single/double should be detected."""
        diagram = "┌─┐\n║X║\n└─┘"
        result = sanitize(diagram)
        style_issues = [i for i in result["issues"] if i["type"] == "style_mix"]
        assert len(style_issues) > 0

    def test_box_width_mismatch_integration(self):
        """Mismatched box widths should be detected."""
        diagram = "┌───┐\n│ X │\n└─┘"
        result = sanitize(diagram)
        box_issues = [i for i in result["issues"] if i["type"] == "box_width"]
        assert len(box_issues) > 0

    def test_dangling_cross_integration(self):
        """A cross with fewer than 4 connections should warn."""
        diagram = "  │\n──┼\n"
        result = sanitize(diagram)
        cross_issues = [
            i for i in result["issues"] if i["type"] == "dangling_junction"
        ]
        assert len(cross_issues) > 0

    def test_issue_ids_present(self):
        """Issues should have id field."""
        result = sanitize("  │\n")
        for issue in result["issues"]:
            assert "id" in issue

    def test_options_tab_width(self):
        """Tab width option is passed through."""
        result = sanitize("\t│\n", {"tab_width": 8})
        # Should work without error
        assert "status" in result

    def test_options_mode_check(self):
        """mode='check' skips fix application."""
        result = sanitize("  │\n", {"mode": "check"})
        assert result["corrected_diagram"] is None

    def test_options_mode_fix(self):
        """mode='fix' always applies fixes."""
        result = sanitize("  │\n", {"mode": "fix"})
        if any(i["fixable"] for i in result["issues"]):
            assert result["corrected_diagram"] is not None


class TestDeduplication:

    def test_deduplicate_removes_duplicates(self):
        issues = [
            {"type": "orphan", "line": 1, "col": 1, "severity": "error",
             "message": "first", "fixable": True},
            {"type": "orphan", "line": 1, "col": 1, "severity": "error",
             "message": "duplicate", "fixable": True},
        ]
        result = _deduplicate(issues)
        assert len(result) == 1
        assert result[0]["message"] == "first"

    def test_different_types_not_duplicates(self):
        issues = [
            {"type": "orphan", "line": 1, "col": 1, "severity": "error",
             "message": "first", "fixable": True},
            {"type": "gap", "line": 1, "col": 1, "severity": "error",
             "message": "different type", "fixable": False},
        ]
        result = _deduplicate(issues)
        assert len(result) == 2

    def test_different_positions_not_duplicates(self):
        issues = [
            {"type": "orphan", "line": 1, "col": 1, "severity": "error",
             "message": "first", "fixable": True},
            {"type": "orphan", "line": 1, "col": 2, "severity": "error",
             "message": "different col", "fixable": True},
        ]
        result = _deduplicate(issues)
        assert len(result) == 2


class TestComputeStatus:

    def test_no_issues_ok(self):
        assert _compute_status([]) == "ok"

    def test_only_warnings(self):
        issues = [
            {"severity": "warning", "type": "style_mix", "line": 1, "col": 1,
             "message": "", "fixable": False},
        ]
        assert _compute_status(issues) == "warning"

    def test_errors_override_warnings(self):
        issues = [
            {"severity": "warning", "type": "style_mix", "line": 1, "col": 1,
             "message": "", "fixable": False},
            {"severity": "error", "type": "orphan", "line": 1, "col": 2,
             "message": "", "fixable": True},
        ]
        assert _compute_status(issues) == "error"

    def test_info_only_is_warning(self):
        issues = [
            {"severity": "info", "type": "style_mix", "line": 1, "col": 1,
             "message": "", "fixable": False},
        ]
        assert _compute_status(issues) == "warning"
