"""Preprocessing stage — normalizes raw input before analysis.

Handles BOM stripping, ANSI escape removal, tab expansion,
line-ending normalization, trailing whitespace trimming, and
full-width character expansion (CJK, emoji).
"""

from __future__ import annotations

import re

# ANSI escape sequence pattern (CSI sequences: ESC [ ... m)
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

# UTF-8 BOM character
_BOM = "\ufeff"

# Try to import wcwidth for CJK full-width support (optional)
try:
    from wcwidth import wcswidth as _wcswidth
    _HAS_WCWIDTH = True
except ImportError:
    _HAS_WCWIDTH = False
    def _wcswidth(s: str) -> int:
        return len(s)


def display_width(ch: str) -> int:
    """Return the display width of a character (1 or 2 for CJK/emoji).

    Uses wcwidth if available, otherwise falls back to 1 for all chars.
    """
    if not ch:
        return 0
    w = _wcswidth(ch)
    return w if w > 0 else 1


def preprocess(text: str, tab_width: int = 4) -> str:
    """Normalize raw diagram input for analysis.

    Applies in order:
    1. BOM stripping (EC-025)
    2. ANSI escape removal (EC-026)
    3. Tab expansion (EC-009)
    4. Full-width character expansion (EC-015, NFR-002)
    5. Line-ending normalization (FR-002)
    6. Trailing whitespace trimming (EC-011)

    Args:
        text: Raw UTF-8 input string.
        tab_width: Number of spaces per tab (default 4).

    Returns:
        Normalized string with LF line endings and no trailing whitespace.
    """
    # 1. Strip UTF-8 BOM if present
    if text.startswith(_BOM):
        text = text[1:]

    # 2. Remove ANSI escape sequences
    text = _ANSI_ESCAPE_RE.sub("", text)

    # 3. Expand tabs
    text = text.expandtabs(tab_width)

    # 4. Expand full-width characters to preserve column alignment (EC-015)
    if _HAS_WCWIDTH:
        lines = text.split("\n")
        expanded_lines: list[str] = []
        for line in lines:
            expanded = ""
            for ch in line:
                w = display_width(ch)
                if w >= 2:
                    expanded += ch + " " * (w - 1)
                else:
                    expanded += ch
            expanded_lines.append(expanded)
        text = "\n".join(expanded_lines)

    # 5. Normalize line endings to LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 5. Trim trailing whitespace from each line
    lines = text.split("\n")
    lines = [line.rstrip() for line in lines]
    text = "\n".join(lines)

    return text
