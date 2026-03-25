# Test Plan

## Objective

Validate that the extraction pipeline can reliably recover page number, prefecture block, and star-linked serial number from photographed magazine pages, then aggregate counts by prefecture with bounded error.

## Scope

In scope:

- page splitting
- page number extraction
- row segmentation
- star anchor detection
- serial number OCR
- prefecture header detection
- prefecture state propagation
- sequence reconciliation
- AI-assisted review behavior

Out of scope for milestone 1:

- full-text OCR correctness
- semantic interpretation of profile content
- generalization to unrelated magazine layouts

## Test Assets

Primary sample set:

- `images/IMG_8795.jpg`
- `images/IMG_8796.jpg`
- `images/IMG_8797.jpg`
- `images/IMG_8798.jpg`
- `images/IMG_8799.jpg`

Derived assets to retain during testing:

- logical page crops
- row crops
- anchor crops
- prefecture header crops
- overlay images
- extracted JSONL or CSV outputs

## Ground Truth Strategy

Use the 5 current images as a golden evaluation set.

Minimum ground truth:

- true page number per logical page
- true prefecture header positions and values where visible
- true anchor positions
- true serial numbers for each anchor

Optional ground truth:

- location raw text near anchors
- continued prefecture state across pages

## Test Categories

### 1. Preprocessing Tests

Goal:

- verify the page crops preserve the full printed area and remove enough irrelevant background

Checks:

- both logical pages are extracted from spread images
- page crops do not cut off page numbers
- page crops do not cut off bottom rows
- severe shadow does not fully erase printed text regions

Failure examples:

- gutter split shifts too far and truncates rightmost text
- page crop includes large background regions that confuse later detectors

### 2. Page Number Tests

Goal:

- ensure every logical page gets the correct page number

Checks:

- exact match of page number against manual truth
- proper ordering across spreads
- invalid OCR strings are rejected rather than accepted silently

Acceptance target:

- 100 percent exact match on the current sample

### 3. Row Segmentation Tests

Goal:

- ensure each entry row is discoverable enough to support anchor search

Checks:

- expected row count per page is approximately correct
- row order matches reading order
- row boxes overlap anchor locations

Acceptance target:

- anchor search region derived from row boxes covers nearly all true anchors

### 4. Anchor Detection Tests

Goal:

- find nearly all `☆NNN` clusters

Checks:

- anchor recall
- anchor precision
- robustness to pen marks, page curvature, and shadow

Acceptance target:

- recall above 95 percent on the golden set
- false positives low enough not to dominate review

### 5. Serial OCR Tests

Goal:

- read the digit portion of detected anchors accurately enough for sequence reconciliation

Checks:

- exact match on confident cases
- top-N candidate recall on difficult cases
- ability to flag low-confidence digits

Acceptance target:

- strong exact match on clear anchors
- high candidate coverage where exact match fails

### 6. Prefecture Header Tests

Goal:

- detect block-level prefecture markers such as `（新潟県）`

Checks:

- header recall and precision
- correct normalized prefecture value
- header ordering within pages

Acceptance target:

- no missed transitions on the 5-image sample

### 7. Stateful Assignment Tests

Goal:

- ensure each anchor receives the correct active prefecture

Checks:

- entries after a prefecture header inherit that prefecture
- entries continue the previous prefecture when no new header appears
- first entry on a page correctly continues a prior prefecture when applicable

Acceptance target:

- prefecture assignment exact match on the golden set

### 8. Sequence Reconciliation Tests

Goal:

- recover the intended serial order from noisy OCR

Checks:

- impossible jumps are flagged
- low-confidence digits are corrected when continuity strongly supports it
- duplicated serials are surfaced
- missing serials are reported

Acceptance target:

- repaired sequence matches manual truth on the golden set except explicitly unresolved anomalies

### 9. AI Review Tests

Goal:

- ensure AI assistance improves difficult cases without corrupting easy cases

Checks:

- only ambiguous cases are sent to AI
- AI receives bounded evidence, not uncontrolled context
- AI output is structured and schema-valid
- deterministic high-confidence values are preserved
- all AI edits are logged with rationale

Acceptance target:

- measurable reduction in unresolved ambiguous cases
- no increase in errors on high-confidence cases

## Metrics

Primary metrics:

- page number exact match
- anchor recall
- anchor precision
- serial exact match
- serial top-N candidate recall
- prefecture header exact match
- prefecture assignment exact match
- count accuracy by prefecture

Secondary metrics:

- number of cases sent to review
- number of cases resolved by sequence repair
- number of cases resolved by AI review
- end-to-end runtime on the sample set

## Test Execution Order

1. verify page crops manually
2. test page number extraction
3. test row segmentation
4. test anchor detection
5. test serial OCR
6. test prefecture header detection
7. test prefecture state propagation
8. test sequence reconciliation
9. test AI review gating
10. validate final prefecture counts

## Manual Review Protocol

For each failed or uncertain case, record:

- image id
- page number
- bbox crop path
- model or rule output
- expected value
- failure reason
- whether AI review corrected it

## Regression Policy

Any change that lowers one of the following should block merge until explained:

- page number exact match
- anchor recall
- prefecture assignment accuracy
- final prefecture count accuracy

## Sample-Specific Edge Cases

- `IMG_8795` has a different layout than later spreads
- `IMG_8796` contains blue pen marks on the right page
- lower-right shadows appear in later images
- some rows contain heavy vertical text density that may interfere with naive OCR

