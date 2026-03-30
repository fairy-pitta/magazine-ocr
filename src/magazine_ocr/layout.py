from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from magazine_ocr.schemas import PageCrop, RowCandidate


def split_image_into_pages(
    image_path: Path,
    pages_dir: Path,
) -> list[PageCrop]:
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    image_id = image_path.stem
    pages: list[PageCrop] = []

    if width > height * 1.15:
        split_x = width // 2
        gutter = max(10, width // 80)
        crops = [
            ("right", 0, (split_x - gutter, 0, width, height)),
            ("left", 1, (0, 0, split_x + gutter, height)),
        ]
    else:
        crops = [("single", 0, (0, 0, width, height))]

    for side, page_order, bbox in crops:
        crop = image.crop(bbox)
        crop_path = pages_dir / f"{image_id}_{side}.jpg"
        crop.save(crop_path, quality=95)
        pages.append(
            PageCrop(
                image_id=image_id,
                page_side=side,
                page_order=page_order,
                bbox=bbox,
                image_path=image_path,
                crop_path=crop_path,
            )
        )

    return pages


def _detect_horizontal_lines(image: np.ndarray) -> list[int]:
    """Detect horizontal rule y-positions using multiple kernel sizes."""
    h, w = image.shape[:2]

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 41, 15,
    )

    # Try multiple kernel sizes to catch lines at different scales
    all_lines: list[int] = []
    for divisor in [5, 6, 8]:
        kernel_width = max(80, w // divisor)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 1))
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            _, y, cw, ch = cv2.boundingRect(contour)
            if cw >= int(w * 0.12) and ch <= 20:
                all_lines.append(y)

    all_lines = sorted(all_lines)
    merged: list[int] = []
    for y in all_lines:
        if not merged or abs(y - merged[-1]) > 25:
            merged.append(y)
        else:
            merged[-1] = (merged[-1] + y) // 2

    return merged


def _fill_to_target_rows(boundaries: list[int], target: int = 5) -> list[int]:
    """Split the largest gaps until we reach the target row count."""
    boundaries = sorted(set(boundaries))
    while len(boundaries) - 1 < target:
        # Find the largest gap
        max_gap = 0
        max_idx = 0
        for i in range(len(boundaries) - 1):
            gap = boundaries[i + 1] - boundaries[i]
            if gap > max_gap:
                max_gap = gap
                max_idx = i
        mid = (boundaries[max_idx] + boundaries[max_idx + 1]) // 2
        boundaries.insert(max_idx + 1, mid)
    return boundaries


def detect_rows(page: PageCrop, rows_dir: Path) -> list[RowCandidate]:
    image = cv2.imread(str(page.crop_path))
    if image is None:
        return []

    h, w = image.shape[:2]
    lines = _detect_horizontal_lines(image)

    # Skip lines in the top 8% (header area) and bottom 5%
    header_cutoff = int(h * 0.08)
    footer_cutoff = int(h * 0.95)
    lines = [y for y in lines if header_cutoff < y < footer_cutoff]

    # Build boundaries: [0, ...lines..., page_bottom]
    boundaries = [0, *lines, h - 1]

    # Remove tiny segments (header slivers < 8% of page)
    min_row_height = max(90, int(h * 0.08))
    clean: list[int] = [boundaries[0]]
    for b in boundaries[1:]:
        if b - clean[-1] >= min_row_height:
            clean.append(b)
    if clean[-1] != h - 1:
        clean.append(h - 1)
    boundaries = clean

    # Fill gaps to reach 5 rows (split largest gaps)
    target_rows = 5
    if len(boundaries) - 1 < target_rows:
        boundaries = _fill_to_target_rows(boundaries, target_rows)

    # Build row regions
    regions = [(boundaries[i], boundaries[i + 1]) for i in range(len(boundaries) - 1)]

    # If we have too many rows (>5), fall back to equal split
    if len(regions) > 5:
        return _save_equal_rows(target_rows, page, rows_dir)

    return _save_rows(regions, image, page, rows_dir)


def _save_rows(
    regions: list[tuple[int, int]],
    image: np.ndarray,
    page: PageCrop,
    rows_dir: Path,
) -> list[RowCandidate]:
    rows: list[RowCandidate] = []
    for idx, (top, bottom) in enumerate(regions):
        bbox = (0, top, image.shape[1], bottom)
        crop = image[top:bottom, :]
        crop_path = rows_dir / f"{page.image_id}_{page.page_side}_row_{idx:02d}.jpg"
        cv2.imwrite(str(crop_path), crop)
        rows.append(
            RowCandidate(
                image_id=page.image_id,
                page_side=page.page_side,
                page_number=None,
                row_index=idx,
                bbox=bbox,
                crop_path=crop_path,
            )
        )
    return rows


def _save_equal_rows(
    count: int, page: PageCrop, rows_dir: Path,
) -> list[RowCandidate]:
    page_image = Image.open(page.crop_path)
    width, height = page_image.size
    rows: list[RowCandidate] = []
    for idx in range(count):
        top = int(height * idx / count)
        bottom = int(height * (idx + 1) / count)
        bbox = (0, top, width, bottom)
        crop = page_image.crop(bbox)
        crop_path = rows_dir / f"{page.image_id}_{page.page_side}_row_{idx:02d}.jpg"
        crop.save(crop_path, quality=95)
        rows.append(
            RowCandidate(
                image_id=page.image_id,
                page_side=page.page_side,
                page_number=None,
                row_index=idx,
                bbox=bbox,
                crop_path=crop_path,
            )
        )
    return rows
