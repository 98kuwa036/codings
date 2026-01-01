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
5. 処理済みファイルの整理・出力機能
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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum

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
    (r'(?:IMG_?|VID_?|PXL_?|DSC_?)?(\d{4})(\d{2})(\d{2})[_-]?(\d{2})(\d{2})(\d{2})', '%Y%m%d%H%M%S'),
    (r'(\d{4})-(\d{2})-(\d{2})[_\s](\d{2})-(\d{2})-(\d{2})', '%Y-%m-%d %H-%M-%S'),
    (r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', '%Y%m%d_%H%M%S'),
    (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),
    (r'(\d{4})(\d{2})(\d{2})', '%Y%m%d'),
]

# 処理ログファイル名
PROCESSING_LOG_FILE = '.photo_metadata_processed.json'


class MatchStatus(Enum):
    """マッチング状態"""
    MATCHED = "matched"
    DEVICE_MISMATCH = "device_mismatch"
    DATE_MISMATCH = "date_mismatch"
    NO_EXIF = "no_exif"
    UNIDENTIFIABLE = "unidentifiable"


@dataclass
class PhotoPair:
    """JPG/RAWペア情報"""
    jpg_path: Optional[Path] = None
    raw_path: Optional[Path] = None
    video_path: Optional[Path] = None
    json_path: Optional[Path] = None
    device_match: bool = False
    date_match: bool = False
    match_status: MatchStatus = MatchStatus.UNIDENTIFIABLE
    jpg_device: Optional[str] = None
    raw_device: Optional[str] = None
    jpg_datetime: Optional[datetime] = None
    raw_datetime: Optional[datetime] = None


@dataclass
class FileInfo:
    """ファイル情報"""
    path: str
    device: Optional[str] = None
    datetime: Optional[str] = None
    has_gps: bool = False
    has_exif: bool = False
    is_corrupted: bool = False
    error_message: Optional[str] = None


@dataclass
class DeviceStats:
    """端末別統計"""
    device_name: str
    total_files: int = 0
    with_gps: int = 0
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    file_types: Dict[str, int] = field(default_factory=dict)


@dataclass
class MatchingReport:
    """マッチングレポート"""
    total_pairs: int = 0
    matched: int = 0
    device_mismatch: int = 0
    date_mismatch: int = 0
    no_exif: int = 0
    details: List[Dict[str, Any]] = field(default_factory=list)


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
    device_stats: Dict[str, Dict] = field(default_factory=dict)
    matching_report: Dict[str, Any] = field(default_factory=dict)
    unidentifiable_files: List[Dict[str, Any]] = field(default_factory=list)
    corrupted_files: List[Dict[str, Any]] = field(default_factory=list)


class ProcessingLog:
    """処理ログ管理"""

    def __init__(self, target_dir: Path):
        self.log_path = target_dir / PROCESSING_LOG_FILE
        self.processed: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        """ログを読み込み"""
        if self.log_path.exists():
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed = data.get('processed', {})
                logger.info(f"Loaded processing log: {len(self.processed)} files")
            except Exception as e:
                logger.warning(f"Failed to load processing log: {e}")
                self.processed = {}

    def save(self):
        """ログを保存"""
        data = {
            'version': '2.0',
            'last_updated': datetime.now().isoformat(),
            'processed': self.processed
        }
        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def is_processed(self, file_path: Path) -> bool:
        """処理済みかチェック"""
        key = str(file_path)
        if key not in self.processed:
            return False
        # ファイルの更新日時をチェック
        try:
            mtime = file_path.stat().st_mtime
            return self.processed[key].get('mtime') == mtime
        except OSError:
            return False

    def mark_processed(self, file_path: Path, info: Dict[str, Any]):
        """処理済みとしてマーク"""
        try:
            mtime = file_path.stat().st_mtime
        except OSError:
            mtime = None

        self.processed[str(file_path)] = {
            'mtime': mtime,
            'processed_at': datetime.now().isoformat(),
            **info
        }


class ExifToolWrapper:
    """exiftoolのラッパークラス"""

    def __init__(self):
        self.available = self._check_exiftool()

    def _check_exiftool(self) -> bool:
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

    # 撮影日時の許容誤差（秒）
    DATETIME_TOLERANCE_SECONDS = 5

    def __init__(self, target_dir: str, output_dir: Optional[str] = None,
                 dry_run: bool = False, verbose: bool = False,
                 immich_mode: bool = False, organize_output: Optional[str] = None,
                 skip_processed: bool = False, move_files: bool = False):
        self.target_dir = Path(target_dir).resolve()
        self.output_dir = Path(output_dir).resolve() if output_dir else None
        self.dry_run = dry_run
        self.verbose = verbose
        self.immich_mode = immich_mode
        self.organize_output = Path(organize_output).resolve() if organize_output else None
        self.skip_processed = skip_processed
        self.move_files = move_files

        if verbose:
            logger.setLevel(logging.DEBUG)

        self.exiftool = ExifToolWrapper()
        if not self.exiftool.available:
            logger.warning("exiftool not found. DNG/RAW support will be limited.")
            logger.warning("Install with: sudo apt install libimage-exiftool-perl")

        # 処理ログ
        self.processing_log = ProcessingLog(self.target_dir) if skip_processed else None

        self.stats = {
            'images_found': 0,
            'exif_extracted': 0,
            'exif_written': 0,
            'raw_synced': 0,
            'xmp_created': 0,
            'errors': 0,
            'skipped': 0,
            'skipped_processed': 0,
            'corrupted': 0,
            'organized': 0,
        }

        self.report = ImmichReport()
        self.matching_report = MatchingReport()
        self.device_stats: Dict[str, DeviceStats] = defaultdict(lambda: DeviceStats(device_name="Unknown"))
        self.file_infos: List[FileInfo] = []

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
        images, _ = self.find_all_files()
        return images

    def check_file_corrupted(self, image_path: Path) -> Tuple[bool, Optional[str]]:
        """ファイルが破損しているかチェック"""
        ext = image_path.suffix.lower()

        # RAWファイルはexiftoolでチェック
        if ext in RAW_EXTENSIONS:
            if self.exiftool.available:
                result = self.exiftool.read_exif(image_path)
                if result is None:
                    return True, "Failed to read EXIF with exiftool"
            return False, None

        try:
            with Image.open(image_path) as img:
                # 画像を検証（完全に読み込んでみる）
                img.verify()
            # verifyの後は再度開く必要がある
            with Image.open(image_path) as img:
                img.load()
            return False, None
        except Exception as e:
            return True, str(e)

    def extract_exif(self, image_path: Path) -> Optional[Dict[str, Any]]:
        """画像からEXIF情報を抽出"""
        ext = image_path.suffix.lower()

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

    def get_datetime_from_exif(self, exif_data: Optional[Dict[str, Any]]) -> Optional[datetime]:
        """EXIFから撮影日時を取得"""
        if not exif_data:
            return None

        # 様々なフィールド名を試行
        date_fields = [
            'DateTimeOriginal', 'DateTimeDigitized', 'DateTime',
            'CreateDate', 'ModifyDate'
        ]

        for field in date_fields:
            date_str = exif_data.get(field)
            if date_str:
                try:
                    # 複数のフォーマットを試行
                    for fmt in ['%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S']:
                        try:
                            return datetime.strptime(str(date_str), fmt)
                        except ValueError:
                            continue
                except:
                    continue
        return None

    def check_datetime_match(self, dt1: Optional[datetime], dt2: Optional[datetime]) -> bool:
        """2つの日時が許容誤差内で一致するかチェック"""
        if dt1 is None or dt2 is None:
            return False

        diff = abs((dt1 - dt2).total_seconds())
        return diff <= self.DATETIME_TOLERANCE_SECONDS

    def export_exif_to_json(self, image_path: Path, exif_data: Dict[str, Any]) -> Path:
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
        json_path1 = image_path.with_suffix(image_path.suffix + '.json')
        if json_path1.exists():
            return json_path1

        json_path2 = image_path.with_suffix('.json')
        if json_path2.exists():
            return json_path2

        stem = image_path.stem
        for json_file in image_path.parent.glob('*.json'):
            if json_file.stem.startswith(stem):
                return json_file

        return None

    def parse_google_photo_json(self, json_path: Path) -> Optional[Dict[str, Any]]:
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

            if 'people' in data:
                result['people'] = [p.get('name') for p in data['people'] if p.get('name')]

            return result

        except Exception as e:
            logger.error(f"Failed to parse {json_path}: {e}")
            return None

    def extract_date_from_filename(self, filename: str) -> Optional[datetime]:
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
        ext = image_path.suffix.lower()

        if ext in RAW_EXTENSIONS:
            return self._write_exif_with_exiftool(image_path, dt, geo_data)

        if ext not in EXIF_WRITABLE_EXTENSIONS:
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
            base_name = image_path.stem
            key = str(image_path.parent / base_name)

            if ext in RAW_EXTENSIONS:
                pairs[key].raw_path = image_path
            elif ext in {'.jpg', '.jpeg'}:
                pairs[key].jpg_path = image_path

        for key, pair in pairs.items():
            if pair.jpg_path:
                pair.json_path = self.find_google_photo_json(pair.jpg_path)
            elif pair.raw_path:
                pair.json_path = self.find_google_photo_json(pair.raw_path)

        return {k: v for k, v in pairs.items() if v.raw_path and v.jpg_path}

    def find_live_photos(self, images: List[Path], videos: List[Path]) -> List[Tuple[Path, Path]]:
        live_photos = []

        image_bases = {}
        for img in images:
            base = img.stem.lower()
            image_bases[base] = img
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

            hash_groups: Dict[str, List[Path]] = defaultdict(list)
            for path in paths:
                try:
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
        albums: Dict[str, List[Path]] = defaultdict(list)

        for img in images:
            rel_path = img.relative_to(self.target_dir)
            parts = rel_path.parts

            if len(parts) > 1:
                album_name = parts[0]
                if not re.match(r'^\d{4}(-\d{2})?$', album_name):
                    albums[album_name].append(img)

        self.report.albums = {k: [str(p) for p in v] for k, v in albums.items()}
        return albums

    def get_device_info(self, exif_data: Optional[Dict[str, Any]]) -> Optional[str]:
        if not exif_data:
            return None

        make = exif_data.get('Make', exif_data.get('make', ''))
        model = exif_data.get('Model', exif_data.get('model', ''))

        if make or model:
            return f"{make} {model}".strip()
        return None

    def update_device_stats(self, device: Optional[str], file_path: Path,
                            dt: Optional[datetime], has_gps: bool):
        """端末別統計を更新"""
        device_name = device or "Unknown"

        if device_name not in self.device_stats:
            self.device_stats[device_name] = DeviceStats(device_name=device_name)

        stats = self.device_stats[device_name]
        stats.total_files += 1

        if has_gps:
            stats.with_gps += 1

        ext = file_path.suffix.lower()
        stats.file_types[ext] = stats.file_types.get(ext, 0) + 1

        if dt:
            dt_str = dt.isoformat()
            if stats.date_range_start is None or dt_str < stats.date_range_start:
                stats.date_range_start = dt_str
            if stats.date_range_end is None or dt_str > stats.date_range_end:
                stats.date_range_end = dt_str

    def sync_jpg_to_raw(self, pairs: Dict[str, PhotoPair]) -> int:
        """JPGのEXIF情報をRAWファイルにコピー（日時照合付き）"""
        synced = 0
        self.matching_report.total_pairs = len(pairs)

        for key, pair in pairs.items():
            if not pair.jpg_path or not pair.raw_path:
                continue

            # JPGのEXIFを確認
            jpg_exif = self.extract_exif(pair.jpg_path)
            if not jpg_exif:
                pair.match_status = MatchStatus.NO_EXIF
                self.matching_report.no_exif += 1
                self.matching_report.details.append({
                    'jpg': str(pair.jpg_path),
                    'raw': str(pair.raw_path),
                    'status': 'no_exif',
                    'reason': 'JPG has no EXIF data'
                })
                continue

            # RAWのEXIFを確認
            raw_exif = self.exiftool.read_exif(pair.raw_path) if self.exiftool.available else None

            # デバイス情報の取得と照合
            jpg_device = self.get_device_info(jpg_exif)
            raw_device = self.get_device_info(raw_exif) if raw_exif else None
            pair.jpg_device = jpg_device
            pair.raw_device = raw_device

            if jpg_device and raw_device and jpg_device != raw_device:
                pair.match_status = MatchStatus.DEVICE_MISMATCH
                self.matching_report.device_mismatch += 1
                self.matching_report.details.append({
                    'jpg': str(pair.jpg_path),
                    'raw': str(pair.raw_path),
                    'status': 'device_mismatch',
                    'jpg_device': jpg_device,
                    'raw_device': raw_device
                })
                logger.warning(f"Device mismatch: {pair.jpg_path.name} ({jpg_device}) vs {pair.raw_path.name} ({raw_device})")
                continue

            # 撮影日時の取得と照合
            jpg_datetime = self.get_datetime_from_exif(jpg_exif)
            raw_datetime = self.get_datetime_from_exif(raw_exif) if raw_exif else None
            pair.jpg_datetime = jpg_datetime
            pair.raw_datetime = raw_datetime

            if jpg_datetime and raw_datetime:
                if not self.check_datetime_match(jpg_datetime, raw_datetime):
                    pair.match_status = MatchStatus.DATE_MISMATCH
                    self.matching_report.date_mismatch += 1
                    self.matching_report.details.append({
                        'jpg': str(pair.jpg_path),
                        'raw': str(pair.raw_path),
                        'status': 'date_mismatch',
                        'jpg_datetime': jpg_datetime.isoformat(),
                        'raw_datetime': raw_datetime.isoformat(),
                        'difference_seconds': abs((jpg_datetime - raw_datetime).total_seconds())
                    })
                    logger.warning(f"Date mismatch: {pair.jpg_path.name} ({jpg_datetime}) vs {pair.raw_path.name} ({raw_datetime})")
                    continue

            # EXIFをコピー
            if self.exiftool.copy_exif(pair.jpg_path, pair.raw_path, self.dry_run):
                synced += 1
                pair.device_match = True
                pair.date_match = True
                pair.match_status = MatchStatus.MATCHED
                self.matching_report.matched += 1
                self.matching_report.details.append({
                    'jpg': str(pair.jpg_path),
                    'raw': str(pair.raw_path),
                    'status': 'matched',
                    'device': jpg_device,
                    'datetime': jpg_datetime.isoformat() if jpg_datetime else None
                })

        self.stats['raw_synced'] = synced
        self.report.raw_synced = synced
        return synced

    def collect_unidentifiable_files(self, images: List[Path]) -> List[Dict[str, Any]]:
        """判別不能ファイルの一覧を生成"""
        unidentifiable = []

        for img in images:
            exif = self.extract_exif(img)
            device = self.get_device_info(exif)
            dt = self.get_datetime_from_exif(exif)
            json_path = self.find_google_photo_json(img)

            # 判別不能の条件：デバイス情報なし AND 日時情報なし AND JSONなし
            has_json_date = False
            if json_path:
                photo_info = self.parse_google_photo_json(json_path)
                has_json_date = photo_info and 'datetime' in photo_info

            filename_date = self.extract_date_from_filename(img.name)

            if not device and not dt and not has_json_date and not filename_date:
                unidentifiable.append({
                    'path': str(img),
                    'filename': img.name,
                    'extension': img.suffix.lower(),
                    'size_bytes': img.stat().st_size if img.exists() else 0,
                    'reason': 'No device, no EXIF date, no JSON, no date in filename'
                })

        return unidentifiable

    def organize_files(self, images: List[Path], videos: List[Path]):
        """処理済みファイルを整理して出力"""
        if not self.organize_output:
            return

        logger.info(f"Organizing files to {self.organize_output}")

        all_files = images + videos

        for file_path in all_files:
            # メタデータを取得
            exif = self.extract_exif(file_path) if file_path.suffix.lower() not in VIDEO_EXTENSIONS else None
            device = self.get_device_info(exif) if exif else None
            dt = self.get_datetime_from_exif(exif) if exif else None

            # JSONから日時を取得
            if not dt:
                json_path = self.find_google_photo_json(file_path)
                if json_path:
                    photo_info = self.parse_google_photo_json(json_path)
                    if photo_info and 'datetime' in photo_info:
                        dt = photo_info['datetime']

            # ファイル名から日時を取得
            if not dt:
                dt = self.extract_date_from_filename(file_path.name)

            # 出力パスを決定
            if dt:
                year_month = dt.strftime('%Y/%Y-%m')
            else:
                year_month = 'unknown_date'

            device_folder = device.replace(' ', '_').replace('/', '_') if device else 'unknown_device'

            # 出力先: output_dir/YYYY/YYYY-MM/Device/filename
            rel_output = Path(year_month) / device_folder / file_path.name
            output_path = self.organize_output / rel_output

            # ディレクトリ作成
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # ファイルをコピーまたは移動
            if not self.dry_run:
                if self.move_files:
                    shutil.move(str(file_path), str(output_path))
                    logger.debug(f"Moved: {file_path.name} -> {rel_output}")
                else:
                    shutil.copy2(str(file_path), str(output_path))
                    logger.debug(f"Copied: {file_path.name} -> {rel_output}")

                # 関連ファイルもコピー（JSON, XMP等）
                for related_ext in ['.json', '.xmp', '.exif.json']:
                    related_path = file_path.with_suffix(file_path.suffix + related_ext)
                    if related_path.exists():
                        related_output = output_path.with_suffix(output_path.suffix + related_ext)
                        if self.move_files:
                            shutil.move(str(related_path), str(related_output))
                        else:
                            shutil.copy2(str(related_path), str(related_output))

                self.stats['organized'] += 1
            else:
                logger.info(f"[DRY RUN] Would {'move' if self.move_files else 'copy'}: {file_path.name} -> {rel_output}")

    def run_extract(self) -> Dict[str, int]:
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
        logger.info("=== EXIF Write Mode ===")
        images = self.find_images()

        for image_path in images:
            try:
                json_path = self.find_google_photo_json(image_path)
                photo_info = None

                if json_path:
                    photo_info = self.parse_google_photo_json(json_path)

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

        # 0. 破損ファイルチェック
        logger.info("Step 0: Checking for corrupted files...")
        for image_path in images:
            is_corrupted, error_msg = self.check_file_corrupted(image_path)
            if is_corrupted:
                self.stats['corrupted'] += 1
                self.report.corrupted_files.append({
                    'path': str(image_path),
                    'error': error_msg
                })
                logger.warning(f"Corrupted file: {image_path.name} - {error_msg}")

        # 1. JPG/RAWペアを検出してEXIF同期（日時照合付き）
        logger.info("Step 1: Detecting JPG/RAW pairs with datetime validation...")
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
            # 処理済みスキップ
            if self.processing_log and self.processing_log.is_processed(image_path):
                self.stats['skipped_processed'] += 1
                continue

            try:
                # EXIF抽出
                exif_data = self.extract_exif(image_path)
                device = self.get_device_info(exif_data)
                dt = self.get_datetime_from_exif(exif_data)
                has_gps = False

                if exif_data:
                    self.export_exif_to_json(image_path, exif_data)
                    self.stats['exif_extracted'] += 1
                    self.report.with_exif += 1
                    if 'GPSInfo' in exif_data or 'GPSLatitude' in str(exif_data):
                        self.report.with_gps += 1
                        has_gps = True
                else:
                    self.report.without_exif += 1

                # 端末別統計更新
                self.update_device_stats(device, image_path, dt, has_gps)

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

                # 処理済みとしてマーク
                if self.processing_log:
                    self.processing_log.mark_processed(image_path, {
                        'device': device,
                        'datetime': dt.isoformat() if dt else None,
                        'has_gps': has_gps
                    })

            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
                self.stats['errors'] += 1

        # 6. 判別不能ファイルの収集
        logger.info("Step 6: Collecting unidentifiable files...")
        self.report.unidentifiable_files = self.collect_unidentifiable_files(images)

        # 7. ファイル整理（オプション）
        if self.organize_output:
            logger.info("Step 7: Organizing files...")
            self.organize_files(images, videos)

        # 処理ログ保存
        if self.processing_log and not self.dry_run:
            self.processing_log.save()

        # レポート生成
        self._generate_immich_report()

        return self.stats

    def _generate_immich_report(self):
        """Immich用レポートを生成"""
        report_path = self.target_dir / 'immich_import_report.json'

        # 端末別統計をシリアライズ
        device_stats_dict = {}
        for device, stats in self.device_stats.items():
            device_stats_dict[device] = {
                'device_name': stats.device_name,
                'total_files': stats.total_files,
                'with_gps': stats.with_gps,
                'date_range_start': stats.date_range_start,
                'date_range_end': stats.date_range_end,
                'file_types': stats.file_types
            }

        # マッチングレポート
        matching_report_dict = {
            'total_pairs': self.matching_report.total_pairs,
            'matched': self.matching_report.matched,
            'device_mismatch': self.matching_report.device_mismatch,
            'date_mismatch': self.matching_report.date_mismatch,
            'no_exif': self.matching_report.no_exif,
            'details': self.matching_report.details[:100]  # 最初の100件
        }

        report_data = {
            'generated_at': datetime.now().isoformat(),
            'tool_version': '2.0',
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
                'corrupted_files': len(self.report.corrupted_files),
                'unidentifiable_files': len(self.report.unidentifiable_files),
            },
            'device_statistics': device_stats_dict,
            'matching_report': matching_report_dict,
            'duplicates': self.report.duplicates[:50],
            'albums': {k: v[:20] for k, v in list(self.report.albums.items())[:20]},
            'unidentifiable_files': self.report.unidentifiable_files[:100],
            'corrupted_files': self.report.corrupted_files[:50],
            'issues': self.report.issues[:100],
        }

        if not self.dry_run:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Generated Immich report: {report_path}")
        else:
            logger.info(f"[DRY RUN] Would generate report: {report_path}")

    def print_stats(self):
        """統計情報を出力"""
        print("\n" + "=" * 70)
        print("Processing Statistics")
        print("=" * 70)
        print(f"Images found:           {self.stats['images_found']}")
        print(f"EXIF extracted:         {self.stats['exif_extracted']}")
        print(f"EXIF written:           {self.stats['exif_written']}")
        print(f"RAW synced from JPG:    {self.stats['raw_synced']}")
        print(f"XMP sidecars created:   {self.stats['xmp_created']}")
        print(f"Files organized:        {self.stats['organized']}")
        print(f"Skipped (no info):      {self.stats['skipped']}")
        print(f"Skipped (processed):    {self.stats['skipped_processed']}")
        print(f"Corrupted files:        {self.stats['corrupted']}")
        print(f"Errors:                 {self.stats['errors']}")
        print("=" * 70)

        if self.immich_mode:
            print("\nImmich-Specific Stats:")
            print("-" * 50)
            print(f"Files with EXIF:        {self.report.with_exif}")
            print(f"Files without EXIF:     {self.report.without_exif}")
            print(f"Files with GPS:         {self.report.with_gps}")
            print(f"Live Photos detected:   {self.report.live_photos}")
            print(f"Duplicate groups:       {len(self.report.duplicates)}")
            print(f"Albums detected:        {len(self.report.albums)}")
            print(f"Dates fixed from name:  {self.report.date_fixed}")
            print(f"Unidentifiable files:   {len(self.report.unidentifiable_files)}")
            print(f"Corrupted files:        {len(self.report.corrupted_files)}")
            print("-" * 50)

            # JPG/RAW マッチングレポート
            if self.matching_report.total_pairs > 0:
                print("\nJPG/RAW Matching Report:")
                print("-" * 50)
                print(f"Total pairs found:      {self.matching_report.total_pairs}")
                print(f"Successfully matched:   {self.matching_report.matched}")
                print(f"Device mismatch:        {self.matching_report.device_mismatch}")
                print(f"Date mismatch (>{self.DATETIME_TOLERANCE_SECONDS}s): {self.matching_report.date_mismatch}")
                print(f"No EXIF data:           {self.matching_report.no_exif}")
                print("-" * 50)

            # 端末別統計
            if self.device_stats:
                print("\nDevice Statistics:")
                print("-" * 50)
                for device, stats in sorted(self.device_stats.items(),
                                            key=lambda x: x[1].total_files, reverse=True):
                    date_range = ""
                    if stats.date_range_start and stats.date_range_end:
                        start = stats.date_range_start[:10]
                        end = stats.date_range_end[:10]
                        date_range = f" ({start} ~ {end})"
                    print(f"  {device}: {stats.total_files} files{date_range}")
                print("-" * 50)


def main():
    parser = argparse.ArgumentParser(
        description='Photo Metadata Tool - Google Photo Takeout用EXIF処理ツール（Immich対応）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本的なEXIF処理
  python photo_metadata_tool.py /path/to/photos --extract
  python photo_metadata_tool.py /path/to/photos --write
  python photo_metadata_tool.py /path/to/photos --both

  # Immich向け準備モード（推奨）
  python photo_metadata_tool.py /path/to/photos --immich

  # ドライラン（実際には変更しない）
  python photo_metadata_tool.py /path/to/photos --immich --dry-run

  # 処理済みファイルを年月/端末別に整理して出力
  python photo_metadata_tool.py /path/to/photos --immich --organize /path/to/output

  # 処理済みファイルをスキップして再実行
  python photo_metadata_tool.py /path/to/photos --immich --skip-processed

  # ファイルを移動（コピーではなく）
  python photo_metadata_tool.py /path/to/photos --immich --organize /path/to/output --move

Immichモードの機能:
  - JPG/RAWペア検出とEXIF同期（デバイス+日時照合）
  - Live Photo（モーションフォト）検出
  - 重複ファイル検出
  - アルバム情報抽出
  - ファイル名からの日付推測
  - XMPサイドカーファイル生成（HEIC等用）
  - 端末別統計レポート
  - 判別不能ファイル一覧
  - 破損ファイル検出
  - 処理ログによる再実行時スキップ
  - 年月/端末別フォルダ整理

出力フォルダ構造（--organize使用時）:
  output/
  ├── 2023/
  │   ├── 2023-01/
  │   │   ├── Google_Pixel_7/
  │   │   │   ├── IMG_0001.jpg
  │   │   │   └── IMG_0001.dng
  │   │   └── Samsung_SM-G998/
  │   │       └── IMG_0002.jpg
  │   └── 2023-02/
  │       └── ...
  └── unknown_date/
      └── unknown_device/
          └── ...
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
    parser.add_argument('--organize', type=str,
                        help='処理済みファイルを年月/端末別に整理して出力するディレクトリ')
    parser.add_argument('--move', action='store_true',
                        help='--organizeと併用：ファイルをコピーではなく移動')
    parser.add_argument('--skip-processed', action='store_true',
                        help='処理済みファイルをスキップ（処理ログを使用）')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='ドライラン（実際には書き込まない）')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='詳細ログ')

    args = parser.parse_args()

    if not any([args.extract, args.write, args.both, args.immich]):
        parser.error("少なくとも --extract, --write, --both, --immich のいずれかを指定してください")

    if not os.path.isdir(args.target_dir):
        parser.error(f"ディレクトリが存在しません: {args.target_dir}")

    if args.move and not args.organize:
        parser.error("--move は --organize と一緒に使用してください")

    tool = PhotoMetadataTool(
        target_dir=args.target_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        verbose=args.verbose,
        immich_mode=args.immich,
        organize_output=args.organize,
        skip_processed=args.skip_processed,
        move_files=args.move
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
