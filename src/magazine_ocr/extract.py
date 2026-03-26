from __future__ import annotations

import re
from dataclasses import dataclass

import cv2
import numpy as np
import pytesseract
from PIL import Image

from magazine_ocr.constants import PREFECTURES
from magazine_ocr.schemas import PageCrop, RowCandidate


STRICT_PAGE_NUMBER_RE = re.compile(r"\(\s*(\d{1,3})\s*\)")
PAGE_NUMBER_RE = re.compile(r"\(?\s*(\d{1,3})\s*\)?")
SERIAL_RE = re.compile(r"(?<!\d)(\d{1,3})(?!\d)")


@dataclass(slots=True)
class PageNumberResult:
    value: int | None
    text: str
    confidence: float


@dataclass(slots=True)
class RowExtraction:
    serial_raw: str | None
    serial_candidates: list[str]
    serial_confidence: float
    prefecture_header_raw: str | None
    prefecture_norm: str | None
    prefecture_confidence: float
    location_raw: str | None
    location_confidence: float
    anchor_bbox: tuple[int, int, int, int] | None
    pref_bbox: tuple[int, int, int, int] | None
    raw_text: str


def _ocr_text(image: Image.Image, *, lang: str, config: str) -> str:
    return pytesseract.image_to_string(image, lang=lang, config=config).strip()


def _preprocess_binary(image: Image.Image, *, invert: bool = False, scale: int = 2) -> Image.Image:
    gray = image.convert("L")
    if scale > 1:
        gray = gray.resize((gray.width * scale, gray.height * scale), Image.Resampling.LANCZOS)
    np_img = cv2.cvtColor(np.array(gray), cv2.COLOR_GRAY2BGR)
    gray_np = cv2.cvtColor(np_img, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(
        gray_np,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        41,
        15,
    )
    if invert:
        binary = 255 - binary
    return Image.fromarray(binary)


def extract_page_number(page: PageCrop) -> PageNumberResult:
    image = Image.open(page.crop_path).convert("RGB")
    width, height = image.size
    side_specific = [
        image.crop((int(width * 0.62), 0, width, int(height * 0.07))),
        image.crop((0, 0, int(width * 0.38), int(height * 0.07))),
    ]
    if page.page_side == "left":
        side_specific.reverse()

    header_crops = side_specific + [
        image.crop((int(width * 0.18), 0, int(width * 0.82), int(height * 0.07))),
    ]

    texts: list[str] = []
    candidates: list[int] = []
    for header in header_crops:
        variants = [
            header,
            _preprocess_binary(header, scale=3),
            _preprocess_binary(header, invert=True, scale=3),
        ]
        for variant in variants:
            large = variant.resize((variant.width * 4, variant.height * 4), Image.Resampling.LANCZOS)
            for config in [
                "--psm 11 -c tessedit_char_whitelist=()0123456789",
                "--psm 7 -c tessedit_char_whitelist=()0123456789",
            ]:
                text = _ocr_text(
                    large,
                    lang="eng",
                    config=config,
                )
                texts.append(text)
                for match in STRICT_PAGE_NUMBER_RE.finditer(text):
                    digits = match.group(1)
                    if len(digits) >= 2:
                        candidates.append(int(digits))

    if candidates:
        best = max(set(candidates), key=lambda value: (candidates.count(value), value))
        return PageNumberResult(
            value=best,
            text=" ".join(texts),
            confidence=0.9,
        )

    compact = " ".join(texts)
    match = STRICT_PAGE_NUMBER_RE.search(compact)
    if match and len(match.group(1)) >= 2:
        return PageNumberResult(value=int(match.group(1)), text=compact, confidence=0.7)

    return PageNumberResult(value=None, text=compact, confidence=0.0)


def _extract_prefecture(text: str) -> tuple[str | None, float]:
    for prefecture in PREFECTURES:
        if prefecture in text:
            return prefecture, 0.9
    return None, 0.0


def _extract_serial_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for match in SERIAL_RE.finditer(text):
        value = match.group(1)
        if len(value) == 1:
            continue
        if value not in candidates:
            candidates.append(value)
    return candidates


def _ocr_variants(image: Image.Image, *, mode: str) -> list[str]:
    if mode == "anchor":
        variants = [
            (image.rotate(90, expand=True), "eng", "--psm 6 -c tessedit_char_whitelist=0123456789()"),
            (_preprocess_binary(image.rotate(90, expand=True), scale=2), "eng", "--psm 6 -c tessedit_char_whitelist=0123456789()"),
            (image, "jpn_vert+eng", "--psm 5"),
        ]
    else:
        variants = [
            (image, "jpn_vert+eng", "--psm 5"),
            (_preprocess_binary(image, scale=2), "jpn_vert+eng", "--psm 5"),
            (image.rotate(90, expand=True), "jpn+eng", "--psm 6"),
        ]

    texts: list[str] = []
    seen: set[str] = set()
    for variant, lang, config in variants:
        text = _ocr_text(variant, lang=lang, config=config)
        text = text.strip()
        if text and text not in seen:
            seen.add(text)
            texts.append(text)
    return texts


def extract_row_fields(row: RowCandidate) -> RowExtraction:
    image = Image.open(row.crop_path).convert("RGB")
    width, height = image.size

    top_band = image.crop((0, 0, width, int(height * 0.62)))
    pref_region = image.crop((0, 0, int(width * 0.50), int(height * 0.62)))
    anchor_region = image.crop((int(width * 0.55), 0, width, int(height * 0.62)))

    row_texts = _ocr_variants(top_band, mode="row")
    pref_texts = _ocr_variants(pref_region, mode="row")
    anchor_texts = _ocr_variants(anchor_region, mode="anchor")
    combined_text = "\n".join(anchor_texts + pref_texts + row_texts)

    prefecture_header_raw = None
    prefecture_norm, prefecture_confidence = _extract_prefecture("\n".join(pref_texts + row_texts))
    if prefecture_norm:
        prefecture_header_raw = prefecture_norm

    serial_candidates = _extract_serial_candidates("\n".join(anchor_texts))
    if not serial_candidates:
        serial_candidates = _extract_serial_candidates(combined_text)

    serial_raw = serial_candidates[0] if serial_candidates else None
    serial_confidence = 0.8 if serial_raw else 0.0
    if len(serial_candidates) > 1:
        serial_confidence = 0.55

    location_raw = None
    location_confidence = 0.0
    for text in row_texts:
        cleaned = re.sub(r"\s+", "", text)
        if cleaned:
            location_raw = cleaned[:80]
            location_confidence = 0.35
            break

    anchor_bbox = (
        int(width * 0.55),
        0,
        width,
        int(height * 0.62),
    )
    pref_bbox = (0, 0, int(width * 0.50), int(height * 0.62)) if prefecture_norm else None

    return RowExtraction(
        serial_raw=serial_raw,
        serial_candidates=serial_candidates,
        serial_confidence=serial_confidence,
        prefecture_header_raw=prefecture_header_raw,
        prefecture_norm=prefecture_norm,
        prefecture_confidence=prefecture_confidence,
        location_raw=location_raw,
        location_confidence=location_confidence,
        anchor_bbox=anchor_bbox,
        pref_bbox=pref_bbox,
        raw_text=combined_text,
    )
