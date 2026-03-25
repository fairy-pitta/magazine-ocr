# Workflow

## Objective

Define the operational workflow from raw magazine image to reviewed prefecture count output.

## Workflow Summary

The workflow should be run in stages, with review checkpoints after each stage that changes high-value fields.

The intended flow is:

1. ingest images
2. extract structural crops
3. extract page number, prefecture header, and anchor candidates
4. reconcile sequence and prefecture state
5. send only uncertain cases to AI review
6. run manual spot-checks
7. export final records and counts

## Stage 1: Prepare Inputs

Inputs:

- photographed JPEG images in `images/`

Actions:

- verify filenames
- verify images are readable
- collect dimensions
- create a new run directory under output

Outputs:

- run manifest
- stable image IDs

## Stage 2: Structural Extraction

Actions:

- split each spread into logical pages
- store page crops
- detect and store row boxes
- render quick diagnostic overlays

Review checkpoint:

- verify that page crops are aligned and complete

Outputs:

- page crops
- row crops or row metadata

## Stage 3: Deterministic Field Extraction

Actions:

- extract page number from header crop
- detect prefecture header candidates
- detect `☆NNN` anchor candidates
- OCR digit candidates

Review checkpoint:

- spot-check that extracted crops correspond to the intended printed elements

Outputs:

- raw field candidate table
- evidence crop paths
- confidence scores

## Stage 4: Reconciliation

Actions:

- sort records by reading order
- propagate prefecture state from explicit headers
- repair serial numbers using sequence continuity
- flag contradictions and impossible transitions

Review checkpoint:

- inspect anomaly report before AI review

Outputs:

- reconciled record table
- anomaly queue

## Stage 5: AI Review

This stage exists to reduce mistakes, not to replace deterministic extraction.

Actions:

- collect low-confidence or contradictory records
- build compact prompts with crops and candidate values
- ask Claude Code for structured decisions
- merge accepted review results back into the record table

Rules:

- do not send clean high-confidence cases
- do not ask AI to infer the whole magazine in one shot
- do not discard deterministic evidence after AI review

Outputs:

- reviewed records
- AI review log

## Stage 6: Manual Audit

Actions:

- inspect overlays for page number, prefecture header, and anchor positions
- inspect any record with low final confidence
- inspect every sequence anomaly that remains unresolved

Outputs:

- final accepted record table

## Stage 7: Export

Actions:

- export record-level CSV or JSONL
- export prefecture count summary
- export serial anomaly summary
- export overlay images and review artifacts

Outputs:

- `records.csv`
- `prefecture_counts.csv`
- `sequence_anomalies.csv`
- overlay images

## AI Review Workflow Details

Recommended Claude Code workflow:

1. deterministic pipeline produces candidate fields and confidence
2. a review queue selects only uncertain cases
3. each case is packaged with:
   - crop image
   - image id
   - page number if known
   - neighboring serial numbers
   - active prefecture state if known
   - candidate values and scores
4. Claude Code returns structured JSON
5. the system accepts or rejects the AI response by schema and confidence checks
6. all accepted AI changes are logged

Recommended review case types:

- uncertain page number
- uncertain prefecture header
- uncertain serial digit
- conflict between OCR and sequence continuity
- missing or duplicate serials

## Human Review Workflow Details

Recommended manual review order:

1. page number failures
2. missed prefecture transitions
3. anchor misses
4. serial continuity anomalies
5. remaining AI-reviewed cases

This order prioritizes upstream errors that cascade into many downstream mistakes.

## Artifact Layout

Recommended output layout:

```text
output/
  runs/
    <run-id>/
      manifests/
      pages/
      rows/
      crops/
        page_numbers/
        pref_headers/
        anchors/
      overlays/
      review/
        queue.jsonl
        ai_responses.jsonl
      exports/
        records.csv
        prefecture_counts.csv
        sequence_anomalies.csv
```

## Decision Policy

Recommended precedence order for final fields:

1. explicit deterministic extraction with high confidence
2. deterministic extraction corrected by sequence or state consistency
3. AI-reviewed choice with preserved evidence
4. manual override

## Operational Notes

- every run should be reproducible from inputs and config
- every field change should be explainable from evidence
- every inferred prefecture should indicate whether it came from an explicit header or propagation
- every serial repair should indicate the neighboring values used

