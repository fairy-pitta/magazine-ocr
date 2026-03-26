from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

from magazine_ocr.schemas import EntryRecord, PageCrop, RowCandidate


def export_records_csv(records: list[EntryRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [record.to_dict() for record in records]
    fieldnames = list(rows[0].keys()) if rows else [
        "image_id",
        "page_side",
        "page_order",
        "page_number",
        "reading_order",
        "row_index",
        "serial_number_raw",
        "serial_number_final",
        "serial_candidates",
        "serial_confidence",
        "prefecture_header_raw",
        "prefecture_norm",
        "prefecture_source",
        "prefecture_confidence",
        "location_raw",
        "location_confidence",
        "bbox_anchor",
        "bbox_pref_header",
        "bbox_row",
        "needs_review",
        "review_reasons",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_prefecture_counts(records: list[EntryRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    counter = Counter(
        record.prefecture_norm
        for record in records
        if record.prefecture_norm
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["prefecture", "count"])
        for prefecture, count in sorted(counter.items()):
            writer.writerow([prefecture, count])


def export_review_queue(records: list[EntryRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            if not record.needs_review:
                continue
            payload = {
                "image_id": record.image_id,
                "page_number": record.page_number,
                "page_side": record.page_side,
                "row_index": record.row_index,
                "serial_number_raw": record.serial_number_raw,
                "serial_candidates": record.serial_candidates,
                "prefecture_norm": record.prefecture_norm,
                "location_raw": record.location_raw,
                "review_reasons": record.review_reasons,
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def render_page_overlay(
    page: PageCrop,
    rows: list[RowCandidate],
    records: list[EntryRecord],
    path: Path,
) -> None:
    image = Image.open(page.crop_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    for row in rows:
        draw.rectangle(row.bbox, outline="gold", width=3)

    for record in records:
        if record.page_side != page.page_side or record.image_id != page.image_id:
            continue
        if record.bbox_anchor:
            draw.rectangle(record.bbox_anchor, outline="red", width=3)
        if record.bbox_pref_header:
            draw.rectangle(record.bbox_pref_header, outline="cyan", width=3)
        label = f"p={record.page_number} s={record.serial_number_final or '?'} pref={record.prefecture_norm or '?'}"
        if record.bbox_row:
            draw.text((10, record.bbox_row[1] + 5), label, fill="red")

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, quality=95)

