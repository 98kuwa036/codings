#!/usr/bin/env python3
"""
OneDrive Photo Metadata Fixer for GitHub Actions
Processes photos from OneDrive Folder A, fixes metadata using JSON files,
and uploads to OneDrive Folder B.

Designed to run in GitHub Actions with Microsoft Graph API.
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
from typing import Optional, Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

import requests
from msal import ConfidentialClientApplication

# ==========================================
# Settings and Constants
# ==========================================

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.tiff', '.tif', '.heic', '.heif', '.avif'}
RAW_EXTENSIONS = {'.dng', '.cr2', '.nef', '.arw', '.raf', '.orf', '.rw2', '.pef', '.srw'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.3gp', '.m4v', '.mpg', '.webm'}
ALL_TARGETS = IMAGE_EXTENSIONS | RAW_EXTENSIONS | VIDEO_EXTENSIONS
JSON_EXTENSION = {'.json'}

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

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


class Statistics:
    """Track processing statistics"""

    def __init__(self):
        self.total_files = 0
        self.processed = 0
        self.errors = 0
        self.duplicates = 0
        self.skipped = 0
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
                'skipped': self.skipped,
                'errors': self.errors,
                'duration_seconds': round(time.time() - self.start_time, 2)
            },
            'metadata_source': dict(self.source_counts),
            'file_types': dict(self.file_types),
            'issues_sample': self.issues[:100]
        }


class OneDriveClient:
    """Microsoft Graph API client for OneDrive operations"""

    def __init__(self, client_id: str, client_secret: str, tenant_id: str, drive_type: str = "me"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.drive_type = drive_type
        self.access_token: Optional[str] = None
        self.token_expires: float = 0

        self.app = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}"
        )

    def _ensure_token(self):
        """Ensure we have a valid access token"""
        if self.access_token and time.time() < self.token_expires - 60:
            return

        scopes = ["https://graph.microsoft.com/.default"]
        result = self.app.acquire_token_for_client(scopes=scopes)

        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "Unknown error"))
            raise Exception(f"Failed to acquire token: {error}")

        self.access_token = result["access_token"]
        self.token_expires = time.time() + result.get("expires_in", 3600)
        logger.info("Successfully acquired Microsoft Graph API token")

    def _headers(self) -> Dict[str, str]:
        self._ensure_token()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def _get_drive_path(self, user_id: Optional[str] = None) -> str:
        """Get the base drive path for API calls"""
        if user_id:
            return f"{GRAPH_API_BASE}/users/{user_id}/drive"
        return f"{GRAPH_API_BASE}/me/drive"

    def list_folder(self, folder_path: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all items in a OneDrive folder recursively"""
        drive_path = self._get_drive_path(user_id)

        # Normalize folder path
        folder_path = folder_path.strip('/')
        if folder_path:
            url = f"{drive_path}/root:/{folder_path}:/children"
        else:
            url = f"{drive_path}/root/children"

        all_items = []

        while url:
            response = requests.get(url, headers=self._headers())

            if response.status_code == 404:
                logger.warning(f"Folder not found: {folder_path}")
                return []

            response.raise_for_status()
            data = response.json()

            for item in data.get("value", []):
                if "folder" in item:
                    # Recursively get contents of subfolders
                    subfolder_path = f"{folder_path}/{item['name']}" if folder_path else item['name']
                    all_items.extend(self.list_folder(subfolder_path, user_id))
                else:
                    item['_folder_path'] = folder_path
                    all_items.append(item)

            url = data.get("@odata.nextLink")

        return all_items

    def download_file(self, item_id: str, local_path: Path, user_id: Optional[str] = None) -> bool:
        """Download a file from OneDrive"""
        drive_path = self._get_drive_path(user_id)
        url = f"{drive_path}/items/{item_id}/content"

        try:
            response = requests.get(url, headers=self._headers(), stream=True)
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            logger.error(f"Failed to download file {item_id}: {e}")
            return False

    def upload_file(self, local_path: Path, dest_folder: str, filename: str, user_id: Optional[str] = None) -> bool:
        """Upload a file to OneDrive (supports files up to 4MB directly, larger via upload session)"""
        drive_path = self._get_drive_path(user_id)
        dest_folder = dest_folder.strip('/')

        file_size = local_path.stat().st_size

        if file_size < 4 * 1024 * 1024:  # < 4MB
            return self._upload_small_file(local_path, dest_folder, filename, drive_path)
        else:
            return self._upload_large_file(local_path, dest_folder, filename, drive_path)

    def _upload_small_file(self, local_path: Path, dest_folder: str, filename: str, drive_path: str) -> bool:
        """Upload small file (< 4MB) directly"""
        if dest_folder:
            url = f"{drive_path}/root:/{dest_folder}/{filename}:/content"
        else:
            url = f"{drive_path}/root:/{filename}:/content"

        try:
            with open(local_path, 'rb') as f:
                content = f.read()

            headers = self._headers()
            headers['Content-Type'] = 'application/octet-stream'

            response = requests.put(url, headers=headers, data=content)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to upload {filename}: {e}")
            return False

    def _upload_large_file(self, local_path: Path, dest_folder: str, filename: str, drive_path: str) -> bool:
        """Upload large file using upload session"""
        if dest_folder:
            url = f"{drive_path}/root:/{dest_folder}/{filename}:/createUploadSession"
        else:
            url = f"{drive_path}/root:/{filename}:/createUploadSession"

        try:
            # Create upload session
            session_response = requests.post(url, headers=self._headers(), json={
                "item": {"@microsoft.graph.conflictBehavior": "rename"}
            })
            session_response.raise_for_status()
            upload_url = session_response.json()["uploadUrl"]

            # Upload in chunks
            file_size = local_path.stat().st_size
            chunk_size = 10 * 1024 * 1024  # 10MB chunks

            with open(local_path, 'rb') as f:
                chunk_start = 0
                while chunk_start < file_size:
                    chunk_end = min(chunk_start + chunk_size, file_size) - 1
                    chunk_data = f.read(chunk_size)

                    headers = {
                        'Content-Length': str(len(chunk_data)),
                        'Content-Range': f'bytes {chunk_start}-{chunk_end}/{file_size}'
                    }

                    response = requests.put(upload_url, headers=headers, data=chunk_data)
                    response.raise_for_status()
                    chunk_start = chunk_end + 1

            return True
        except Exception as e:
            logger.error(f"Failed to upload large file {filename}: {e}")
            return False

    def create_folder(self, folder_path: str, user_id: Optional[str] = None) -> bool:
        """Create a folder in OneDrive (creates parent folders as needed)"""
        drive_path = self._get_drive_path(user_id)

        parts = folder_path.strip('/').split('/')
        current_path = ""

        for part in parts:
            if current_path:
                parent_url = f"{drive_path}/root:/{current_path}:/children"
            else:
                parent_url = f"{drive_path}/root/children"

            try:
                response = requests.post(parent_url, headers=self._headers(), json={
                    "name": part,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "fail"
                })

                if response.status_code not in [201, 409]:  # 409 = already exists
                    response.raise_for_status()

            except requests.exceptions.HTTPError as e:
                if e.response.status_code != 409:
                    logger.error(f"Failed to create folder {part}: {e}")
                    return False

            current_path = f"{current_path}/{part}" if current_path else part

        return True


class ExifToolWrapper:
    """Wrapper for exiftool operations"""

    def __init__(self):
        self.path = shutil.which('exiftool')
        self.available = self.path is not None

        if not self.available:
            logger.warning("ExifTool not found in PATH. Metadata writing will be limited.")

    def write_metadata(self, file_path: Path, tags: Dict[str, Any], sidecar: bool = True) -> bool:
        """Write metadata tags to a file"""
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
            if res.returncode != 0:
                logger.debug(f"ExifTool stderr: {res.stderr}")
                return False

            if sidecar:
                xmp_path = file_path.with_suffix(file_path.suffix + '.xmp')
                xmp_cmd = [self.path, '-tagsfromfile', str(file_path), '-all:all', str(xmp_path)]
                subprocess.run(xmp_cmd, capture_output=True)

            return True
        except Exception as e:
            logger.error(f"ExifTool error: {e}")
            return False

    def read_metadata(self, file_path: Path) -> Dict:
        """Read metadata from a file"""
        if not self.available:
            return {}

        cmd = [
            self.path, '-json', '-n', '-G',
            '-DateTimeOriginal', '-CreateDate', '-DateCreated',
            '-MediaCreateDate', '-Model', '-AndroidModel',
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


class OneDrivePhotoFixer:
    """Main class for processing photos from OneDrive"""

    def __init__(self, args):
        self.args = args
        self.src_folder = args.src_folder.strip('/')
        self.dst_folder = args.dst_folder.strip('/')
        self.dup_folder = f"{self.dst_folder}/duplicates"

        self.client = OneDriveClient(
            client_id=args.client_id,
            client_secret=args.client_secret,
            tenant_id=args.tenant_id
        )

        self.stats = Statistics()
        self.exiftool = ExifToolWrapper()
        self.tz = timezone(timedelta(hours=args.timezone))
        self.hash_db: Dict[str, str] = {}

        self.temp_dir = Path(tempfile.mkdtemp(prefix='onedrive_photo_fixer_'))
        self.processed_temp_dir = self.temp_dir / 'processed'
        self.processed_temp_dir.mkdir()

        logger.info(f"Using temporary directory: {self.temp_dir}")

    def cleanup(self):
        """Clean up temporary files"""
        try:
            shutil.rmtree(self.temp_dir)
            logger.info("Cleaned up temporary files")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp dir: {e}")

    def calculate_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return ""

    def find_json_in_items(self, file_name: str, all_items: List[Dict], folder_path: str) -> Optional[Dict]:
        """Find matching JSON metadata file from OneDrive items"""
        stem = Path(file_name).stem
        suffix = Path(file_name).suffix

        candidates = [
            f"{file_name}.json",
            f"{stem}.json",
            f"{file_name}.supplemental-metadata.json"
        ]

        for item in all_items:
            if item.get('_folder_path') != folder_path:
                continue

            item_name = item.get('name', '')
            if item_name in candidates:
                return item

            # Handle truncated filenames (Google Photos often truncates to ~40 chars)
            if item_name.endswith('.json') and stem[:40] in item_name:
                return item

        return None

    def infer_date_from_filename(self, filename: str) -> Optional[datetime]:
        """Try to extract date from filename patterns"""
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
                except:
                    continue
        return None

    def parse_exif_date(self, date_str: str) -> Optional[datetime]:
        """Parse various EXIF date formats"""
        try:
            if not date_str or str(date_str).startswith("0000"):
                return None
            clean_str = str(date_str)[:19].replace('-', ':').replace('/', ':')
            return datetime.strptime(clean_str, '%Y:%m:%d %H:%M:%S')
        except:
            return None

    def process_item(self, item: Dict, all_items: List[Dict]) -> bool:
        """Process a single file from OneDrive"""
        file_name = item.get('name', '')
        item_id = item.get('id')
        folder_path = item.get('_folder_path', '')

        suffix = Path(file_name).suffix.lower()
        if suffix not in ALL_TARGETS:
            self.stats.skipped += 1
            return True

        logger.info(f"Processing: {folder_path}/{file_name}")

        try:
            # Download file to temp directory
            local_file = self.temp_dir / file_name
            if not self.client.download_file(item_id, local_file):
                self.stats.errors += 1
                self.stats.issues.append(f"Download failed: {file_name}")
                return False

            # Check for duplicate
            file_hash = self.calculate_hash(local_file)
            if file_hash and file_hash in self.hash_db:
                logger.info(f"Duplicate found: {file_name} (matches {self.hash_db[file_hash]})")
                # Upload to duplicates folder
                self.client.create_folder(self.dup_folder)
                self.client.upload_file(local_file, self.dup_folder, file_name)
                self.stats.duplicates += 1
                local_file.unlink()
                return True

            if file_hash:
                self.hash_db[file_hash] = file_name

            meta_tags = {}
            source = "Unknown"

            # --- STEP 1: Read internal EXIF (Priority #1) ---
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

            # --- STEP 2: JSON metadata (Priority #2) ---
            if 'DateTimeOriginal' not in meta_tags:
                json_item = self.find_json_in_items(file_name, all_items, folder_path)
                if json_item:
                    json_local = self.temp_dir / json_item['name']
                    if self.client.download_file(json_item['id'], json_local):
                        try:
                            with open(json_local, 'r', encoding='utf-8') as f:
                                json_data = json.load(f)

                            ts = int(json_data.get('photoTakenTime', {}).get('timestamp', 0))
                            if ts > 0:
                                dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(self.tz).replace(tzinfo=None)
                                if 1980 < dt.year < 2030:
                                    meta_tags['DateTimeOriginal'] = dt
                                    meta_tags['CreateDate'] = dt
                                    source = "JSON"

                            # Also try to get geo data
                            geo_data = json_data.get('geoData', {})
                            if geo_data.get('latitude') and geo_data.get('longitude'):
                                meta_tags['GPSLatitude'] = geo_data['latitude']
                                meta_tags['GPSLongitude'] = geo_data['longitude']
                        except Exception as e:
                            logger.debug(f"JSON parse error: {e}")
                        finally:
                            json_local.unlink(missing_ok=True)

            # --- STEP 3: Filename (Priority #3) ---
            if 'DateTimeOriginal' not in meta_tags:
                inferred_dt = self.infer_date_from_filename(file_name)
                if inferred_dt:
                    meta_tags['DateTimeOriginal'] = inferred_dt
                    source = "Filename"

            # --- STEP 4: File modification time (fallback) ---
            if 'DateTimeOriginal' not in meta_tags:
                # Use OneDrive lastModifiedDateTime
                last_modified = item.get('lastModifiedDateTime')
                if last_modified:
                    try:
                        dt = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                        meta_tags['DateTimeOriginal'] = dt.astimezone(self.tz).replace(tzinfo=None)
                        source = "OneDrive_LastModified"
                    except:
                        meta_tags['DateTimeOriginal'] = datetime.fromtimestamp(local_file.stat().st_mtime)
                        source = "FileSystem_LastResort"
                else:
                    meta_tags['DateTimeOriginal'] = datetime.fromtimestamp(local_file.stat().st_mtime)
                    source = "FileSystem_LastResort"

            # Write metadata to file
            if meta_tags and self.exiftool.available:
                self.exiftool.write_metadata(local_file, meta_tags, sidecar=self.args.create_xmp)

            # Determine destination folder based on date
            final_dt = meta_tags.get('DateTimeOriginal', datetime.now())
            date_folder = final_dt.strftime('%Y/%Y-%m')
            dest_folder_path = f"{self.dst_folder}/{date_folder}"

            # Create folder and upload
            self.client.create_folder(dest_folder_path)

            if self.client.upload_file(local_file, dest_folder_path, file_name):
                logger.info(f"OK [{source}]: {file_name} -> {dest_folder_path}")
                self.stats.processed += 1
                self.stats.source_counts[source] += 1
                self.stats.file_types[suffix] += 1

                # Upload XMP sidecar if created
                if self.args.create_xmp:
                    xmp_file = local_file.with_suffix(suffix + '.xmp')
                    if xmp_file.exists():
                        self.client.upload_file(xmp_file, dest_folder_path, xmp_file.name)
            else:
                self.stats.errors += 1
                self.stats.issues.append(f"Upload failed: {file_name}")

            # Cleanup local file
            local_file.unlink(missing_ok=True)

            return True

        except Exception as e:
            logger.error(f"Error processing {file_name}: {e}")
            self.stats.errors += 1
            self.stats.issues.append(f"Error {file_name}: {str(e)}")
            return False

    def run(self):
        """Main execution method"""
        logger.info("=" * 60)
        logger.info("OneDrive Photo Fixer Started")
        logger.info(f"Source: {self.src_folder}")
        logger.info(f"Destination: {self.dst_folder}")
        logger.info("=" * 60)

        try:
            # List all files in source folder
            logger.info("Listing files in source folder...")
            all_items = self.client.list_folder(self.src_folder)

            # Filter to target file types
            media_items = [
                item for item in all_items
                if Path(item.get('name', '')).suffix.lower() in ALL_TARGETS
            ]

            self.stats.total_files = len(media_items)
            logger.info(f"Found {self.stats.total_files} media files to process")

            if not media_items:
                logger.warning("No media files found in source folder")
                return

            # Process files
            if self.args.threads > 1:
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

            # Generate and upload report
            report = self.stats.to_dict()
            report_json = json.dumps(report, indent=2, ensure_ascii=False, default=str)

            report_file = self.temp_dir / 'migration_report.json'
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_json)

            self.client.create_folder(self.dst_folder)
            self.client.upload_file(report_file, self.dst_folder, 'migration_report.json')

            logger.info("=" * 60)
            logger.info("Processing Complete!")
            logger.info(f"  Total files: {self.stats.total_files}")
            logger.info(f"  Processed: {self.stats.processed}")
            logger.info(f"  Duplicates: {self.stats.duplicates}")
            logger.info(f"  Errors: {self.stats.errors}")
            logger.info(f"  Duration: {round(time.time() - self.stats.start_time, 2)}s")
            logger.info("=" * 60)

            # Print report to stdout for GitHub Actions
            print("\n--- MIGRATION REPORT ---")
            print(report_json)

        finally:
            self.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="OneDrive Photo Metadata Fixer - Processes photos and fixes metadata"
    )

    # Required arguments (will be provided via environment variables in GitHub Actions)
    parser.add_argument(
        '--client-id',
        default=os.environ.get('AZURE_CLIENT_ID'),
        help='Azure App Client ID (or set AZURE_CLIENT_ID env var)'
    )
    parser.add_argument(
        '--client-secret',
        default=os.environ.get('AZURE_CLIENT_SECRET'),
        help='Azure App Client Secret (or set AZURE_CLIENT_SECRET env var)'
    )
    parser.add_argument(
        '--tenant-id',
        default=os.environ.get('AZURE_TENANT_ID'),
        help='Azure Tenant ID (or set AZURE_TENANT_ID env var)'
    )

    # Folder paths
    parser.add_argument(
        '--src-folder',
        default=os.environ.get('ONEDRIVE_SRC_FOLDER', 'Photos/Google Takeout'),
        help='Source folder path in OneDrive'
    )
    parser.add_argument(
        '--dst-folder',
        default=os.environ.get('ONEDRIVE_DST_FOLDER', 'Photos/Processed'),
        help='Destination folder path in OneDrive'
    )

    # Options
    parser.add_argument(
        '--timezone',
        type=int,
        default=int(os.environ.get('TZ_OFFSET', '9')),
        help='Timezone offset from UTC (default: 9 for JST)'
    )
    parser.add_argument(
        '--threads',
        type=int,
        default=int(os.environ.get('THREADS', '1')),
        help='Number of parallel threads (default: 1 for rate limit safety)'
    )
    parser.add_argument(
        '--create-xmp',
        action='store_true',
        default=os.environ.get('CREATE_XMP', '').lower() == 'true',
        help='Create XMP sidecar files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='List files without processing'
    )

    args = parser.parse_args()

    # Validate required credentials
    if not all([args.client_id, args.client_secret, args.tenant_id]):
        parser.error(
            "Azure credentials required. Provide via arguments or environment variables:\n"
            "  AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID"
        )

    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be modified")
        client = OneDriveClient(args.client_id, args.client_secret, args.tenant_id)
        items = client.list_folder(args.src_folder)
        for item in items:
            print(f"{item.get('_folder_path', '')}/{item.get('name', '')}")
        return

    fixer = OneDrivePhotoFixer(args)
    fixer.run()


if __name__ == '__main__':
    main()
