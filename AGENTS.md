# diagram-sanitizer

> Validate and auto-correct ASCII diagrams for structural integrity.

A Python tool (CLI + library) that parses ASCII diagrams into a 2D character grid, analyzes connectivity between Unicode box-drawing characters, detects orphans, gaps, box-width mismatches, and style inconsistencies, and auto-fixes unambiguous errors.

**Current status:** Early development — CLI scaffold exists, core sanitizer logic is a TODO placeholder. The comprehensive [SPEC.md](./SPEC.md) defines the full processing pipeline.

---

## Build & Development

- **Package manager**: `uv`
- **Build system**: `hatchling` (via `pyproject.toml`)
- **Python**: >= 3.10

| Action | Command |
|---|---|
| Install dependencies & package | `uv sync` |
| Run package as module | `uv run python -m diagram_sanitizer` |
| Run CLI directly | `uv run das [file] [--json] [--version]` |
| Build distribution | `uv build` |

The package is installed in editable mode. After `uv sync`, the `das` CLI is available inside `uv run`.

---

## Testing

No tests have been written yet. The git history shows tests existed in a previous implementation but were removed during a refactor.

When testing is added, use:

- **Run all tests**: `uv run pytest` (expects `pytest` to be installed)
- **Run with coverage**: `uv run pytest --cov=diagram_sanitizer`

When adding tests, place them in a `tests/` directory at the project root. Follow the naming convention `test_*.py`.

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
| `src/diagram_sanitizer/cli.py` | CLI entry point (`das` command, argparse) |
| `SPEC.md` | Full specification — the source of truth for requirements, pipeline, data model, and edge cases |

### Processing Pipeline (from SPEC.md)

The analysis follows this fixed order:

```
Preprocessing → Grid Construction → Connector Classification →
Connected Component Analysis → Orphan Detection → Gap Detection →
Box Analysis → Style Analysis → Cross/Arrow/Circle Validation →
Fix Application → Output Generation
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
| Dependencies | None (stdlib only for library API; optional CLI extras may add `click`/`typer`/`pydantic`/`wcwidth`) |
| Setup | `uv sync` installs the package in editable mode |

No database, containers, or external services required.

---

## Dependencies

Currently **zero runtime dependencies** — the library API uses only Python stdlib (argparse for CLI). The `uv.lock` confirms no third-party packages are installed.

The SPEC.md contemplates optional CLI extras (`click`, `typer`, `pydantic`, `wcwidth`) but these are not yet added to `pyproject.toml`.

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

2. **Core logic is unimplemented**: The `cli.py` currently just prints input back via `print(diagram)` (marked with a `# TODO`). The full sanitizer engine needs to be built from scratch following the pipeline in SPEC.md (FR-027).

3. **Connector character map**: The set of recognized connector characters and their expected connection directions is defined in [SPEC.md Appendix A](./SPEC.md). Any implementation must support the full Unicode box-drawing set, arrows, circles, diagonals, and ASCII fallbacks (`+`, `-`, `|`).

4. **The corrected diagram field is null unless fixable issues exist**: Per FR-025, `corrected_diagram` is `null` when there are no issues or no fixable issues. It's a string only when at least one fixable issue was corrected.

5. **No linting/formatting config yet**: If adding code, maintain consistency with the existing style (type hints, snake_case, triple-quote docstrings). Consider adding `ruff` configuration to `pyproject.toml`.

6. **Keep the package zero-dependency for the library API**: Per the spec's constraints, the library core (`sanitize()` function) must work with only Python stdlib. CLI extras can declare additional dependencies.
