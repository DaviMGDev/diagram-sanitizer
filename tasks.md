# Tasks — ASCII Diagram Sanitizer

## Implementation

- [x] **Step 1: Project scaffold with uv**
  - [x] Create `pyproject.toml` with uv config, metadata, deps
  - [x] Create package directory structure
  - [x] Create `ascii_sanitizer/__init__.py` (placeholder)
  - [x] Install dev deps (pytest, ruff)

- [x] **Step 2: Grid module** (`grid.py`)
  - [x] `parse(text: str) -> list[list[str]]` — split, normalize LF, expand tabs, pad rows
  - [x] `reconstruct(grid: list[list[str]]) -> str` — join rows, handle trailing whitespace
  - [x] Handle CJK width via `wcwidth` (available as optional dep)

- [x] **Step 3: Connector module** (`connectors.py`)
  - [x] Define `Dir` enum (UP, DOWN, LEFT, RIGHT)
  - [x] Build `CONNECTOR_MAP: dict[str, set[Dir]]` for all chars in Appendix A
  - [x] `is_connector(char: str) -> bool`
  - [x] `expected_directions(char: str) -> set[Dir]`

- [x] **Step 4: Analyzer — trace engine** (`analyzer.py`)
  - [x] `trace(grid, row, col, direction)` — walk from connector, return gap info
  - [x] Detect: connected, gap(1 cell = fixable), gap(2+ = not fixable), dangling edge
  - [x] Handle content cells as valid endpoints
  - [x] Handle intentional line crossings (no junction char = valid)
  - [x] Smart dangling detection (only flag truly isolated connectors)

- [x] **Step 5: Analyzer — box detection**
  - [x] Find `┌…┐` top-corner pairs on same row
  - [x] Trace down to find matching `└…┘` bottom corners
  - [x] Compare top vs bottom horizontal span width
  - [x] Check internal borders and content rows for width consistency
  - [x] Determine canonical width (modal width, tie = ambiguous)

- [x] **Step 6: Analyzer — style check**
  - [x] Build connector adjacency graph
  - [x] BFS to find connected components
  - [x] Count single-line vs double-line chars per component
  - [x] Flag mixed styles as warnings; >80% majority = fixable

- [x] **Step 7: Analyzer — arrow/circle connectivity**
  - [x] Check arrow heads (▶▼◀▲) have line chars in expected direction
  - [x] Handle decorative arrows in box borders (between ─ chars)
  - [x] Check circles (●○) have at least one connection

- [x] **Step 8: Fixer** (`fixer.py`)
  - [x] `fill_gaps(grid, gap_issues)` — insert │/─/═/║ at single-cell gap positions
  - [x] `normalize_boxes(grid, box_issues)` — extend/shrink borders to canonical width
  - [x] `unify_styles(grid, style_issues)` — replace minority chars with majority equivalents
  - [x] `apply_fixes(grid, issues) -> list[list[str]]` — staged fixes with re-analysis

- [x] **Step 9: Report generator** (`report.py`)
  - [x] `build_report(issues, corrected_grid) -> dict` — JSON-serializable report
  - [x] `format_text(report) -> str` — human-readable text output
  - [x] Status determination: max severity across issues

- [x] **Step 10: CLI** (`cli.py`)
  - [x] `--check` mode: exit 0/1/2, no output
  - [x] `--fix` mode: output corrected diagram to stdout
  - [x] `--in-place`: overwrite input file
  - [x] `--format json|text`: output format control
  - [x] `--tab-width N`: configurable tab expansion
  - [x] File argument, `-` for stdin, default stdin
  - [x] Entry point: `ascii-sanitize` console script

- [x] **Step 11: Public API** (`__init__.py`)
  - [x] `sanitize(diagram: str, *, tab_width: int = 4) -> dict`
  - [x] `__version__` string
  - [x] Export `Report`, `Issue`, `Severity`, `IssueType` types

- [x] **Step 12: Tests** (75 passing)
  - [x] `test_grid.py` — parse, reconstruct, tabs
  - [x] `test_connectors.py` — direction maps, classification
  - [x] `test_analyzer.py` — gaps, boxes, styles, arrows, crossings, nesting
  - [x] `test_fixer.py` — gap fill, width normalize, style unify, content preservation

- [x] **Step 13: Polish**
  - [x] Run against `diagram.md` — 13/21 diagrams pass (remaining have real issues)
  - [x] `uv run pytest` — 75 tests pass
  - [x] `uv run ruff check` — lint clean
