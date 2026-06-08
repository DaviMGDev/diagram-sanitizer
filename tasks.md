# Tasks: diagram-sanitizer Core Engine Implementation

## Phase 0: Project Foundation

- [x] **Step 0.1: Set up dev dependencies and test infrastructure**
  - [x] Add `pytest` as dev dependency in `pyproject.toml`
  - [x] Configure `[tool.pytest.ini_options]` in `pyproject.toml`
  - [x] Remove `uv.lock` from `.gitignore`
  - [x] Run `uv sync` to install pytest
  - [x] Create `tests/__init__.py`
  - [x] Create `tests/conftest.py` with shared fixture diagrams

- [x] **Step 0.2: Define connector direction map** (`connector_map.py`)
  - [x] Create `Direction` constants (UP, DOWN, LEFT, RIGHT)
  - [x] Define `ConnectorDef` dataclass with `directions` and `mode`
  - [x] Build `CONNECTOR_MAP` dict from Appendix A
  - [x] Define character set constants (SINGLE_LINE, DOUBLE_LINE, ARROW_HEADS, etc.)
  - [x] Define style unification mapping (single ↔ double, ASCII)
  - [x] Write `tests/test_connector_map.py`

## Phase 1: Core Data Structures & Preprocessing

- [x] **Step 1.1: Implement Grid** (`grid.py`)
  - [x] `Grid` class (rows list, height/width, bounds-safe get/set)
  - [x] `ConnectorCell` dataclass (row, col, char, expected)
  - [x] `classify_connectors(grid, connector_map)` function
  - [x] `to_string(grid)` — reconstruct normalized string
  - [x] Write `tests/test_grid.py`

- [x] **Step 1.2: Implement Preprocessor** (`preprocessor.py`)
  - [x] BOM stripping (U+FEFF)
  - [x] ANSI escape sequence stripping (CSI regex)
  - [x] Tab expansion (configurable width)
  - [x] Line ending normalization (\r\n → \n, \r → \n)
  - [x] Trailing whitespace trimming per line
  - [x] Write `tests/test_preprocessor.py`

## Phase 2: Analysis Engine

- [x] **Step 2.1: Connected Component Analysis** (`components.py`)
  - [x] Union-find (disjoint set) data structure
  - [x] `find_components(connectors, grid)` → list[Component]
  - [x] Connectivity: bidirectional check per spec definition
  - [x] Diagonal character handling (Chebyshev distance 1)
  - [x] Sort by size, identify largest component
  - [x] Write `tests/test_components.py`

- [x] **Step 2.2: Orphan Detection** (`detectors.py`)
  - [x] Fully isolated orphan detection (size 1, no direct connections)
  - [x] Component orphan detection (>50% threshold vs largest)
  - [x] Special cases: circles >1 cell away, circles at 1 cell, diagonals
  - [x] Arrow head orphan detection (AC-015)
  - [x] Generate orphan issues with correct severity
  - [x] Write orphan detection tests

- [x] **Step 2.3: Gap Detection** (`detectors.py`)
  - [x] Ray-cast from each connector along expected directions
  - [x] 1-cell gap = fixable; 2+ = unfixable (EC-006)
  - [x] Determine fill character (│ for vertical, ─ for horizontal)
  - [x] Bidirectional check: target must also expect connection back
  - [x] Stop ray at first connector (don't look through)
  - [x] Write gap detection tests

- [x] **Step 2.4: Box Analysis** (`detectors.py`)
  - [x] Identify box corners (single and double line)
  - [x] Greedy left-to-right corner pairing
  - [x] Compare top vs bottom border span widths
  - [x] Modal width determination for fix (narrower on tie)
  - [x] Write box analysis tests

- [x] **Step 2.5: Style Analysis** (`detectors.py`)
  - [x] Count single vs double line chars per component
  - [x] Report mixed style as warning
  - [x] >80% majority = fixable (AC-009)
  - [x] Unicode/ASCII mixing = info, never auto-fix (EC-030)
  - [x] Write style analysis tests

- [x] **Step 2.6: Cross/Arrow/Circle Validation** (`detectors.py`)
  - [x] Cross (┼╬): check 4 directions, <4 = warning
  - [x] Arrow heads (▶◀▼▲): check expected direction, empty = error
  - [x] Full arrows (→←↑↓): check both sides, orphan if none
  - [x] Circles (●○): distance-based logic per FR-011
  - [x] Write validation tests

## Phase 3: Fix Application

- [x] **Step 3.1: Fix Application** (`fixer.py`)
  - [x] `apply_fixes(grid, issues)` → str | None
  - [x] Orphan removal: replace cells with space
  - [x] Gap fill: insert fill character for fixable gaps
  - [x] Box normalize: extend/shrink borders to modal width
  - [x] Style unify: replace minority chars via mapping table
  - [x] Strict ordering: orphan → gap → box → style
  - [x] Return None if no fixable issues (FR-025)
  - [x] Write `tests/test_fixer.py`

## Phase 4: Pipeline Orchestration & Integration

- [x] **Step 4.1: Pipeline Engine** (`engine.py`)
  - [x] `sanitize(diagram, options=None)` → dict
  - [x] Merge options with defaults
  - [x] Orchestrate all 11 pipeline stages
  - [x] Deduplicate issues by (type, line, col)
  - [x] Compute status from issue severities
  - [x] Build report dict matching spec Data Model
  - [x] Issue ID generation (<TYPE>-<LINE>-<COL>)
  - [x] 0-indexed → 1-indexed coordinate conversion
  - [x] Handle empty/no-connector inputs (EC-001/002)
  - [x] Write `tests/test_engine.py`

- [x] **Step 4.2: CLI Integration** (`cli.py`)
  - [x] Import sanitize from engine
  - [x] Replace TODO placeholder with sanitize() call
  - [x] Pass tab_width option from CLI flag
  - [x] Pass mode based on --check/--fix flags
  - [x] Write `tests/test_cli.py`

- [x] **Step 4.3: Public API** (`__init__.py`)
  - [x] Add `from .engine import sanitize`
  - [x] Verify `from diagram_sanitizer import sanitize` works

## Phase 5: Polish & Verification

- [x] **Step 5.1: Full test suite**
  - [x] Run `uv run pytest -v` — all 210 tests pass
  - [ ] Verify all 30 EC cases covered
  - [ ] Verify all 18 AC entries testable

- [ ] **Step 5.2: Manual smoke tests**
  - [x] CLI with real diagram files
  - [x] Stdin pipe
  - [x] --fix --in-place atomicity
  - [ ] Performance: 200×200 diagram < 2 seconds

- [ ] **Step 5.3: Edge case hardening**
  - [x] Empty string (EC-001)
  - [x] No connectors (EC-002/003)
  - [ ] Invalid UTF-8 (NFR-006)
  - [ ] Very wide diagrams (EC-010)
