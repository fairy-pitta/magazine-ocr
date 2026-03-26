from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from magazine_ocr.extract import extract_page_number, extract_row_fields
from magazine_ocr.layout import detect_rows, split_image_into_pages
from magazine_ocr.reconcile import assign_prefecture_state, reconcile_serial_sequence, sort_records
from magazine_ocr.report import (
    export_prefecture_counts,
    export_records_csv,
    export_review_queue,
    render_page_overlay,
)
from magazine_ocr.schemas import EntryRecord


def _iter_inputs(input_path: Path) -> list[Path]:
    if input_path.is_dir():
        return sorted(
            path
            for path in input_path.iterdir()
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
        )
    return [input_path]


def _offset_bbox(
    bbox: tuple[int, int, int, int] | None,
    row_bbox: tuple[int, int, int, int],
) -> tuple[int, int, int, int] | None:
    if bbox is None:
        return None
    left, top, right, bottom = bbox
    row_left, row_top, _, _ = row_bbox
    return (left + row_left, top + row_top, right + row_left, bottom + row_top)


def _infer_missing_page_numbers(records: list[EntryRecord]) -> None:
    by_image: dict[str, list[EntryRecord]] = {}
    for record in records:
        by_image.setdefault(record.image_id, []).append(record)

    for image_records in by_image.values():
        by_side: dict[str, list[EntryRecord]] = {}
        for record in image_records:
            by_side.setdefault(record.page_side, []).append(record)

        right_number = next((record.page_number for record in by_side.get("right", []) if record.page_number is not None), None)
        left_number = next((record.page_number for record in by_side.get("left", []) if record.page_number is not None), None)

        if right_number is not None and left_number is None:
            for record in by_side.get("left", []):
                record.page_number = right_number + 1
                record.review_reasons = [reason for reason in record.review_reasons if reason != "missing_page_number"]
                record.needs_review = bool(record.review_reasons)
        if left_number is not None and right_number is None:
            for record in by_side.get("right", []):
                record.page_number = left_number - 1
                record.review_reasons = [reason for reason in record.review_reasons if reason != "missing_page_number"]
                record.needs_review = bool(record.review_reasons)


def _image_sort_key(image_id: str) -> tuple[int, str]:
    match = re.search(r"(\d+)$", image_id)
    return (int(match.group(1)) if match else 0, image_id)


def _reconcile_spread_page_numbers(records: list[EntryRecord]) -> None:
    grouped: dict[str, dict[str, int | None]] = {}
    for record in records:
        sides = grouped.setdefault(record.image_id, {"right": None, "left": None, "single": None})
        if record.page_side in sides and record.page_number is not None:
            sides[record.page_side] = record.page_number

    spread_ids = [
        image_id
        for image_id, sides in grouped.items()
        if sides["single"] is None
    ]
    spread_ids.sort(key=_image_sort_key)

    for index in range(1, len(spread_ids) - 1):
        current_id = spread_ids[index]
        prev_id = spread_ids[index - 1]
        next_id = spread_ids[index + 1]

        prev_right = grouped[prev_id]["right"]
        next_right = grouped[next_id]["right"]
        if prev_right is None or next_right is None:
            continue
        if next_right - prev_right != 4:
            continue

        expected_right = prev_right + 2
        current_right = grouped[current_id]["right"]
        current_left = grouped[current_id]["left"]

        should_rewrite = current_right is None or abs(current_right - expected_right) > 1
        if current_left is not None and current_left != expected_right + 1:
            should_rewrite = True
        if not should_rewrite:
            continue

        for record in records:
            if record.image_id != current_id:
                continue
            if record.page_side == "right":
                record.page_number = expected_right
            elif record.page_side == "left":
                record.page_number = expected_right + 1
            record.review_reasons = [reason for reason in record.review_reasons if reason != "missing_page_number"]
            record.needs_review = bool(record.review_reasons)


def run_extraction(input_path: Path, output_root: Path | None = None) -> Path:
    input_path = input_path.expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_root = output_root or input_path.parent / "output" / "runs" / run_id
    output_root = output_root.expanduser().resolve()

    pages_dir = output_root / "pages"
    rows_dir = output_root / "rows"
    overlays_dir = output_root / "overlays"
    exports_dir = output_root / "exports"
    review_dir = output_root / "review"
    for directory in [pages_dir, rows_dir, overlays_dir, exports_dir, review_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    records: list[EntryRecord] = []
    page_rows_map: dict[tuple[str, str], list] = {}
    pages = []
    for image_path in _iter_inputs(input_path):
        for page in split_image_into_pages(image_path, pages_dir=pages_dir):
            pages.append(page)
            page_number_result = extract_page_number(page)
            rows = detect_rows(page, rows_dir=rows_dir)
            page_rows_map[(page.image_id, page.page_side)] = rows
            for row in rows:
                row.page_number = page_number_result.value
                extracted = extract_row_fields(row)
                record = EntryRecord(
                    image_id=row.image_id,
                    page_side=row.page_side,
                    page_order=page.page_order,
                    page_number=page_number_result.value,
                    reading_order=0,
                    row_index=row.row_index,
                    serial_number_raw=extracted.serial_raw,
                    serial_number_final=None,
                    serial_candidates=extracted.serial_candidates,
                    serial_confidence=extracted.serial_confidence,
                    prefecture_header_raw=extracted.prefecture_header_raw,
                    prefecture_norm=extracted.prefecture_norm,
                    prefecture_source="explicit_header" if extracted.prefecture_norm else "unknown",
                    prefecture_confidence=extracted.prefecture_confidence,
                    location_raw=extracted.location_raw,
                    location_confidence=extracted.location_confidence,
                    bbox_anchor=_offset_bbox(extracted.anchor_bbox, row.bbox),
                    bbox_pref_header=_offset_bbox(extracted.pref_bbox, row.bbox),
                    bbox_row=row.bbox,
                )
                if page_number_result.value is None:
                    record.needs_review = True
                    record.review_reasons.append("missing_page_number")
                if not record.serial_candidates:
                    record.needs_review = True
                    record.review_reasons.append("missing_serial_candidate")
                records.append(record)

    _infer_missing_page_numbers(records)
    _reconcile_spread_page_numbers(records)
    ordered_records = sort_records(records)
    for index, record in enumerate(ordered_records):
        record.reading_order = index

    assign_prefecture_state(ordered_records)
    reconcile_serial_sequence(ordered_records)

    export_records_csv(ordered_records, exports_dir / "records.csv")
    export_prefecture_counts(ordered_records, exports_dir / "prefecture_counts.csv")
    export_review_queue(ordered_records, review_dir / "review_queue.jsonl")

    for page in pages:
        page_records = [
            record
            for record in ordered_records
            if record.image_id == page.image_id and record.page_side == page.page_side
        ]
        rows = page_rows_map[(page.image_id, page.page_side)]
        render_page_overlay(
            page,
            rows,
            page_records,
            overlays_dir / f"{page.image_id}_{page.page_side}.jpg",
        )

    return output_root
