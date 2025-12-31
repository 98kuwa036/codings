#!/usr/bin/env python3
"""
Photo Metadata Tool
Google Photo Takeout用のEXIF情報抽出・書き込みツール
Immich対応の拡張機能付き

機能:
1. 指定フォルダ以下の画像からEXIF情報をJSONに書き出し
2. Google PhotoのJSONからタイムスタンプを画像のEXIFに書き込み
3. DNG対応（exiftool使用、JPGからEXIFコピー）
4. Immich向けスマート機能
"""

import os
import sys
import json
import argparse
import logging
import hashlib
import subprocess
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass, field

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
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp', '.tiff', '.tif', '.dng', '.cr2', '.nef', '.arw', '.raf', '.orf', '.rw2'}
EXIF_WRITABLE_EXTENSIONS = {'.jpg', '.jpeg', '.tiff', '.tif'}
RAW_EXTENSIONS = {'.dng', '.cr2', '.nef', '.arw', '.raf', '.orf', '.rw2'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.3gp', '.m4v'}

# ファイル名から日付を抽出するパターン
DATE_PATTERNS = [
    # IMG_20231225_123456.jpg
    (r'(?:IMG_?|VID_?|PXL_?|DSC_?)?(\d{4})(\d{2})(\d{2})[_-]?(\d{2})(\d{2})(\d{2})', '%Y%m%d%H%M%S'),
    # 2023-12-25_12-34-56.jpg
    (r'(\d{4})-(\d{2})-(\d{2})[_\s](\d{2})-(\d{2})-(\d{2})', '%Y-%m-%d %H-%M-%S'),
    # 20231225_123456.jpg
    (r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', '%Y%m%d_%H%M%S'),
    # 2023-12-25.jpg (日付のみ)
    (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),
    # 20231225.jpg (日付のみ)
    (r'(\d{4})(\d{2})(\d{2})', '%Y%m%d'),
]


@dataclass
class PhotoPair:
    """JPG/RAWペア情報"""
    jpg_path: Optional[Path] = None
    raw_path: Optional[Path] = None
    video_path: Optional[Path] = None  # Live Photo用
    json_path: Optional[Path] = None
    device_match: bool = False


@dataclass
class ImmichReport:
    """Immichインポート用レポート"""
    total_files: int = 0
    with_exif: int = 0
    without_exif: int = 0
    with_gps: int = 0
    live_photos: int = 0
    duplicates: List[List[str]] = field(default_factory=list)
    albums: Dict[str, List[str]] = field(default_factory=dict)
    date_fixed: int = 0
    raw_synced: int = 0
    issues: List[str] = field(default_factory=list)


class ExifToolWrapper:
    """exiftoolのラッパークラス"""

    def __init__(self):
        self.available = self._check_exiftool()

    def _check_exiftool(self) -> bool:
        """exiftoolが利用可能かチェック"""
        try:
            result = subprocess.run(
                ['exiftool', '-ver'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def read_exif(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """exiftoolでEXIFを読み取り"""
        if not self.available:
            return None

        try:
            result = subprocess.run(
                ['exiftool', '-json', '-n', str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data[0] if data else None
        except Exception as e:
            logger.debug(f"exiftool read failed: {e}")
        return None

    def write_exif(self, file_path: Path, tags: Dict[str, Any], dry_run: bool = False) -> bool:
        """exiftoolでEXIFを書き込み"""
        if not self.available:
            logger.warning("exiftool not available")
            return False

        args = ['exiftool', '-overwrite_original']
        for key, value in tags.items():
            args.append(f'-{key}={value}')
        args.append(str(file_path))

        if dry_run:
            logger.info(f"[DRY RUN] Would run: {' '.join(args)}")
            return True

        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"exiftool write failed: {e}")
            return False

    def copy_exif(self, src_path: Path, dst_path: Path, dry_run: bool = False) -> bool:
        """exiftoolでEXIFをコピー"""
        if not self.available:
            logger.warning("exiftool not available for EXIF copy")
            return False

        args = [
            'exiftool',
            '-overwrite_original',
            '-TagsFromFile', str(src_path),
            '-all:all',
            '-FileModifyDate<DateTimeOriginal',
            str(dst_path)
        ]

        if dry_run:
            logger.info(f"[DRY RUN] Would copy EXIF: {src_path.name} -> {dst_path.name}")
            return True

        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                logger.info(f"Copied EXIF: {src_path.name} -> {dst_path.name}")
                return True
            else:
                logger.warning(f"EXIF copy warning: {result.stderr}")
                return result.returncode == 0
        except Exception as e:
            logger.error(f"exiftool copy failed: {e}")
            return False


class PhotoMetadataTool:
    """写真メタデータ処理クラス"""

    def __init__(self, target_dir: str, output_dir: Optional[str] = None,
                 dry_run: bool = False, verbose: bool = False,
                 immich_mode: bool = False):
        self.target_dir = Path(target_dir).resolve()
        self.output_dir = Path(output_dir).resolve() if output_dir else None
        self.dry_run = dry_run
        self.verbose = verbose
        self.immich_mode = immich_mode

        if verbose:
            logger.setLevel(logging.DEBUG)

        self.exiftool = ExifToolWrapper()
        if not self.exiftool.available:
            logger.warning("exiftool not found. DNG/RAW support will be limited.")
            logger.warning("Install with: sudo apt install libimage-exiftool-perl")

        self.stats = {
            'images_found': 0,
            'exif_extracted': 0,
            'exif_written': 0,
            'raw_synced': 0,
            'xmp_created': 0,
            'errors': 0,
            'skipped': 0
        }

        self.report = ImmichReport()

    def find_all_files(self) -> Tuple[List[Path], List[Path]]:
        """対象ディレクトリ以下の全ファイルを再帰的に検索"""
        images = []
        videos = []

        for ext in SUPPORTED_IMAGE_EXTENSIONS:
            images.extend(self.target_dir.rglob(f'*{ext}'))
            images.extend(self.target_dir.rglob(f'*{ext.upper()}'))

        for ext in VIDEO_EXTENSIONS:
            videos.extend(self.target_dir.rglob(f'*{ext}'))
            videos.extend(self.target_dir.rglob(f'*{ext.upper()}'))

        images = sorted(set(images))
        videos = sorted(set(videos))

        self.stats['images_found'] = len(images)
        self.report.total_files = len(images) + len(videos)

        logger.info(f"Found {len(images)} images and {len(videos)} videos in {self.target_dir}")
        return images, videos

    def find_images(self) -> List[Path]:
        """対象ディレクトリ以下の全画像ファイルを再帰的に検索"""
        images, _ = self.find_all_files()
        return images

    def extract_exif(self, image_path: Path) -> Optional[Dict[str, Any]]:
        """画像からEXIF情報を抽出"""
        ext = image_path.suffix.lower()

        # RAWファイルはexiftoolを使用
        if ext in RAW_EXTENSIONS:
            return self.exiftool.read_exif(image_path)

        try:
            with Image.open(image_path) as img:
                exif_data = img._getexif()

                if not exif_data:
                    logger.debug(f"No EXIF data in {image_path}")
                    return None

                readable_exif = {}
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)

                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='ignore')
                        except:
                            value = str(value)

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
            return float(value)
        else:
            try:
                json.dumps(value)
                return value
            except:
                return str(value)

    def export_exif_to_json(self, image_path: Path, exif_data: Dict[str, Any]) -> Path:
        """EXIF情報をJSONファイルに書き出し"""
        if self.output_dir:
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
        """Google Photo Takeoutの対応JSONファイルを検索"""
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
        """Google Photo TakeoutのJSONファイルをパース"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            result = {
                'title': data.get('title'),
                'description': data.get('description'),
            }

            if 'photoTakenTime' in data:
                taken_time = data['photoTakenTime']
                if 'timestamp' in taken_time:
                    result['timestamp'] = int(taken_time['timestamp'])
                    result['datetime'] = datetime.fromtimestamp(result['timestamp'])
                if 'formatted' in taken_time:
                    result['formatted'] = taken_time['formatted']
            elif 'creationTime' in data:
                creation_time = data['creationTime']
                if 'timestamp' in creation_time:
                    result['timestamp'] = int(creation_time['timestamp'])
                    result['datetime'] = datetime.fromtimestamp(result['timestamp'])

            if 'geoData' in data:
                geo = data['geoData']
                if geo.get('latitude') != 0.0 or geo.get('longitude') != 0.0:
                    result['geoData'] = {
                        'latitude': geo.get('latitude'),
                        'longitude': geo.get('longitude'),
                        'altitude': geo.get('altitude')
                    }

            # Google Photoのpeople情報（Immich用）
            if 'people' in data:
                result['people'] = [p.get('name') for p in data['people'] if p.get('name')]

            return result

        except Exception as e:
            logger.error(f"Failed to parse {json_path}: {e}")
            return None

    def extract_date_from_filename(self, filename: str) -> Optional[datetime]:
        """ファイル名から日付を抽出"""
        for pattern, date_format in DATE_PATTERNS:
            match = re.search(pattern, filename)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) >= 6:
                        date_str = f"{groups[0]}{groups[1]}{groups[2]}{groups[3]}{groups[4]}{groups[5]}"
                        return datetime.strptime(date_str, '%Y%m%d%H%M%S')
                    elif len(groups) >= 3:
                        date_str = f"{groups[0]}{groups[1]}{groups[2]}"
                        return datetime.strptime(date_str, '%Y%m%d')
                except ValueError:
                    continue
        return None

    def write_exif_datetime(self, image_path: Path, dt: datetime,
                            geo_data: Optional[Dict] = None) -> bool:
        """画像にEXIF日時情報を書き込み"""
        ext = image_path.suffix.lower()

        # RAWファイルはexiftoolを使用
        if ext in RAW_EXTENSIONS:
            return self._write_exif_with_exiftool(image_path, dt, geo_data)

        if ext not in EXIF_WRITABLE_EXTENSIONS:
            # XMPサイドカーファイルを生成
            return self._create_xmp_sidecar(image_path, dt, geo_data)

        try:
            try:
                exif_dict = piexif.load(str(image_path))
            except:
                exif_dict = {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'thumbnail': None}

            datetime_str = dt.strftime('%Y:%m:%d %H:%M:%S')
            datetime_bytes = datetime_str.encode('utf-8')

            exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = datetime_bytes
            exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = datetime_bytes
            exif_dict['0th'][piexif.ImageIFD.DateTime] = datetime_bytes

            if geo_data and geo_data.get('latitude') and geo_data.get('longitude'):
                lat = geo_data['latitude']
                lon = geo_data['longitude']
                alt = geo_data.get('altitude', 0)

                lat_deg = self._to_deg(abs(lat))
                exif_dict['GPS'][piexif.GPSIFD.GPSLatitudeRef] = 'N' if lat >= 0 else 'S'
                exif_dict['GPS'][piexif.GPSIFD.GPSLatitude] = lat_deg

                lon_deg = self._to_deg(abs(lon))
                exif_dict['GPS'][piexif.GPSIFD.GPSLongitudeRef] = 'E' if lon >= 0 else 'W'
                exif_dict['GPS'][piexif.GPSIFD.GPSLongitude] = lon_deg

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

    def _write_exif_with_exiftool(self, image_path: Path, dt: datetime,
                                   geo_data: Optional[Dict] = None) -> bool:
        """exiftoolでEXIF書き込み（RAWファイル用）"""
        datetime_str = dt.strftime('%Y:%m:%d %H:%M:%S')

        tags = {
            'DateTimeOriginal': datetime_str,
            'CreateDate': datetime_str,
            'ModifyDate': datetime_str,
        }

        if geo_data and geo_data.get('latitude') and geo_data.get('longitude'):
            lat = geo_data['latitude']
            lon = geo_data['longitude']
            tags['GPSLatitude'] = abs(lat)
            tags['GPSLatitudeRef'] = 'N' if lat >= 0 else 'S'
            tags['GPSLongitude'] = abs(lon)
            tags['GPSLongitudeRef'] = 'E' if lon >= 0 else 'W'
            if geo_data.get('altitude'):
                tags['GPSAltitude'] = abs(geo_data['altitude'])
                tags['GPSAltitudeRef'] = 'Above Sea Level' if geo_data['altitude'] >= 0 else 'Below Sea Level'

        return self.exiftool.write_exif(image_path, tags, self.dry_run)

    def _create_xmp_sidecar(self, image_path: Path, dt: datetime,
                            geo_data: Optional[Dict] = None) -> bool:
        """XMPサイドカーファイルを生成（Immich対応）"""
        xmp_path = image_path.with_suffix(image_path.suffix + '.xmp')

        datetime_str = dt.strftime('%Y-%m-%dT%H:%M:%S')

        xmp_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description
      xmlns:exif="http://ns.adobe.com/exif/1.0/"
      xmlns:xmp="http://ns.adobe.com/xap/1.0/"
      xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">
      <exif:DateTimeOriginal>{datetime_str}</exif:DateTimeOriginal>
      <xmp:CreateDate>{datetime_str}</xmp:CreateDate>
      <xmp:ModifyDate>{datetime_str}</xmp:ModifyDate>'''

        if geo_data and geo_data.get('latitude') and geo_data.get('longitude'):
            lat = geo_data['latitude']
            lon = geo_data['longitude']
            lat_ref = 'N' if lat >= 0 else 'S'
            lon_ref = 'E' if lon >= 0 else 'W'
            xmp_content += f'''
      <exif:GPSLatitude>{abs(lat)},{lat_ref}</exif:GPSLatitude>
      <exif:GPSLongitude>{abs(lon)},{lon_ref}</exif:GPSLongitude>'''

        xmp_content += '''
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>'''

        if not self.dry_run:
            with open(xmp_path, 'w', encoding='utf-8') as f:
                f.write(xmp_content)
            logger.info(f"Created XMP sidecar: {xmp_path.name}")
            self.stats['xmp_created'] += 1
        else:
            logger.info(f"[DRY RUN] Would create XMP: {xmp_path.name}")

        return True

    def _to_deg(self, value: float) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
        """小数の緯度/経度をEXIF形式（度分秒）に変換"""
        deg = int(value)
        min_float = (value - deg) * 60
        min_val = int(min_float)
        sec = int((min_float - min_val) * 60 * 10000)
        return ((deg, 1), (min_val, 1), (sec, 10000))

    def find_jpg_raw_pairs(self, images: List[Path]) -> Dict[str, PhotoPair]:
        """JPGとRAWファイルのペアを検出"""
        pairs: Dict[str, PhotoPair] = defaultdict(PhotoPair)

        for image_path in images:
            ext = image_path.suffix.lower()
            # ファイル名のベース（拡張子なし）をキーに
            base_name = image_path.stem
            key = str(image_path.parent / base_name)

            if ext in RAW_EXTENSIONS:
                pairs[key].raw_path = image_path
            elif ext in {'.jpg', '.jpeg'}:
                pairs[key].jpg_path = image_path

        # JSONファイルも紐付け
        for key, pair in pairs.items():
            if pair.jpg_path:
                pair.json_path = self.find_google_photo_json(pair.jpg_path)
            elif pair.raw_path:
                pair.json_path = self.find_google_photo_json(pair.raw_path)

        return {k: v for k, v in pairs.items() if v.raw_path and v.jpg_path}

    def find_live_photos(self, images: List[Path], videos: List[Path]) -> List[Tuple[Path, Path]]:
        """Live Photo（モーションフォト）のペアを検出"""
        live_photos = []

        # 画像ファイルのベース名をインデックス
        image_bases = {}
        for img in images:
            base = img.stem.lower()
            # Google Photoの形式: IMG_1234.jpg, IMG_1234.MP4
            # iPhoneの形式: IMG_1234.HEIC, IMG_1234.MOV
            image_bases[base] = img
            # MV接頭辞のパターン
            if base.startswith('img_'):
                mv_base = 'mv' + base[3:]
                image_bases[mv_base] = img

        for video in videos:
            base = video.stem.lower()
            if base in image_bases:
                live_photos.append((image_bases[base], video))
                logger.debug(f"Live Photo detected: {image_bases[base].name} + {video.name}")

        self.report.live_photos = len(live_photos)
        return live_photos

    def detect_duplicates(self, images: List[Path]) -> List[List[Path]]:
        """重複ファイルを検出（ファイルサイズ + 部分ハッシュ）"""
        # サイズでグループ化
        size_groups: Dict[int, List[Path]] = defaultdict(list)
        for img in images:
            try:
                size = img.stat().st_size
                size_groups[size].append(img)
            except OSError:
                continue

        duplicates = []

        for size, paths in size_groups.items():
            if len(paths) < 2:
                continue

            # 同サイズのファイル群を部分ハッシュで比較
            hash_groups: Dict[str, List[Path]] = defaultdict(list)
            for path in paths:
                try:
                    # 先頭と末尾の各64KBをハッシュ
                    with open(path, 'rb') as f:
                        head = f.read(65536)
                        f.seek(-min(65536, size), 2)
                        tail = f.read(65536)
                    file_hash = hashlib.md5(head + tail).hexdigest()
                    hash_groups[file_hash].append(path)
                except OSError:
                    continue

            for paths in hash_groups.values():
                if len(paths) > 1:
                    duplicates.append(paths)
                    logger.info(f"Duplicate detected: {[p.name for p in paths]}")

        self.report.duplicates = [[str(p) for p in group] for group in duplicates]
        return duplicates

    def extract_albums(self, images: List[Path]) -> Dict[str, List[Path]]:
        """ディレクトリ構造からアルバム情報を抽出"""
        albums: Dict[str, List[Path]] = defaultdict(list)

        for img in images:
            # Google Photo Takeoutの構造を考慮
            rel_path = img.relative_to(self.target_dir)
            parts = rel_path.parts

            # "Google Photos/アルバム名" や "Photos from 2023" などを検出
            if len(parts) > 1:
                album_name = parts[0]
                # 日付フォルダはスキップ
                if not re.match(r'^\d{4}(-\d{2})?$', album_name):
                    albums[album_name].append(img)

        self.report.albums = {k: [str(p) for p in v] for k, v in albums.items()}
        return albums

    def get_device_info(self, exif_data: Optional[Dict[str, Any]]) -> Optional[str]:
        """EXIFからデバイス情報を取得"""
        if not exif_data:
            return None

        make = exif_data.get('Make', exif_data.get('make', ''))
        model = exif_data.get('Model', exif_data.get('model', ''))

        if make or model:
            return f"{make} {model}".strip()
        return None

    def sync_jpg_to_raw(self, pairs: Dict[str, PhotoPair]) -> int:
        """JPGのEXIF情報をRAWファイルにコピー"""
        synced = 0

        for key, pair in pairs.items():
            if not pair.jpg_path or not pair.raw_path:
                continue

            # JPGのEXIFを確認
            jpg_exif = self.extract_exif(pair.jpg_path)
            if not jpg_exif:
                continue

            # RAWのEXIFを確認
            raw_exif = self.exiftool.read_exif(pair.raw_path) if self.exiftool.available else None

            # デバイス情報の照合
            jpg_device = self.get_device_info(jpg_exif)
            raw_device = self.get_device_info(raw_exif) if raw_exif else None

            if jpg_device and raw_device and jpg_device != raw_device:
                logger.debug(f"Device mismatch, skipping: {pair.jpg_path.name}")
                continue

            # EXIFをコピー
            if self.exiftool.copy_exif(pair.jpg_path, pair.raw_path, self.dry_run):
                synced += 1
                pair.device_match = True

        self.stats['raw_synced'] = synced
        self.report.raw_synced = synced
        return synced

    def run_extract(self) -> Dict[str, int]:
        """EXIF抽出モードを実行"""
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
        """EXIF書き込みモードを実行"""
        logger.info("=== EXIF Write Mode ===")
        images = self.find_images()

        for image_path in images:
            try:
                json_path = self.find_google_photo_json(image_path)
                photo_info = None

                if json_path:
                    photo_info = self.parse_google_photo_json(json_path)

                # JSONがない場合はファイル名から日付を推測
                if not photo_info or 'datetime' not in photo_info:
                    extracted_date = self.extract_date_from_filename(image_path.name)
                    if extracted_date:
                        logger.info(f"Date from filename: {image_path.name} -> {extracted_date}")
                        photo_info = photo_info or {}
                        photo_info['datetime'] = extracted_date
                        self.report.date_fixed += 1

                if not photo_info or 'datetime' not in photo_info:
                    logger.debug(f"No datetime info for {image_path}")
                    self.stats['skipped'] += 1
                    continue

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
        """抽出と書き込みの両方を実行"""
        logger.info("=== Full Processing Mode ===")
        images = self.find_images()

        for image_path in images:
            try:
                exif_data = self.extract_exif(image_path)
                if exif_data:
                    self.export_exif_to_json(image_path, exif_data)
                    self.stats['exif_extracted'] += 1

                json_path = self.find_google_photo_json(image_path)
                photo_info = None

                if json_path:
                    photo_info = self.parse_google_photo_json(json_path)

                if not photo_info or 'datetime' not in photo_info:
                    extracted_date = self.extract_date_from_filename(image_path.name)
                    if extracted_date:
                        photo_info = photo_info or {}
                        photo_info['datetime'] = extracted_date
                        self.report.date_fixed += 1

                if photo_info and 'datetime' in photo_info:
                    geo_data = photo_info.get('geoData')
                    if self.write_exif_datetime(image_path, photo_info['datetime'], geo_data):
                        self.stats['exif_written'] += 1
                        logger.info(f"Updated: {image_path.name} <- {photo_info['datetime']}")
                    else:
                        self.stats['errors'] += 1
                else:
                    self.stats['skipped'] += 1

            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
                self.stats['errors'] += 1

        return self.stats

    def run_immich_prepare(self) -> Dict[str, int]:
        """Immich向け準備モード（全機能実行）"""
        logger.info("=== Immich Preparation Mode ===")

        images, videos = self.find_all_files()

        # 1. JPG/RAWペアを検出してEXIF同期
        logger.info("Step 1: Detecting JPG/RAW pairs...")
        pairs = self.find_jpg_raw_pairs(images)
        if pairs:
            logger.info(f"Found {len(pairs)} JPG/RAW pairs")
            self.sync_jpg_to_raw(pairs)

        # 2. Live Photo検出
        logger.info("Step 2: Detecting Live Photos...")
        live_photos = self.find_live_photos(images, videos)

        # 3. 重複検出
        logger.info("Step 3: Detecting duplicates...")
        duplicates = self.detect_duplicates(images)

        # 4. アルバム情報抽出
        logger.info("Step 4: Extracting album information...")
        albums = self.extract_albums(images)

        # 5. 通常のEXIF処理
        logger.info("Step 5: Processing EXIF data...")
        for image_path in images:
            try:
                # EXIF抽出
                exif_data = self.extract_exif(image_path)
                if exif_data:
                    self.export_exif_to_json(image_path, exif_data)
                    self.stats['exif_extracted'] += 1
                    self.report.with_exif += 1
                    if 'GPSInfo' in exif_data or 'GPSLatitude' in str(exif_data):
                        self.report.with_gps += 1
                else:
                    self.report.without_exif += 1

                # EXIF書き込み
                json_path = self.find_google_photo_json(image_path)
                photo_info = self.parse_google_photo_json(json_path) if json_path else None

                if not photo_info or 'datetime' not in photo_info:
                    extracted_date = self.extract_date_from_filename(image_path.name)
                    if extracted_date:
                        photo_info = photo_info or {}
                        photo_info['datetime'] = extracted_date
                        self.report.date_fixed += 1

                if photo_info and 'datetime' in photo_info:
                    geo_data = photo_info.get('geoData')
                    if self.write_exif_datetime(image_path, photo_info['datetime'], geo_data):
                        self.stats['exif_written'] += 1
                    else:
                        self.stats['errors'] += 1
                else:
                    self.stats['skipped'] += 1
                    self.report.issues.append(f"No date info: {image_path.name}")

            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
                self.stats['errors'] += 1

        # レポート生成
        self._generate_immich_report()

        return self.stats

    def _generate_immich_report(self):
        """Immich用レポートを生成"""
        report_path = self.target_dir / 'immich_import_report.json'

        report_data = {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_files': self.report.total_files,
                'with_exif': self.report.with_exif,
                'without_exif': self.report.without_exif,
                'with_gps': self.report.with_gps,
                'live_photos': self.report.live_photos,
                'duplicates_groups': len(self.report.duplicates),
                'albums': len(self.report.albums),
                'date_fixed_from_filename': self.report.date_fixed,
                'raw_synced_from_jpg': self.report.raw_synced,
            },
            'duplicates': self.report.duplicates[:50],  # 最初の50グループ
            'albums': {k: v[:20] for k, v in list(self.report.albums.items())[:20]},  # 最初の20アルバム
            'issues': self.report.issues[:100],  # 最初の100件の問題
        }

        if not self.dry_run:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Generated Immich report: {report_path}")
        else:
            logger.info(f"[DRY RUN] Would generate report: {report_path}")

    def print_stats(self):
        """統計情報を出力"""
        print("\n" + "=" * 60)
        print("Processing Statistics")
        print("=" * 60)
        print(f"Images found:           {self.stats['images_found']}")
        print(f"EXIF extracted:         {self.stats['exif_extracted']}")
        print(f"EXIF written:           {self.stats['exif_written']}")
        print(f"RAW synced from JPG:    {self.stats['raw_synced']}")
        print(f"XMP sidecars created:   {self.stats['xmp_created']}")
        print(f"Skipped:                {self.stats['skipped']}")
        print(f"Errors:                 {self.stats['errors']}")
        print("=" * 60)

        if self.immich_mode:
            print("\nImmich-Specific Stats:")
            print("-" * 40)
            print(f"Files with EXIF:        {self.report.with_exif}")
            print(f"Files without EXIF:     {self.report.without_exif}")
            print(f"Files with GPS:         {self.report.with_gps}")
            print(f"Live Photos detected:   {self.report.live_photos}")
            print(f"Duplicate groups:       {len(self.report.duplicates)}")
            print(f"Albums detected:        {len(self.report.albums)}")
            print(f"Dates fixed from name:  {self.report.date_fixed}")
            print("-" * 40)


def main():
    parser = argparse.ArgumentParser(
        description='Photo Metadata Tool - Google Photo Takeout用EXIF処理ツール（Immich対応）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # EXIF情報をJSONに書き出し
  python photo_metadata_tool.py /path/to/photos --extract

  # Google Photo JSONからタイムスタンプを画像に書き込み
  python photo_metadata_tool.py /path/to/photos --write

  # 両方を実行（抽出してから書き込み）
  python photo_metadata_tool.py /path/to/photos --both

  # Immich向け準備モード（推奨）
  python photo_metadata_tool.py /path/to/photos --immich

  # ドライラン（実際には書き込まない）
  python photo_metadata_tool.py /path/to/photos --immich --dry-run

Immichモードの追加機能:
  - JPG/RAWペア検出とEXIF同期
  - Live Photo（モーションフォト）検出
  - 重複ファイル検出
  - アルバム情報抽出
  - ファイル名からの日付推測
  - XMPサイドカーファイル生成（HEIC等用）
  - インポートレポート生成
"""
    )

    parser.add_argument('target_dir', help='処理対象ディレクトリ')
    parser.add_argument('--extract', '-e', action='store_true',
                        help='EXIF情報をJSONに書き出す')
    parser.add_argument('--write', '-w', action='store_true',
                        help='Google Photo JSONからタイムスタンプを書き込む')
    parser.add_argument('--both', '-b', action='store_true',
                        help='抽出と書き込みの両方を実行')
    parser.add_argument('--immich', '-i', action='store_true',
                        help='Immich向け準備モード（全機能）')
    parser.add_argument('--output-dir', '-o', type=str,
                        help='EXIF JSON出力ディレクトリ')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='ドライラン')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='詳細ログ')

    args = parser.parse_args()

    if not any([args.extract, args.write, args.both, args.immich]):
        parser.error("少なくとも --extract, --write, --both, --immich のいずれかを指定してください")

    if not os.path.isdir(args.target_dir):
        parser.error(f"ディレクトリが存在しません: {args.target_dir}")

    tool = PhotoMetadataTool(
        target_dir=args.target_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        verbose=args.verbose,
        immich_mode=args.immich
    )

    if args.immich:
        tool.run_immich_prepare()
    elif args.both:
        tool.run_both()
    elif args.extract:
        tool.run_extract()
    elif args.write:
        tool.run_write()

    tool.print_stats()


if __name__ == '__main__':
    main()
