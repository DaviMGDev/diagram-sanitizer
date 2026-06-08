# SPEC.md — ASCII Diagram Sanitizer

**Version:** 1.3  
**Date:** 2026-06-08  
**Status:** Draft

---

## Overview

The ASCII Diagram Sanitizer is a Python tool (CLI + library) that validates
ASCII diagrams for structural integrity and automatically corrects
unambiguous errors. It targets the common problem where AI-generated ASCII
diagrams have disconnected lines — vertical bars (`│`) and horizontal dashes
(`─`) that fail to meet their intended corners, T-junctions, arrows, or
circles — causing "rendered" diagrams to look broken.

The tool parses the diagram into a 2D character grid, analyzes connectivity
between the Unicode box-drawing character set, and produces a structured JSON
report with issue locations, severities, and fix suggestions. When a fix is
unambiguous, it also returns the corrected diagram.

A key responsibility is **orphan symbol detection**: identifying box-drawing,
arrow, circle, or ASCII line characters that are completely disconnected from
any other connector — meaning they are fragments of a broken arrow, a broken
box wall, a broken line, or any other once-intact structure. These orphans are
reported and, when unambiguous, removed from the corrected diagram.

---

## Definitions

### Connector

A **connector** is any cell in the 2D character grid whose character is
listed in Appendix A (box-drawing characters, arrows, circles, ASCII line
characters, diagonals). Every connector has a set of **expected connection
directions** determined by its character type (see Appendix A).

All characters matching the connector set are treated as diagram connectors
during analysis. Characters that are not connectors (letters, digits,
punctuation outside the connector set, whitespace) are **non-connector
content** and are preserved as-is in the output (see FR-019).

> **Note:** Connector characters (`-`, `|`, `+`, etc.) embedded in non-diagram
> prose may produce false-positive issues. Users should isolate diagram
> regions before analysis, or use the tool's library API to process specific
> sections. Future versions may add context-aware text-region detection.

### Adjacency

Two connectors are **adjacent** if their cells share an edge (i.e., are
immediately next to each other in one of the four cardinal directions: up,
down, left, right). Diagonal adjacency does **not** qualify for connectivity,
except for diagonal characters (`╲`, `╱`) which use Chebyshev distance 1
(any of the 8 neighboring cells).

### Connectivity (Direct Connection)

Two adjacent connectors are **directly connected** if each cell's expected
connection directions include the direction toward the other cell. Formally,
for cells A and B separated by one step in direction D (where D is one of
up/down/left/right):

- A expects connection in direction D toward B, **and**
- B expects connection in the opposite direction (toward A).

If either cell does not expect a connection in that direction, the two cells
are not directly connected (they may be coincidentally adjacent without being
part of the same diagram line).

### Connected Component

A **connected component** is a maximal set of connectors where every cell is
reachable from every other cell via a path of directly connected intermediate
cells (using the connectivity rule above). Non-connector cells are never part
of a connected component.

### Orphan

An **orphan** is a connector or a connected component that is disconnected
from the main diagram structure. Specifically:

- **Fully isolated orphan (size 1):** A single connector with zero directly
  connected neighbors in any of its expected directions.
- **Component orphan (size 2+):** A connected component of 2 or more
  connectors where the entire component has no direct connections to any
  connector outside the component.

A component is considered an orphan **regardless of its size** if it is
disconnected from the largest connected component in the input. If the input
contains multiple large disconnected diagrams of comparable size, each is
analyzed independently and neither is treated as an orphan of the other (see
EC-012).

### Gap

A **gap** is one or more consecutive empty cells along a row or column that
interrupt the expected connection path between two connectors. A gap of
exactly 1 empty cell is **auto-fixable** when the line character to fill it
is unambiguous.

### Markdown Table

A **markdown table** is a contiguous block of lines that follows the
GitHub-Flavored Markdown (GFM) table syntax:

- Lines are separated by `\n`, with one table row per line.
- Each row contains one or more `|` (U+007C VERTICAL LINE) characters acting
  as column separators.
- The second line (separator row) contains only `|`, `-` (U+002D HYPHEN-MINUS),
  `:` (optional alignment markers), and whitespace.
- Leading and trailing `|` characters on each row are optional but common.
- A block is identified as a markdown table when **at least two consecutive rows**
  match the table row pattern, and the second row is a separator row.

Markdown tables are **not diagram structures**. The `|`, `-`, and `:`
characters within an identified markdown table block are **exempted from
connector classification** — they are preserved as table formatting, not
treated as diagram connectors.

When a markdown table is identified, the system MAY optionally normalize its
column widths (see FR-029). The table content (cell text) is always preserved
unchanged.

---

## User Stories

- **US-001:** As a developer using AI to generate ASCII diagrams, I want to
  validate my diagrams so that I can catch rendering errors before sharing
  them in documentation, READMEs, or slide decks.
- **US-002:** As a developer, I want auto-fixable connectivity errors
  corrected automatically so that I don't have to manually realign every
  broken corner or missing line segment.
- **US-003:** As a tool author or CI pipeline maintainer, I want to integrate
  the sanitizer as an importable library so that ASCII diagram validation can
  be part of automated documentation checks.

---

## Acceptance Criteria

### From US-001 (Validation)

- **AC-001:** WHEN a valid ASCII diagram with no connectivity issues is
  provided, THE system MUST return `status: "ok"` and an empty `issues` array.
- **AC-002:** WHEN a diagram contains a disconnected line (a `│` or `─` that
  does not touch a connector in at least one expected direction),
  THE system MUST report each gap as an issue with its `line`, `col`,
  `severity`, and `message`.
- **AC-003:** WHEN a box has mismatched top and bottom border widths (i.e.,
  the horizontal span between `┌─…─┐` differs from `└─…─┘`), THE system MUST
  report a structural error for that box. This applies to both single-line
  (`┌┐└┘`) and double-line (`╔╗╚╝`) corners.
- **AC-004:** WHEN a connected component mixes single-line box-drawing
  characters (`┌─┐│└┘├┤┴┬┼`) with double-line characters (`╔═╗║╚╝`), THE system
  MUST report a warning.
- **AC-005:** WHEN a diagram contains a `┼` (cross) that does not have
  connectors in all four cardinal directions, THE system MUST
  report a warning (the cross may be intentional decoration rather than a
  true junction).
- **AC-006:** WHEN an arrow head (`▶▼◀▲`) or circle (`●○`) has no line
  character in its expected pointing/connecting direction, THE system MUST
  report a connectivity error.
- **AC-013:** WHEN a single connector has no directly connected neighbors in
  any of its expected directions (a fully isolated orphan of size 1), THE
  system MUST report it as an orphan issue and MUST remove it (replace with
  `U+0020 SPACE`) in `corrected_diagram`.
- **AC-014:** WHEN a connected component of 2 or more connectors has no
  direct connections to any connector outside the component (a component
  orphan), THE system MUST report each constituent connector as an orphan and
  MUST remove the entire orphan component in `corrected_diagram`. This applies
  regardless of the component's size; there is no upper size limit.
- **AC-015:** WHEN a diagram contains an arrow head pointing at empty space
  (no line character in its expected connecting direction), THE system MUST
  report a broken-arrow orphan and MUST remove the arrow head in
  `corrected_diagram`.
- **AC-017:** WHEN a connectivity gap is detected, THE system MUST assign
  severity `"error"`. WHEN a style inconsistency is detected, THE system
  MUST assign severity `"warning"`. WHEN an optional suggestion is provided,
  THE system MUST assign severity `"info"`.
- **AC-018:** WHEN a diagram is processed, every entry in the `issues` array
  MUST include a `fixable` boolean field. WHEN an issue has a single
  unambiguous correction, `fixable` MUST be `true`. WHEN an issue has
  multiple possible corrections or unclear intent, `fixable` MUST be `false`.

### From US-002 (Auto-fix)

- **AC-007:** WHEN a connectivity gap is exactly one empty cell wide and the
  line character to fill it is unambiguous, THE system MUST include the
  corrected diagram in `corrected_diagram` with the gap filled.
- **AC-008:** WHEN a box has mismatched top and bottom border widths and the
  intended width is unambiguous (one border is clearly the correct one), THE
  system MUST normalize the box to the consistent width.
- **AC-009:** WHEN a connected component uses mixed single/double line
  characters and the majority style is clear (>80% one style), THE system
  MUST unify the component to the majority style and include the result in
  `corrected_diagram`.
- **AC-010:** WHEN an issue is ambiguous (multiple possible fixes, unclear
  intent), THE system MUST set `fixable: false` and MUST NOT modify the
  diagram in `corrected_diagram` (the field MUST be `null`).
- **AC-016:** WHEN a diagram contains text, labels, or prose intermixed with
  box-drawing characters, THE system MUST preserve all non-connector
  characters unchanged in `corrected_diagram`, subject only to whitespace
  normalization (FR-002, FR-019).

### From US-003 (Library)

- **AC-011:** The system MUST expose a top-level function
  `sanitize(diagram: str, options: dict | None = None) -> dict` that accepts
  a diagram string and optional options dictionary, and returns the full JSON
  report as a Python dict.
- **AC-012:** The CLI MUST read from a file path argument, or from stdin when
  passed `-` as the file argument or when stdin is a pipe and no file argument
  is given. When invoked with no arguments and stdin is a terminal, the CLI
  MUST print the help message and exit with code `0`. The CLI MUST print the
  JSON report to stdout and exit with code `0` (ok), `1` (warnings), or
  `2` (errors).

### From US-004 (Markdown Table Awareness)

- **AC-019:** WHEN the input contains a valid markdown table block, THE
  system MUST recognize it as a markdown table and MUST NOT treat `|`, `-`,
  or `:` characters within the table as diagram connectors. These characters
  MUST be preserved as-is in `corrected_diagram` (they are table formatting,
  not diagram lines).
- **AC-020:** WHEN a markdown table has misaligned columns (cells of unequal
  widths across rows), THE system MUST report an `info`-severity issue and
  MUST normalize the column widths in `corrected_diagram` by adding trailing
  spaces to shorter cells. The separator row dashes MUST also be padded to
  match the column width.
- **AC-021:** WHEN a markdown table has a missing, malformed, or misaligned
  separator row (the `|---|---|` line), THE system MUST report a `warning`
  and MUST insert or normalize the separator row in `corrected_diagram` to
  match the column count and widths of the data rows.
- **AC-022:** WHEN a line matches the GFM table row pattern but is not part
  of a contiguous multi-row table block (isolated single row), THE system
  MUST NOT treat it as a markdown table — it falls through to normal
  connector classification.

---

## Functional Requirements

- **FR-001:** The system MUST accept an ASCII diagram as a plain UTF-8 string.
- **FR-002:** The system MUST normalize input line endings to `\n` (LF).
- **FR-003:** The system MUST parse the diagram into a 2D character grid with
  explicit row and column coordinates.
- **FR-004:** The system MUST classify every non-empty cell that contains a
  box-drawing, arrow, or circle character as a **connector** and determine
  its expected connections based on character type (see appendix).
- **FR-005:** The CLI MUST support `--check` mode (exit with code 0 if no
  issues, 1 if only warnings, 2 if any errors; no output), `--fix` mode
  (output corrected diagram to stdout), and `--fix --in-place` mode
  (atomically overwrite the input file with corrections).
- **FR-006:** The CLI MUST support `--format json|text` to control output
  format (default: `json`). The CLI MUST also support `--tab-width N`
  to control tab expansion width (default: 4).
- **FR-007:** The system MUST traverse each connector's expected directions
  by ray-casting outward cell-by-cell in each cardinal direction until it
  either encounters another connector (connection satisfied) or reaches empty
  space. The system MUST report a **connectivity gap** when the path to the
  next connector is interrupted by empty space. Only connectors along the
  same row (horizontal) or same column (vertical) are considered; diagonal
  adjacency does not satisfy cardinal-direction connections.
- **FR-008:** The system MUST detect **orphan symbols** — connectors that
  have no directly connected neighbors in any of their expected directions (as
  defined in the Definitions section and Appendix A). A connector is orphaned
  if and only if the cell in every expected cardinal direction is empty,
  non-connector, or out of bounds.
- **FR-009:** The system MUST distinguish between:
  - **Fully isolated orphan** — a single connector with zero directly
    connected neighbors.
  - **Component orphan** — a connected component of 2 or more connectors
    where every connector in the component has no direct connections to any
    connector outside the component. This applies uniformly regardless of
    component size; there is no size threshold distinction.
  Both types MUST be reported as orphans and removed in `corrected_diagram`.
- **FR-010:** When a connector is determined to be an orphan, the unambiguous
  fix is to replace it with `U+0020 SPACE` in `corrected_diagram`. For
  component orphans, every cell in the orphan component MUST be replaced with
  `U+0020 SPACE`.
- **FR-011:** The system MUST NOT treat a standalone `●` or `○` (circle) as
  an orphan if it is more than 1 cell away from any other connector — it may
  be an intentional node label marker. Circles exactly 1 cell away from
  another connector that do not connect to it MUST be reported as potential
  orphans at `warning` severity (not removed automatically).
- **FR-012:** The system MUST report a **box-width mismatch** when the
  horizontal span between a pair of top corners (`┌…┐`) differs from the
  span between the corresponding bottom corners (`└…┘`) of the same box.
  A box is identified by matching `┌` with the closest `┐` to its right on
  the same row that has a corresponding `└` at the same column offset below,
  and vice versa for bottom corners. Box corners are paired greedily
  left-to-right, top-to-bottom. The same algorithm applies to double-line
  corners (`╔╗╚╝`).
- **FR-013:** The system MUST report a **style inconsistency** when a single
  connected component contains both single-line and double-line box-drawing
  characters.
- **FR-014:** The system MUST assign one of three severities to every issue:
  `error` (broken connectivity, box mismatch, orphan symbol, missing box
  side), `warning` (style inconsistency, likely-decorative cross, intact
  single-character component that may be intentional, diagonal orphan, circle
  1 cell from another connector without connection), `info` (suggestions).
- **FR-015:** The system MUST produce a JSON output object with the schema:
  `{status, issues[], corrected_diagram}` (see Data Model).
- **FR-016:** The system MUST auto-fill single-cell connectivity gaps when the
  line direction is unambiguous (only one possible line character to fill).
- **FR-017:** The system MUST normalize box widths when the correct width is
  unambiguous (either the top width matches all internal rows, or the modal
  width among the box's horizontal borders). In case of a tie for modal
  width, the narrower width MUST be used (conservative normalization).
- **FR-018:** The system MUST unify mixed single/double line characters when
  the majority style exceeds an 80% threshold within the connected component.
- **FR-019:** The system MUST preserve all non-diagram content (labels, text,
  surrounding prose) identical in `corrected_diagram`, except for characters
  explicitly corrected and whitespace normalization (trailing whitespace
  trimming, tab expansion, line‑ending normalization as defined in FR-002).
  The corrected diagram MUST be derived from the normalized input copy, not
  the raw original.
- **FR-020:** The system MUST expose a public function
  `sanitize(diagram: str, options: dict | None = None) -> dict` as the
  library entry point. The function MUST accept a diagram string and return
  the full JSON report as a Python dict.
- **FR-021:** The system MUST report a warning when a `┼` (cross) character
  has connectors in fewer than 4 cardinal directions.
- **FR-022:** Every issue in the `issues` array MUST include a `fixable`
  boolean field indicating whether the system can unambiguously correct
  the issue.
- **FR-023:** The CLI MUST exit with code `0` when `status` is `"ok"`, code
  `1` when `status` is `"warning"` (only warnings, no errors), and code `2`
  when `status` is `"error"` (any error-level issues present). In `--check`
  mode, the exit code carries the status but no JSON or text output is
  produced.
- **FR-024:** When `--fix --in-place` is used, the system MUST write the
  corrected diagram to a temporary file first, then atomically replace the
  original file. If any error occurs during correction, the original file
  MUST NOT be modified and the system MUST exit with code `2`.
- **FR-025:** The `corrected_diagram` field in the output MUST be `null` when
  no issues are fixable (i.e., all issues have `fixable: false`, or the
  issues array is empty). It MUST be a string when at least one fixable issue
  was corrected.
- **FR-026:** The system MUST treat every character matching the connector
  character set (Appendix A) as a diagram connector during analysis. Characters
  not in the connector set are **non-connector content** and MUST be preserved
  as-is. The system does not perform semantic text-vs-diagram classification;
  users processing files with connector characters in prose should isolate
  diagram sections beforehand.
- **FR-028:** The system MUST detect markdown table blocks before connector
  classification (during or immediately after preprocessing). A block is
  identified as a markdown table when it meets all of:
  1. At least **two consecutive rows** that each contain one or more `|`
     characters with non-empty cell content between or around them.
  2. The **second row** of the block (the separator row) consists entirely
     of `|`, `-`, `:`, and whitespace.
  3. All rows in the block have the same number of `|`-delimited columns.
- **FR-029:** When a markdown table is identified, the system MUST:
  1. **Exempt** all `|`, `-`, and `:` characters within the table block from
     connector classification — they are preserved as table formatting.
  2. **Normalize** column widths by computing the maximum content width per
     column across all rows, then padding each cell with trailing spaces to
     match the column width. The separator row `-` sequences MUST also be
     padded to the column width (preserving any `:` alignment markers at
     the start or end of the dash sequence).
  3. **Preserve** all cell content text unchanged (only whitespace padding
     is added).
- **FR-030:** When a markdown table has a missing or malformed separator row,
  the system MUST:
  1. Report an issue at `warning` severity.
  2. In `corrected_diagram`, insert or rewrite the separator row with the
     correct number of columns. Each separator cell MUST be at least three
     dashes (`---`) and MUST be padded to match the column width.
- **FR-031:** The system MUST distinguish between `|` characters inside a
  markdown table block (preserved as formatting) and `|` characters outside
  such blocks (treated as ASCII vertical line connectors per Appendix A). A
  `|` that is not part of a recognized markdown table follows the standard
  connector classification and orphan detection rules.
- **FR-027:** The system MUST process the diagram in the following pipeline
  order:
  1. **Preprocessing**: BOM stripping (EC-025), ANSI escape removal (EC-026),
     tab expansion (EC-009), line-ending normalization (FR-002), trailing
     whitespace trimming (EC-011).
  2. **Markdown table detection**: Identify contiguous GFM table blocks in the
     preprocessed input (FR-028). Exempt `|`, `-`, and `:` within identified
     table blocks from subsequent connector classification. Record table
     boundaries for column-width normalization during fix application.
  3. **Grid construction**: Parse normalized input into a 2D character grid
     (FR-003).
  4. **Connector classification**: Classify every cell (outside markdown
     table blocks) as connector or non-connector (FR-004).
  5. **Connected component analysis**: Cluster connectors into connected
     components using the adjacency and connectivity rules (Definitions).
  6. **Orphan detection**: Identify fully isolated orphans and component
     orphans (FR-008, FR-009).
  7. **Gap detection**: Ray-cast from each connector along expected
     directions to find gaps (FR-007).
  8. **Box analysis**: Identify boxes and detect width mismatches (FR-012,
     AC-003).
  9. **Style analysis**: Detect mixed single/double-line within components
     (FR-013).
  10. **Cross/arrow/circle validation**: Check crosses, arrow heads, circles
      (FR-021, AC-005, AC-006).
  11. **Fix application**: Apply unambiguous fixes in order: orphan removal →
      gap fill → box normalization → style unification → markdown table
      normalization (FR-016–018, FR-010, FR-029). Orphan removal runs
      first so that gaps pointing at orphaned cells do not trigger spurious
      gap fills. Markdown table normalization runs last so that table
      content from earlier fixes (e.g., orphan removal of diagram fragments
      near a table) does not affect column-width calculations.
  12. **Output generation**: Produce JSON report and corrected diagram
      (FR-015, FR-025).

---

## Non-Functional Requirements

- **NFR-001:** The system SHOULD process a diagram of up to 200 lines × 200
  columns in under 2 seconds on consumer hardware.
- **NFR-002:** The system MUST handle UTF-8 input including full-width
  characters and emoji gracefully (treating them as single-cell content
  within the grid, though width calculation must account for display width).
- **NFR-003:** Error messages in `issues` MUST be human-readable and MUST
  reference the actual characters found vs. expected.
- **NFR-004:** The system SHOULD process diagrams with up to 10,000 connector
  cells without exceeding 256 MB of memory.
- **NFR-005:** The system MUST support Python 3.10, 3.11, 3.12, 3.13, and
  3.14.
- **NFR-006:** The system MUST handle input encoding errors gracefully:
  invalid UTF-8 sequences SHOULD be replaced with U+FFFD (REPLACEMENT
  CHARACTER) before analysis, and a warning SHOULD be emitted.

---

## Data Model

### Input

```
diagram: str  — raw UTF-8 string containing the ASCII diagram
options: dict | None (optional) — configuration options:
  {
    "tab_width": 4,        // spaces per tab (default: 4)
    "max_grid_width": 400, // maximum columns before warning (default: 400)
    "mode": "check" | "fix" | "auto"  // processing mode (default: "auto")
  }
```

### Output (JSON)

```jsonc
{
  "status": "ok",           // "ok" | "warning" | "error"
  "issues": [
    {
      "id": "GAP-5-12",     // optional, stable identifier for CI integration
      "line": 5,            // 1-indexed line number
      "col": 12,            // 1-indexed column (character position)
      "end_line": 5,        // optional, present for multi-cell issues
      "end_col": 14,        //   (boxes, component orphans, multi-cell gaps)
      "severity": "error",  // "error" | "warning" | "info"
      "type": "gap",        // "gap" | "box_width" | "style_mix"
                            // | "dangling_junction" | "orphan" | "missing_side"
      "message": "Disconnected vertical line: expected connector below '├' at (5,12), found empty space for 1 cell before '└'",
      "fixable": true,
      "fix_suggestion": "Insert '│' at (6,12) to connect '├' to '└'"
    }
  ],
  "corrected_diagram": "…"  // string | null
                            // null when no issues or no fixable issues;
                            // string when at least one fixable issue was corrected
}
```

The `corrected_diagram` field is:
- **`null`** when the `issues` array is empty (no issues found)
- **`null`** when all issues have `fixable: false` (no unambiguous corrections)
- **`string`** when at least one issue has `fixable: true` and the correction
  was applied

The `id` field is optional and provides a stable, predictable identifier for
each issue. When present, it follows the format `<TYPE>-<LINE>-<COL>` where
`TYPE` is an abbreviated issue type code. Implementations MAY include it for
CI integration.

| Issue type | `id` prefix |
|---|---|
| `gap` | `GAP` |
| `box_width` | `BOX` |
| `style_mix` | `STYLE` |
| `dangling_junction` | `DANGL` |
| `orphan` | `ORPH` |
| `missing_side` | `SIDE` |
| `arrow_orphan` | `ARRW` |
| `markdown_table` | `MDTBL` |

The `end_line` and `end_col` fields are present for multi-cell issues:
- **Box-width mismatches** — span of the box borders
- **Component orphans** — bounding box of the orphan component
- **Style inconsistencies** — span of the mixed-style component
- **Multi-cell gaps** — start and end of the empty cell run

Single-cell issues (fully isolated orphans, single-cell gaps) do not include
`end_line` / `end_col`.

---

## Edge Cases & Error Handling

| ID | Scenario | Expected Behavior |
|----|----------|-------------------|
| EC-001 | Empty string input | Return `{status: "ok", issues: [], corrected_diagram: null}` |
| EC-002 | Input has no box-drawing, arrow, or circle characters | Return `{status: "ok", issues: []}` — not an error, just no diagram to check |
| EC-003 | Input contains only plain text, no diagram structure | Same as EC-002 |
| EC-004 | Diagram uses plain ASCII (`+`, `-`, `\|`) instead of Unicode box-drawing | The system MUST detect `+` as a potential junction and `-`/`\|` as potential lines. Treat as a valid but separate style. Report as `info` if mixed Unicode/ASCII connectors. |
| EC-005 | A `┼` (cross) has lines in only 3 of 4 directions | Report as `warning` — the cross may be intentional decoration or a T-junction mis-drawn as a cross |
| EC-006 | Two connectors are separated by 2+ empty cells | Report as `error` but mark `fixable: false` — the gap is too large to unambiguously fill |
| EC-007 | A box contains another box nested inside | Handle correctly — the outer box's interior space should not be treated as connectivity gaps. The inner box is a separate connected component. |
| EC-008 | Lines that intentionally cross without connecting (e.g., network diagram with `╲` crossing a `│`) | Do NOT report crossings as errors unless characters at the crossing point imply a junction. A `│` crossing a `─` with no `┼` at the intersection is valid. |
| EC-009 | Diagram with tab characters | Replace tabs with 4 spaces before analysis (configurable via option) |
| EC-010 | Very wide diagram (>200 columns) | Process normally; the 2D grid is sparse so performance is bounded by character count, not grid dimensions |
| EC-011 | Diagram with trailing whitespace | Trim trailing whitespace from each line before analysis (whitespace normalization is applied to the analysis copy; the `corrected_diagram` output preserves original whitespace on unmodified lines and uses normalized whitespace on corrected lines) |
| EC-012 | Multiple disconnected diagram regions in one input | Analyze each connected component independently. Each component is compared against the largest component: components disconnected from the largest are reported as orphans (see Definitions — Orphan). If no single largest component is clearly dominant, all components are analyzed for internal issues but none is treated as an orphan of another. |
| EC-013 | A `│` at the very top or bottom of the diagram with no connector above/below | Report as `error` — a vertical line must connect to something or it's a fragment |
| EC-014 | Mixed arrow styles in same diagram (Unicode `→` vs ASCII `->`) | Report as `warning` (style inconsistency). Do not attempt to unify arrow styles automatically. |
| EC-015 | Diagram with diacritics or combining characters that affect column alignment | Treat each Unicode grapheme cluster as occupying its display width (e.g., CJK chars = 2 cells). Report alignment issues if detected. |
| EC-016 | A standalone `│` with empty cells above and below | Report as `orphan` (severity: `error`); replace with space in `corrected_diagram` |
| EC-017 | A `└` and `─` adjacent (forming a partial bottom-left corner of a box) with no matching right-side or top connectors anywhere | Report both cells as component orphans; remove the entire orphan fragment in `corrected_diagram` |
| EC-018 | An arrow tail `▶` with no `─` to its left | Report as `orphan` (broken arrow head); remove in `corrected_diagram` |
| EC-019 | A fragment of a box wall: three `─` in a row with nothing connected to either end | Report as component orphan; remove all three in `corrected_diagram` |
| EC-020 | A `●` (circle) more than 1 cell away from any connector | Do NOT report as orphan — likely an intentional label node |
| EC-021 | A `●` exactly 1 cell away from a `│` but not touching it | Report as potential orphan at `warning` severity; do NOT auto-remove |
| EC-022 | A `╲` (diagonal) with no diagonal neighbour in either direction (within Chebyshev distance 1, i.e., any of the 4 diagonal cells) | Report as `orphan` at `warning` severity; remove in `corrected_diagram` |
| EC-023 | A box with only three complete sides (e.g., `┌──┐` with `│` on left and right but no bottom `└┘`) | Report missing side as a structural `error`; mark `fixable: false` — the intended shape is ambiguous |
| EC-024 | Two independent diagram components that share one or more cells (overlapping layouts) | Report each overlapping cell as a conflict `error`; mark `fixable: false` — the intended topology is ambiguous |
| EC-025 | Input starts with a UTF-8 BOM (U+FEFF) | Strip the BOM before analysis; do not treat it as diagram content |
| EC-026 | Input contains ANSI escape codes | Strip ANSI escape sequences before analysis (they are not diagram content); do not report them as errors |
| EC-027 | Two analysis stages detect the same issue on the same cell | Deduplicate: keep the first occurrence by pipeline stage order. Duplicates are defined as issues sharing the same `type`, `line`, and `col`. |
| EC-028 | Diagram consists entirely of `─` or `│` characters with no junctions, corners, or arrow heads | Report as `orphan` (each disconnected segment is an orphan); remove all in `corrected_diagram` |
| EC-029 | An orphaned full arrow (`→`, `←`, `↑`, `↓`) with no connectors on either expected side | Report as `orphan` (severity: `error`); remove in `corrected_diagram`. Same as other fully isolated orphans. |
| EC-030 | A connected component mixes Unicode box-drawing characters (`┌─┐│└┘`) with ASCII equivalents (`+`, `-`, `\|`) | Report as `info` — the component uses two styles for the same structural purpose. Do not attempt to unify automatically (the conversion is lossy: `+` could be a cross or a corner). |
| EC-031 | A valid markdown table block containing `|` and `-` characters | Do NOT treat `|` or `-` within the table block as diagram connectors. Exempt them from connector classification. Preserve them as-is in `corrected_diagram`. Normalize column widths (FR-029). |
| EC-032 | A markdown table with a missing or malformed separator row (e.g., a `|` data row directly followed by another `|` data row with no `|---|` row between them) | Report as `warning` (`MDTBL` type). Insert or rewrite the separator row in `corrected_diagram` with the correct number of columns and padded dashes matching column widths. |
| EC-033 | A markdown table with inconsistent column counts across rows (e.g., row 1 has 3 columns, row 2 has 4 columns) | Report as `warning`. Normalize to the maximum column count. Rows with fewer columns get empty cells appended. Rows with extra columns beyond a reasonable threshold MAY be flagged as ambiguous. |

---

## Out of Scope

- **Pie charts** — ASCII cannot faithfully represent them; the tool will not
  attempt to validate pie chart approximations.
- **Diagram generation** — this tool validates and fixes existing diagrams; it
  does not create new diagrams from descriptions.
- **Rendering or visualization** — the tool works at the character-grid level
  only.
- **Non-ASCII diagrams** — images, SVG, Mermaid, Graphviz DOT, or any
  non-text diagram format.
- **Formal diagram types beyond basic boxes, trees, and flowcharts** — UML
  class diagrams, BPMN, detailed circuit diagrams, etc. are not explicitly
  supported though generic box/line analysis may catch some issues.
- **Interactive mode** — the tool is batch/one-shot; no TUI or real-time
  editing.
- **Semantic validation** — the tool does not check whether a flowchart is
  logically correct, only whether its structure is geometrically sound.
- **Color or styling** — ANSI escape codes in the input are stripped during
  preprocessing (see EC-026).
- **Context-aware text-region detection** — the tool treats all matching
  connector characters as connectors. Users must isolate diagram regions if
  connector characters appear in prose (see FR-026).

---

## Processing Pipeline

The analysis proceeds in the following fixed order (as defined in FR-027):

```
Preprocessing → Markdown Table Detection → Grid Construction →
Connector Classification → Connected Component Analysis →
Orphan Detection → Gap Detection → Box Analysis → Style Analysis →
Cross/Arrow/Circle Validation → Fix Application → Output Generation
```

Key properties of the pipeline:

- **Detections are additive**: later stages may report issues on the same
  cells as earlier stages (e.g., an orphan cell may also be part of a box).
  All issues are collected and reported.
- **Fixes are sequential**: when multiple fix types apply to the same region,
  they are applied in the order listed in FR-027 step 10 (orphan removal →
  gap fill → box normalization → style unification). Earlier fixes may
  affect later fix applicability (e.g., removing an orphan may resolve a gap
  that was detected during analysis).
- **Duplicate issues MUST be deduplicated** before the report is generated.
  Two issues are duplicates if they share the same `type`, `line`, and
  `col`. When duplicates exist, the one from the earliest pipeline stage
  that detected it is kept.
- **The corrected diagram is derived from the normalized input copy** with
  fixes applied incrementally. Intermediate states are not exposed.
- **If any fix is ambiguous** (the step cannot determine a single correction),
  the step is skipped and the corresponding issues are marked `fixable: false`.

---

## Dependencies & Assumptions

- **Runtime:** Python 3.10+.
- **Libraries:** Uses `click` for CLI (required for the `das` command).
  May optionally use `pydantic` for data model validation and `wcwidth` for
  Unicode display width. The library API (`sanitize()`) uses only Python
  stdlib.
- **Assumption:** Input is rendered in a monospaced font where every
  character occupies exactly one column (or two for CJK full-width).
- **Assumption:** Box-drawing characters follow standard Unicode semantics
  (e.g., `┌` always expects connections to the right and down).
- **Assumption:** Diagrams read top-to-bottom, left-to-right. The analysis
  does not depend on reading order for arrow semantics.

---

## Constraints

- Must be installable via `pip install diagram-sanitizer` (or equivalent
  — the published package name).
- Must not require network access at runtime.
- Must not modify the input file on disk unless explicitly asked (`--fix
  --in-place`), and even then must use atomic file replacement (FR-024).
- The library API must have zero required dependencies beyond Python stdlib;
  CLI extras can declare additional deps.

---

## Appendix A: Connector Direction Map

The following characters are recognized as connectors, with their expected
connection directions:

| Character(s) | Name | Expects connection… |
|---|---|---|
| `─` | Horizontal line | Left and/or Right (at least one side; a cell connected on both sides is a continuous segment, on one side is an endpoint — endpoints are valid and not an error) |
| `│` | Vertical line | Above and/or Below (at least one side; endpoints are valid) |
| `═` | Double horizontal | Left and/or Right (at least one side; endpoints are valid) |
| `║` | Double vertical | Above and/or Below (at least one side; endpoints are valid) |
| `┌` | Top-left corner | Right (`─`) and Below (`│`) |
| `┐` | Top-right corner | Left (`─`) and Below (`│`) |
| `└` | Bottom-left corner | Right (`─`) and Above (`│`) |
| `┘` | Bottom-right corner | Left (`─`) and Above (`│`) |
| `├` | T-right | Above (`│`), Below (`│`), Right (`─`) |
| `┤` | T-left | Above (`│`), Below (`│`), Left (`─`) |
| `┬` | T-down | Left (`─`), Right (`─`), Below (`│`) |
| `┴` | T-up | Left (`─`), Right (`─`), Above (`│`) |
| `┼` | Cross | Above, Below, Left, Right (all four) |
| `╔╗╚╝╠╣╦╩╬` | Double-line equivalents | Same as single-line counterparts |
| `▶` | Right arrow head | Left (`─`) |
| `◀` | Left arrow head | Right (`─`) |
| `▼` | Down arrow head | Above (`│`) |
| `▲` | Up arrow head | Below (`│`) |
| `→` | Right arrow (full) | Left and Right (continuation) |
| `←` | Left arrow (full) | Left and Right (continuation) |
| `↑` | Up arrow (full) | Above and Below (continuation) |
| `↓` | Down arrow (full) | Above and Below (continuation) |
| `●` `○` | Circle (node) | Any direction (loose — reports warning if not connected to anything) |
| `╲` `╱` | Diagonal lines | Diagonal neighbors (loose check) |
| `+` | ASCII junction | Any cardinal direction |
| `-` | ASCII horizontal | Left and/or Right (at least one side; endpoints are valid) |
| `\|` | ASCII vertical | Above and/or Below (at least one side; endpoints are valid) |

> **Markdown table exception:** When `|`, `-`, or `:` characters appear
> inside a recognized markdown table block (see FR-028), they are exempted
> from connector classification and are NOT treated as diagram connectors.
> They are preserved as table formatting characters. Only `|`, `-`, and `:`
> outside markdown table blocks are subject to the connector rules above.

For each direction a connector expects, the tool traces outward cell-by-cell
until it either hits another connector (connection satisfied) or empty space
(potential gap). A gap of exactly 1 empty cell that would connect to another
connector is auto-fixable; gaps of 2+ are reported but not auto-fixed.

---

## Appendix B: CLI Usage Sketch

The installed command is `das`.

```
$ das diagram.txt
{ "status": "error", "issues": [...], "corrected_diagram": "..." }

$ das --check diagram.txt                # exit code only, no output
$ das --fix diagram.txt                  # print corrected diagram to stdout
$ das --fix --in-place diagram.txt       # overwrite file atomically
$ das --format text diagram.txt          # human-readable text report
$ das --tab-width 2 diagram.txt          # custom tab expansion width
$ cat diagram.txt | das --fix -          # read from stdin, fix, print to stdout
$ das                                    # prints help (stdin is terminal)
```
