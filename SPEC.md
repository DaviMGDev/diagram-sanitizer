# SPEC.md — ASCII Diagram Sanitizer

**Version:** 1.0  
**Date:** 2026-06-06  
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
  report a structural error for that box.
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
- **AC-013:** WHEN a connector has no adjacent connectors in any of its
  expected directions (i.e., it is fully orphaned — not part of any connected
  component larger than itself), THE system MUST report it as an orphan issue
  and MUST remove it (replace with `U+0020 SPACE`) in `corrected_diagram`.
- **AC-014:** WHEN an isolated component (2 or more characters that are
  connected to each other but not to any larger structure) is recognisable as
  a fragment of a broken structure (e.g., a wall segment missing both ends, a
  corner pair with no opposite corners, an arrow tail without a head), THE
  system MUST report each constituent connector as an orphan and MUST remove
  the entire orphan component in `corrected_diagram`.
- **AC-015:** WHEN a diagram contains an arrow head pointing at empty space
  (no line character in its expected connecting direction), THE system MUST
  report a broken-arrow orphan and MUST remove the arrow head in
  `corrected_diagram`.
- **AC-016:** WHEN a diagram contains text, labels, or prose intermixed with
  box-drawing characters, THE system MUST preserve all non-connector
  characters unchanged in `corrected_diagram`, subject only to whitespace
  normalization (FR-002, FR-019).
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

### From US-003 (Library)

- **AC-011:** The system MUST expose a top-level function
  `sanitize(diagram: str) -> dict` that accepts a string and returns the full
  JSON report as a Python dict.
- **AC-012:** The CLI MUST read from a file path argument or stdin, print
  the JSON report to stdout, and exit with code `0` (ok), `1` (warnings),
  or `2` (errors).

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
  issues, 1 if only warnings, 2 if any errors; no output) and `--fix` mode
  (output corrected diagram to stdout or file).
- **FR-006:** The CLI MUST support `--format json|text` to control output
  format.
- **FR-007:** The system MUST traverse each connector's expected directions
  by ray-casting outward cell-by-cell in each cardinal direction until it
  either encounters another connector (connection satisfied) or reaches empty
  space. The system MUST report a **connectivity gap** when the path to the
  next connector is interrupted by empty space. Only connectors along the
  same row (horizontal) or same column (vertical) are considered; diagonal
  adjacency does not satisfy cardinal-direction connections.
- **FR-008:** The system MUST detect **orphan symbols** — connectors that
  have no adjacent connectors in any of their expected directions (as defined
  in Appendix A). A connector is orphaned if and only if the cell in every
  expected cardinal direction is empty, non-connector, or out of bounds.
- **FR-009:** The system MUST distinguish between:
  - **Fully isolated orphan** — a single connector with zero connections.
  - **Component orphan** — a connected component of 2 or more cells where
    every connector in the component is disconnected from the wider diagram.
    Components of 2–4 cells are presumptive orphans; components of 5+ cells
    that are similarly isolated from any larger structure MUST also be
    reported as orphans. These are fragments of a larger structure (e.g., a
    wall segment, a corner pair, a partial arrow) and MUST be removed in
    their entirety.
- **FR-010:** When a connector is determined to be an orphan, the unambiguous
  fix is to replace it with `U+0020 SPACE` in `corrected_diagram`. For
  component orphans, every cell in the orphan component MUST be replaced with
  `U+0020 SPACE`.
- **FR-011:** The system MUST NOT treat a standalone `●` or `○` (circle) as
  an orphan if it is at least 2 cells away from any other connector — it may
  be an intentional node label marker. Circles within 1 cell of another
  connector that do not connect to it MUST be reported as potential orphans
  at `warning` severity (not removed automatically).
- **FR-012:** The system MUST report a **box-width mismatch** when the
  horizontal span between a pair of top corners (`┌…┐`) differs from the
  span between the corresponding bottom corners (`└…┘`) of the same box.
  A box is identified by matching `┌` with the nearest `┐` on the same row
  that has a corresponding `└`/`┘` pair vertically aligned at the same
  columns. Box corners are paired greedily left-to-right, top-to-bottom.
- **FR-013:** The system MUST report a **style inconsistency** when a single
  connected component contains both single-line and double-line box-drawing
  characters.
- **FR-014:** The system MUST assign one of three severities to every issue:
  `error` (broken connectivity, box mismatch, orphan symbol), `warning` (style
  inconsistency, likely-decorative cross, intact single-character component
  that may be intentional), `info` (suggestions).
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

---

## Non-Functional Requirements

- **NFR-001:** The system SHOULD process a diagram of up to 200 lines × 200
  columns in under 2 seconds on consumer hardware.
- **NFR-002:** The system MUST handle UTF-8 input including full-width
  characters and emoji gracefully (treating them as single-cell content
  within the grid, though width calculation must account for display width).
- **NFR-003:** Error messages in `issues` MUST be human-readable and MUST
  reference the actual characters found vs. expected.

---

## Data Model

### Input

```
diagram: str  — raw UTF-8 string containing the ASCII diagram
```

### Output (JSON)

```jsonc
{
  "status": "ok",           // "ok" | "warning" | "error"
  "issues": [
    {
      "line": 5,            // 1-indexed line number
      "col": 12,            // 1-indexed column (character position)
      "end_line": 5,        // optional, for multi-cell issues
      "end_col": 14,
      "severity": "error",  // "error" | "warning" | "info"
      "type": "gap",        // "gap" | "box_width" | "style_mix" | "dangling_junction" | "orphan"
      "message": "Disconnected vertical line: expected connector below '├' at (5,12), found empty space for 1 cell before '└'",
      "fixable": true,
      "fix_suggestion": "Insert '│' at (6,12) to connect '├' to '└'"
    }
  ],
  "corrected_diagram": "…"  // string | null (null if no fix, or no fixable issues)
}
```

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
| EC-012 | Multiple disconnected diagram regions in one input | Analyze each connected component independently. Report issues per component. |
| EC-013 | A `│` at the very top or bottom of the diagram with no connector above/below | Report as `error` — a vertical line must connect to something or it's a fragment |
| EC-014 | Mixed arrow styles in same diagram (Unicode `→` vs ASCII `->`) | Report as `warning` (style inconsistency). Do not attempt to unify arrow styles automatically. |
| EC-015 | Diagram with diacritics or combining characters that affect column alignment | Treat each Unicode grapheme cluster as occupying its display width (e.g., CJK chars = 2 cells). Report alignment issues if detected. |
| EC-016 | A standalone `│` with empty cells above and below | Report as `orphan` (severity: `error`); replace with space in `corrected_diagram` |
| EC-017 | A `└` and `─` adjacent (forming a partial bottom-left corner of a box) with no matching right-side or top connectors anywhere | Report both cells as component orphans; remove the entire orphan fragment in `corrected_diagram` |
| EC-018 | An arrow tail `▶` with no `─` to its left | Report as `orphan` (broken arrow head); remove in `corrected_diagram` |
| EC-019 | A fragment of a box wall: three `─` in a row with nothing connected to either end | Report as component orphan; remove all three in `corrected_diagram` |
| EC-020 | A `●` (circle) over 2 cells away from any connector | Do NOT report as orphan — likely an intentional label node |
| EC-021 | A `●` exactly 1 cell away from a `│` but not touching it | Report as potential orphan at `warning` severity; do NOT auto-remove |
| EC-022 | A `╲` (diagonal) with no diagonal neighbour in either direction (within Chebyshev distance 1, i.e., any of the 4 diagonal cells) | Report as `orphan` at `warning` severity; remove in `corrected_diagram` |
| EC-023 | A box with only three complete sides (e.g., `┌──┐` with `│` on left and right but no bottom `└┘`) | Report missing side as a structural `error`; mark `fixable: false` — the intended shape is ambiguous |
| EC-024 | Two independent diagram components that share one or more cells (overlapping layouts) | Report each overlapping cell as a conflict `error`; mark `fixable: false` — the intended topology is ambiguous |
| EC-025 | Input starts with a UTF-8 BOM (U+FEFF) | Strip the BOM before analysis; do not treat it as diagram content |
| EC-026 | Input contains ANSI escape codes | Strip ANSI escape sequences before analysis (they are not diagram content); do not report them as errors |
| EC-027 | An isolated component of 5+ cells that is completely disconnected from any larger structure | Report as component orphan (severity: `error`); remove in `corrected_diagram` (same treatment as 2–4 cell component orphans) |
| EC-028 | Diagram consists entirely of `─` or `│` characters with no junctions, corners, or arrow heads | Report as `orphan` (each disconnected segment is an orphan); remove all in `corrected_diagram` |

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
- **Formal diagram types beyond the 16 in diagram.md** — UML class diagrams,
  BPMN, detailed circuit diagrams, etc. are not explicitly supported though
  generic box/line analysis may catch some issues.
- **Interactive mode** — the tool is batch/one-shot; no TUI or real-time
  editing.
- **Semantic validation** — the tool does not check whether a flowchart is
  logically correct, only whether its structure is geometrically sound.
- **Color or styling** — ANSI escape codes in the input are stripped during preprocessing (see EC-026).

---

## Dependencies & Assumptions

- **Runtime:** Python 3.10+.
- **Libraries:** May use `click` or `typer` for CLI; `pydantic` for data
  model validation; `wcwidth` for Unicode display width. All optional at
  library level (CLI extras).
- **Assumption:** Input is rendered in a monospaced font where every
  character occupies exactly one column (or two for CJK full-width).
- **Assumption:** Box-drawing characters follow standard Unicode semantics
  (e.g., `┌` always expects connections to the right and down).
- **Assumption:** Diagrams read top-to-bottom, left-to-right. The analysis
  does not depend on reading order for arrow semantics.

---

## Constraints

- Must be installable via `pip install ascii-sanitizer` (or equivalent).
- Must not require network access at runtime.
- Must not modify the input file on disk unless explicitly asked (`--fix
  --in-place`).
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

For each direction a connector expects, the tool traces outward cell-by-cell
until it either hits another connector (connection satisfied) or empty space
(potential gap). A gap of exactly 1 empty cell that would connect to another
connector is auto-fixable; gaps of 2+ are reported but not auto-fixed.

---

## Appendix B: CLI Usage Sketch

```
$ ascii-sanitizer diagram.txt
{ "status": "error", "issues": [...], "corrected_diagram": "..." }

$ ascii-sanitizer --check diagram.txt    # exit code only, no output
$ ascii-sanitizer --fix diagram.txt      # print corrected diagram to stdout
$ ascii-sanitizer --fix --in-place diagram.txt   # overwrite file
$ cat diagram.txt | ascii-sanitizer --fix -      # stdin to stdout
```
