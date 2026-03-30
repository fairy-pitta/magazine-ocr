#!/usr/bin/env python3
"""Generate row crops from magazine images (layout only, no OCR content extraction).

Usage:
    python scripts/crop_rows.py [input_dir] [output_dir]
    python scripts/crop_rows.py images output/crops
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add src to path so we can import magazine_ocr
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from magazine_ocr.layout import detect_rows, split_image_into_pages
from magazine_ocr.extract import extract_page_number


def crop_rows(input_path: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = output_dir / "pages"
    rows_dir = output_dir / "rows"
    pages_dir.mkdir(exist_ok=True)
    rows_dir.mkdir(exist_ok=True)

    if input_path.is_dir():
        images = sorted(
            p for p in input_path.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
        )
    else:
        images = [input_path]

    manifest: dict = {"images": []}

    for image_path in images:
        print(f"Processing {image_path.name}...")
        image_entry: dict = {"image_id": image_path.stem, "path": str(image_path), "pages": []}

        for page in split_image_into_pages(image_path, pages_dir=pages_dir):
            page_num = extract_page_number(page)
            rows = detect_rows(page, rows_dir=rows_dir)

            page_entry: dict = {
                "side": page.page_side,
                "page_number": page_num.value,
                "crop_path": str(page.crop_path),
                "rows": [],
            }
            for row in rows:
                page_entry["rows"].append({
                    "row_index": row.row_index,
                    "crop_path": str(row.crop_path),
                    "bbox": list(row.bbox),
                })
            image_entry["pages"].append(page_entry)

            row_count = len(rows)
            print(f"  {page.page_side} (p{page_num.value}): {row_count} rows")

        manifest["images"].append(image_entry)

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    total = sum(len(r["rows"]) for img in manifest["images"] for r in img["pages"])
    print(f"\nDone: {total} row crops → {rows_dir}")
    print(f"Manifest: {manifest_path}")
    return manifest


if __name__ == "__main__":
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("images")
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output/crops")
    crop_rows(input_path, output_dir)
