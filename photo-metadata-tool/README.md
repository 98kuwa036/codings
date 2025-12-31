# Photo Metadata Tool

Google Photo Takeout用のEXIF情報抽出・書き込みツールです。
**Immich対応の拡張機能付き**

## 機能

### 基本機能
1. **EXIF抽出**: 画像からEXIF情報を抽出してJSONファイルに書き出し
2. **タイムスタンプ書き込み**: Google Photo TakeoutのJSONファイルから撮影日時を読み取り、画像のEXIFに書き込み
3. **GPS情報書き込み**: Google PhotoのgeoDataがあれば位置情報も書き込み

### DNG/RAW対応
4. **DNG/RAWファイル対応**: exiftoolを使用してDNG、CR2、NEF、ARW等のRAWファイルに対応
5. **JPG→DNG EXIF同期**: 同名のJPGファイルからEXIF情報をDNG/RAWにコピー（デバイス情報照合付き）

### Immich向けスマート機能
6. **XMPサイドカー生成**: HEIC等EXIF書き込み不可のファイル用にXMPファイルを生成
7. **Live Photo検出**: 画像と動画のペアを検出してレポート
8. **重複ファイル検出**: ファイルサイズ+部分ハッシュで高速に重複を検出
9. **アルバム情報抽出**: ディレクトリ構造からアルバム情報を推測
10. **ファイル名からの日付推測**: `IMG_20231225_123456.jpg`等のパターンから日付を抽出
11. **インポートレポート生成**: Immichへのインポート前の状態を確認できるJSONレポート

## インストール

```bash
cd photo-metadata-tool
pip install -r requirements.txt

# DNG/RAWファイル対応のためexiftoolもインストール（推奨）
# Ubuntu/Debian
sudo apt install libimage-exiftool-perl

# macOS
brew install exiftool

# Windows
# https://exiftool.org/ からダウンロード
```

## 使い方

### Immichモード（推奨）

Immichにインポートする予定なら、このモードを使用してください：

```bash
python photo_metadata_tool.py /path/to/Takeout/Google\ Photos --immich
```

このモードでは以下を自動実行：
- JPG/RAWペアの検出とEXIF同期
- Live Photo検出
- 重複ファイル検出
- アルバム情報抽出
- EXIF情報の抽出と書き込み
- XMPサイドカー生成
- `immich_import_report.json` の生成

### 基本的な使い方

```bash
# EXIF情報をJSONに書き出し
python photo_metadata_tool.py /path/to/photos --extract

# Google Photo JSONからタイムスタンプを画像に書き込み
python photo_metadata_tool.py /path/to/photos --write

# 両方を実行（抽出してから書き込み）
python photo_metadata_tool.py /path/to/photos --both
```

### オプション

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--extract` | `-e` | EXIF情報をJSONに書き出す |
| `--write` | `-w` | Google Photo JSONからタイムスタンプを書き込む |
| `--both` | `-b` | 抽出と書き込みの両方を実行 |
| `--immich` | `-i` | Immich向け準備モード（全機能） |
| `--output-dir` | `-o` | EXIF JSONの出力先ディレクトリ |
| `--dry-run` | `-n` | 実際には書き込まない（テスト用） |
| `--verbose` | `-v` | 詳細ログを出力 |

### 使用例

```bash
# ドライラン（実際には変更しない）で確認
python photo_metadata_tool.py /path/to/Takeout/Google\ Photos --immich --dry-run

# 詳細ログを出力しながら処理
python photo_metadata_tool.py /path/to/Takeout/Google\ Photos --immich --verbose

# EXIF JSONを別ディレクトリに出力
python photo_metadata_tool.py /path/to/photos --extract --output-dir /path/to/backup
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
- JPEG (.jpg, .jpeg) - piexifで直接書き込み
- TIFF (.tiff, .tif) - piexifで直接書き込み
- DNG/RAW各種 - exiftoolで書き込み
- その他（HEIC、PNG等） - XMPサイドカーファイルを生成

## JPG→DNG EXIF同期機能

同じファイル名のJPGとDNGがある場合（例：`IMG_1234.jpg` と `IMG_1234.dng`）：

1. 両ファイルのデバイス情報（Make/Model）を照合
2. デバイスが一致する場合、JPGのEXIF情報をDNGにコピー
3. これにより、Google PhotoのメタデータがDNGにも適用される

## Immichインポートレポート

`--immich` モードで生成される `immich_import_report.json` には以下が含まれます：

```json
{
  "generated_at": "2024-01-01T12:00:00",
  "summary": {
    "total_files": 1000,
    "with_exif": 950,
    "without_exif": 50,
    "with_gps": 800,
    "live_photos": 30,
    "duplicates_groups": 5,
    "albums": 10,
    "date_fixed_from_filename": 20,
    "raw_synced_from_jpg": 100
  },
  "duplicates": [...],
  "albums": {...},
  "issues": [...]
}
```

## Google Photo Takeoutの構造

Google Photo Takeoutでエクスポートすると、以下のような構造になります：

```
Takeout/
└── Google Photos/
    ├── 2023/
    │   ├── IMG_0001.jpg
    │   ├── IMG_0001.jpg.json    # メタデータ
    │   ├── IMG_0001.dng         # RAWファイル（あれば）
    │   ├── IMG_0002.heic
    │   └── IMG_0002.heic.json
    └── Albums/
        └── 旅行/
            ├── photo.jpg
            └── photo.jpg.json
```

## ファイル名からの日付推測

JSONファイルがない場合、以下のパターンからファイル名から日付を推測：

- `IMG_20231225_123456.jpg` → 2023-12-25 12:34:56
- `PXL_20231225_123456.jpg` → 2023-12-25 12:34:56
- `VID_20231225_123456.mp4` → 2023-12-25 12:34:56
- `2023-12-25_12-34-56.jpg` → 2023-12-25 12:34:56
- `20231225.jpg` → 2023-12-25 00:00:00

## 注意事項

- **バックアップ推奨**: EXIF書き込みは画像ファイルを直接変更します。処理前にバックアップを取ることを推奨します。
- **ドライラン**: 初回は `--dry-run` オプションで動作確認することを推奨します。
- **exiftool**: DNG/RAWファイルのサポートにはexiftoolが必要です。

## トラブルシューティング

### exiftoolがないという警告
```bash
# Ubuntu/Debian
sudo apt install libimage-exiftool-perl

# macOS
brew install exiftool
```

### piexifインストールエラー
```bash
pip install --upgrade pip
pip install piexif
```

### HEIC読み取りエラー
```bash
# HEICサポートを有効化（オプション）
pip install pillow-heif
```

## ライセンス

MIT License
