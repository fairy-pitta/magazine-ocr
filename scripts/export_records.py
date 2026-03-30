#!/usr/bin/env python3
"""Export per-entry records from annotation JSON files.

Usage:
    python scripts/export_records.py [annotations_dir] [output_csv]
    python scripts/export_records.py annotations output/records.csv
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

IMAGE_ORDER = ["IMG_8795", "IMG_8796", "IMG_8797", "IMG_8798", "IMG_8799"]


def build_serial_to_page(annotation: dict) -> dict[int, int]:
    """Map serial number → page number from a single annotation."""
    result: dict[int, int] = {}
    for page in annotation["pages"]:
        pnum = page["page_number"]
        for row in page["rows"]:
            for s in row.get("serials", []):
                result[s] = pnum
    return result


def build_serial_to_prefecture(annotation: dict) -> dict[int, str]:
    """Map serial number → prefecture from prefecture_flow."""
    result: dict[int, str] = {}
    for entry in annotation.get("prefecture_flow", []):
        pref = entry["prefecture"]
        lo, hi = entry["serial_range"]
        for s in range(lo, hi + 1):
            result[s] = pref
    return result


def load_annotations(ann_dir: Path) -> list[dict]:
    annotations = []
    for img_id in IMAGE_ORDER:
        path = ann_dir / f"{img_id}.json"
        if path.exists():
            with open(path) as f:
                annotations.append(json.load(f))
        else:
            print(f"  Warning: {path} not found, skipping", file=sys.stderr)
    return annotations


def export_records(ann_dir: Path, output_csv: Path) -> None:
    annotations = load_annotations(ann_dir)

    # Build global maps: serial → page, serial → prefecture
    serial_to_page: dict[int, int] = {}
    serial_to_pref: dict[int, str] = {}
    all_serials: set[int] = set()

    for ann in annotations:
        serial_to_page.update(build_serial_to_page(ann))
        serial_to_pref.update(build_serial_to_prefecture(ann))
        for page in ann["pages"]:
            for row in page["rows"]:
                all_serials.update(row.get("serials", []))

    # Determine serial range coverage
    if all_serials:
        full_range = range(min(all_serials), max(all_serials) + 1)
        missing = sorted(set(full_range) - all_serials)
    else:
        missing = []

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows_out = []
    for s in sorted(all_serials):
        rows_out.append({
            "serial": s,
            "prefecture": serial_to_pref.get(s, "unknown"),
            "page_number": serial_to_page.get(s, ""),
        })

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["serial", "prefecture", "page_number"])
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Exported {len(rows_out)} records → {output_csv}")

    # Summary by prefecture
    from collections import Counter
    counts = Counter(r["prefecture"] for r in rows_out)
    print("\nEntries by prefecture:")
    for pref, count in sorted(counts.items(), key=lambda x: min(
        s for s in all_serials if serial_to_pref.get(s) == x[0]
    )):
        print(f"  {pref}: {count}")

    if missing:
        print(f"\nMissing serials (pages not photographed): "
              f"☆{missing[0]}–☆{missing[-1]} ({len(missing)} entries)")


if __name__ == "__main__":
    ann_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("annotations")
    output_csv = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output/records.csv")
    export_records(ann_dir, output_csv)
