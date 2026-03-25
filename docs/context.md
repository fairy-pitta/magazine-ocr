# Context

## Purpose

This project aims to extract structured index data from photographed magazine pages.

The immediate goal is not full OCR of all Japanese text. The immediate goal is to reconstruct:

- magazine page number
- prefecture block transitions
- serial numbers attached to star marks (`☆NNN`)
- optional raw location text near each serial number

Once those fields are available, the system can compute:

- how many star entries appear for each prefecture in the magazine
- serial number ranges per prefecture
- missing or misread serial numbers by using sequence continuity

## User Constraints

- Full manual annotation is undesirable.
- Annotation across the current 5 images is acceptable if tightly scoped.
- The system should prefer low-error extraction over aggressive automation.
- AI assistance is allowed and desired as a complement, with Claude Code considered first.

## Current Data

The current sample set contains 5 JPEG images in `images/`.

- `IMG_8795.jpg`
- `IMG_8796.jpg`
- `IMG_8797.jpg`
- `IMG_8798.jpg`
- `IMG_8799.jpg`

Observed image properties:

- magazine pages are photographed by hand, not scanned
- perspective distortion exists
- page curvature near the gutter exists
- warm paper tone and uneven lighting exist
- shadows exist, especially lower-right areas
- fingers and background fabric are visible
- `IMG_8796` contains blue pen marks on the right page

## Observed Layout Facts

These are based on direct visual inspection of the current 5 images.

### 1. Spread structure

- `IMG_8796` to `IMG_8799` are photographed two-page spreads
- page order is right-to-left Japanese magazine order
- visible page numbers include `(36)`, `(37)`, `(38)`, `(39)`, `(40)`, `(41)`, `(42)`, `(43)`
- `IMG_8795` includes page `(31)` and has a different editorial layout, but still contains star-number entries

### 2. Entry anchors

- each entry contains a stable star marker and serial number, visually of the form `☆NNN`
- the star shape is visually consistent across pages
- the number is typically 2 or 3 digits
- star anchors are easier to detect than the full surrounding text

### 3. Page segmentation cues

- long horizontal rules separate rows or entry blocks
- each page can be treated as a collection of vertically written entry boxes
- the page header line is visually distinct and should help isolate page number crops

### 4. Prefecture transition cues

- prefecture changes are explicitly marked as block-level labels
- the user indicated a clear example on `IMG_8799` right page
- visual inspection confirms a short prefecture label line such as `（新潟県）`
- this prefecture marker appears before the subsequent star-number entries in reading order

### 5. Location cues

- location text near entries may contain prefecture names, cities, wards, or combinations
- examples visually observed include city and ward names such as `目黒区`, `板橋区`, `大田区`, `長岡市`, `横浜`, `平塚市`
- this means raw location text is useful as supporting evidence, but should not be the primary prefecture source when a prefecture header is present

## Problem Reframing

This is not primarily a "read all vertical Japanese text" problem.

It is better framed as a layered structured extraction problem:

1. split spreads into logical pages
2. extract page numbers
3. detect prefecture header transitions
4. detect star-number entry anchors
5. assign each entry to the most recent prefecture header
6. use serial continuity to repair OCR errors and missing entries

## Required Outputs

At minimum, each extracted entry should produce:

- `image_id`
- `page_number`
- `page_side`
- `reading_order`
- `serial_number`
- `prefecture_header_raw`
- `prefecture_norm`
- `location_raw`
- `bbox_anchor`
- `bbox_pref_header`
- `confidence`
- `needs_review`

Aggregate outputs should include:

- count of star entries by prefecture
- serial min and max by prefecture
- list of serial gaps
- list of uncertain fields sent to review

## Key Assumptions

- serial numbers are intended to be sequential across the magazine
- prefecture headers define contiguous blocks of following entries
- right page should be processed before left page within a photographed spread
- page number OCR is easier than body text OCR
- AI assistance should only be used on bounded evidence crops and structured prompts

## Risks

- prefecture header text may be partially occluded or shaded
- serial number OCR may confuse similar digits
- the first image (`IMG_8795`) has a somewhat different layout from the others
- blue pen marks may interfere with OCR or detection on `IMG_8796`
- some entries may have location text that is truncated or ambiguous

## Non-Goals For The First Milestone

- full body-text OCR
- semantic understanding of ad or profile text
- generalized layout support for arbitrary magazines
- model fine-tuning before deterministic extraction is tested

