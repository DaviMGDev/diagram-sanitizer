"""Preprocessing stage — normalizes raw input before analysis.

Handles BOM stripping, ANSI escape removal, tab expansion,
line-ending normalization, and trailing whitespace trimming.
"""

from __future__ import annotations

import re

# ANSI escape sequence pattern (CSI sequences: ESC [ ... m)
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

# UTF-8 BOM character
_BOM = "\ufeff"


def preprocess(text: str, tab_width: int = 4) -> str:
    """Normalize raw diagram input for analysis.

    Applies in order:
    1. BOM stripping (EC-025)
    2. ANSI escape removal (EC-026)
    3. Tab expansion (EC-009)
    4. Line-ending normalization (FR-002)
    5. Trailing whitespace trimming (EC-011)

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

    # 4. Normalize line endings to LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 5. Trim trailing whitespace from each line
    lines = text.split("\n")
    lines = [line.rstrip() for line in lines]
    text = "\n".join(lines)

    return text
