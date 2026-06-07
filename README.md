# diagram-sanitizer

> Validate and auto-correct ASCII diagrams for structural integrity.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Beta-blueviolet)](.)

**diagram-sanitizer** is a Python tool (CLI + library) that parses ASCII diagrams into a 2D character grid, analyzes the connectivity of Unicode box-drawing characters, and detects — and where possible, automatically fixes — structural issues.

> **Why?** AI-generated ASCII diagrams often have disconnected lines — vertical bars (`│`) and horizontal dashes (`─`) that fail to meet their intended corners, T-junctions, arrows, or circles. This tool catches those errors and fixes the unambiguous ones, so your diagrams render correctly in documentation, READMEs, and slide decks.

---

## Status

| Aspect | Status |
|---|---|
| **Specification** | ✅ Complete — see [SPEC.md](./SPEC.md) (v1.1) |
| **CLI scaffold** | ✅ Done |
| **Core engine** | 🚧 **Not yet implemented** — placeholder in place |
| **Tests** | ❌ Not yet written |

The [SPEC.md](./SPEC.md) is the authoritative source of truth for all requirements, edge cases, and the processing pipeline. The core logic is the next thing to build.

---

## Features (planned)

- **🕵️ Orphan detection** — Finds box-drawing, arrow, and circle characters completely disconnected from any diagram structure. Fully isolated orphans (single cell) and component orphans (disconnected multi-cell fragments) are both detected and removed in the corrected output.
- **🔍 Gap detection** — Ray-casts from each connector along its expected directions to find gaps. Single-cell gaps with an unambiguous line character are auto-filled.
- **📦 Box-width analysis** — Detects mismatched top/bottom border widths and normalizes to the correct width when unambiguous.
- **🎨 Style consistency** — Detects mixed single-line (`┌─┐│└┘`) and double-line (`╔═╗║╚╝`) characters within the same connected component. Unifies to the majority style (>80% threshold).
- **⚠️ Cross/arrow/circle validation** — Warns on crosses with fewer than 4 connections, arrow heads pointing at empty space, and potential circle orphans.
- **📋 Structured JSON output** — Full report with status, issue list (line/col/severity/type/message/fixable), and corrected diagram.
- **🔌 Library API** — Import `sanitize()` directly in your Python code for CI pipeline integration.

---

## Installation

```bash
# Install from source (requires Python 3.10+ and uv)
git clone https://github.com/davi/diagram-sanitizer.git
cd diagram-sanitizer
uv sync
```

The `das` CLI command is then available via `uv run das`.

### Requirements

- **Python**: 3.10, 3.11, 3.12, 3.13, or 3.14
- **Dependencies**: None — library API uses only Python stdlib (CLI uses `argparse`)

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

### CLI options (planned)

| Flag | Description |
|---|---|
| `--check` | Exit code only; no output to stdout |
| `--fix` | Print corrected diagram to stdout |
| `--fix --in-place` | Atomically overwrite the input file |
| `--json` | Output full JSON report |
| `--format json\|text` | Control output format |
| `--version` | Show version and exit |

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

The analysis follows a fixed 11-step pipeline (defined in [SPEC.md FR-027](./SPEC.md)):

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
│11. Output Generation│  Produce JSON report + corrected diagram
└─────────────────────┘
          │
          ▼
       Output
```

### Package structure

```
diagram-sanitizer/
├── src/
│   └── diagram_sanitizer/
│       ├── __init__.py      # Package init, exposes __version__
│       ├── __main__.py      # python -m diagram_sanitizer support
│       └── cli.py           # CLI entry point (argparse)
├── SPEC.md                  # Full specification (source of truth)
├── AGENTS.md                # AI agent context
├── pyproject.toml           # Build config (hatchling)
├── uv.lock                  # Dependency lockfile
└── .gitignore
```

---

## What kinds of issues does it detect?

The tool recognizes the full Unicode box-drawing character set (single-line `┌─┐│└┘├┤┴┬┼`, double-line `╔═╗║╚╝╠╣╦╩╬`), arrows (`▶◀▼▲→←↑↓`), circles (`●○`), diagonals (`╲╱`), and ASCII fallbacks (`+`, `-`, `|`).

### Issues detected

| Type | Severity | Example |
|---|---|---|
| **Connectivity gap** | `error` | `│` above `└` with empty cell between them |
| **Orphan symbol** | `error` / `warning` | A `│` with no neighbors in any expected direction |
| **Box-width mismatch** | `error` | `┌───┐` top vs `└─┘` bottom |
| **Style inconsistency** | `warning` | `┌─┐` mixed with `║` in same component |
| **Dangling cross** | `warning` | A `┼` with only 3 connected directions |
| **Broken arrow** | `error` | Arrow head `▶` with no `─` to its left |

---

## Development

```bash
# Install in editable mode
uv sync

# Run the package
uv run das --help
uv run python -m diagram_sanitizer --help

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

1. **Implement core engine** — build the sanitizer pipeline (connector classification → component analysis → orphan/gap/box detection → fix application)
2. **Add test suite** — unit tests for each pipeline stage, integration tests for full diagrams
3. **Add linting** — configure `ruff` for code quality
4. **Set up CI** — GitHub Actions for lint → test → build

---

## License

MIT — see [LICENSE](LICENSE) for details.
