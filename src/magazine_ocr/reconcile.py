from __future__ import annotations

from collections.abc import Iterable

from magazine_ocr.schemas import EntryRecord


def assign_prefecture_state(records: list[EntryRecord]) -> None:
    current_prefecture: str | None = None
    for record in records:
        if record.prefecture_norm:
            current_prefecture = record.prefecture_norm
            record.prefecture_source = "explicit_header"
            if record.prefecture_confidence <= 0.0:
                record.prefecture_confidence = 0.9
        elif current_prefecture:
            record.prefecture_norm = current_prefecture
            record.prefecture_source = "inferred_from_state"
            record.prefecture_confidence = max(record.prefecture_confidence, 0.6)
        else:
            record.needs_review = True
            record.review_reasons.append("missing_prefecture_state")


def reconcile_serial_sequence(records: list[EntryRecord]) -> None:
    previous_serial: int | None = None
    for record in records:
        if record.serial_number_raw and record.serial_number_raw.isdigit():
            record.serial_number_final = int(record.serial_number_raw)

        if record.serial_number_final is None:
            record.needs_review = True
            record.review_reasons.append("missing_serial")
            continue

        if previous_serial is not None:
            delta = record.serial_number_final - previous_serial
            if delta < 0:
                record.needs_review = True
                record.review_reasons.append("serial_decrease")
            elif delta > 5:
                record.needs_review = True
                record.review_reasons.append("serial_gap")

        previous_serial = record.serial_number_final


def sort_records(records: Iterable[EntryRecord]) -> list[EntryRecord]:
    return sorted(
        records,
        key=lambda record: (
            record.page_number if record.page_number is not None else 9999,
            record.page_order,
            record.row_index,
        ),
    )

