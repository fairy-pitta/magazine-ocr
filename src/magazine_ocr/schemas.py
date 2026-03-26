from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(slots=True)
class PageCrop:
    image_id: str
    page_side: str
    page_order: int
    bbox: tuple[int, int, int, int]
    image_path: Path
    crop_path: Path


@dataclass(slots=True)
class RowCandidate:
    image_id: str
    page_side: str
    page_number: int | None
    row_index: int
    bbox: tuple[int, int, int, int]
    crop_path: Path


@dataclass(slots=True)
class EntryRecord:
    image_id: str
    page_side: str
    page_order: int
    page_number: int | None
    reading_order: int
    row_index: int
    serial_number_raw: str | None
    serial_number_final: int | None
    serial_candidates: list[str] = field(default_factory=list)
    serial_confidence: float = 0.0
    prefecture_header_raw: str | None = None
    prefecture_norm: str | None = None
    prefecture_source: str = "unknown"
    prefecture_confidence: float = 0.0
    location_raw: str | None = None
    location_confidence: float = 0.0
    bbox_anchor: tuple[int, int, int, int] | None = None
    bbox_pref_header: tuple[int, int, int, int] | None = None
    bbox_row: tuple[int, int, int, int] | None = None
    needs_review: bool = False
    review_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["serial_candidates"] = "|".join(self.serial_candidates)
        data["review_reasons"] = "|".join(self.review_reasons)
        return data

