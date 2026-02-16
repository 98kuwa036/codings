#!/usr/bin/env python3
"""
OneDrive Photo Metadata Fixer for GitHub Actions (v4.0 - rclone backend)
Processes photos from OneDrive Folder A, fixes metadata using JSON files,
and uploads to OneDrive Folder B.

Azure AD登録不要。rclone の OAuth 設定を GitHub Secret に保存するだけで動作。

v4.0 Changes:
- Replaced Azure AD/MSAL with rclone (no app registration needed)
- All OneDrive operations via `rclone` subprocess calls
- rclone config stored as RCLONE_CONFIG secret in GitHub Actions

Previous features retained:
- EXIF repair from Google Takeout JSON sidecars
- ZIP extraction support (Google Takeout ZIPs from OneDrive)
- Adaptive Vision AI tagging (Google Cloud Vision + DeepL)
- Resume/skip-existing functionality
- Duplicate detection
"""

import os
import sys
import json
import argparse
import logging
import hashlib
import shutil
import time
import re
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

# ==========================================
# Settings and Constants
# ==========================================

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.tiff', '.tif', '.heic', '.heif', '.avif'}
RAW_EXTENSIONS = {'.dng', '.cr2', '.cr3', '.nef', '.arw', '.raf', '.orf', '.rw2', '.pef', '.srw'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.3gp', '.m4v', '.mpg', '.webm', '.mts', '.m2ts'}
ALL_TARGETS = IMAGE_EXTENSIONS | RAW_EXTENSIONS | VIDEO_EXTENSIONS
JSON_EXTENSION = {'.json'}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

DATE_PATTERNS = [
    (r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', '%Y%m%d_%H%M%S'),
    (r'(\d{4})(\d{2})(\d{2})[_-](\d{2})(\d{2})(\d{2})', '%Y%m%d-%H%M%S'),
    (r'(\d{4})-(\d{2})-(\d{2})\s(\d{2})\.(\d{2})\.(\d{2})', '%Y-%m-%d %H.%M.%S'),
    (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),
    (r'(\d{4})(\d{2})(\d{2})', '%Y%m%d'),
]


# ==========================================
# rclone Client (replaces OneDriveClient)
# ==========================================

class RcloneClient:
    """
    OneDrive access via rclone subprocess.

    Azure AD app registration不要。
    rclone の設定を一度だけローカルで行い、
    生成された設定ファイルを RCLONE_CONFIG として
    GitHub Secret に保存するだけで使用できる。

    Setup (one-time, on your local machine):
        1. Install rclone: https://rclone.org/install/
        2. rclone config
           → New remote → name: "onedrive" → Microsoft OneDrive
           → Follow the browser OAuth flow
        3. cat ~/.config/rclone/rclone.conf
           → Copy the [onedrive] section as GitHub Secret RCLONE_CONFIG
    """

    def __init__(
        self,
        remote_name: str = "onedrive",
        config_path: Optional[str] = None,
        retries: int = 5,
        transfers: int = 4,
    ):
        self.remote = remote_name
        self.config_path = config_path  # Path to rclone.conf (written from secret)
        self.retries = retries
        self.transfers = transfers
        self._verify_rclone()

    def _verify_rclone(self):
        """Check that rclone is available"""
        if not shutil.which("rclone"):
            raise RuntimeError(
                "rclone not found in PATH. "
                "Install: curl https://rclone.org/install.sh | bash"
            )

    def _base_cmd(self) -> List[str]:
        """Build base rclone command with common flags"""
        cmd = ["rclone", "--retries", str(self.retries), "--low-level-retries", "10"]
        if self.config_path:
            cmd += ["--config", self.config_path]
        return cmd

    def _remote_path(self, folder_path: str) -> str:
        """Build rclone remote path string"""
        folder_path = folder_path.strip("/")
        return f"{self.remote}:{folder_path}" if folder_path else f"{self.remote}:"

    def list_files(self, folder_path: str, recursive: bool = False) -> List[Dict[str, Any]]:
        """
        List files in a remote folder.
        Returns list of dicts with 'name', 'path', 'size', '_folder_path'.
        """
        cmd = self._base_cmd() + [
            "lsjson",
            "--files-only",
            "--no-modtime",
        ]
        if recursive:
            cmd.append("--recursive")
        cmd.append(self._remote_path(folder_path))

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )
            if result.returncode != 0:
                if "directory not found" in result.stderr.lower() or "not found" in result.stderr.lower():
                    logger.warning(f"Folder not found: {folder_path}")
                    return []
                logger.error(f"rclone lsjson failed: {result.stderr[:300]}")
                return []

            items = json.loads(result.stdout or "[]")
            # Normalize to match expected dict structure
            normalized = []
            for item in items:
                item_path = item.get("Path", item.get("Name", ""))
                item_name = Path(item_path).name
                item_folder = str(Path(folder_path) / Path(item_path).parent).strip("/")
                normalized.append({
                    "name": item_name,
                    "id": f"rclone::{self.remote}/{folder_path}/{item_path}",
                    "size": item.get("Size", 0),
                    "file": {"mimeType": ""},
                    "_folder_path": item_folder if item_folder != "." else folder_path,
                    "_rclone_path": f"{folder_path}/{item_path}".strip("/"),
                })
            return normalized
        except Exception as e:
            logger.error(f"list_files error: {e}")
            return []

    def list_folder(self, folder_path: str) -> List[Dict[str, Any]]:
        """Recursive listing (matches old OneDriveClient.list_folder signature)"""
        return self.list_files(folder_path, recursive=True)

    def download_file(self, item_id: str, local_path: Path, user_id=None) -> bool:
        """
        Download a file by its rclone path (stored in item_id as 'rclone::remote/path').
        Falls back to treating item_id as a remote path directly.
        """
        # item_id format: "rclone::onedrive/Photos/file.jpg"
        if item_id.startswith("rclone::"):
            remote_path = item_id[len("rclone::"):]
            # remote_path is "onedrive/Photos/file.jpg" → "onedrive:Photos/file.jpg"
            parts = remote_path.split("/", 1)
            rclone_src = f"{parts[0]}:{parts[1]}" if len(parts) > 1 else f"{parts[0]}:"
        else:
            rclone_src = item_id

        cmd = self._base_cmd() + ["copyto", rclone_src, str(local_path)]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )
            if result.returncode == 0:
                return True
            logger.error(f"rclone download failed: {result.stderr[:300]}")
            return False
        except Exception as e:
            logger.error(f"download_file error: {e}")
            return False

    def download_file_bytes(self, file_path: str, user_id=None) -> Optional[bytes]:
        """Download file content to memory (used by ZipExtractor)"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            success = self.download_file(
                f"rclone::{self.remote}/{file_path.strip('/')}",
                tmp_path,
            )
            if success and tmp_path.exists():
                return tmp_path.read_bytes()
            return None
        finally:
            tmp_path.unlink(missing_ok=True)

    def upload_file(
        self,
        local_path: Path,
        dest_folder: str,
        filename: str,
        user_id=None,
    ) -> bool:
        """Upload a local file to a remote folder"""
        dest_folder = dest_folder.strip("/")
        remote_dest = f"{self.remote}:{dest_folder}/{filename}"

        cmd = self._base_cmd() + [
            "copyto",
            str(local_path),
            remote_dest,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )
            if result.returncode == 0:
                return True
            logger.error(f"rclone upload failed: {result.stderr[:300]}")
            return False
        except Exception as e:
            logger.error(f"upload_file error: {e}")
            return False

    def upload_folder(self, local_dir: Path, remote_folder: str) -> bool:
        """Upload all files in a local directory to a remote folder"""
        remote_dest = self._remote_path(remote_folder)
        cmd = self._base_cmd() + [
            "copy", str(local_dir), remote_dest,
            "--transfers", str(self.transfers),
            "--progress",
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"upload_folder error: {e}")
            return False

    def file_exists(self, folder_path: str, filename: str, user_id=None) -> bool:
        """Check if a file exists in a remote folder (rclone lsf)"""
        remote_path = self._remote_path(f"{folder_path.strip('/')}/{filename}")
        cmd = self._base_cmd() + ["lsf", remote_path]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )
            return result.returncode == 0 and filename in result.stdout
        except Exception:
            return False

    def create_folder(self, folder_path: str, user_id=None) -> bool:
        """Create a remote folder (rclone mkdir)"""
        cmd = self._base_cmd() + ["mkdir", self._remote_path(folder_path)]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )
            return result.returncode == 0
        except Exception:
            return False

    def invalidate_cache(self, folder_path: str):
        """No-op: rclone doesn't use a local cache that needs invalidating"""
        pass


# ==========================================
# Statistics
# ==========================================

class Statistics:
    """Track processing statistics"""

    def __init__(self):
        self.total_files = 0
        self.processed = 0
        self.errors = 0
        self.duplicates = 0
        self.skipped = 0
        self.already_exists = 0
        self.source_counts = Counter()
        self.file_types = Counter()
        self.issues: List[str] = []
        self.start_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'summary': {
                'total_files': self.total_files,
                'processed_success': self.processed,
                'duplicates_isolated': self.duplicates,
                'skipped_already_exists': self.already_exists,
                'skipped_other': self.skipped,
                'errors': self.errors,
                'duration_seconds': round(time.time() - self.start_time, 2)
            },
            'metadata_source': dict(self.source_counts),
            'file_types': dict(self.file_types),
            'issues_sample': self.issues[:100]
        }


# ==========================================
# ExifTool Wrapper
# ==========================================

class ExifToolWrapper:
    """Wrapper for exiftool operations"""

    def __init__(self):
        self.path = shutil.which('exiftool')
        self.available = self.path is not None
        if not self.available:
            logger.warning("ExifTool not found in PATH. Metadata writing will be limited.")

    def write_metadata(self, file_path: Path, tags: Dict[str, Any], sidecar: bool = True) -> bool:
        if not self.available:
            return False

        cmd = [self.path, '-overwrite_original', '-m', '-charset', 'filename=UTF8']
        for key, val in tags.items():
            if isinstance(val, datetime):
                val_str = val.strftime('%Y:%m:%d %H:%M:%S')
                cmd.append(f'-{key}={val_str}')
            elif isinstance(val, list):
                for v in val:
                    cmd.append(f'-{key}+={v}')
            else:
                cmd.append(f'-{key}={val}')
        cmd.append(str(file_path))

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            return res.returncode == 0
        except Exception as e:
            logger.error(f"ExifTool error: {e}")
            return False

    def read_metadata(self, file_path: Path) -> Dict:
        if not self.available:
            return {}

        cmd = [
            self.path, '-json', '-n', '-G',
            '-DateTimeOriginal', '-CreateDate', '-DateCreated',
            '-MediaCreateDate', '-Model', '-GPSLatitude', '-GPSLongitude',
            '-GPSLatitudeRef', '-GPSLongitudeRef',
            str(file_path)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                if data:
                    return data[0]
        except Exception as e:
            logger.debug(f"Failed to read metadata: {e}")
        return {}


# ==========================================
# Main Fixer
# ==========================================

class OneDrivePhotoFixer:
    """Main class for processing photos from OneDrive via rclone"""

    def __init__(self, args):
        self.args = args
        self.src_folder = args.src_folder.strip('/')
        self.dst_folder = args.dst_folder.strip('/')
        self.dup_folder = f"{self.dst_folder}/duplicates"

        self.client = RcloneClient(
            remote_name=args.rclone_remote,
            config_path=args.rclone_config,
            retries=5,
        )

        self.stats = Statistics()
        self.exiftool = ExifToolWrapper()
        self.tz = timezone(timedelta(hours=args.timezone))
        self.hash_db: Dict[str, str] = {}
        self.skip_existing = args.skip_existing

        self.temp_dir = Path(tempfile.mkdtemp(prefix='photo_fixer_'))
        self.processed_temp_dir = self.temp_dir / 'processed'
        self.processed_temp_dir.mkdir()

        # AI tagger (optional)
        self.ai_tagger = self._init_ai_tagger()

        logger.info(f"Using temporary directory: {self.temp_dir}")
        logger.info(f"Skip existing files: {self.skip_existing}")

    def _init_ai_tagger(self):
        """Initialize AdaptiveVisionAnalyzer if AI tagging is enabled."""
        if not getattr(self.args, 'enable_ai_tagging', False):
            return None

        vision_creds = (getattr(self.args, 'vision_credentials', None) or
                        os.environ.get('GOOGLE_VISION_CREDENTIALS_JSON'))
        deepl_key = (getattr(self.args, 'deepl_api_key', None) or
                     os.environ.get('DEEPL_API_KEY'))

        if not vision_creds or not deepl_key:
            logger.warning("AI tagging requested but credentials missing; skipping")
            return None

        try:
            from adaptive_vision_analyzer import AdaptiveVisionAnalyzer
            tagger = AdaptiveVisionAnalyzer(
                vision_credentials_json=vision_creds,
                deepl_api_key=deepl_key,
                deepl_free_tier=getattr(self.args, 'deepl_free_tier', False),
                confidence_threshold=getattr(self.args, 'ai_confidence', 0.75),
                cache_path=getattr(self.args, 'ai_cache_path', None),
            )
            logger.info("AdaptiveVisionAnalyzer initialized")
            return tagger
        except Exception as e:
            logger.warning(f"Failed to initialize AI tagger: {e}")
            return None

    def cleanup(self):
        try:
            shutil.rmtree(self.temp_dir)
            logger.info("Cleaned up temporary files")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp dir: {e}")

    def calculate_hash(self, file_path: Path) -> str:
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""

    def find_json_in_items(self, file_name: str, all_items: List[Dict], folder_path: str) -> Optional[Dict]:
        stem = Path(file_name).stem
        candidates = {
            f"{file_name}.json",
            f"{stem}.json",
            f"{file_name}.supplemental-metadata.json",
            f"{stem[:47]}.json",
        }
        for item in all_items:
            if item.get('_folder_path') != folder_path:
                continue
            item_name = item.get('name', '')
            if item_name in candidates:
                return item
            if item_name.endswith('.json') and stem[:40] in item_name:
                return item
        return None

    def infer_date_from_filename(self, filename: str) -> Optional[datetime]:
        for pattern, _ in DATE_PATTERNS:
            match = re.search(pattern, filename)
            if match:
                try:
                    nums = match.groups()
                    if len(nums) == 3:
                        y, m, d = nums[:3]
                        return datetime(int(y), int(m), int(d))
                    elif len(nums) >= 6:
                        y, m, d, H, M, S = nums[:6]
                        return datetime(int(y), int(m), int(d), int(H), int(M), int(S))
                except Exception:
                    continue
        return None

    def parse_exif_date(self, date_str: str) -> Optional[datetime]:
        try:
            if not date_str or str(date_str).startswith("0000"):
                return None
            clean_str = str(date_str)[:19].replace('-', ':').replace('/', ':')
            return datetime.strptime(clean_str, '%Y:%m:%d %H:%M:%S')
        except Exception:
            return None

    def _load_json_file(self, json_path: Path) -> Optional[Dict]:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"JSON load error {json_path}: {e}")
            return None

    def _apply_json_metadata(self, json_data: Dict, meta_tags: Dict, source: str):
        ts = int(json_data.get('photoTakenTime', {}).get('timestamp', 0))
        if ts > 0:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(self.tz).replace(tzinfo=None)
            if 1980 < dt.year < 2030:
                meta_tags['DateTimeOriginal'] = dt
                meta_tags['CreateDate'] = dt
                source = "JSON"

        geo_data = json_data.get('geoData', {})
        lat = geo_data.get('latitude', 0.0)
        lon = geo_data.get('longitude', 0.0)
        if lat and lon and abs(lat) > 0.001 and abs(lon) > 0.001:
            meta_tags['GPSLatitude'] = lat
            meta_tags['GPSLongitude'] = lon

        return meta_tags, source

    def process_item(self, item: Dict, all_items: List[Dict]) -> bool:
        """Process a single file"""
        file_name = item.get('name', '')
        item_id = item.get('id', '')
        folder_path = item.get('_folder_path', '')

        suffix = Path(file_name).suffix.lower()
        if suffix not in ALL_TARGETS:
            self.stats.skipped += 1
            return True

        logger.info(f"Processing: {folder_path}/{file_name}")

        try:
            # --- Fast-path: file already local (from ZIP extraction) ---
            local_path_str = item.get('_local_path')
            if local_path_str:
                local_file = Path(local_path_str)
                if not local_file.exists():
                    self.stats.errors += 1
                    self.stats.issues.append(f"Local file missing: {file_name}")
                    return False
            else:
                local_file = self.temp_dir / file_name
                if not self.client.download_file(item_id, local_file):
                    self.stats.errors += 1
                    self.stats.issues.append(f"Download failed: {file_name}")
                    return False

            # Duplicate check
            file_hash = self.calculate_hash(local_file)
            if file_hash and file_hash in self.hash_db:
                logger.info(f"Duplicate: {file_name} matches {self.hash_db[file_hash]}")
                self.client.create_folder(self.dup_folder)
                self.client.upload_file(local_file, self.dup_folder, file_name)
                self.stats.duplicates += 1
                if not local_path_str:
                    local_file.unlink(missing_ok=True)
                return True
            if file_hash:
                self.hash_db[file_hash] = file_name

            meta_tags = {}
            source = "Unknown"

            # --- STEP 1: Internal EXIF ---
            exif_data = self.exiftool.read_metadata(local_file)
            raw_date = (
                exif_data.get('EXIF:DateTimeOriginal') or
                exif_data.get('EXIF:CreateDate') or
                exif_data.get('QuickTime:MediaCreateDate') or
                exif_data.get('XMP:DateTimeOriginal')
            )
            if raw_date:
                parsed_dt = self.parse_exif_date(raw_date)
                if parsed_dt and 1980 < parsed_dt.year < 2030:
                    meta_tags['DateTimeOriginal'] = parsed_dt
                    meta_tags['CreateDate'] = parsed_dt
                    source = "Internal_Exif"

            # GPS from EXIF
            if 'EXIF:GPSLatitude' in exif_data:
                meta_tags['GPSLatitude'] = exif_data['EXIF:GPSLatitude']
                meta_tags['GPSLongitude'] = exif_data.get('EXIF:GPSLongitude')

            # --- STEP 2: JSON sidecar ---
            if 'DateTimeOriginal' not in meta_tags:
                json_sidecar_path = item.get('_json_sidecar_path')
                if json_sidecar_path:
                    json_data = self._load_json_file(Path(json_sidecar_path))
                    if json_data:
                        meta_tags, source = self._apply_json_metadata(json_data, meta_tags, source)
                else:
                    json_item = self.find_json_in_items(file_name, all_items, folder_path)
                    if json_item:
                        json_local = self.temp_dir / json_item['name']
                        if self.client.download_file(json_item['id'], json_local):
                            try:
                                json_data = self._load_json_file(json_local)
                                if json_data:
                                    meta_tags, source = self._apply_json_metadata(json_data, meta_tags, source)
                            finally:
                                json_local.unlink(missing_ok=True)

            # --- STEP 3: Filename ---
            if 'DateTimeOriginal' not in meta_tags:
                inferred_dt = self.infer_date_from_filename(file_name)
                if inferred_dt:
                    meta_tags['DateTimeOriginal'] = inferred_dt
                    source = "Filename"

            # --- STEP 4: File mtime fallback ---
            if 'DateTimeOriginal' not in meta_tags:
                meta_tags['DateTimeOriginal'] = datetime.fromtimestamp(local_file.stat().st_mtime)
                source = "FileSystem_LastResort"

            # Determine destination path
            final_dt = meta_tags.get('DateTimeOriginal', datetime.now())
            date_folder = final_dt.strftime('%Y/%Y-%m')
            dest_folder_path = f"{self.dst_folder}/{date_folder}"

            # Skip if already exists
            if self.skip_existing and self.client.file_exists(dest_folder_path, file_name):
                logger.info(f"SKIP (exists): {file_name}")
                self.stats.already_exists += 1
                if not local_path_str:
                    local_file.unlink(missing_ok=True)
                return True

            # Write EXIF metadata
            if meta_tags and self.exiftool.available:
                self.exiftool.write_metadata(local_file, meta_tags, sidecar=self.args.create_xmp)

            # --- AI Tagging ---
            ai_xmp_path = None
            if self.ai_tagger is not None:
                try:
                    result = self.ai_tagger.analyze(
                        image_path=local_file,
                        exif_data={
                            'gps_lat': meta_tags.get('GPSLatitude'),
                            'gps_lon': meta_tags.get('GPSLongitude'),
                            'folder_path': folder_path,
                            'Model': exif_data.get('EXIF:Model'),
                        },
                        immich_has_faces=False,
                    )
                    if result and result.xmp_path and Path(result.xmp_path).exists():
                        ai_xmp_path = Path(result.xmp_path)
                        logger.info(
                            f"AI tagged: {len(result.tags_japanese)} tags, "
                            f"type={result.feature_profile}, cost=${result.cost_usd:.4f}"
                        )
                except Exception as e:
                    logger.warning(f"AI tagging failed for {file_name}: {e}")

            # Upload
            self.client.create_folder(dest_folder_path)

            if self.client.upload_file(local_file, dest_folder_path, file_name):
                logger.info(f"OK [{source}]: {file_name} -> {dest_folder_path}")
                self.stats.processed += 1
                self.stats.source_counts[source] += 1
                self.stats.file_types[suffix] += 1

                if self.args.create_xmp:
                    xmp_file = local_file.with_suffix(suffix + '.xmp')
                    if xmp_file.exists():
                        self.client.upload_file(xmp_file, dest_folder_path, xmp_file.name)

                if ai_xmp_path and ai_xmp_path.exists():
                    self.client.upload_file(ai_xmp_path, dest_folder_path, ai_xmp_path.name)
            else:
                self.stats.errors += 1
                self.stats.issues.append(f"Upload failed: {file_name}")

            if not local_path_str:
                local_file.unlink(missing_ok=True)
            return True

        except Exception as e:
            logger.error(f"Error processing {file_name}: {e}")
            self.stats.errors += 1
            self.stats.issues.append(f"Error {file_name}: {str(e)}")
            return False

    def _extract_zips_and_build_items(self, zip_folder: str) -> List[Dict]:
        """Find, download, and extract ZIP files; return synthetic item dicts."""
        from zip_extractor import ZipExtractor

        extractor = ZipExtractor(self.client)
        zip_items = extractor.find_zips(zip_folder)

        if not zip_items:
            logger.warning(f"No ZIP files found in {zip_folder}")
            return []

        extract_base = self.temp_dir / 'extracted'
        extract_base.mkdir(exist_ok=True)

        all_synthetic: List[Dict] = []
        for zip_item in zip_items:
            logger.info(f"Processing ZIP: {zip_item['name']}")
            extracted_files = extractor.download_and_extract(
                zip_item=zip_item,
                extract_to=extract_base,
                zip_folder_path=zip_folder,
            )
            synthetic = extractor.build_synthetic_items(
                files=extracted_files,
                base_path=extract_base,
                original_zip_name=zip_item['name'],
            )
            all_synthetic.extend(synthetic)
            logger.info(f"  -> {len(synthetic)} items from {zip_item['name']}")

        logger.info(f"Total items from ZIPs: {len(all_synthetic)}")
        return all_synthetic

    def run(self):
        """Main execution method"""
        logger.info("=" * 60)
        logger.info("OneDrive Photo Fixer v4.0 (rclone backend)")
        logger.info(f"Remote: {self.client.remote}")
        logger.info(f"Source: {self.src_folder}")
        logger.info(f"Destination: {self.dst_folder}")
        logger.info(f"Skip existing: {self.skip_existing}")
        if self.ai_tagger:
            logger.info("AI tagging: ENABLED")
        logger.info("=" * 60)

        try:
            all_items: List[Dict] = []

            if getattr(self.args, 'extract_zips', False):
                zip_folder = getattr(self.args, 'zip_folder', None) or self.src_folder
                all_items = self._extract_zips_and_build_items(zip_folder)
            else:
                logger.info("Listing files in source folder...")
                all_items = self.client.list_folder(self.src_folder)

            media_items = [
                item for item in all_items
                if Path(item.get('name', '')).suffix.lower() in ALL_TARGETS
            ]

            self.stats.total_files = len(media_items)
            logger.info(f"Found {self.stats.total_files} media files to process")

            if not media_items:
                logger.warning("No media files found")
                return

            if self.args.threads > 1:
                logger.warning("Multi-threading may cause rate limit issues; consider --threads 1")
                with ThreadPoolExecutor(max_workers=self.args.threads) as executor:
                    futures = [
                        executor.submit(self.process_item, item, all_items)
                        for item in media_items
                    ]
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(f"Thread error: {e}")
            else:
                for item in media_items:
                    self.process_item(item, all_items)

            # Save and upload report
            report = self.stats.to_dict()
            report_json = json.dumps(report, indent=2, ensure_ascii=False, default=str)

            report_file = self.temp_dir / 'migration_report.json'
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_json)

            self.client.create_folder(self.dst_folder)
            self.client.upload_file(report_file, self.dst_folder, 'migration_report.json')

            logger.info("=" * 60)
            logger.info("Processing Complete!")
            logger.info(f"  Total:     {self.stats.total_files}")
            logger.info(f"  Processed: {self.stats.processed}")
            logger.info(f"  Skipped:   {self.stats.already_exists}")
            logger.info(f"  Dupes:     {self.stats.duplicates}")
            logger.info(f"  Errors:    {self.stats.errors}")
            logger.info(f"  Duration:  {round(time.time() - self.stats.start_time, 2)}s")
            logger.info("=" * 60)
            print("\n--- MIGRATION REPORT ---")
            print(report_json)

        finally:
            self.cleanup()


# ==========================================
# CLI
# ==========================================

def main():
    parser = argparse.ArgumentParser(
        description="OneDrive Photo Fixer v4.0 (rclone backend, Azure不要)"
    )

    # rclone settings
    parser.add_argument(
        '--rclone-remote',
        default=os.environ.get('RCLONE_REMOTE', 'onedrive'),
        help='rclone remote name (default: onedrive)'
    )
    parser.add_argument(
        '--rclone-config',
        default=os.environ.get('RCLONE_CONFIG_PATH', ''),
        help='Path to rclone.conf (auto-written from RCLONE_CONFIG secret)'
    )

    # Folder paths
    parser.add_argument(
        '--src-folder',
        default=os.environ.get('ONEDRIVE_SRC_FOLDER', 'Photos/Google Takeout'),
        help='Source folder in OneDrive'
    )
    parser.add_argument(
        '--dst-folder',
        default=os.environ.get('ONEDRIVE_DST_FOLDER', 'Photos/Immich'),
        help='Destination folder in OneDrive'
    )

    # Processing options
    parser.add_argument('--timezone', type=int, default=int(os.environ.get('TZ_OFFSET', '9')))
    parser.add_argument('--threads', type=int, default=int(os.environ.get('THREADS', '1')))
    parser.add_argument('--create-xmp', action='store_true',
                        default=os.environ.get('CREATE_XMP', '').lower() == 'true')
    parser.add_argument('--skip-existing', action='store_true',
                        default=os.environ.get('SKIP_EXISTING', 'true').lower() == 'true')
    parser.add_argument('--dry-run', action='store_true')

    # ZIP extraction
    parser.add_argument('--extract-zips', action='store_true',
                        default=os.environ.get('EXTRACT_ZIPS', '').lower() == 'true')
    parser.add_argument('--zip-folder', default=os.environ.get('ONEDRIVE_ZIP_FOLDER', ''))

    # AI tagging
    parser.add_argument('--enable-ai-tagging', action='store_true',
                        default=os.environ.get('ENABLE_AI_TAGGING', '').lower() == 'true')
    parser.add_argument('--vision-credentials',
                        default=os.environ.get('GOOGLE_VISION_CREDENTIALS_JSON', ''))
    parser.add_argument('--deepl-api-key', default=os.environ.get('DEEPL_API_KEY', ''))
    parser.add_argument('--deepl-free-tier', action='store_true',
                        default=os.environ.get('DEEPL_FREE_TIER', '').lower() == 'true')
    parser.add_argument('--ai-confidence', type=float,
                        default=float(os.environ.get('AI_CONFIDENCE', '0.75')))
    parser.add_argument('--ai-cache-path',
                        default=os.environ.get('AI_CACHE_PATH', '/tmp/translation_cache.json'))

    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN MODE")
        client = RcloneClient(args.rclone_remote, args.rclone_config)
        items = client.list_folder(args.src_folder)
        for item in items:
            print(f"{item.get('_folder_path', '')}/{item.get('name', '')}")
        return

    fixer = OneDrivePhotoFixer(args)
    fixer.run()


if __name__ == '__main__':
    main()
