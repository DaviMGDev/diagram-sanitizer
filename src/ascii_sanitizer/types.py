"""Data types for the ASCII diagram sanitizer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueType(str, Enum):
    GAP = "gap"
    BOX_WIDTH = "box_width"
    STYLE_MIX = "style_mix"
    DANGLING_JUNCTION = "dangling_junction"
    ARROW_ORPHAN = "arrow_orphan"


@dataclass
class Issue:
    """A single detected issue in a diagram."""
    line: int          # 1-indexed
    col: int           # 1-indexed
    severity: Severity
    type: IssueType
    message: str
    fixable: bool = False
    fix_suggestion: str | None = None
    end_line: int | None = None
    end_col: int | None = None


@dataclass
class Report:
    """Full analysis report."""
    status: str       # "ok", "warning", "error"
    issues: list[Issue] = field(default_factory=list)
    corrected_diagram: str | None = None

    def to_dict(self) -> dict:
        result: dict = {
            "status": self.status,
            "issues": [],
            "corrected_diagram": self.corrected_diagram,
        }
        for issue in self.issues:
            d: dict = {
                "line": issue.line,
                "col": issue.col,
                "severity": issue.severity.value,
                "type": issue.type.value,
                "message": issue.message,
                "fixable": issue.fixable,
                "fix_suggestion": issue.fix_suggestion,
            }
            if issue.end_line is not None:
                d["end_line"] = issue.end_line
            if issue.end_col is not None:
                d["end_col"] = issue.end_col
            result["issues"].append(d)
        return result
