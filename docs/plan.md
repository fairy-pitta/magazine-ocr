# Plan

## Goal

Build a robust extraction pipeline for magazine images that can recover page number, prefecture block, and star-linked serial number with enough accuracy to aggregate counts by prefecture.

## Strategy Summary

The strategy should be deterministic first, AI-assisted second.

- deterministic components handle page structure, page number extraction, anchor detection, and sequence reconciliation
- AI components handle bounded ambiguity review, not the primary extraction path
- manual review is reserved for low-confidence cases only

## Phase 0: Freeze Scope

Deliverables:

- document the observed page structure
- define output schema
- define reading order assumptions
- define confidence and review rules

Success criteria:

- team agrees that the first milestone is page number + prefecture block + serial number extraction

## Phase 1: Preprocessing And Page Decomposition

Tasks:

- load image metadata
- detect the magazine page region and suppress obvious background
- split spread images into logical right and left pages
- normalize orientation if needed
- apply contrast normalization suitable for paper images

Expected output:

- per-page cropped images
- page masks or page bounding boxes

Notes:

- exact dewarping can be postponed if row segmentation works without it
- background removal should not aim for perfection; it only needs to make later steps more stable

## Phase 2: Page Number Extraction

Tasks:

- crop top header region of each logical page
- OCR only the page number pattern, ideally using a regex like `\((\d{1,3})\)`
- preserve the crop image for review

Expected output:

- `page_number`
- `page_number_confidence`
- `bbox_page_number`

Success criteria:

- page number exact match on the current 5-image sample

## Phase 3: Entry Row Segmentation

Tasks:

- detect long horizontal rules that separate entry blocks
- generate ordered row candidates per page
- store row bounding boxes and reading order

Expected output:

- `row_index`
- `bbox_row`

Notes:

- the pipeline should tolerate imperfect row boundaries
- rows are a search aid for anchors, not a final truth source

## Phase 4: Star Anchor Detection

Tasks:

- detect star-number clusters of the form `☆NNN`
- start with template-based or heuristic detection
- OCR only the digit portion near anchor candidates
- keep alternative digit hypotheses if possible

Expected output:

- `serial_number_raw`
- `serial_number_candidates`
- `bbox_anchor`
- `anchor_confidence`

Success criteria:

- high recall on anchor detection is more important than exact number OCR in the first pass

## Phase 5: Prefecture Header Detection

Tasks:

- detect short prefecture marker lines such as `（新潟県）`
- limit OCR vocabulary to 47 prefectures and expected delimiters
- distinguish block-level prefecture labels from ordinary location text

Expected output:

- `prefecture_header_raw`
- `prefecture_norm`
- `bbox_pref_header`
- `prefecture_header_confidence`

Success criteria:

- correct identification of prefecture transitions in the 5-image sample

## Phase 6: Stateful Assignment

Tasks:

- sort extracted elements in reading order
- carry forward the most recent prefecture header to downstream anchors
- link each anchor to the prefecture state active at that point in the page sequence

Expected output:

- `prefecture_norm` assigned to every entry
- `prefecture_source = explicit_header | inferred_from_state | fallback_location`

Notes:

- this step is where the new requirement changes the design the most
- prefecture should be treated as a block state, not an independently OCRed field per entry

## Phase 7: Sequence Reconciliation

Tasks:

- sort all anchors across pages in global reading order
- compare serial numbers against expected continuity
- repair likely OCR mistakes using neighboring numbers and confidence
- flag impossible gaps or duplicates

Expected output:

- `serial_number_final`
- `serial_repair_reason`
- `sequence_anomaly_flag`

Examples of repairs:

- a missing entry between two strong neighboring serials
- a low-confidence OCR result corrected by adjacent continuity
- duplicate numbers split into one correct and one review candidate

## Phase 8: Supporting Location OCR

Tasks:

- OCR local location text only when needed
- use location as supporting evidence, not primary prefecture source
- normalize common city or ward names if explicit prefecture headers are missing

Expected output:

- `location_raw`
- `location_norm`
- `location_confidence`

Notes:

- this phase can be partially deferred until the prefecture-block pipeline is stable

## Phase 9: AI Review Layer

Tasks:

- send only ambiguous crops and extracted candidates to AI
- ask AI for structured selection, not freeform summaries
- keep deterministic evidence and provenance for every AI-assisted field

Expected output:

- `ai_review_decision`
- `ai_review_reason`
- `ai_review_confidence`

Rules:

- AI does not become the source of truth for clean high-confidence cases
- AI does not see the entire magazine unless needed
- AI should receive page number, neighboring serials, and candidate crops to reduce hallucination

## Phase 10: Aggregation And Reporting

Tasks:

- export record-level CSV or JSONL
- export prefecture-level counts
- export serial gap reports
- generate overlay images for manual audit

Expected output:

- `records.csv`
- `prefecture_counts.csv`
- `sequence_anomalies.csv`
- overlay images

## Recommended Implementation Order

1. page split and page number extraction
2. row detection
3. anchor detection and digit OCR
4. prefecture header detection
5. stateful prefecture assignment
6. sequence reconciliation
7. AI review layer
8. reporting and audit views

## Recommended Use Of The 5 Images

- use them as a golden sample, not primarily as a training set
- annotate the minimum required fields for evaluation
- delay any learned detector until the deterministic pipeline is measured

## Exit Criteria For Milestone 1

- page numbers recovered for all logical pages in the sample
- prefecture transitions recovered in the sample
- star anchors detected with high recall
- serial sequence mostly reconstructable from evidence plus continuity
- prefecture counts exportable for the sample

