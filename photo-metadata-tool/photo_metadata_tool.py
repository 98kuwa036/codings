#!/usr/bin/env python3
"""
Photo Metadata Tool
Google Photo Takeout用のEXIF情報抽出・書き込みツール

機能:
1. 指定フォルダ以下の画像からEXIF情報をJSONに書き出し
2. Google PhotoのJSONからタイムスタンプを画像のEXIFに書き込み
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)

try:
    import piexif
except ImportError:
    print("Error: piexif is required. Install with: pip install piexif")
    sys.exit(1)

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 対応画像形式
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp', '.tiff', '.tif'}
EXIF_WRITABLE_EXTENSIONS = {'.jpg', '.jpeg', '.tiff', '.tif'}


class PhotoMetadataTool:
    """写真メタデータ処理クラス"""

    def __init__(self, target_dir: str, output_dir: Optional[str] = None,
                 dry_run: bool = False, verbose: bool = False):
        """
        初期化

        Args:
            target_dir: 処理対象ディレクトリ
            output_dir: JSON出力ディレクトリ（Noneの場合は画像と同じ場所）
            dry_run: ドライラン（実際に書き込まない）
            verbose: 詳細ログ出力
        """
        self.target_dir = Path(target_dir).resolve()
        self.output_dir = Path(output_dir).resolve() if output_dir else None
        self.dry_run = dry_run
        self.verbose = verbose

        if verbose:
            logger.setLevel(logging.DEBUG)

        self.stats = {
            'images_found': 0,
            'exif_extracted': 0,
            'exif_written': 0,
            'errors': 0,
            'skipped': 0
        }

    def find_images(self) -> List[Path]:
        """対象ディレクトリ以下の全画像ファイルを再帰的に検索"""
        images = []
        for ext in SUPPORTED_IMAGE_EXTENSIONS:
            images.extend(self.target_dir.rglob(f'*{ext}'))
            images.extend(self.target_dir.rglob(f'*{ext.upper()}'))

        # 重複を除去してソート
        images = sorted(set(images))
        self.stats['images_found'] = len(images)
        logger.info(f"Found {len(images)} images in {self.target_dir}")
        return images

    def extract_exif(self, image_path: Path) -> Optional[Dict[str, Any]]:
        """
        画像からEXIF情報を抽出

        Args:
            image_path: 画像ファイルパス

        Returns:
            EXIF情報の辞書（取得できない場合はNone）
        """
        try:
            with Image.open(image_path) as img:
                exif_data = img._getexif()

                if not exif_data:
                    logger.debug(f"No EXIF data in {image_path}")
                    return None

                # 読みやすい形式に変換
                readable_exif = {}
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)

                    # バイト型はデコード試行
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='ignore')
                        except:
                            value = str(value)

                    # GPSInfoの展開
                    if tag_name == 'GPSInfo' and isinstance(value, dict):
                        gps_data = {}
                        for gps_tag_id, gps_value in value.items():
                            gps_tag_name = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_data[str(gps_tag_name)] = self._serialize_value(gps_value)
                        value = gps_data
                    else:
                        value = self._serialize_value(value)

                    readable_exif[str(tag_name)] = value

                return readable_exif

        except Exception as e:
            logger.error(f"Failed to extract EXIF from {image_path}: {e}")
            return None

    def _serialize_value(self, value: Any) -> Any:
        """値をJSON互換形式にシリアライズ"""
        if isinstance(value, bytes):
            try:
                return value.decode('utf-8', errors='ignore')
            except:
                return str(value)
        elif isinstance(value, tuple):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {str(k): self._serialize_value(v) for k, v in value.items()}
        elif hasattr(value, 'numerator') and hasattr(value, 'denominator'):
            # Rational型
            return float(value)
        else:
            try:
                json.dumps(value)
                return value
            except:
                return str(value)

    def export_exif_to_json(self, image_path: Path, exif_data: Dict[str, Any]) -> Path:
        """
        EXIF情報をJSONファイルに書き出し

        Args:
            image_path: 元の画像ファイルパス
            exif_data: EXIF情報

        Returns:
            出力したJSONファイルのパス
        """
        if self.output_dir:
            # 出力ディレクトリ指定時は相対パス構造を維持
            rel_path = image_path.relative_to(self.target_dir)
            json_path = self.output_dir / rel_path.with_suffix(rel_path.suffix + '.exif.json')
            json_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            json_path = image_path.with_suffix(image_path.suffix + '.exif.json')

        output_data = {
            'source_file': str(image_path),
            'extracted_at': datetime.now().isoformat(),
            'exif': exif_data
        }

        if not self.dry_run:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Exported EXIF to {json_path}")
        else:
            logger.info(f"[DRY RUN] Would export EXIF to {json_path}")

        return json_path

    def find_google_photo_json(self, image_path: Path) -> Optional[Path]:
        """
        Google Photo Takeoutの対応JSONファイルを検索

        Google Photoのエクスポート形式：
        - image.jpg -> image.jpg.json
        - image.jpg -> image.json (一部のケース)
        - image(1).jpg -> image(1).jpg.json
        """
        # パターン1: image.jpg.json
        json_path1 = image_path.with_suffix(image_path.suffix + '.json')
        if json_path1.exists():
            return json_path1

        # パターン2: image.json（拡張子を置換）
        json_path2 = image_path.with_suffix('.json')
        if json_path2.exists():
            return json_path2

        # パターン3: 同じディレクトリ内で名前が似ているJSONを探す
        stem = image_path.stem
        for json_file in image_path.parent.glob('*.json'):
            if json_file.stem.startswith(stem):
                return json_file

        return None

    def parse_google_photo_json(self, json_path: Path) -> Optional[Dict[str, Any]]:
        """
        Google Photo TakeoutのJSONファイルをパース

        Returns:
            パースした情報（photoTakenTime等を含む辞書）
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            result = {
                'title': data.get('title'),
                'description': data.get('description'),
            }

            # photoTakenTimeの取得
            if 'photoTakenTime' in data:
                taken_time = data['photoTakenTime']
                if 'timestamp' in taken_time:
                    result['timestamp'] = int(taken_time['timestamp'])
                    result['datetime'] = datetime.fromtimestamp(result['timestamp'])
                if 'formatted' in taken_time:
                    result['formatted'] = taken_time['formatted']

            # creationTimeのフォールバック
            elif 'creationTime' in data:
                creation_time = data['creationTime']
                if 'timestamp' in creation_time:
                    result['timestamp'] = int(creation_time['timestamp'])
                    result['datetime'] = datetime.fromtimestamp(result['timestamp'])

            # geoDataの取得
            if 'geoData' in data:
                geo = data['geoData']
                if geo.get('latitude') != 0.0 or geo.get('longitude') != 0.0:
                    result['geoData'] = {
                        'latitude': geo.get('latitude'),
                        'longitude': geo.get('longitude'),
                        'altitude': geo.get('altitude')
                    }

            return result

        except Exception as e:
            logger.error(f"Failed to parse {json_path}: {e}")
            return None

    def write_exif_datetime(self, image_path: Path, dt: datetime,
                            geo_data: Optional[Dict] = None) -> bool:
        """
        画像にEXIF日時情報を書き込み

        Args:
            image_path: 画像ファイルパス
            dt: 書き込む日時
            geo_data: GPS情報（オプション）

        Returns:
            成功したかどうか
        """
        ext = image_path.suffix.lower()
        if ext not in EXIF_WRITABLE_EXTENSIONS:
            logger.warning(f"EXIF writing not supported for {ext}: {image_path}")
            return False

        try:
            # 既存のEXIFを読み込み
            try:
                exif_dict = piexif.load(str(image_path))
            except:
                exif_dict = {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'thumbnail': None}

            # 日時文字列のフォーマット
            datetime_str = dt.strftime('%Y:%m:%d %H:%M:%S')
            datetime_bytes = datetime_str.encode('utf-8')

            # DateTimeOriginal (撮影日時)
            exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = datetime_bytes

            # DateTimeDigitized (デジタル化日時)
            exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = datetime_bytes

            # DateTime (変更日時)
            exif_dict['0th'][piexif.ImageIFD.DateTime] = datetime_bytes

            # GPS情報の書き込み
            if geo_data and geo_data.get('latitude') and geo_data.get('longitude'):
                lat = geo_data['latitude']
                lon = geo_data['longitude']
                alt = geo_data.get('altitude', 0)

                # 緯度
                lat_deg = self._to_deg(abs(lat))
                exif_dict['GPS'][piexif.GPSIFD.GPSLatitudeRef] = 'N' if lat >= 0 else 'S'
                exif_dict['GPS'][piexif.GPSIFD.GPSLatitude] = lat_deg

                # 経度
                lon_deg = self._to_deg(abs(lon))
                exif_dict['GPS'][piexif.GPSIFD.GPSLongitudeRef] = 'E' if lon >= 0 else 'W'
                exif_dict['GPS'][piexif.GPSIFD.GPSLongitude] = lon_deg

                # 高度
                if alt:
                    exif_dict['GPS'][piexif.GPSIFD.GPSAltitudeRef] = 0 if alt >= 0 else 1
                    exif_dict['GPS'][piexif.GPSIFD.GPSAltitude] = (int(abs(alt) * 100), 100)

            if not self.dry_run:
                exif_bytes = piexif.dump(exif_dict)
                piexif.insert(exif_bytes, str(image_path))
                logger.debug(f"Wrote EXIF datetime {datetime_str} to {image_path}")
            else:
                logger.info(f"[DRY RUN] Would write datetime {datetime_str} to {image_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to write EXIF to {image_path}: {e}")
            return False

    def _to_deg(self, value: float) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
        """
        小数の緯度/経度をEXIF形式（度分秒）に変換
        """
        deg = int(value)
        min_float = (value - deg) * 60
        min_val = int(min_float)
        sec = int((min_float - min_val) * 60 * 10000)

        return ((deg, 1), (min_val, 1), (sec, 10000))

    def run_extract(self) -> Dict[str, int]:
        """
        EXIF抽出モードを実行
        全画像からEXIF情報を抽出してJSONに書き出す
        """
        logger.info("=== EXIF Extraction Mode ===")
        images = self.find_images()

        for image_path in images:
            try:
                exif_data = self.extract_exif(image_path)
                if exif_data:
                    self.export_exif_to_json(image_path, exif_data)
                    self.stats['exif_extracted'] += 1
                else:
                    self.stats['skipped'] += 1
            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
                self.stats['errors'] += 1

        return self.stats

    def run_write(self) -> Dict[str, int]:
        """
        EXIF書き込みモードを実行
        Google Photo JSONからタイムスタンプを読み取り、画像に書き込む
        """
        logger.info("=== EXIF Write Mode ===")
        images = self.find_images()

        for image_path in images:
            try:
                # 対応するGoogle Photo JSONを検索
                json_path = self.find_google_photo_json(image_path)
                if not json_path:
                    logger.debug(f"No Google Photo JSON found for {image_path}")
                    self.stats['skipped'] += 1
                    continue

                # JSONをパース
                photo_info = self.parse_google_photo_json(json_path)
                if not photo_info or 'datetime' not in photo_info:
                    logger.warning(f"No datetime in {json_path}")
                    self.stats['skipped'] += 1
                    continue

                # EXIF書き込み
                geo_data = photo_info.get('geoData')
                if self.write_exif_datetime(image_path, photo_info['datetime'], geo_data):
                    self.stats['exif_written'] += 1
                    logger.info(f"Updated: {image_path.name} <- {photo_info['datetime']}")
                else:
                    self.stats['errors'] += 1

            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
                self.stats['errors'] += 1

        return self.stats

    def run_both(self) -> Dict[str, int]:
        """
        抽出と書き込みの両方を実行
        """
        logger.info("=== Full Processing Mode ===")
        images = self.find_images()

        for image_path in images:
            try:
                # 1. 既存のEXIF情報を抽出・保存
                exif_data = self.extract_exif(image_path)
                if exif_data:
                    self.export_exif_to_json(image_path, exif_data)
                    self.stats['exif_extracted'] += 1

                # 2. Google Photo JSONがあればタイムスタンプを書き込み
                json_path = self.find_google_photo_json(image_path)
                if json_path:
                    photo_info = self.parse_google_photo_json(json_path)
                    if photo_info and 'datetime' in photo_info:
                        geo_data = photo_info.get('geoData')
                        if self.write_exif_datetime(image_path, photo_info['datetime'], geo_data):
                            self.stats['exif_written'] += 1
                            logger.info(f"Updated: {image_path.name} <- {photo_info['datetime']}")
                        else:
                            self.stats['errors'] += 1
                    else:
                        self.stats['skipped'] += 1
                else:
                    self.stats['skipped'] += 1

            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
                self.stats['errors'] += 1

        return self.stats

    def print_stats(self):
        """統計情報を出力"""
        print("\n" + "=" * 50)
        print("Processing Statistics")
        print("=" * 50)
        print(f"Images found:     {self.stats['images_found']}")
        print(f"EXIF extracted:   {self.stats['exif_extracted']}")
        print(f"EXIF written:     {self.stats['exif_written']}")
        print(f"Skipped:          {self.stats['skipped']}")
        print(f"Errors:           {self.stats['errors']}")
        print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description='Photo Metadata Tool - Google Photo Takeout用EXIF処理ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # EXIF情報をJSONに書き出し
  python photo_metadata_tool.py /path/to/photos --extract

  # Google Photo JSONからタイムスタンプを画像に書き込み
  python photo_metadata_tool.py /path/to/photos --write

  # 両方を実行（抽出してから書き込み）
  python photo_metadata_tool.py /path/to/photos --both

  # ドライラン（実際には書き込まない）
  python photo_metadata_tool.py /path/to/photos --both --dry-run

  # EXIF JSONを別ディレクトリに出力
  python photo_metadata_tool.py /path/to/photos --extract --output-dir /path/to/output
"""
    )

    parser.add_argument('target_dir', help='処理対象ディレクトリ')
    parser.add_argument('--extract', '-e', action='store_true',
                        help='EXIF情報をJSONに書き出す')
    parser.add_argument('--write', '-w', action='store_true',
                        help='Google Photo JSONからタイムスタンプを書き込む')
    parser.add_argument('--both', '-b', action='store_true',
                        help='抽出と書き込みの両方を実行')
    parser.add_argument('--output-dir', '-o', type=str,
                        help='EXIF JSON出力ディレクトリ（省略時は画像と同じ場所）')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='ドライラン（実際には書き込まない）')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='詳細ログを出力')

    args = parser.parse_args()

    # 引数チェック
    if not any([args.extract, args.write, args.both]):
        parser.error("少なくとも --extract, --write, --both のいずれかを指定してください")

    if not os.path.isdir(args.target_dir):
        parser.error(f"ディレクトリが存在しません: {args.target_dir}")

    # ツール実行
    tool = PhotoMetadataTool(
        target_dir=args.target_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    if args.both:
        tool.run_both()
    elif args.extract:
        tool.run_extract()
    elif args.write:
        tool.run_write()

    tool.print_stats()


if __name__ == '__main__':
    main()
