from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pypdfium2 as pdfium
import pytesseract
from PIL import Image

from magazine_ocr.pipeline import run_extraction


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}


def extract_text_from_image(path: Path, lang: str) -> str:
    with Image.open(path) as image:
        return pytesseract.image_to_string(image, lang=lang).strip()


def extract_text_from_pdf(path: Path, lang: str, scale: float = 2.0) -> str:
    pdf = pdfium.PdfDocument(str(path))
    pages_text: list[str] = []

    for idx, page in enumerate(pdf):
        pil_image = page.render(scale=scale).to_pil()
        text = pytesseract.image_to_string(pil_image, lang=lang).strip()
        header = f"--- Page {idx + 1} ---"
        pages_text.append(f"{header}\n{text}")

    return "\n\n".join(pages_text)


def ocr(path: Path, lang: str) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path, lang=lang)
    if suffix in IMAGE_SUFFIXES:
        return extract_text_from_image(path, lang=lang)
    raise ValueError(f"Unsupported file type: {suffix}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OCR and extraction tools for magazine pages.")
    subparsers = parser.add_subparsers(dest="command")

    ocr_parser = subparsers.add_parser("ocr", help="Run plain OCR on a single file")
    ocr_parser.add_argument("input", type=Path, help="Input image/PDF path")
    ocr_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output text file path (default: input filename + .txt)",
    )
    ocr_parser.add_argument(
        "-l",
        "--lang",
        default="jpn+eng",
        help="Tesseract language(s), e.g. jpn+eng, eng",
    )

    extract_parser = subparsers.add_parser("extract", help="Run structured extraction on image files")
    extract_parser.add_argument("input", type=Path, help="Input image file or directory")
    extract_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Output run directory (default: output/runs/<timestamp>)",
    )

    return parser


def parse_args() -> argparse.Namespace:
    if len(sys.argv) > 1 and sys.argv[1] not in {"ocr", "extract", "-h", "--help"}:
        sys.argv.insert(1, "ocr")
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.error("a command is required: ocr or extract")
    return args


def run_plain_ocr(input_path: Path, output_path: Path | None, lang: str) -> None:
    input_path = input_path.expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    output_path = output_path or input_path.with_suffix(".txt")
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    text = ocr(input_path, lang=lang)
    output_path.write_text(text, encoding="utf-8")
    print(f"Wrote OCR text: {output_path}")


def main() -> None:
    args = parse_args()
    if args.command == "ocr":
        run_plain_ocr(args.input, args.output, args.lang)
        return

    if args.command == "extract":
        output_root = run_extraction(args.input, args.output_dir)
        print(f"Wrote extraction outputs: {output_root}")
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
