# magazine-ocr

雑誌画像・PDF向けの最小OCR CLIです。  
Tesseractを使って `txt` を出力します。

## 1) Prerequisites

- Python 3.10+
- Tesseract OCR

macOS (Homebrew):

```bash
brew install tesseract tesseract-lang
```

## 2) Setup

```bash
cd /Users/wao_singapore/Projects/pitta/magazine-ocr
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## 3) Usage

画像:

```bash
magazine-ocr ./samples/page01.jpg -l jpn+eng
```

PDF:

```bash
magazine-ocr ./samples/magazine.pdf -o ./output/magazine.txt -l jpn+eng
```

`-o` を省略すると入力ファイルと同じ場所に `*.txt` を出力します。

## 4) Notes

- 文字認識精度は入力品質に依存します。
- 必要なら前処理（傾き補正・2値化）を追加して精度改善できます。

