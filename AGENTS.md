# diagram-sanitizer

> Validate and auto-correct ASCII diagrams for structural integrity.

A Python tool (CLI + library) that parses ASCII diagrams into a 2D character grid, analyzes connectivity between Unicode box-drawing characters, detects orphans, gaps, box-width mismatches, and style inconsistencies, and auto-fixes unambiguous errors.

**Current status:** v1.0.0 — Core engine fully implemented with 12-stage pipeline, 8 detectors, and auto-fix capability. 246 tests passing. The comprehensive [SPEC.md](./SPEC.md) (v1.3) defines the full processing pipeline and all edge cases.

---

## Build & Development

- **Package manager**: `uv`
- **Build system**: `hatchling` (via `pyproject.toml`)
- **Python**: >= 3.10

| Action | Command |
|---|---|
| Install dependencies & package | `uv sync` |
| Run package as module | `uv run python -m diagram_sanitizer` |
| Run CLI directly | `uv run das [file] [--check\|--fix] [--json\|--text]` |
| Run all tests | `uv run pytest` |
| Build distribution | `uv build` |

The package is installed in editable mode. After `uv sync`, the `das` CLI is available inside `uv run`.

---

## Testing

Tests are written with `pytest` and live in `tests/`. There are 246 tests across 9 test files covering all pipeline stages, plus 37 shared fixtures in `conftest.py`.

| Action | Command |
|---|---|
| Run all tests | `uv run pytest` |
| Run with verbose output | `uv run pytest -v` |
| Run a single test file | `uv run pytest tests/test_cli.py` |
| Run with coverage (if installed) | `uv run pytest --cov=diagram_sanitizer` |

Test files follow the `test_*.py` naming convention. When adding tests, place them in the `tests/` directory.

---

## Code Style

| Aspect | Convention |
|---|---|
| Language | Python 3.10+ |
| Package manager | `uv` |
| Build backend | `hatchling` |
| Import style | Standard library imports first, then third-party, then local; absolute imports preferred |
| Type annotations | Used throughout — functions have type hints (PEP 484) |
| Docstrings | Triple-quoted `"""..."""` strings; module-level docstring in `__init__.py`, function-level in APIs |
| String quotes | Double quotes (`"`) for docstrings and user-facing strings |
| File naming | `snake_case.py` for modules |
| Function/variable naming | `snake_case` |
| Class naming | `PascalCase` |
| Constants | `UPPER_CASE` |
| Exit codes | `0` (ok), `1` (warnings), `2` (errors) — defined in CLIs |

*(Linting/formatting tools like `ruff` or `black` are not yet configured.)*

---

## Architecture

### Pattern

Single Python package with a CLI entry point and a library API.

### Key directories

| Path | Purpose |
|---|---|
| `src/diagram_sanitizer/` | Main package — all source code |
| `src/diagram_sanitizer/__init__.py` | Package init, exposes `__version__` |
| `src/diagram_sanitizer/__main__.py` | Enables `python -m diagram_sanitizer` |
| `src/diagram_sanitizer/cli.py` | CLI entry point (`das` command, Click-based) |
| `src/diagram_sanitizer/engine.py` | Pipeline orchestrator — the `sanitize()` entry point |
| `src/diagram_sanitizer/preprocessor.py` | BOM, ANSI, tab, CJK, line-ending normalization |
| `src/diagram_sanitizer/markdown.py` | GFM markdown table detection & normalization |
| `src/diagram_sanitizer/grid.py` | 2D character grid + connector classification |
| `src/diagram_sanitizer/connector_map.py` | Connector character definitions (Appendix A) |
| `src/diagram_sanitizer/components.py` | Connected component analysis (union-find) |
| `src/diagram_sanitizer/detectors.py` | All 8 detection stages (orphan, gap, box, style, etc.) |
| `src/diagram_sanitizer/fixer.py` | Fix application (orphan removal, gap fill, box norm, style unification) |
| `tests/` | 246 tests across 9 files + conftest fixtures |
| `SPEC.md` | Full specification (v1.3) — source of truth for requirements, pipeline, data model, and edge cases |

### Processing Pipeline (from SPEC.md)

The analysis follows this fixed order:

```
Preprocessing → Grid Construction → Markdown Table Detection →
Connector Classification → Connected Component Analysis →
Orphan Detection → Gap Detection → Box Analysis → Missing Side
Detection → Style Analysis → Cross/Arrow/Circle Validation →
Overlap Detection → Mixed Arrow Detection → Fix Application →
Markdown Table Normalization → Output Generation
```

The pipeline is defined in detail in [SPEC.md](./SPEC.md) (FR-027).

### Library API

```python
from diagram_sanitizer import sanitize

report = sanitize(diagram_string, options={"tab_width": 4})
# Returns: {"status": "ok"|"warning"|"error", "issues": [...], "corrected_diagram": str|null}
```

### CLI Usage

```bash
das diagram.txt                    # validate, output JSON report
das --check diagram.txt            # exit code only
das --fix diagram.txt              # print corrected diagram
das --fix --in-place diagram.txt   # atomically overwrite file
cat diagram.txt | das --fix -      # stdin to stdout
```

---

## Environment

| Requirement | Value |
|---|---|
| Python | >= 3.10 (3.10–3.14 supported per classifiers) |
| Dependencies | Runtime: `click>=8.0` (CLI). Optional: `wcwidth>=0.2` (CJK). Dev: `pytest>=8` |
| Setup | `uv sync` installs the package in editable mode |

No database, containers, or external services required.

---

## Dependencies

Runtime dependency: [`click`](https://click.palletsprojects.com/) ≥ 8.0 for the CLI (replaces argparse). The library API (`sanitize()`) works with only Python stdlib if you bypass the CLI.

Optional: [`wcwidth`](https://pypi.org/project/wcwidth/) ≥ 0.2 for CJK full-width character expansion (falls back gracefully if not installed).

Dev: [`pytest`](https://docs.pytest.org/) ≥ 8 for the test suite.

---

## PR & Commit Guidelines

Based on commit history, the project uses **Conventional Commits**:

| Prefix | Purpose |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `build:` | Build system / dependencies |
| `docs:` | Documentation |
| `refactor:` | Code refactoring |
| `test:` | Adding or updating tests |
| `chore:` | Maintenance tasks |

Branch naming follows the pattern: `feature/`, `fix/`, `chore/`, `refactor/`.

---

## Notes for AI Agents

1. **Spec-Driven Development**: This project follows an SDD approach. [SPEC.md](./SPEC.md) is the authoritative source of truth — it defines all requirements, the processing pipeline, edge cases, and the data model. Before implementing any feature, read the relevant sections of SPEC.md.

2. **Core logic is fully implemented**: The 12-stage pipeline in `engine.py` orchestrates all processing. When implementing new features, follow the existing module organization:
   - Detection logic → `detectors.py` (new function per detection type)
   - Fix logic → `fixer.py` (add fix type to `FIX_ORDER` + handler function)
   - Pipeline integration → `engine.py` (call detector, add issues to list)
   - Tests → `tests/` (new file or add to existing `test_detectors.py` / `test_fixer.py`)

3. **Connector character map**: The set of recognized connector characters and their expected connection directions is defined in [SPEC.md Appendix A](./SPEC.md). Any implementation must support the full Unicode box-drawing set, arrows, circles, diagonals, and ASCII fallbacks (`+`, `-`, `|`).

4. **The corrected diagram field is null unless fixable issues exist**: Per FR-025, `corrected_diagram` is `null` when there are no issues or no fixable issues. It's a string only when at least one fixable issue was corrected.

5. **No linting/formatting config yet**: If adding code, maintain consistency with the existing style (type hints, snake_case, triple-quote docstrings). Consider adding `ruff` configuration to `pyproject.toml`.

6. **Dependency policy**: The project now has `click` as a runtime dependency (CLI). The library API (`sanitize()`) can still function with only stdlib if the CLI wrapper is bypassed. Optional `wcwidth` gracefully degrades. New dependencies must be justified and added to both `pyproject.toml` dependencies and `uv sync`.
