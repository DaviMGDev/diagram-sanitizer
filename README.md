# ASCII Diagram Sanitizer

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Version](https://img.shields.io/badge/version-0.1.0-informational)](pyproject.toml)
[![Status](https://img.shields.io/badge/status-WIP-orange)](#current-status)

**Validate and auto-fix structural errors in ASCII diagrams.**

A Python library + CLI that parses ASCII diagrams into a 2D character grid,
detects connectivity gaps, box-width mismatches, and style inconsistencies,
then auto-corrects unambiguous errors.

---

## Quick Example

### The Problem

AI-generated or hand-drawn ASCII diagrams often have disconnected lines
that make them look broken when rendered in documentation:

```
┌──────┐
│ text │
└──   ┘       ← bottom border is too short!
```

### The Fix

```bash
$ ascii-sanitize --fix broken-diagram.txt
┌──────┐
│ text │
└──────┘      ← corrected!
```

### JSON Report (default output)

```bash
$ ascii-sanitize diagram.txt
```
```json
{
  "status": "error",
  "issues": [
    {
      "line": 3,
      "col": 1,
      "severity": "error",
      "type": "box_width",
      "message": "Box width mismatch: top border at row 1 has width 6, bottom border at row 3 has width 4",
      "fixable": true,
      "fix_suggestion": "Normalize box borders to width 6 (top is 6, bottom is 4)"
    }
  ],
  "corrected_diagram": "┌──────┐\n│ text │\n└──────┘"
}
```

---

## Features

- **Connectivity trace** — detects broken lines (vertical `│`, horizontal `─`)
- **Gap analysis** — single-cell gaps are auto-fixable; 2+ cell gaps are reported
- **Box-width normalization** — fixes mismatched top/bottom borders
- **Style unification** — detects mixed single (`┌─┐`) and double (`╔═╗`) line styles
- **Arrow/circle checks** — flags orphaned arrow heads and circles
- **Content preservation** — labels, text, and surrounding prose are untouched
- **JSON or human-readable output** — `--format json|text`
- **Exit codes** — `0` (ok), `1` (warning), `2` (error) for CI pipelines

### Supported Diagram Types

The 16 diagram types from [`diagram.md`](diagram.md):
flowcharts, trees, networks, tables, timelines, Venn diagrams,
bar charts, pipelines, state machines, mind maps, sequence diagrams,
Gantt charts, ER diagrams, pie charts, architecture blocks, and swimlanes.

### Connector Characters Supported

All Unicode box-drawing (single `┌─┐│└┘├┤┴┬┼` and double `╔═╗║╚╝╠╣╩╦╬`),
arrow heads (`▶▼◀▲`), full arrows (`→←↑↓`), circles (`●○`), diagonals (`╲╱`),
and ASCII fallbacks (`+`, `-`, `|`).

---

## Installation

> **Current status**: The package is in development and not yet published to PyPI.
> You can install from source:

```bash
# Clone and install with uv (recommended)
git clone https://github.com/your-org/ascii-sanitizer.git
cd ascii-sanitizer
uv sync
uv pip install -e .

# Or with pip
pip install -e .
```

### Requirements

- Python 3.10 or later
- `click` ≥ 8 (CLI dependency)
- `wcwidth` ≥ 0.2 (optional, for CJK width handling)

The **library API** has zero required dependencies beyond the Python standard library.

---

## Usage

### CLI

```bash
# Validate a diagram (JSON report)
ascii-sanitize diagram.txt

# Human-readable report
ascii-sanitize --format text diagram.txt

# CI check — exit code only (0=ok, 1=warnings, 2=errors)
ascii-sanitize --check diagram.txt

# Auto-fix and print corrected diagram
ascii-sanitize --fix diagram.txt

# Auto-fix in-place (overwrites file)
ascii-sanitize --fix --in-place diagram.txt

# Read from stdin
cat diagram.txt | ascii-sanitize --fix -
```

### Library API

```python
from ascii_sanitizer import sanitize, format_text

diagram = """┌──────┐
│ text │
└──   ┘"""

report = sanitize(diagram)

print(report.status)          # "error"
print(len(report.issues))     # 1
print(report.issues[0].type)  # IssueType.BOX_WIDTH
print(report.corrected_diagram)  # "┌──────┐\n│ text │\n└──────┘" or None

# JSON-serializable dict
data = report.to_dict()

# Human-readable format
print(format_text(report))
```

---

## Architecture

```
ascii_sanitizer/
├── __init__.py       # Public API: sanitize(), __version__
├── grid.py           # 2D grid: parse string → grid, reconstruct grid → string
├── connectors.py     # Character classification, direction maps, style maps
├── analyzer.py       # Core engine: trace, gap/box/style/arrow detection
├── fixer.py          # Auto-fix: gap fill, box normalize, style unify
├── report.py         # JSON report builder + human-readable formatter
├── cli.py            # Click-based CLI with all flags
└── types.py          # Dataclasses: Issue, Report, Severity, IssueType
```

### Data Flow

```
Input string
    │
    ▼
[parse] ───► 2D Character Grid
    │
    ▼
[analyze] ───► List of Issues
    │              │
    │    ┌─────────┘
    ▼    ▼
[build_report] ───► Report {status, issues, corrected_diagram}
    │
    ▼
[apply_fixes] (if fixable) ───► corrected grid
    │
    ▼
Output (JSON / text / corrected diagram)
```

### Algorithm

1. **Parse** — split on `\n`, expand tabs, pad rows to uniform width
2. **Identify connectors** — scan grid for box-drawing, arrow, circle characters
3. **Trace** — walk outward from each connector in expected directions, flag gaps
4. **Box detection** — match `┌…┐` / `└…┘` pairs, compare widths
5. **Style check** — BFS to find connected components, count single vs double
6. **Auto-fix** — fill 1-cell gaps; normalize box widths; unify mixed styles (>80% majority)
7. **Report** — sort issues, determine overall status, serialize to JSON/text

---

## Development

```bash
# Install dev dependencies
uv sync

# Run tests (75 tests)
uv run pytest

# Lint
uv run ruff check

# Run against reference diagrams
python -m ascii_sanitizer.cli --fix diagram.md
```

---

## Current Status

> ⚠️ **This project is in active development and does not yet work as intended.**

The core engine is implemented and **75 tests pass**, verifying the basic
algorithms for connectivity tracing, gap detection, box matching, style
analysis, and auto-fixing.

However, when run against real-world diagrams from [`diagram.md`](diagram.md),
**only 13 of 21 reference diagrams pass validation cleanly** (as of 2026-06-06).
The remaining 8 diagrams expose edge cases that are not yet correctly handled:

### Known Issues

| Diagram | Problem |
|---------|---------|
| Tree/Hierarchy (with `││` double vertical) | Incorrectly flagged as structural errors |
| Network/Graph with diagonals (`╲`) | Diagonal trace not fully implemented |
| Swimlane diagram | Multiple disconnected regions cause false positives |
| State Machine | Arrow semantics not fully traced |
| Sequence Diagram | Mixed connectors cause style warnings |
| Several others | False-positive gap/box errors on valid diagrams |

### What's Needed

- **Finer-grained tracing**: Better handling of empty space around connectors
  (especially in networks and multi-column layouts)
- **Diagonal support**: Complete trace for `╲` and `╱` characters
- **Multi-region isolation**: Better detection of intentionally separate diagram components
- **Fewer false positives**: Tuning the tracer so valid compact diagrams don't trigger errors

The test suite covers the happy path and known edge cases well, but the
gap between passing unit tests and successful real-world diagram processing
indicates more integration testing and algorithm refinement is needed.

---

## Roadmap

- [ ] **Fix the 8 failing diagrams** from `diagram.md`
- [ ] Add integration test suite using `diagram.md` as golden source
- [ ] Full diagonal line support
- [ ] Multi-line component-aware style checking
- [ ] Publish to PyPI as `ascii-sanitizer`
- [ ] GitHub Actions CI (lint, test, type-check)
- [ ] Performance optimization for very large diagrams (>1000×1000)
- [ ] `pre-commit` hook integration

---

## License

[Add license here]

---

## Author

Davi Macêdo Gomes — [dev.davi.macedo.gomes@gmail.com](mailto:dev.davi.macedo.gomes@gmail.com)
