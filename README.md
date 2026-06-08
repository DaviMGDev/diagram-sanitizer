# diagram-sanitizer

> Validate and auto-correct ASCII diagrams for structural integrity.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-blue)](.)
[![Tests](https://img.shields.io/badge/Tests-246%20passed-brightgreen)](.)

**diagram-sanitizer** parses ASCII and Unicode box-drawing diagrams into a 2D character grid, analyzes connectivity between connectors, and detects — and where possible, automatically fixes — structural issues.

> **Why?** AI-generated ASCII diagrams often have disconnected lines — vertical bars (`│`) and horizontal dashes (`─`) that fail to meet their intended corners, T-junctions, arrows, or circles. This tool catches those errors and fixes the unambiguous ones, so your diagrams render correctly in documentation, READMEs, and slide decks.

---

## Status

| Aspect | Status |
|---|---|
| **Specification** | ✅ Complete — [SPEC.md](./SPEC.md) (v1.3) |
| **Core engine** | ✅ Fully implemented — 12-stage pipeline |
| **CLI** | ✅ Done — Click-based, all flags operational |
| **Tests** | ✅ 246 tests, all passing |
| **Markdown tables** | ✅ Detection & normalization (GFM) |

The [SPEC.md](./SPEC.md) is the authoritative source of truth for all requirements, edge cases, and the processing pipeline.

---

## Features

- **🕵️ Orphan detection** — Finds box-drawing, arrow, and circle characters completely disconnected from any diagram structure. Fully isolated orphans (single cell) and component orphans (disconnected multi-cell fragments) are both detected and removed in the corrected output.
- **🔍 Gap detection** — Ray-casts from each connector along its expected directions to find gaps. Single-cell gaps with an unambiguous line character are auto-filled.
- **📦 Box-width analysis** — Detects mismatched top/bottom border widths and normalizes to the correct width when unambiguous (modal width, narrower-wins tiebreaker).
- **🎨 Style consistency** — Detects mixed single-line (`┌─┐│└┘`) and double-line (`╔═╗║╚╝`) characters within the same connected component. Unifies to the majority style (>80% threshold).
- **⚠️ Cross/arrow/circle validation** — Warns on crosses with fewer than 4 connections, arrow heads pointing at empty space, broken full arrows (`→←↑↓`), and potential circle orphans.
- **🧩 Missing side detection** — Identifies boxes with incomplete vertical borders or missing corners (3-sided boxes).
- **↔️ Overlap detection** — Detects when two connected components share grid positions (malformed input).
- **🏷️ Mixed arrow detection** — Warns when both Unicode arrows (`→←↑↓`) and ASCII dash connectors (`-`) are present.
- **📊 Markdown table awareness** — Automatically detects GFM markdown tables, exempts their formatting characters from diagram analysis, normalizes column widths, and inserts missing separator rows.
- **🌏 CJK support** — Full-width character expansion (Chinese, Japanese, Korean, emoji) preserves column alignment via optional `wcwidth`.
- **📋 Structured JSON output** — Full report with status, issue list (line/col/severity/type/message/fixable/fix_suggestion), and corrected diagram.
- **🔌 Library API** — Import `sanitize()` directly in your Python code for CI pipeline integration.

---

## Installation

```bash
# Install from source (requires Python 3.10+ and uv)
git clone https://github.com/davi/diagram-sanitizer.git
cd diagram-sanitizer
uv sync
```

This installs the package in editable mode with its sole runtime dependency (`click`). The `das` CLI is then available via `uv run das` or directly in your shell after `uv sync`.

### Requirements

- **Python**: 3.10, 3.11, 3.12, 3.13, or 3.14
- **Runtime dependency**: [`click`](https://click.palletsprojects.com/) ≥ 8.0 (CLI framework)
- **Optional**: [`wcwidth`](https://pypi.org/project/wcwidth/) ≥ 0.2 (CJK full-width character support)
- **Dev**: [`pytest`](https://docs.pytest.org/) ≥ 8 (test runner)

---

## CLI Usage

```bash
# Validate a diagram file, output JSON report
das diagram.txt

# Check-only mode (exit code, no output)
das --check diagram.txt

# Print corrected diagram to stdout
das --fix diagram.txt

# Overwrite the file atomically with corrections
das --fix --in-place diagram.txt

# Pipe input from stdin
cat diagram.txt | das

# Output full JSON report (instead of corrected diagram)
das --json diagram.txt

# Show version
das --version
```

### Exit codes

| Code | Meaning |
|---|---|
| `0` | No issues (status: `"ok"`) |
| `1` | Warnings only (status: `"warning"`) |
| `2` | Errors present (status: `"error"`) |

### CLI options

| Flag | Description |
|---|---|
| `--check` | Exit code only; no output to stdout |
| `--fix` | Print corrected diagram to stdout |
| `--fix --in-place` | Atomically overwrite the input file |
| `--format json\|text` | Control output format (default: `json`) |
| `--tab-width N` | Spaces per tab (default: 4) |
| `--version` | Show version and exit |
| `--help` | Show help and exit |

---

## Library API

```python
from diagram_sanitizer import sanitize

report = sanitize(
    diagram_string,
    options={"tab_width": 4}
)
```

### Options

| Key | Type | Default | Description |
|---|---|---|---|
| `tab_width` | `int` | `4` | Spaces per tab |
| `max_grid_width` | `int` | `400` | Maximum columns before warning |
| `mode` | `str` | `"auto"` | `"check"`, `"fix"`, or `"auto"` |

### Return value

```python
{
    "status": "ok",                # "ok" | "warning" | "error"
    "issues": [
        {
            "id": "GAP-5-12",      # optional stable identifier
            "line": 5,             # 1-indexed line
            "col": 12,             # 1-indexed column
            "end_line": 5,         # optional (multi-cell issues)
            "end_col": 14,         # optional
            "severity": "error",   # "error" | "warning" | "info"
            "type": "gap",         # "gap" | "orphan" | "box_width" | ...
            "message": "...",
            "fixable": True,
            "fix_suggestion": "Insert '│' at (6,12)"
        }
    ],
    "corrected_diagram": "..."     # string | None
}
```

The `corrected_diagram` field is:
- **`None`** — when no issues found, or no issues are fixable
- **`string`** — when at least one fixable issue was corrected

---

## Architecture

The analysis follows a fixed 12-step pipeline (defined in [SPEC.md FR-027](./SPEC.md)):

```
Input
  │
  ▼
┌─────────────────────┐
│ 1. Preprocessing    │  BOM stripping, ANSI removal, tab expansion,
│                     │  line-ending normalization, whitespace trim
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 2. Grid Construction│  Parse normalized input into 2D char grid
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 2b. Markdown Detect │  Detect & exempt GFM table formatting chars
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 3. Connector Class. │  Classify cells as connector or non-connector
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 4. Component Analysis│  Cluster connectors into connected components
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 5. Orphan Detection │  Find fully isolated & component orphans
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 6. Gap Detection    │  Ray-cast for connectivity gaps
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 7. Box Analysis     │  Identify boxes, detect width mismatches
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 8. Style Analysis   │  Detect mixed single/double-line characters
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ 9. Cross/Arrow/Circ │  Validate crosses, arrows, circles
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│10. Fix Application  │  Apply unambiguous fixes in order
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│10b. Table Normalize │  Normalize markdown table columns (if detected)
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│11. Output Generation│  Produce JSON report + corrected diagram
└─────────────────────┘
          │
          ▼
       Output
```

### Package structure

```
diagram-sanitizer/
├── src/diagram_sanitizer/
│   ├── __init__.py          # Package init, exposes __version__ & sanitize()
│   ├── __main__.py          # python -m diagram_sanitizer support
│   ├── cli.py               # CLI entry point (Click-based)
│   ├── engine.py            # Pipeline orchestrator (sanitize entry point)
│   ├── preprocessor.py      # BOM/ANSI/tab/CJK normalization
│   ├── markdown.py          # GFM table detection & normalization
│   ├── grid.py              # 2D character grid + connector classification
│   ├── connector_map.py     # Connector character definitions (Appendix A)
│   ├── components.py        # Connected component analysis (union-find)
│   ├── detectors.py         # All 8 detection stages
│   └── fixer.py             # Fix application (orphan, gap, box, style)
├── tests/
│   ├── conftest.py          # 37 shared fixtures
│   ├── test_cli.py          # CLI tests (Click runner)
│   ├── test_components.py   # Union-find + component tests
│   ├── test_connector_map.py # Connector map completeness tests
│   ├── test_detectors.py    # Orphan/gap/box/style/cross detection tests
│   ├── test_engine.py       # Pipeline integration + API contract tests
│   ├── test_fixer.py        # Fix application tests
│   ├── test_grid.py         # Grid construction + access tests
│   ├── test_markdown.py     # Markdown table detection & normalization tests
│   └── test_preprocessor.py # Preprocessing normalization tests
├── SPEC.md                  # Full specification (source of truth, v1.3)
├── AGENTS.md                # AI agent context
├── pyproject.toml           # Build config (hatchling)
├── uv.lock                  # Dependency lockfile
└── .gitignore
```

---

## What kinds of issues does it detect?

The tool recognizes the full Unicode box-drawing character set (single-line `┌─┐│└┘├┤┴┬┼`, double-line `╔═╗║╚╝╠╣╦╩╬`), arrows (`▶◀▼▲→←↑↓`), circles (`●○`), diagonals (`╲╱`), and ASCII fallbacks (`+`, `-`, `|`).

### Issues detected

| Type | Severity | Fixable | Example |
|---|---|---|---|
| **Connectivity gap** | `error` | ✅ (1-cell) | `│` above `└` with empty cell between them |
| **Orphan symbol** | `error` | ✅ (removal) | A `│` with no neighbors in any expected direction |
| **Component orphan** | `error` | ✅ (removal) | Disconnected fragment with <50% of largest component |
| **Box-width mismatch** | `error` | ✅ | `┌───┐` top vs `└─┘` bottom |
| **Missing side** | `error` | — | Box with incomplete vertical borders or corners |
| **Arrow orphan** | `error` | ✅ (removal) | Arrow head `▶` or full arrow `→` with no connections |
| **Overlap** | `error` | — | Two components sharing grid positions |
| **Style inconsistency** | `warning` | ✅ (>80%) | `┌─┐` mixed with `║` in same component |
| **Dangling cross** | `warning` | — | A `┼` with only 3 connected directions |
| **Circle near connector** | `warning` | — | `●` exactly 1 cell from a connector but not linked |
| **Mixed arrow styles** | `warning` | — | Unicode arrows (`→`) + ASCII dashes (`-`) in same input |
| **Unicode/ASCII mix** | `info` | — | Unicode box-drawing mixed with ASCII `+\|-` connectors |
| **Markdown table** | `warning`/`info` | ✅ | Missing separator row or uneven column widths |
| **Encoding** | `warning` | — | Input contains invalid UTF-8 sequences |

---

## Development

```bash
# Install in editable mode with dev dependencies
uv sync

# Run the package
uv run das --help
uv run python -m diagram_sanitizer --help

# Run all tests (246 tests)
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Build distribution
uv build
```

### Code style

- **Python**: 3.10+ with type hints (PEP 484)
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **Docstrings**: Triple-quoted `"""..."""` at module and function level
- **Imports**: stdlib first, then third-party, then local; absolute preferred
- **Exit codes**: `0` (ok), `1` (warnings), `2` (errors)

> Linting/formatting config (`ruff`, `black`) has not yet been set up.

---

## Contributing

Contributions are welcome! This project follows a **Spec-Driven Development** approach — the [SPEC.md](./SPEC.md) is the authoritative source of truth.

1. Read the [SPEC.md](./SPEC.md) to understand the full requirements.
2. Check the [AGENTS.md](./AGENTS.md) for AI agent context.
3. Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `build:`, `test:`, `refactor:`, `chore:`).
4. Submit a pull request.

### Roadmap

1. ~~**Implement core engine**~~ ✅ Done — 12-stage pipeline with 8 detectors
2. ~~**Add test suite**~~ ✅ Done — 246 passing tests across 9 test files
3. **Add linting** — configure `ruff` for code quality
4. **Set up CI** — GitHub Actions for lint → test → build
5. **Context-aware text regions** — auto-detect prose vs. diagram sections to reduce false positives
6. **Multi-line gap fill** — extend auto-fix to multi-cell gaps with unambiguous context
7. **Arrow chain validation** — validate arrow → line → arrow head sequences

---

## License

MIT — see [LICENSE](LICENSE) for details.
