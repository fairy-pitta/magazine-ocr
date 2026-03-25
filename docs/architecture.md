# Architecture

## Design Principles

- deterministic extraction first
- AI assistance only for bounded ambiguity
- every decision should have retained visual evidence
- structured outputs are more important than freeform OCR text
- preserve provenance for every inferred or corrected field

## High-Level Pipeline

The proposed architecture has six layers.

1. Ingest
2. Layout extraction
3. Field extraction
4. State and reconciliation
5. AI review
6. Reporting

## Layer 1: Ingest

Responsibilities:

- enumerate input images
- collect metadata
- define stable image IDs
- create run directories

Possible module:

- `src/magazine_ocr/ingest.py`

Outputs:

- input manifest
- image dimensions
- run identifier

## Layer 2: Layout Extraction

Responsibilities:

- split spreads into logical pages
- identify page header region
- identify row or entry regions
- preserve bounding boxes for all structural elements

Possible modules:

- `src/magazine_ocr/layout/page_split.py`
- `src/magazine_ocr/layout/page_crop.py`
- `src/magazine_ocr/layout/row_detect.py`

Outputs:

- logical page images
- page bounding boxes
- row bounding boxes

## Layer 3: Field Extraction

Responsibilities:

- extract page numbers
- detect prefecture header blocks
- detect `☆NNN` anchor blocks
- OCR only the necessary text snippets

Possible modules:

- `src/magazine_ocr/extract/page_number.py`
- `src/magazine_ocr/extract/pref_header.py`
- `src/magazine_ocr/extract/anchor.py`
- `src/magazine_ocr/extract/location.py`

Outputs:

- raw field candidates
- confidence scores
- crop evidence paths

## Layer 4: State And Reconciliation

Responsibilities:

- order elements in reading sequence
- propagate prefecture state across entries
- reconcile serial numbers using continuity
- produce a normalized record per entry

Possible modules:

- `src/magazine_ocr/reconcile/reading_order.py`
- `src/magazine_ocr/reconcile/prefecture_state.py`
- `src/magazine_ocr/reconcile/serial_sequence.py`

Outputs:

- normalized entry records
- anomaly flags
- repair reasons

## Layer 5: AI Review

Responsibilities:

- review only low-confidence or contradictory cases
- accept compact evidence bundles
- return structured decisions
- never silently overwrite deterministic evidence

Possible modules:

- `src/magazine_ocr/ai/review_queue.py`
- `src/magazine_ocr/ai/claude_review.py`
- `src/magazine_ocr/ai/prompt_builder.py`

Outputs:

- reviewed field values
- AI review rationale
- audit log of AI involvement

## Layer 6: Reporting

Responsibilities:

- export record-level files
- export prefecture counts
- export anomaly reports
- render overlay images for audit

Possible modules:

- `src/magazine_ocr/report/export_csv.py`
- `src/magazine_ocr/report/overlay.py`
- `src/magazine_ocr/report/summary.py`

Outputs:

- `records.csv`
- `prefecture_counts.csv`
- `sequence_anomalies.csv`
- overlay images

## Canonical Record Schema

Proposed record fields:

- `image_id`
- `page_number`
- `page_side`
- `reading_order`
- `row_index`
- `serial_number_raw`
- `serial_number_final`
- `serial_confidence`
- `prefecture_header_raw`
- `prefecture_norm`
- `prefecture_source`
- `prefecture_confidence`
- `location_raw`
- `location_confidence`
- `bbox_page_number`
- `bbox_pref_header`
- `bbox_anchor`
- `needs_review`
- `review_source`
- `repair_reason`

## Confidence Model

Each field should carry its own confidence.

Recommended fields:

- `raw_confidence`
- `reconciled_confidence`
- `needs_review`

Suggested confidence sources:

- OCR engine confidence if available
- template matching score
- regex validation
- sequence consistency
- prefecture-state consistency

## AI Integration Strategy

Claude Code should be used as a constrained review component, not as the first extraction engine.

Recommended use cases:

- ambiguous page number crops
- ambiguous prefecture header crops
- anchor digit candidates that conflict with sequence continuity
- contradictory cases where local OCR and global sequence disagree
- sparse cases where deterministic heuristics fail on layout variation

Not recommended as primary AI tasks:

- reading the whole page and returning freeform notes
- deriving prefecture counts directly without structured extraction
- overwriting high-confidence deterministic values

## Claude Code Review Contract

Input bundle to Claude Code should include:

- cropped image path or inline crop
- page number candidate if known
- neighboring serial numbers
- current prefecture state if known
- deterministic candidates and confidence
- explicit task and JSON schema

Example review tasks:

- choose best serial from candidate list
- decide whether a prefecture header is present
- decide whether a crop belongs to the current prefecture block or starts a new one

Required output characteristics:

- structured JSON only
- no hidden chain-of-thought requirements
- explicit uncertainty field
- evidence-based decision rationale in short form

## Why Hybrid Instead Of AI-Only

AI-only extraction is tempting, but risky here for three reasons.

- the magazine has strong layout structure that deterministic rules can exploit cheaply
- the final deliverable is count accuracy, so provenance and repeatability matter
- serial continuity gives a powerful correction signal that should live outside the model

The hybrid design reduces hallucination risk while still using AI where it adds value.

## Failure Containment

When uncertainty is high:

- keep the original deterministic candidates
- preserve the crop
- mark the record for review
- do not collapse multiple plausible values into one without traceability

## Suggested Directory Layout

Proposed project structure as implementation grows:

```text
src/magazine_ocr/
  cli.py
  ingest.py
  schemas.py
  layout/
    page_split.py
    page_crop.py
    row_detect.py
  extract/
    page_number.py
    pref_header.py
    anchor.py
    location.py
  reconcile/
    reading_order.py
    prefecture_state.py
    serial_sequence.py
  ai/
    prompt_builder.py
    review_queue.py
    claude_review.py
  report/
    export_csv.py
    overlay.py
    summary.py
```

## Recommended First Architecture Milestone

Implement the following path first:

- ingest
- page split
- page number extraction
- anchor detection
- prefecture header detection
- stateful prefecture assignment
- serial reconciliation
- CSV export

Only after that should the AI review queue be connected.

