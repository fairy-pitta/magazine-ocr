#!/usr/bin/env python3
"""Compile Claude Code readings into annotation JSON.

This script is designed to be used WITHIN a Claude Code session:

1. Generate crops:   python scripts/crop_rows.py images output/crops
2. Claude Code reads each row crop image using the Read tool
3. Claude Code calls this script to compile results:

   python scripts/claude_read.py compile output/crops/manifest.json \\
       --readings readings.json --output annotations/auto

readings.json format (what Claude Code produces):
{
  "IMG_8799": {
    "right": {
      "rows": [[146,147,148,149], [150,151,152], ...],
      "headers": [{"row": 3, "prefecture": "新潟県", "between": [157,158]}]
    },
    "left": {
      "rows": [[162,163,164], ...],
      "headers": [...]
    }
  }
}

headers の書き方:
  {"row": 3, "prefecture": "新潟県", "between": [157, 158]}
    → ☆157 と ☆158 の間にヘッダー行がある（☆158 から新潟県）

  {"row": 3, "prefecture": "新潟県", "before": 157}
    → ☆157 より前にヘッダー行がある（☆157 から新潟県）

  {"row": 3, "prefecture": "新潟県", "after": 157}
    → ☆157 より後にヘッダー行がある（☆158 から新潟県）

前の画像から都道府県が引き継がれる場合（ページ先頭にヘッダーなし）:
  row 0 に "before": <その画像の最初のシリアル番号> で明示的に書く。

  例: IMG_8799 の先頭が前の画像から引き継いで東京都の場合
  {"row": 0, "prefecture": "東京都", "before": 146}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from magazine_ocr.constants import PREFECTURES


def load_manifest(manifest_path: Path) -> dict:
    with open(manifest_path) as f:
        return json.load(f)


def build_annotation(image_id: str, manifest_entry: dict, readings_entry: dict) -> dict:
    """Build annotation JSON from manifest + Claude readings."""
    annotation: dict = {
        "image_id": image_id,
        "version": "claude-auto-v1",
        "pages": [],
    }

    for page_data in manifest_entry["pages"]:
        side = page_data["side"]
        page_number = page_data["page_number"]

        side_reading = readings_entry.get(side, {})
        row_serials = side_reading.get("rows", [])
        headers = side_reading.get("headers", [])
        # Use Claude-read page number if provided, fall back to OCR
        page_number = side_reading.get("page_number") or page_number

        # Build header lookup by row_index
        header_map: dict[int, dict] = {}
        for h in headers:
            header_map[h["row"]] = {k: v for k, v in h.items() if k != "row"}

        page_ann: dict = {
            "side": side,
            "page_number": page_number,
            "rows": [],
        }

        for i, row_data in enumerate(page_data["rows"]):
            serials = row_serials[i] if i < len(row_serials) else []
            header = header_map.get(i)
            page_ann["rows"].append({
                "row_index": row_data["row_index"],
                "serials": serials,
                "header": header,
            })

        annotation["pages"].append(page_ann)

    # Build prefecture flow
    annotation["prefecture_flow"] = build_prefecture_flow(annotation)

    # Summary
    all_serials = [s for p in annotation["pages"] for r in p["rows"] for s in r.get("serials", [])]
    annotation["summary"] = {
        "total_entries": len(all_serials),
        "serial_range": [min(all_serials), max(all_serials)] if all_serials else [],
    }

    return annotation


def build_prefecture_flow(annotation: dict) -> list[dict]:
    """Derive prefecture flow from header positions and serial numbers."""
    events: list[tuple[int, str, str]] = []  # (serial, event_type, prefecture)

    for page in annotation["pages"]:
        for row in page["rows"]:
            header = row.get("header")
            if not header or "prefecture" not in header:
                continue
            pref = header["prefecture"]
            if "before" in header:
                events.append((header["before"], "before", pref))
            elif "between" in header:
                events.append((header["between"][1], "start", pref))
            elif "after" in header:
                events.append((header["after"] + 1, "start", pref))

    events.sort(key=lambda e: e[0])
    all_serials = sorted(s for p in annotation["pages"] for r in p["rows"] for s in r.get("serials", []))
    if not all_serials:
        return []

    flow: list[dict] = []
    prev_end = all_serials[0]

    for serial, etype, pref in events:
        if etype == "before":
            start = serial
        else:
            start = serial

        if flow:
            flow[-1]["serial_range"][1] = start - 1
        elif prev_end < start:
            flow.append({"prefecture": "unknown", "serial_range": [prev_end, start - 1]})

        flow.append({"prefecture": pref, "serial_range": [start, all_serials[-1]]})

    if not flow:
        flow.append({"prefecture": "unknown", "serial_range": [all_serials[0], all_serials[-1]]})

    if flow:
        flow[-1]["serial_range"][1] = all_serials[-1]

    return flow


def compile_readings(manifest_path: Path, readings_path: Path, output_dir: Path) -> None:
    manifest = load_manifest(manifest_path)
    with open(readings_path) as f:
        readings = json.load(f)

    output_dir.mkdir(parents=True, exist_ok=True)

    for image_data in manifest["images"]:
        image_id = image_data["image_id"]
        if image_id not in readings:
            print(f"  Skip {image_id} (no readings)")
            continue

        annotation = build_annotation(image_id, image_data, readings[image_id])
        path = output_dir / f"{image_id}.json"
        with open(path, "w") as f:
            json.dump(annotation, f, indent=2, ensure_ascii=False)

        total = annotation["summary"]["total_entries"]
        sr = annotation["summary"]["serial_range"]
        print(f"  {image_id}: {total} entries (☆{sr[0]}-{sr[1]}) → {path}")


def print_reading_plan(manifest_path: Path) -> None:
    """Print a reading plan for Claude Code sessions."""
    manifest = load_manifest(manifest_path)
    print("# Reading Plan")
    print("# Read each row crop and identify ☆serial numbers + prefecture headers\n")

    for image_data in manifest["images"]:
        image_id = image_data["image_id"]
        print(f"## {image_id}")
        for page_data in image_data["pages"]:
            side = page_data["side"]
            pnum = page_data["page_number"]
            print(f"### Page {pnum} ({side})")
            for row_data in page_data["rows"]:
                print(f"  Row {row_data['row_index']}: {row_data['crop_path']}")
        print()

    # Print template
    print("\n# Output template (readings.json):")
    template: dict = {}
    for image_data in manifest["images"]:
        image_id = image_data["image_id"]
        template[image_id] = {}
        for page_data in image_data["pages"]:
            side = page_data["side"]
            n_rows = len(page_data["rows"])
            template[image_id][side] = {
                "page_number": page_data["page_number"],
                "rows": [[] for _ in range(n_rows)],
                "headers": [],
            }
    print(json.dumps(template, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/claude_read.py plan <manifest.json>")
        print("  python scripts/claude_read.py compile <manifest.json> --readings <readings.json> [--output <dir>]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "plan":
        manifest_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output/crops/manifest.json")
        print_reading_plan(manifest_path)

    elif command == "compile":
        manifest_path = Path(sys.argv[2])
        readings_path = None
        output_dir = Path("annotations/auto")

        args = sys.argv[3:]
        i = 0
        while i < len(args):
            if args[i] == "--readings":
                readings_path = Path(args[i + 1])
                i += 2
            elif args[i] == "--output":
                output_dir = Path(args[i + 1])
                i += 2
            else:
                i += 1

        if readings_path is None:
            print("Error: --readings is required")
            sys.exit(1)

        compile_readings(manifest_path, readings_path, output_dir)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
