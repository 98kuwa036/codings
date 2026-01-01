# Photo Metadata Tool

Google Photo Takeout用のEXIF情報抽出・書き込みツールです。
**Immich対応の拡張機能付き（v2.0）**

## 機能一覧

### 基本機能
1. **EXIF抽出**: 画像からEXIF情報を抽出してJSONファイルに書き出し
2. **タイムスタンプ書き込み**: Google Photo TakeoutのJSONから撮影日時をEXIFに書き込み
3. **GPS情報書き込み**: geoDataがあれば位置情報も書き込み

### DNG/RAW対応
4. **DNG/RAWファイル対応**: exiftoolでDNG、CR2、NEF、ARW等に対応
5. **JPG→DNG EXIF同期**: 同名JPGからEXIFをコピー（デバイス+日時照合付き）
6. **XMPサイドカー生成**: HEIC等のEXIF書き込み不可ファイル用

### Immich向けスマート機能
7. **Live Photo検出**: 画像と動画のペアを検出
8. **重複ファイル検出**: ファイルサイズ+部分ハッシュで高速検出
9. **アルバム情報抽出**: ディレクトリ構造からアルバム情報を推測
10. **ファイル名からの日付推測**: `IMG_20231225_123456.jpg`等から日付抽出
11. **端末別統計**: どの端末で何枚撮影したかの統計レポート
12. **判別不能ファイル一覧**: デバイス・日時情報がないファイルをリスト化
13. **破損ファイル検出**: 読み取れないファイルを検出
14. **処理ログ**: 再実行時に処理済みファイルをスキップ
15. **フォルダ整理**: 年月/端末別にファイルを自動整理

## インストール

```bash
cd photo-metadata-tool
pip install -r requirements.txt

# DNG/RAWファイル対応のためexiftoolもインストール（推奨）
# Ubuntu/Debian
sudo apt install libimage-exiftool-perl

# macOS
brew install exiftool
```

## 使い方

### Immichモード（推奨）

```bash
# 基本実行
python photo_metadata_tool.py /path/to/Takeout/Google\ Photos --immich

# ドライランで確認（実際には変更しない）
python photo_metadata_tool.py /path/to/photos --immich --dry-run

# 処理済みファイルをスキップして再実行
python photo_metadata_tool.py /path/to/photos --immich --skip-processed

# 年月/端末別にファイルを整理して出力
python photo_metadata_tool.py /path/to/photos --immich --organize /path/to/output

# ファイルを移動（コピーではなく）
python photo_metadata_tool.py /path/to/photos --immich --organize /path/to/output --move
```

### 基本コマンド

```bash
# EXIF情報をJSONに書き出し
python photo_metadata_tool.py /path/to/photos --extract

# Google Photo JSONからタイムスタンプを書き込み
python photo_metadata_tool.py /path/to/photos --write

# 両方を実行
python photo_metadata_tool.py /path/to/photos --both
```

## オプション一覧

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--extract` | `-e` | EXIF情報をJSONに書き出す |
| `--write` | `-w` | Google Photo JSONからタイムスタンプを書き込む |
| `--both` | `-b` | 抽出と書き込みの両方を実行 |
| `--immich` | `-i` | Immich向け準備モード（全機能） |
| `--output-dir` | `-o` | EXIF JSONの出力先ディレクトリ |
| `--organize` | | 処理済みファイルを年月/端末別に整理して出力 |
| `--move` | | `--organize`と併用：コピーではなく移動 |
| `--skip-processed` | | 処理済みファイルをスキップ |
| `--dry-run` | `-n` | 実際には書き込まない |
| `--verbose` | `-v` | 詳細ログを出力 |

## 処理フォルダ構造

### 入力フォルダ（処理後）

処理後、元のフォルダには以下のファイルが追加されます：

```
Takeout/Google Photos/
├── 2023/
│   ├── IMG_0001.jpg
│   ├── IMG_0001.jpg.json          # Google Photoメタデータ（元からある）
│   ├── IMG_0001.jpg.exif.json     # 抽出したEXIF情報（新規作成）
│   ├── IMG_0002.heic
│   ├── IMG_0002.heic.json
│   └── IMG_0002.heic.xmp          # XMPサイドカー（HEIC用、新規作成）
├── immich_import_report.json      # インポートレポート（新規作成）
└── .photo_metadata_processed.json # 処理ログ（--skip-processed使用時）
```

### 出力フォルダ（`--organize`使用時）

```
output/
├── 2023/
│   ├── 2023-01/
│   │   ├── Google_Pixel_7/
│   │   │   ├── IMG_0001.jpg
│   │   │   ├── IMG_0001.jpg.json
│   │   │   └── IMG_0001.dng
│   │   └── Samsung_SM-G998/
│   │       └── IMG_0002.jpg
│   └── 2023-02/
│       └── ...
└── unknown_date/
    └── unknown_device/
        └── ...
```

## JPG/RAW マッチング機能

同名のJPGとDNGファイルがある場合、以下の照合を行います：

### 1. デバイス照合
```
IMG_0001.jpg (Google Pixel 7)
IMG_0001.dng (Google Pixel 7) → ✓ デバイス一致
```

### 2. 撮影日時照合（±5秒以内）
```
IMG_0001.jpg (2023-12-25 10:30:00)
IMG_0001.dng (2023-12-25 10:30:02) → ✓ 日時一致（2秒差）

IMG_0001.jpg (2023-12-25 10:30:00)
IMG_0001.dng (2023-12-25 10:35:00) → ✗ 日時不一致（5分差）
```

### 3. マッチングレポート出力
```
JPG/RAW Matching Report:
--------------------------------------------------
Total pairs found:      150
Successfully matched:   145
Device mismatch:        3
Date mismatch (>5s):    2
No EXIF data:           0
--------------------------------------------------
```

## 端末別統計

複数端末の画像がある場合、端末ごとの統計を表示：

```
Device Statistics:
--------------------------------------------------
  Google Pixel 7: 5000 files (2022-01-01 ~ 2023-12-31)
  Samsung SM-G998: 3000 files (2020-06-15 ~ 2022-05-20)
  Apple iPhone 12: 1500 files (2021-03-10 ~ 2021-12-25)
  Unknown: 50 files
--------------------------------------------------
```

## 判別不能ファイル

以下の条件をすべて満たすファイルは「判別不能」としてレポート：
- デバイス情報（Make/Model）がない
- EXIF日時情報がない
- Google Photo JSONがない（または日時情報がない）
- ファイル名に日付パターンがない

## レポート出力例

`immich_import_report.json`の内容：

```json
{
  "generated_at": "2024-01-01T12:00:00",
  "tool_version": "2.0",
  "summary": {
    "total_files": 10000,
    "with_exif": 9500,
    "without_exif": 500,
    "with_gps": 8000,
    "live_photos": 100,
    "duplicates_groups": 50,
    "albums": 20,
    "date_fixed_from_filename": 200,
    "raw_synced_from_jpg": 500,
    "corrupted_files": 5,
    "unidentifiable_files": 30
  },
  "device_statistics": {
    "Google Pixel 7": {
      "total_files": 5000,
      "with_gps": 4500,
      "date_range_start": "2022-01-01T00:00:00",
      "date_range_end": "2023-12-31T23:59:59",
      "file_types": {".jpg": 4000, ".dng": 1000}
    }
  },
  "matching_report": {
    "total_pairs": 500,
    "matched": 495,
    "device_mismatch": 3,
    "date_mismatch": 2,
    "details": [...]
  },
  "unidentifiable_files": [...],
  "corrupted_files": [...],
  "duplicates": [...],
  "albums": {...}
}
```

## 対応フォーマット

### 読み取り対応
- JPEG (.jpg, .jpeg)
- PNG (.png)
- HEIC (.heic, .heif)
- WebP (.webp)
- TIFF (.tiff, .tif)
- DNG (.dng) *exiftool必要
- CR2 (.cr2) *exiftool必要
- NEF (.nef) *exiftool必要
- ARW (.arw) *exiftool必要
- RAF (.raf) *exiftool必要
- ORF (.orf) *exiftool必要
- RW2 (.rw2) *exiftool必要

### EXIF書き込み対応
- JPEG, TIFF: piexifで直接書き込み
- DNG/RAW各種: exiftoolで書き込み
- その他（HEIC, PNG等）: XMPサイドカーファイルを生成

## 注意事項

- **バックアップ推奨**: EXIF書き込みは画像ファイルを直接変更します
- **ドライラン推奨**: 初回は `--dry-run` で動作確認してください
- **exiftool**: DNG/RAWファイルのサポートにはexiftoolが必要です

## トラブルシューティング

### exiftoolがないという警告
```bash
sudo apt install libimage-exiftool-perl  # Ubuntu/Debian
brew install exiftool                     # macOS
```

### 再実行時に同じファイルを処理したくない
```bash
python photo_metadata_tool.py /path/to/photos --immich --skip-processed
```

### 処理済みファイルを別フォルダに整理したい
```bash
python photo_metadata_tool.py /path/to/photos --immich --organize /path/to/output
```

## ライセンス

MIT License
