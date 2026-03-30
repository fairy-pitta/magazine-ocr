# magazine-ocr

手撮り雑誌画像から **☆シリアル番号 + 都道府県** を抽出して集計するパイプラインです。

## 前提

- Python 3.10+
- Tesseract OCR（ページ番号抽出にのみ使用）
- Claude Code サブスクリプション（行クロップの読み取りに使用）

```bash
brew install tesseract tesseract-lang
```

## セットアップ

```bash
cd /Users/wao_singapore/Projects/pitta/magazine-ocr
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## パイプライン概要

Tesseract OCR は手撮り縦書き日本語に対して精度が出ないため、コンテンツ抽出には使いません。
代わりに Claude Code の画像読み取り機能を活用した **A→B→C→D** の4段階フローを採用しています。

```
images/          行クロップ生成      Claude読み取り     アノテーション化     レコード出力
IMG_8795.jpg  →  (A) crop_rows  →  (B) 手動読み取り →  (C) compile     →  (D) export
IMG_8796.jpg        ↓                     ↓                  ↓                  ↓
...            output/crops/        readings.json      annotations/       output/records.csv
               manifest.json                           IMG_8795.json 等
```

## A: 行クロップ生成

```bash
python scripts/crop_rows.py images output/crops
```

**何をするか:**
- 各画像を見開き左右のページに分割
- 各ページの水平罫線を検出し、行ごとにクロップ画像を生成
- ページ番号を Tesseract で抽出（数字パターンのみなので精度高）
- すべての情報を `output/crops/manifest.json` にまとめる

**出力:**
```
output/crops/
  manifest.json          # 画像・ページ・行のメタデータ一覧
  pages/                 # ページクロップ画像
  rows/                  # 行クロップ画像（Claude が読む対象）
```

## B: Claude Code による行クロップの読み取り

まずリーディングプラン（どの画像ファイルを読むべきか一覧）を表示します：

```bash
python scripts/claude_read.py plan output/crops/manifest.json
```

次に **この Claude Code セッション内で** Read ツールを使って各行クロップ画像を読み、
以下の形式の `readings.json` を作成します：

```json
{
  "IMG_8799": {
    "right": {
      "page_number": 41,
      "rows": [
        [146, 147, 148, 149],
        [150, 151, 152],
        ...
      ],
      "headers": [
        {"row": 3, "prefecture": "新潟県", "between": [157, 158]}
      ]
    },
    "left": {
      "page_number": 40,
      "rows": [...],
      "headers": [...]
    }
  }
}
```

- `rows`: 各行に含まれる☆シリアル番号のリスト（行インデックス順）
- `headers`: 都道府県ヘッダー行の情報
  - `row`: 何行目に出現したか
  - `prefecture`: 都道府県名
  - `before`/`between`/`after`: どのシリアル番号の前後に現れたか

## C: アノテーションのコンパイル

```bash
python scripts/claude_read.py compile output/crops/manifest.json \
    --readings readings.json --output annotations/auto
```

**何をするか:**
- `manifest.json`（構造情報）と `readings.json`（Claude の読み取り結果）を統合
- 都道府県ヘッダーの位置から都道府県フロー（どのシリアル番号がどの都道府県か）を構築
- 画像ごとに `annotations/auto/IMG_XXXX.json` を出力

**出力例 (`IMG_8799.json` の抜粋):**
```json
{
  "image_id": "IMG_8799",
  "pages": [...],
  "prefecture_flow": [
    {"prefecture": "長野県", "serial_range": [146, 157]},
    {"prefecture": "新潟県", "serial_range": [158, 175]}
  ],
  "summary": {
    "total_entries": 28,
    "serial_range": [146, 175]
  }
}
```

## D: レコードエクスポート

```bash
python scripts/export_records.py annotations output/records.csv
```

**何をするか:**
- 全アノテーション（5画像分）を統合
- シリアル番号ごとに `都道府県` + `ページ番号` を確定
- `output/records.csv` を出力
- 都道府県別集計サマリーをターミナルに表示
- ☆番号の抜けがある場合はその範囲も報告

**出力 (`records.csv`):**
```
serial,prefecture,page_number
1,東京都,31
2,東京都,31
...
175,新潟県,41
```

## 対象データ

| 画像 | ページ | 備考 |
|---|---|---|
| IMG_8795.jpg | 未確認 | 単ページ・レイアウト異なる可能性あり |
| IMG_8796.jpg | 未確認 | 青ペンマークあり |
| IMG_8797.jpg | 未確認 | |
| IMG_8798.jpg | 未確認 | |
| IMG_8799.jpg | 40-41 | アノテーション完了 |

☆シリアル番号の範囲: ☆1〜☆175（全9ページ、122エントリ確認済み）

## ディレクトリ構成

```
images/                  # 入力画像（git管理外）
annotations/             # 人手またはClaude生成のアノテーション
  auto/                  # claude_read.py compile の出力
scripts/
  crop_rows.py           # ステップA: 行クロップ生成
  claude_read.py         # ステップB+C: リーディングプラン表示・コンパイル
  export_records.py      # ステップD: レコードエクスポート
  debug_rows.py          # 行検出のデバッグ用
src/magazine_ocr/
  layout.py              # ページ分割・行検出
  extract.py             # ページ番号抽出（Tesseract）
output/                  # 実行結果（git管理外）
docs/                    # 設計・計画ドキュメント
```

## 旧コマンド（非推奨）

```bash
# Tesseract ベースの旧パイプライン（精度が出ないため現在は使用していない）
magazine-ocr extract ./images
```
