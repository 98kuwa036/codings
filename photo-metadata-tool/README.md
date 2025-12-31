# Photo Metadata Tool

Google Photo Takeout用のEXIF情報抽出・書き込みツールです。

## 機能

1. **EXIF抽出**: 画像からEXIF情報を抽出してJSONファイルに書き出し
2. **タイムスタンプ書き込み**: Google Photo TakeoutのJSONファイルから撮影日時を読み取り、画像のEXIFに書き込み
3. **GPS情報書き込み**: Google PhotoのgeoDataがあれば位置情報も書き込み

## インストール

```bash
cd photo-metadata-tool
pip install -r requirements.txt
```

## 使い方

### EXIF情報をJSONに書き出す

```bash
python photo_metadata_tool.py /path/to/photos --extract
```

各画像に対して `image.jpg.exif.json` というファイルが作成されます。

### Google Photo JSONからタイムスタンプを書き込む

```bash
python photo_metadata_tool.py /path/to/photos --write
```

Google Photo Takeoutでエクスポートされた `image.jpg.json` ファイルから `photoTakenTime` を読み取り、画像のEXIFに書き込みます。

### 両方を実行

```bash
python photo_metadata_tool.py /path/to/photos --both
```

既存のEXIF情報を保存してから、Google PhotoのタイムスタンプをEXIFに書き込みます。

### オプション

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--extract` | `-e` | EXIF情報をJSONに書き出す |
| `--write` | `-w` | Google Photo JSONからタイムスタンプを書き込む |
| `--both` | `-b` | 抽出と書き込みの両方を実行 |
| `--output-dir` | `-o` | EXIF JSONの出力先ディレクトリ |
| `--dry-run` | `-n` | 実際には書き込まない（テスト用） |
| `--verbose` | `-v` | 詳細ログを出力 |

### 使用例

```bash
# ドライラン（実際には変更しない）で確認
python photo_metadata_tool.py /path/to/Takeout/Google\ Photos --both --dry-run

# 詳細ログを出力しながら処理
python photo_metadata_tool.py /path/to/Takeout/Google\ Photos --both --verbose

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

### EXIF書き込み対応
- JPEG (.jpg, .jpeg)
- TIFF (.tiff, .tif)

※PNG, HEIC, WebPはEXIF書き込みに対応していません。これらの形式では読み取りのみ可能です。

## Google Photo Takeoutの構造

Google Photo Takeoutでエクスポートすると、以下のような構造になります：

```
Takeout/
└── Google Photos/
    ├── 2023/
    │   ├── IMG_0001.jpg
    │   ├── IMG_0001.jpg.json    # メタデータ
    │   ├── IMG_0002.heic
    │   └── IMG_0002.heic.json
    └── Albums/
        └── 旅行/
            ├── photo.jpg
            └── photo.jpg.json
```

JSONファイルには以下の情報が含まれています：

```json
{
  "title": "IMG_0001.jpg",
  "photoTakenTime": {
    "timestamp": "1672531200",
    "formatted": "2023年1月1日 12:00:00 UTC"
  },
  "geoData": {
    "latitude": 35.6812,
    "longitude": 139.7671,
    "altitude": 0.0
  }
}
```

## 注意事項

- **バックアップ推奨**: EXIF書き込みは画像ファイルを直接変更します。処理前にバックアップを取ることを推奨します。
- **ドライラン**: 初回は `--dry-run` オプションで動作確認することを推奨します。
- **HEIC対応**: HEICファイルはEXIF読み取りのみ対応。書き込みが必要な場合は事前にJPEGに変換してください。

## トラブルシューティング

### piexifインストールエラー
```bash
pip install --upgrade pip
pip install piexif
```

### Pillowインストールエラー
```bash
# Ubuntu/Debian
sudo apt-get install libjpeg-dev zlib1g-dev
pip install Pillow
```

### HEIC読み取りエラー
```bash
# HEICサポートを有効化
pip install pillow-heif
```

## ライセンス

MIT License
