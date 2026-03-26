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


def detect_rows(page: PageCrop, rows_dir: Path) -> list[RowCandidate]:
    image = cv2.imread(str(page.crop_path))
    if image is None:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        41,
        15,
    )

    kernel_width = max(80, image.shape[1] // 3)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 1))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    lines: list[int] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w >= int(image.shape[1] * 0.55) and h <= 12:
            lines.append(y)

    lines = sorted(lines)
    merged: list[int] = []
    for y in lines:
        if not merged or abs(y - merged[-1]) > 12:
            merged.append(y)
        else:
            merged[-1] = int((merged[-1] + y) / 2)

    boundaries = [0, *merged, image.shape[0] - 1]
    rows: list[RowCandidate] = []
    row_index = 0
    for top, bottom in zip(boundaries, boundaries[1:]):
        if bottom - top < max(90, image.shape[0] // 16):
            continue

        bbox = (0, top, image.shape[1], bottom)
        crop = image[top:bottom, :]
        crop_path = rows_dir / f"{page.image_id}_{page.page_side}_row_{row_index:02d}.jpg"
        cv2.imwrite(str(crop_path), crop)
        rows.append(
            RowCandidate(
                image_id=page.image_id,
                page_side=page.page_side,
                page_number=None,
                row_index=row_index,
                bbox=bbox,
                crop_path=crop_path,
            )
        )
        row_index += 1

    if len(rows) >= 3:
        return rows

    fallback_count = 5
    page_image = Image.open(page.crop_path)
    width, height = page_image.size
    fallback_rows: list[RowCandidate] = []
    for idx in range(fallback_count):
        top = int(height * idx / fallback_count)
        bottom = int(height * (idx + 1) / fallback_count)
        bbox = (0, top, width, bottom)
        crop = page_image.crop(bbox)
        crop_path = rows_dir / f"{page.image_id}_{page.page_side}_row_{idx:02d}.jpg"
        crop.save(crop_path, quality=95)
        fallback_rows.append(
            RowCandidate(
                image_id=page.image_id,
                page_side=page.page_side,
                page_number=None,
                row_index=idx,
                bbox=bbox,
                crop_path=crop_path,
            )
        )
    return fallback_rows
