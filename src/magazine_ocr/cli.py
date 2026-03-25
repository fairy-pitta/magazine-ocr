from __future__ import annotations

import argparse
from pathlib import Path

import pypdfium2 as pdfium
import pytesseract
from PIL import Image


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal OCR for images and PDFs.")
    parser.add_argument("input", type=Path, help="Input image/PDF path")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output text file path (default: input filename + .txt)",
    )
    parser.add_argument(
        "-l",
        "--lang",
        default="jpn+eng",
        help="Tesseract language(s), e.g. jpn+eng, eng",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    output_path = args.output or input_path.with_suffix(".txt")
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    text = ocr(input_path, args.lang)
    output_path.write_text(text, encoding="utf-8")
    print(f"Wrote OCR text: {output_path}")


if __name__ == "__main__":
    main()

