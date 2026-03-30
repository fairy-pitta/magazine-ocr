#!/usr/bin/env python3
"""Debug row detection: save intermediate images and print diagnostics."""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def debug_detect_rows(page_crop_path: Path, debug_dir: Path) -> None:
    debug_dir.mkdir(parents=True, exist_ok=True)
    image = cv2.imread(str(page_crop_path))
    h, w = image.shape[:2]
    print(f"Image: {page_crop_path.name}  size: {w}x{h}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    cv2.imwrite(str(debug_dir / "01_gray.jpg"), gray)

    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 41, 15
    )
    cv2.imwrite(str(debug_dir / "02_binary.jpg"), binary)

    # Current kernel: max(80, w//3)
    kernel_width_current = max(80, w // 3)
    kernel_current = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width_current, 1))
    horiz_current = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_current)
    cv2.imwrite(str(debug_dir / "03_horiz_current.jpg"), horiz_current)

    # Try smaller kernels
    for kw_ratio in [4, 5, 6, 8, 10]:
        kw = max(80, w // kw_ratio)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, 1))
        horiz = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        cv2.imwrite(str(debug_dir / f"03_horiz_k{kw_ratio}.jpg"), horiz)

        contours, _ = cv2.findContours(horiz, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        lines = []
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            lines.append((x, y, cw, ch))

        print(f"\n  kernel w//{kw_ratio} = {kw}px:")
        print(f"    contours found: {len(contours)}")

        # Show all contours (sorted by y)
        for x, y, cw, ch in sorted(lines, key=lambda l: l[1]):
            pct = cw / w * 100
            tag = "✓" if cw >= w * 0.55 and ch <= 12 else " "
            tag2 = "✓h" if ch <= 12 else f" h={ch}"
            tag3 = "✓w" if cw >= w * 0.55 else f" w={pct:.0f}%"
            print(f"    {tag} y={y:4d}  w={cw:4d} ({pct:5.1f}%)  h={ch:2d}  {tag2} {tag3}")

        # Filter like current code
        filtered = [(x, y, cw, ch) for x, y, cw, ch in lines if cw >= w * 0.55 and ch <= 12]
        print(f"    → {len(filtered)} lines pass filter (w≥55%, h≤12)")

        # Try relaxed filter
        relaxed = [(x, y, cw, ch) for x, y, cw, ch in lines if cw >= w * 0.30 and ch <= 20]
        print(f"    → {len(relaxed)} lines pass relaxed (w≥30%, h≤20)")

    # Also try with different threshold methods
    print("\n--- Alternative thresholds ---")
    for block_size in [21, 31, 51, 71]:
        for C in [5, 10, 15, 20]:
            binary_alt = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, block_size, C
            )
            kw = max(80, w // 5)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, 1))
            horiz = cv2.morphologyEx(binary_alt, cv2.MORPH_OPEN, kernel)
            contours, _ = cv2.findContours(horiz, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            lines_ok = 0
            for c in contours:
                x, y, cw, ch = cv2.boundingRect(c)
                if cw >= w * 0.40 and ch <= 20:
                    lines_ok += 1

            if lines_ok >= 3:
                print(f"  ★ block={block_size} C={C}: {lines_ok} lines (w≥40%, h≤20)")
                cv2.imwrite(str(debug_dir / f"04_alt_b{block_size}_c{C}.jpg"), horiz)


if __name__ == "__main__":
    # Debug one page crop
    crop_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/crops/pages/IMG_8799_right.jpg")
    debug_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output/debug_rows")
    debug_detect_rows(crop_path, debug_dir)
