# Checklist

## Current State

- [x] repository initialized
- [x] minimal OCR CLI exists
- [x] current 5 sample images are available locally
- [x] baseline raw OCR was tested and confirmed insufficient for full-page extraction
- [x] page structure was visually inspected
- [x] prefecture header behavior was confirmed on `IMG_8799` right page
- [x] documentation scope for extraction was defined

## Scope Lock

- [ ] confirm the first milestone output schema
- [ ] confirm the naming convention for normalized prefectures
- [ ] confirm whether `location_raw` is required for milestone 1 or only for debug
- [ ] confirm whether `IMG_8795` should be included in milestone 1 evaluation despite layout differences

## Data Preparation

- [x] create `docs/` directory structure and keep docs up to date
- [ ] create a clean output directory plan for crops, overlays, CSV, and review artifacts
- [ ] decide how to handle untracked user image files in git workflow
- [ ] add ignores for generated artifacts if needed

## Annotation

- [ ] define minimal annotation schema
- [ ] annotate `page_number` boxes on the 5-image sample if automation is weak
- [ ] annotate `pref_header` boxes on the 5-image sample
- [ ] annotate `anchor` boxes (`☆NNN`) on the 5-image sample
- [ ] store annotations in a reproducible format

## Preprocessing

- [ ] implement spread-to-page splitting
- [ ] implement page crop extraction
- [ ] implement optional illumination normalization
- [ ] implement optional shadow-aware preprocessing
- [ ] evaluate whether pen-mark suppression is needed for `IMG_8796`

## Page Number Extraction

- [ ] implement page header crop logic
- [ ] implement page number OCR with regex validation
- [ ] record confidence and crop evidence
- [ ] verify page order across spreads

## Row Segmentation

- [ ] detect horizontal separators
- [ ] generate row candidates per logical page
- [ ] verify row ordering on the sample set
- [ ] handle cases where row boundaries are partially occluded

## Anchor Detection

- [ ] define star template extraction approach
- [ ] detect `☆NNN` candidates per row
- [ ] OCR numeric portion only
- [ ] keep alternative candidate values where uncertainty exists
- [ ] mark low-confidence anchors for review

## Prefecture Header Detection

- [ ] define expected prefecture header patterns
- [ ] restrict OCR vocabulary to prefecture-like strings
- [ ] detect header transitions in reading order
- [ ] verify block boundaries manually on sample pages

## Stateful Assignment

- [ ] assign each anchor to the active prefecture block
- [ ] persist provenance of prefecture assignment
- [ ] handle anchors before the first detected header on a page
- [ ] handle pages that continue a prefecture block started earlier

## Sequence Reconciliation

- [ ] define global reading order
- [ ] detect gaps, duplicates, and impossible jumps
- [ ] implement continuity-based repair logic
- [ ] record every auto-repair with a reason
- [ ] send unresolved anomalies to review

## Location Support

- [ ] implement local location OCR around anchors
- [ ] use location only as supporting evidence
- [ ] define fallback normalization for city or ward names
- [ ] track ambiguity when place names map to multiple prefectures

## AI Review Layer

- [ ] define structured prompt format
- [ ] define JSON schema for AI review output
- [ ] decide which cases qualify for AI review
- [ ] provide neighboring context and cropped evidence to AI
- [ ] prevent AI from overwriting high-confidence deterministic outputs
- [ ] log all AI-assisted changes

## Reporting

- [ ] export record-level CSV
- [ ] export prefecture count summary
- [ ] export serial anomaly report
- [ ] generate overlay images for audit
- [ ] create a concise review dashboard or folder structure for manual inspection

## Validation

- [ ] run end-to-end on the 5-image sample
- [ ] compare results against annotated truth
- [ ] measure anchor recall and serial exact match
- [ ] measure prefecture block accuracy
- [ ] verify aggregate prefecture counts

## Release Readiness

- [ ] document CLI commands for the extraction workflow
- [ ] document expected input and output directories
- [ ] document review procedures
- [ ] document known limitations and failure modes
