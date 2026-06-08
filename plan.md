# Implementation Plan: diagram-sanitizer Core Engine

**Date:** 2026-06-07  
**Spec Version:** 1.2  
**Current State:** CLI scaffold complete, core engine TODO placeholder

---

## Goal

Implement the complete 11-stage sanitizer pipeline defined in [SPEC.md FR-027](./SPEC.md), integrate it with the existing Click CLI, expose the `sanitize()` library API, and write comprehensive tests covering all 30 edge cases (EC-001 through EC-030).

**"Done" means:**
- `das diagram.txt` produces a real JSON report with detected issues
- `das --fix diagram.txt` outputs a corrected diagram
- `das --fix --in-place diagram.txt` atomically fixes files
- `das --check diagram.txt` exits with correct codes (0/1/2)
- `sanitize(diagram_string)` returns a dict matching the spec's data model
- All 30 edge cases from SPEC.md have passing tests
- All 18 acceptance criteria (AC-001 through AC-018) are verified
- Library API uses only Python stdlib (zero third-party dependencies)

---

## Requirements

### Functional Requirements (from SPEC.md)

All 27 functional requirements (FR-001 through FR-027) must be satisfied. Key ones:

| FR | Summary | Priority |
|----|---------|----------|
| FR-001 | Accept UTF-8 string input | P0 |
| FR-002 | Normalize line endings to LF | P0 |
| FR-003 | Parse into 2D character grid | P0 |
| FR-004 | Classify connector cells with expected directions | P0 |
| FR-007 | Ray-cast for connectivity gaps | P0 |
| FR-008/009 | Detect fully isolated and component orphans | P0 |
| FR-012 | Detect box-width mismatches | P1 |
| FR-013 | Detect style inconsistencies (single/double mix) | P1 |
| FR-015 | Produce JSON output with correct schema | P0 |
| FR-016–018 | Auto-fix gaps, box widths, style unification | P1 |
| FR-020 | Expose `sanitize()` public function | P0 |
| FR-025 | `corrected_diagram` is null when no fixable issues | P1 |
| FR-027 | Follow fixed pipeline order | P0 |

### Non-Functional Requirements

| NFR | Summary |
|-----|---------|
| NFR-001 | 200×200 diagram in <2 seconds |
| NFR-003 | Human-readable error messages referencing actual characters |
| NFR-005 | Python 3.10–3.14 support |

### Acceptance Criteria

All 18 AC entries from SPEC.md (AC-001 through AC-018). These serve as the test plan backbone.

---

## Context

### Files to Create

```
src/diagram_sanitizer/
├── connector_map.py       # NEW: Appendix A character → direction map
├── grid.py                # NEW: 2D Grid class + connector classification
├── preprocessor.py        # NEW: BOM/ANSI strip, tab expand, LF normalize, trim
├── components.py          # NEW: Union-find connected component analysis
├── detectors.py           # NEW: Orphan, gap, box, style, cross/arrow/circle detection
├── fixer.py               # NEW: Fix application (orphan removal → gap fill → box normalize → style unify)
└── engine.py              # NEW: Pipeline orchestrator + sanitize() function

tests/
├── __init__.py            # NEW
├── conftest.py            # NEW: shared test fixtures (sample diagrams)
├── test_preprocessor.py   # NEW
├── test_grid.py           # NEW
├── test_connector_map.py  # NEW
├── test_components.py     # NEW
├── test_detectors.py      # NEW
├── test_fixer.py          # NEW
├── test_engine.py         # NEW
└── test_cli.py            # NEW
```

### Files to Modify

| File | Changes |
|------|---------|
| `src/diagram_sanitizer/__init__.py` | Add `from .engine import sanitize` |
| `src/diagram_sanitizer/cli.py` | Replace TODO placeholder with real `sanitize()` call |
| `pyproject.toml` | Add `[project.optional-dependencies]` for `dev` (pytest) and configure `[tool.pytest.ini_options]` |
| `.gitignore` | Remove `uv.lock` from gitignore (it's already committed) |

### Dependencies to Add

| Package | Purpose | Type |
|---------|---------|------|
| `pytest` | Test runner | dev |

### Constraints

- **Library API (`sanitize()`) MUST use only Python stdlib** — no third-party imports in `connector_map.py`, `grid.py`, `preprocessor.py`, `components.py`, `detectors.py`, `fixer.py`, or `engine.py`.
- CLI (`cli.py`) already uses `click` — this is fine per the spec.
- Python 3.10+ means `from __future__ import annotations` plus `str | None` syntax is available (PEP 604).

---

## Out of Scope

- Context-aware text-region detection (connector chars in prose are treated as connectors — per FR-026)
- Interactive/TUI mode
- Diagram generation or rendering
- Non-ASCII diagram formats (SVG, Mermaid, etc.)
- `wcwidth` for CJK full-width — treat full-width chars as single-cell for now (address later)
- `pydantic` for data model validation — use plain dicts and dataclasses
- CI/CD setup (GitHub Actions) — plan mentions it but it's a separate task

---

## Design / Architecture

### Module Responsibilities

```
┌─────────────────────────────────────────────────────────────┐
│                       engine.py                              │
│  sanitize(diagram, options) → dict                           │
│  Orchestrates pipeline, manages Issue list, produces report  │
└─────────────────────────────────────────────────────────────┘
         │          │          │          │          │
         ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌──────┐ ┌──────────┐ ┌────────┐ ┌──────────┐
│preprocess│ │ grid │ │components│ │detectors│ │  fixer   │
│  or.py   │ │ .py  │ │   .py    │ │  .py   │ │   .py    │
└──────────┘ └──────┘ └──────────┘ └────────┘ └──────────┘
                    │                               │
                    ▼                               │
            ┌──────────────┐                        │
            │connector_map │◄───────────────────────┘
            │    .py       │
            └──────────────┘
```

### Data Flow

```
Raw string
  │
  ▼
preprocessor.preprocess(text, tab_width) → str (normalized)
  │
  ▼
grid.Grid(normalized_text) → Grid object (2D char array)
  │
  ├─► grid.classify_connectors(grid) → list[ConnectorCell]
  │     (uses connector_map for direction lookup)
  │
  ▼
components.find_components(connectors) → list[Component]
  │
  ▼
detectors.detect_orphans(grid, components) → list[Issue]
detectors.detect_gaps(grid, connectors) → list[Issue]
detectors.detect_box_widths(grid, components) → list[Issue]
detectors.detect_style_mix(components) → list[Issue]
detectors.detect_cross_arrow_circle(grid, connectors) → list[Issue]
  │
  ▼
engine: collect + deduplicate all issues
  │
  ▼
fixer.apply_fixes(grid, issues) → str (corrected diagram)
  │
  ▼
engine: build report dict → return
```

### Key Data Structures

```python
# connector_map.py
# Maps char → set of expected directions
# Directions: an enum or string set {'up', 'down', 'left', 'right'}
CONNECTOR_MAP: dict[str, set[str]]
SINGLE_LINE_CHARS: frozenset[str]   # ┌─┐│└┘├┤┴┬┼
DOUBLE_LINE_CHARS: frozenset[str]   # ╔═╗║╚╝╠╣╦╩╬
ARROW_HEADS: frozenset[str]         # ▶◀▼▲
FULL_ARROWS: frozenset[str]         # →←↑↓
CIRCLES: frozenset[str]             # ●○
DIAGONALS: frozenset[str]           # ╲╱
ASCII_CONNECTORS: frozenset[str]    # + - |
ALL_CONNECTORS: frozenset[str]      # union of all above

# grid.py
@dataclass
class ConnectorCell:
    row: int       # 0-indexed
    col: int       # 0-indexed
    char: str
    expected: set[str]  # directions this char expects connections in

class Grid:
    rows: list[str]          # normalized, may have unequal lengths
    height: int
    width: int               # max row length
    def get(row, col) → str  # returns char or ' ' if out of bounds
    def set(row, col, char)
    def to_string() → str    # reconstruct normalized string

# components.py
@dataclass
class Component:
    id: int
    cells: list[ConnectorCell]
    size: int

# detectors.py — each function returns list[Issue]
# Issue is a TypedDict or simple dict matching the spec schema
```

### Connector Direction Map Design

Each character maps to a set of `Direction` values. There are three categories:

1. **Strict directions**: Corner, T-junction, cross, arrow head — must connect in ALL listed directions
2. **Line characters** (`─│═║-|`): At least ONE of the listed directions must be connected (endpoints are valid)
3. **Loose** (`+●○╲╱`): Any direction accepted, but report warnings for disconnection

This distinction is encoded as:
```python
@dataclass
class ConnectorDef:
    directions: set[str]
    mode: str  # "strict" | "at_least_one" | "loose"
```

For the `at_least_one` mode lines: `─` expects `{left, right}` but only one side needs to be connected.

### Connected Component Algorithm

Use **Union-Find (Disjoint Set Union)**:
1. Initialize each connector as its own component
2. For each connector, check its 4 cardinal neighbors
3. If two adjacent connectors both expect connection toward each other, union them
4. After processing, flatten to components
5. Components are sorted by size for orphan identification (EC-012)

### Pipeline Orchestration (engine.py)

```python
def sanitize(diagram: str, options: dict | None = None) -> dict:
    opts = _merge_options(options)
    
    # Steps 1-3: Preprocess + Grid + Classify
    normalized = preprocess(diagram, opts["tab_width"])
    grid = Grid(normalized)
    connectors = classify_connectors(grid)
    
    if not connectors:
        return {"status": "ok", "issues": [], "corrected_diagram": None}
    
    # Step 4: Components
    components = find_components(connectors, grid)
    
    # Steps 5-9: Detection (all produce issues)
    all_issues: list[dict] = []
    all_issues.extend(detect_orphans(grid, connectors, components))
    all_issues.extend(detect_gaps(grid, connectors))
    all_issues.extend(detect_box_widths(grid, components))
    all_issues.extend(detect_style_mix(components))
    all_issues.extend(detect_cross_arrow_circle(grid, connectors, components))
    
    # Deduplicate
    issues = deduplicate(all_issues)
    
    # Determine status
    status = compute_status(issues)
    
    # Step 10: Fix application
    mode = opts.get("mode", "auto")
    corrected = None
    if mode in ("fix", "auto"):
        corrected = apply_fixes(grid, issues)
    
    # Step 11: Output
    report = build_report(status, issues, corrected)
    return report
```

### Fix Application Strategy

Fixes are applied in strict order to a mutable grid copy:

1. **Orphan removal** — replace orphan cells with space
2. **Gap fill** — insert line chars for single-cell gaps
3. **Box normalization** — extend/shrink borders to match modal width
4. **Style unification** — replace minority-style chars with majority equivalents

Each fix step modifies the grid. If a step is ambiguous for any issue, that issue is marked `fixable: false` and the step is skipped for that issue only.

### Integration with Existing CLI

The `cli.py` change is minimal — replace the TODO block:

```python
# Before (current):
report = {"status": "ok", "issues": [], "corrected_diagram": None}

# After:
from diagram_sanitizer import sanitize
report = sanitize(diagram, {"tab_width": tab_width})
```

The CLI's `_format_report()`, `_write_output()`, `_exit_with_status()` helpers continue to work as-is — they consume the report dict format that `sanitize()` returns.

---

## Edge Cases & Risks

### Critical Implementation Risks

1. **`at_least_one` vs `strict` connector semantics**: Getting the distinction right is crucial. A `─` with nothing on either side is an orphan, but a `─` with a connection on only the left is valid (endpoint). A `┌` MUST have both right AND down connections. Getting this wrong will flood the output with false positives or miss real orphans.

2. **Direction enum consistency**: All modules must agree on direction naming (`up`/`down`/`left`/`right`). Using string sets is error-prone. Consider a `Direction` enum.

3. **1-indexed vs 0-indexed coordinates**: The spec uses 1-indexed `line`/`col` in output issues. Grid internally uses 0-indexed. Conversion must happen at report generation time.

4. **Grid bounds handling**: `grid.get(r, c)` for out-of-bounds must gracefully return a sentinel. This is critical for ray-casting and neighbor checks near edges.

5. **Union-find correctness**: The connectivity rule is bidirectional — A expects D toward B AND B expects opposite toward A. Simple adjacency is not enough.

6. **EC-012 (multiple large components)**: Need a heuristic for "clearly dominant" vs "comparable size" components. Proposal: a component is dominant if its connector count is >50% of the total connectors. Otherwise, no orphan classification.

7. **Style unification character mapping**: When unifying `║` → `│` or vice versa, must have a complete bidirectional mapping for all 40 box-drawing characters.

### Edge Cases from SPEC.md (EC-001 through EC-030)

All 30 must be handled. Key tricky ones:
- **EC-004**: ASCII `+` as junction — it expects any direction, which means it can never be a "fully isolated orphan" in the same way. But it CAN be a component orphan.
- **EC-007**: Nested boxes — the inner box's interior must not trigger gap detection on the outer box.
- **EC-008**: Lines crossing without connecting — no `┼` at intersection = valid, no error.
- **EC-012**: Multiple disconnected regions — size-based dominance heuristic.
- **EC-015**: CJK full-width chars — treat as single-cell for now.
- **EC-024**: Overlapping components — rare, hard to detect. Mark `fixable: false`.
- **EC-027**: Deduplication by `(type, line, col)` — must keep earliest pipeline stage's issue.

---

## Verification

### Testing Strategy

| Test Layer | Scope | File |
|------------|-------|------|
| **Unit: connector_map** | Every char in Appendix A has correct directions; style char sets are correct | `test_connector_map.py` |
| **Unit: preprocessor** | BOM strip, ANSI strip, tab expansion, LF normalize, trailing whitespace trim | `test_preprocessor.py` |
| **Unit: grid** | Grid construction, bounds, get/set, connector classification | `test_grid.py` |
| **Unit: components** | Union-find correctness, connectivity rules, multi-component cases | `test_components.py` |
| **Unit: detectors** | Each detector function tested with minimal fixture diagrams | `test_detectors.py` |
| **Unit: fixer** | Each fix type with canonical inputs; verify ordering | `test_fixer.py` |
| **Integration: engine** | Full pipeline on complete diagrams; all EC cases | `test_engine.py` |
| **Integration: CLI** | CLI flag combinations, stdin/file, exit codes, output formats | `test_cli.py` |

### Test Fixtures

`tests/conftest.py` will contain reusable diagram strings:

```python
# Valid complete box
VALID_BOX = """\
┌───┐
│ A │
└───┘
"""

# Box with width mismatch
MISMATCHED_BOX = """\
┌───┐
│ X │
└─┘
"""

# Orphan vertical bar
ORPHAN_VBAR = """\
some text
  │
more text
"""

# Single-cell gap
SINGLE_GAP = """\
┌─┐
│ │
└ ┘
"""

# Mixed single/double style
MIXED_STYLE = """\
┌─┐
║X║
└─┘
"""

# ... and so on for all 30 EC cases
```

### Acceptance Criteria Mapping

Each AC maps to specific test cases:

| AC | Test |
|----|------|
| AC-001 | `test_engine.py::test_valid_diagram_returns_ok` |
| AC-002 | `test_detectors.py::test_disconnected_line_reports_gap` |
| AC-003 | `test_detectors.py::test_mismatched_box_widths` |
| AC-004 | `test_detectors.py::test_mixed_style_warns` |
| AC-005 | `test_detectors.py::test_dangling_cross_warns` |
| AC-006 | `test_detectors.py::test_broken_arrow_errors` |
| AC-007 | `test_fixer.py::test_fill_single_cell_gap` |
| AC-008 | `test_fixer.py::test_normalize_box_width` |
| AC-009 | `test_fixer.py::test_unify_style_majority` |
| AC-010 | `test_fixer.py::test_ambiguous_fix_not_applied` |
| AC-011 | `test_engine.py::test_sanitize_function_exists_and_returns_dict` |
| AC-012 | `test_cli.py::test_cli_modes` |
| AC-013 | `test_detectors.py::test_fully_isolated_orphan_removed` |
| AC-014 | `test_detectors.py::test_component_orphan_removed` |
| AC-015 | `test_detectors.py::test_arrow_head_orphan` |
| AC-016 | `test_engine.py::test_non_connector_content_preserved` |
| AC-017 | `test_detectors.py::test_severity_assignment` |
| AC-018 | `test_engine.py::test_fixable_field` |

### Manual Verification

After all automated tests pass:
1. `uv run das --help` — CLI works
2. `uv run das tests/fixtures/valid_box.txt` — produces correct JSON
3. `uv run das --fix tests/fixtures/broken.txt` — outputs corrected diagram
4. `uv run das --check tests/fixtures/valid_box.txt && echo "exit 0"` — exits 0
5. `echo "┌─┐" | uv run das` — reads from stdin pipe

---

## Implementation Steps

### Phase 0: Project Foundation

**Step 0.1: Set up dev dependencies and test infrastructure**
- Add `pytest` as dev dependency in `pyproject.toml`
- Configure `[tool.pytest.ini_options]` in `pyproject.toml`
- Create `tests/__init__.py` and `tests/conftest.py`
- Remove `uv.lock` from `.gitignore`
- Run `uv sync` to install pytest

**Step 0.2: Define connector direction map** (`connector_map.py`)
- Create `Direction` enum or use `frozenset` with string constants
- Define `ConnectorDef` dataclass with `directions` and `mode`
- Build `CONNECTOR_MAP: dict[str, ConnectorDef]` from Appendix A
- Define character set constants (`SINGLE_LINE_CHARS`, `DOUBLE_LINE_CHARS`, etc.)
- Define style unification mapping (single ↔ double, ASCII equivalents)
- All public, no `_` prefix (this is a reference data module)

### Phase 1: Core Data Structures & Preprocessing

**Step 1.1: Implement Grid** (`grid.py`)
- `Grid` class with `rows: list[str]`, width/height computed properties
- `get(row, col) → str` with bounds-safe access
- `set(row, col, char)` for mutable modification
- `classify_connectors(grid, connector_map) → list[ConnectorCell]`
- `ConnectorCell` dataclass (row, col, char, expected directions)
- `to_string(grid) → str` — reconstruct normalized string with LF endings
- Write `test_grid.py`

**Step 1.2: Implement Preprocessor** (`preprocessor.py`)
- `preprocess(text: str, tab_width: int = 4) → str`
- BOM stripping (U+FEFF)
- ANSI escape sequence stripping (regex for CSI sequences)
- Tab expansion (replace `\t` with `tab_width` spaces)
- Line ending normalization (`\r\n` → `\n`, `\r` → `\n`)
- Trailing whitespace trimming per line
- Write `test_preprocessor.py`

### Phase 2: Analysis Engine

**Step 2.1: Connected Component Analysis** (`components.py`)
- Implement union-find (disjoint set) data structure
- `find_components(connectors: list[ConnectorCell], grid: Grid) → list[Component]`
- Connectivity rule: for each connector, check 4 cardinal neighbors; if both expect connection toward each other, union
- Handle diagonal characters (`╲╱`) with Chebyshev distance 1 check
- Sort components by size descending
- Write `test_components.py`

**Step 2.2: Orphan Detection** (`detectors.py` — orphan section)
- `detect_orphans(grid, connectors, components) → list[Issue]`
- Fully isolated orphan (size 1, no directly connected neighbors in any expected direction)
- Component orphan (component not in the largest component, using >50% threshold)
- Apply special rules: circles >1 cell away = not orphan (FR-011), circles 1 cell away = warning (EC-021), diagonals = warning (EC-022), `+` junction orphans = warning, arrow heads = error
- Component orphan: report each constituent connector as individual orphan issue (AC-014)
- Write orphan detection tests

**Step 2.3: Gap Detection** (`detectors.py` — gap section)
- `detect_gaps(grid, connectors) → list[Issue]`
- For each connector, ray-cast along each expected direction
- Track empty cells encountered before next connector
- 1 empty cell = fixable gap; 2+ = unfixable gap (EC-006)
- Determine fill character: `│` for vertical, `─` for horizontal
- Cross-check: only report gap if the target connector also expects connection back (bidirectional)
- Do NOT ray-cast through other connectors (stop at first connector)
- Write gap detection tests

**Step 2.4: Box Analysis** (`detectors.py` — box section)
- `detect_box_widths(grid, components) → list[Issue]`
- Identify box corners: `┌` (top-left), `┐` (top-right), `└` (bottom-left), `┘` (bottom-right) — and double-line equivalents
- Greedy left-to-right pairing: `┌` pairs with closest `┐` on same row; find matching `└` at same column below
- Compare top border span vs bottom border span
- Report mismatch if widths differ
- For auto-fix: determine modal width among all horizontal borders, narrowest wins on tie (FR-017)
- Write box analysis tests

**Step 2.5: Style Analysis** (`detectors.py` — style section)
- `detect_style_mix(components) → list[Issue]`
- For each component, count single-line vs double-line characters
- If both styles present, report warning
- If >80% one style, mark fixable (AC-009)
- Also detect Unicode/ASCII mixing (EC-030) — report as `info`, never auto-fix (lossy conversion)
- Write style analysis tests

**Step 2.6: Cross/Arrow/Circle Validation** (`detectors.py` — validation section)
- `detect_cross_arrow_circle(grid, connectors, components) → list[Issue]`
- Crosses (`┼╬`): check 4 directions for connectors (AC-005). Fewer than 4 = warning.
- Arrow heads (`▶◀▼▲`): check expected direction for line char. None found = orphan error.
- Full arrows (`→←↑↓`): check both directions; orphan if neither side connects (EC-029).
- Circles (`●○`): check for any neighbor connector. >1 cell away = skip. Exactly 1 cell away without connection = warning.
- Write validation tests

### Phase 3: Fix Application

**Step 3.1: Fix Application** (`fixer.py`)
- `apply_fixes(grid, issues) → str | None`
- Works on a mutable copy of the grid
- Applies fixes in strict order: orphan removal → gap fill → box normalize → style unify
- Orphan removal: replace cells from orphan issues with `U+0020 SPACE`
- Gap fill: insert fill character at gap location for `fixable: true` gaps
- Box normalize: for fixable box issues, extend/shrink borders to match modal width
- Style unify: for fixable style issues, replace minority chars with majority equivalents using the style mapping
- Returns corrected diagram string, or `None` if no fixable issues
- Write `test_fixer.py`

### Phase 4: Pipeline Orchestration & Integration

**Step 4.1: Pipeline Engine** (`engine.py`)
- `sanitize(diagram: str, options: dict | None = None) → dict`
- Merge options with defaults (`tab_width=4`, `max_grid_width=400`, `mode="auto"`)
- Orchestrate all pipeline stages
- Collect and deduplicate issues (FR-027, EC-027)
- Compute status: `"error"` if any error-severity issues, `"warning"` if only warnings, `"ok"` if none
- Build report dict matching the spec's Data Model schema
- Handle `mode` option: `"check"` skips fix application, `"fix"` always fixes, `"auto"` depends on flag
- Add issue IDs (`<TYPE>-<LINE>-<COL>`) as optional field
- Convert 0-indexed grid coords to 1-indexed line/col in output
- `corrected_diagram` is `None` if no fixable issues (FR-025)
- Write `test_engine.py`

**Step 4.2: CLI Integration** (`cli.py`)
- Import `sanitize` from `diagram_sanitizer.engine`
- Replace the placeholder report with `sanitize(diagram, {"tab_width": tab_width})`
- Pass `mode="check"` when `--check` flag is set
- Pass `mode="fix"` when `--fix` flag is set
- Everything else in CLI (formatting, output, exit codes) stays the same
- Write `test_cli.py`

**Step 4.3: Public API** (`__init__.py`)
- Add `from .engine import sanitize`
- Keep `__version__`

### Phase 5: Polish & Verification

**Step 5.1: Full test suite run**
- `uv run pytest -v` — all tests must pass
- Verify all 30 EC cases are covered by at least one test
- Verify all 18 AC entries are testable

**Step 5.2: Manual smoke tests**
- Test CLI with real ASCII diagrams
- Test stdin pipe
- Test `--fix --in-place` atomicity
- Verify 200×200 diagram processes in <2 seconds

**Step 5.3: Edge case hardening**
- Empty string → `{"status": "ok", "issues": [], "corrected_diagram": null}` (EC-001)
- No connectors → same (EC-002/003)
- Invalid UTF-8 → replacement character + warning (NFR-006)
- Very wide diagrams (EC-010)

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| **Wrong connector semantics** (`at_least_one` vs `strict`) | Implement `ConnectorDef.mode` early, test each char category exhaustively in `test_connector_map.py` |
| **Coordinate off-by-one errors** | Centralize 0→1 conversion in engine.py; all internal code uses 0-indexed exclusively |
| **Performance on large diagrams** | Use sparse iteration — only iterate connector cells, not every grid cell. Union-find is O(n α(n)). |
| **Style unification producing invalid diagrams** | Thoroughly test the single↔double mapping table. If a char has no equivalent in the other style, leave it unchanged. |
| **Pipeline ordering bugs** | Integration tests that verify fix application order (orphan removal before gap fill prevents spurious fills) |
