# Plan — ASCII Diagram Sanitizer

## Goal

Deliver a Python package (`ascii-sanitizer`) that validates ASCII diagrams for
structural integrity and auto-corrects unambiguous connectivity errors. The
package exposes both a library API (`sanitize(str) -> dict`) and a CLI
(`ascii-sanitize`). "Done" means all 15 acceptance criteria pass, all 15 edge
cases are handled, and the tool correctly validates and fixes the diagrams in
`diagram.md`.

---

## Requirements

### Functional (from SPEC.md)

| ID | Summary |
|----|---------|
| FR-001 | Accept UTF-8 string input |
| FR-002 | LF line-end normalization |
| FR-003 | Parse into 2D character grid |
| FR-004 | Classify connector characters and expected directions |
| FR-005 | Trace from each connector, flag gaps (empty space between connectors) |
| FR-006 | Detect box top/bottom border width mismatches |
| FR-007 | Detect mixed single/double line chars in a connected component |
| FR-008 | Assign severity: error / warning / info |
| FR-009 | Output JSON: `{status, issues[], corrected_diagram}` |
| FR-010 | Auto-fill single-cell gaps when direction is unambiguous |
| FR-011 | Normalize box widths when canonical width is clear |
| FR-012 | Unify mixed line styles when >80% majority |
| FR-013 | Preserve non-diagram content unchanged |
| FR-014 | CLI: `--check`, `--fix`, `--in-place`, stdin support |
| FR-015 | CLI: `--format json|text` |

### Non-Functional

- NFR-001: ≤2 seconds for 200×200 diagram on consumer hardware
- NFR-002: Handle full-width CJK and emoji correctly
- NFR-003: Human-readable issue messages referencing actual characters

### Acceptance Criteria (testable)

- AC-001: Valid diagram → `status: "ok"`, empty issues
- AC-002: Disconnected line → reported with position
- AC-003: Mismatched box borders → structural error
- AC-004: Mixed single/double chars → warning
- AC-005: Cross `┼` with <4 connections → warning
- AC-006: Arrow/circle with no line → error
- AC-007: Single-cell gap → auto-filled in corrected_diagram
- AC-008: Mismatched box width → normalized in corrected_diagram
- AC-009: Mixed styles >80% → unified in corrected_diagram
- AC-010: Ambiguous issue → fixable: false, corrected_diagram: null
- AC-011: `sanitize(str) -> dict` importable function
- AC-012: CLI reads file/stdin, exits 0/1/2

---

## Context

- **Project:** Greenfield, only `diagram.md` exists as reference
- **Language:** Python 3.10+
- **Package manager:** uv
- **Key deps:** `click` (CLI), `wcwidth` (Unicode width), `pydantic` (data models — optional, could use dataclasses)
- **Constraint:** Library API must have zero required deps beyond stdlib
- **Test framework:** pytest (stdlib `unittest` would work but pytest is standard)

---

## Out of Scope

- Diagram generation, rendering, interactive editing
- Pie charts, UML, BPMN, circuit diagrams
- Mermaid/Graphviz/DOT/SVG parsing
- Semantic/logical validation of diagram meaning
- ANSI escape code handling (strip and ignore)
- Network access, remote services

---

## Design / Architecture

### Package Structure

```
ascii_sanitizer/
├── __init__.py          # Public API: sanitize(), __version__
├── grid.py              # Grid class (parse string → 2D, reconstruct 2D → string)
├── connectors.py        # Connector character sets, direction expectation maps
├── analyzer.py          # Core: trace engine, gap detection, box check, style check
├── fixer.py             # Apply auto-fixes to grid (gap fill, width normalize, style unify)
├── report.py            # Build JSON report from issue list + grid
└── cli.py               # Click CLI: --check, --fix, --format, --in-place, stdin
```

### Data Types (stdlib `dataclasses`)

```
Severity: Enum(error, warning, info)
IssueType: Enum(gap, box_width, style_mix, dangling_junction)

Issue: line, col, end_line?, end_col?, severity, type, message, fixable, fix_suggestion?

Report: status("ok"|"warning"|"error"), issues: list[Issue], corrected_diagram: str|None
```

### Algorithm Overview

#### Phase 1 — Grid Parsing
1. Split input on `\n`, normalize `\r\n` → `\n`
2. Replace tabs with 4 spaces (configurable)
3. Pad all rows to same length (max row width)
4. Grid is `list[list[str]]` — mutable, index as `grid[row][col]`

#### Phase 2 — Connector Identification
1. Scan every cell in the grid
2. If character is in the connector set, record (row, col, char, expected_directions)
3. Expected directions come from the Connector Direction Map (Appendix A of SPEC.md)
4. Non-connector, non-space cells are "content" (labels, text) — preserved but ignored in analysis

#### Phase 3 — Connectivity Trace
For each connector at (r, c) with expected direction D:
1. Step outward in direction D one cell at a time
2. Track: `gap_start` = first empty cell encountered, `gap_length` = consecutive empty cells
3. If next cell is a connector → connection satisfied (no issue)
4. If next cell is content → ignore (content is transparent for tracing — we step past it if the line character is adjacent)
5. If next cell is empty → gap detected. Continue stepping to find the *next* connector.
6. If hit grid boundary → dangling line (error)
7. If next connector found after gap → compute gap_length
   - gap_length == 1 → auto-fixable gap
   - gap_length >= 2 → non-fixable gap

**Important nuance:** When tracing from a `│` downward and we hit a `┼`, we should consider the trace "connected" at that point and stop. The `┼`'s own trace will handle the cross-direction.

#### Phase 4 — Box Detection
1. Find all top-corner pairs: `┌` at (r, c1) and `┐` at (r, c2) with `─` between them
2. For each pair, trace down along column c1 looking for `│` or `├`/`┤`/`┼` until we find `└` or `┘`
3. Match `└` at (r', c1) with `┘` at (r', c2) on the same row
4. Compare widths: (c2 - c1) for top vs (c2' - c1') for bottom
5. Also check internal horizontal borders (├───┤, ┼───┼) for width consistency
6. Canonical width = modal width among all horizontal borders of the box

#### Phase 5 — Style Check
1. Build a graph of connectors (nodes connected by direction-valid adjacency)
2. Find connected components via BFS/DFS
3. For each component, count single-line chars vs double-line chars
4. If both present → style mix warning
5. If >80% majority → fixable by unification

#### Phase 6 — Fix Application
1. Sort fixes by position (top-left to bottom-right)
2. Apply fixes to a mutable copy of the grid:
   - Gap fill: insert `│`, `─`, `═`, or `║` at the gap position
   - Box normalize: extend/trim horizontal borders by adjusting corner positions and adding/removing `─`
   - Style unify: replace minority-style chars with majority-style equivalents
3. Reconstruction: join rows with `\n`, trim trailing whitespace per row (preserve intentional spaces within diagram)

#### Phase 7 — Report
1. Sort issues by line, then col
2. Determine overall status: max severity across all issues
3. Build JSON-serializable dict
4. CLI: print JSON or human-readable text

### CLI Design

```
ascii-sanitize [OPTIONS] [FILE]

Options:
  --check          Exit non-zero if issues exist (no output)
  --fix            Output corrected diagram to stdout
  --in-place       Overwrite input file with corrected diagram
  --format TEXT    Output format: json (default) or text
  --tab-width INT  Tab replacement width (default: 4)

If FILE is "-" or absent, read from stdin.
```

---

## Edge Cases & Risks

| ID | Edge Case | Handling |
|----|-----------|----------|
| EC-001 | Empty input | Early return: `{status: "ok", issues: [], corrected_diagram: null}` |
| EC-002 | No diagram chars | No connectors found → no analysis → ok status |
| EC-003 | Plain text only | Same as EC-002 |
| EC-004 | ASCII `+`, `-`, `\|` | Treat as valid connectors. If mixed with Unicode, report info |
| EC-005 | 3-way `┼` cross | Warning, not error — may be intentional |
| EC-006 | 2+ cell gap | Error, fixable=false |
| EC-007 | Nested boxes | Connected component analysis isolates inner box; trace stops at inner box boundary |
| EC-008 | Intentional crossings | Only flag if crossing point has a junction char; plain overlap is valid |
| EC-009 | Tab characters | Expand to spaces before analysis |
| EC-010 | Very wide diagrams | Grid is sparse; only connector cells are iterated |
| EC-011 | Trailing whitespace | Strip per-line before analysis, but preserve in output unless line was modified |
| EC-012 | Multiple regions | Component isolation via BFS ensures independent analysis |
| EC-013 | Edge dangling lines | Error — line at boundary with no connector |
| EC-014 | Mixed arrow styles | Warning only, no auto-unification |
| EC-015 | CJK/emoji width | Use `wcwidth` to compute display width; treat as content |

### Risks

1. **Performance:** The trace algorithm is O(C × D) where C = connector count, D = max trace distance. For a 200×200 grid with 10% connectors (~4000 connectors), tracing in 4 directions with avg trace distance of ~20 cells = ~320K operations — negligible.
2. **Box matching false positives:** Top corner pairs might not always form boxes (could be T-junction branches). Mitigation: only flag box-width mismatch when we can confirm `└` and `┘` at matching columns below.
3. **Unicode normalization:** Some box-drawing chars have compatibility equivalents. Input should be treated as-is; no NFC/NFKC normalization.
4. **Style unification ambiguity:** When single and double are exactly 50/50 — mark as not fixable.

---

## Verification

### Unit Tests

- `test_grid.py`: Parse, reconstruct, tab expansion, CJK width
- `test_connectors.py`: Direction map correctness for every connector char
- `test_analyzer.py`:
  - Valid diagram → no issues
  - Single gap → detected, fixable
  - Multi gap → detected, not fixable
  - Box width mismatch → detected
  - Style mix → detected
  - Nested boxes → handled correctly
  - Intentional crossing → not flagged
  - Edge dangling → detected
- `test_fixer.py`:
  - Single gap fill
  - Box width normalization
  - Style unification
  - No-op on valid diagram
  - Content preservation
- `test_report.py`: JSON schema correctness, status aggregation
- `test_cli.py`: Exit codes, --check, --fix, stdin, --format

### Integration Tests

- Run against `diagram.md` extracts (each of the 15 valid diagram types)
- Run against deliberately broken diagrams with known errors
- Verify round-trip: sanitize a diagram, then sanitize the corrected output → should be "ok"

### Manual Checks

- Visual inspection of auto-fixed diagrams against `diagram.md`
- CLI usage with real markdown files containing inline diagrams

---

## Implementation Steps

### Step 1: Project scaffold with uv
Create `pyproject.toml` with uv, set up package structure, configure dev dependencies (pytest, ruff).

### Step 2: Grid module (`grid.py`)
Parse string → 2D list-of-lists. Reconstruct string from grid. Tab expansion. Row padding. Trailing whitespace handling.

### Step 3: Connector module (`connectors.py`)
Define connector character sets. Build direction expectation maps for every character in Appendix A. Provide lookup functions: `is_connector(char) -> bool`, `expected_directions(char) -> set[Direction]`.

### Step 4: Analyzer — trace engine (`analyzer.py`)
Implement the directional trace algorithm. For each connector, walk in each expected direction, detect gaps (1-cell = fixable, 2+ = not), dangling lines (edge hit with no connector), and intentional crossings.

### Step 5: Analyzer — box detection
Find top-corner pairs (`┌…┐`). Trace vertical lines down to find matching bottom corners (`└…┘`). Compare widths. Also check internal horizontal borders (`├…┤`, `┼…┼`).

### Step 6: Analyzer — style check
Build connector adjacency graph. Find connected components via BFS. Count single vs double line characters per component. Flag mixed styles.

### Step 7: Fixer (`fixer.py`)
Implement gap filling (single-cell only), box width normalization, and style unification. Apply fixes to a mutable grid copy. Track which cells were modified.

### Step 8: Report generator (`report.py`)
Build `Report` from issue list + corrected grid. JSON serialization. Human-readable text format.

### Step 9: CLI (`cli.py`)
Click-based CLI with all flags. File/stdin input. Output routing. Exit codes.

### Step 10: `__init__.py` — public API
Expose `sanitize(diagram: str) -> dict` and `__version__`.

### Step 11: Tests
Write unit tests for all modules. Integration tests with diagram.md. Edge case tests.

### Step 12: Polish
README.md with usage examples. Verify `pip install` works. Run against diagram.md and ensure all valid diagrams pass.
