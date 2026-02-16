"""
zip_extractor.py - OneDrive ZIP file extractor for Google Takeout archives

Downloads ZIP files from OneDrive and extracts them to a temporary directory,
producing synthetic OneDrive item dicts with _local_path fields so that
onedrive_photo_fixer.py can process extracted files without re-downloading.
"""

import io
import logging
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Supported image/video extensions to extract
MEDIA_EXTENSIONS = {
    # Images
    ".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif",
    ".heic", ".heif", ".avif", ".bmp",
    # RAW
    ".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf",
    ".rw2", ".orf", ".pef", ".srw", ".x3f",
    # Video
    ".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp",
    ".wmv", ".flv", ".webm", ".mts", ".m2ts",
    # Metadata sidecars (kept alongside media)
    ".json", ".xmp",
}


class ZipExtractor:
    """Downloads and extracts Google Takeout ZIP files from OneDrive."""

    def __init__(self, onedrive_client):
        """
        Args:
            onedrive_client: OneDriveClient instance from onedrive_photo_fixer.py
        """
        self.client = onedrive_client

    def find_zips(self, folder_path: str) -> List[Dict]:
        """
        Find all .zip files in the specified OneDrive folder.

        Args:
            folder_path: OneDrive folder path (e.g., "Photos/Google Takeout ZIPs")

        Returns:
            List of OneDrive item dicts for each ZIP file found
        """
        logger.info(f"Scanning for ZIP files in: {folder_path}")
        all_items = self.client.list_files(folder_path)
        zip_items = [
            item for item in all_items
            if item.get("name", "").lower().endswith(".zip")
            and "file" in item  # Exclude folders
        ]
        logger.info(f"Found {len(zip_items)} ZIP file(s)")
        for item in zip_items:
            size_mb = item.get("size", 0) / 1024 / 1024
            logger.info(f"  - {item['name']} ({size_mb:.1f} MB)")
        return zip_items

    def download_and_extract(
        self,
        zip_item: Dict,
        extract_to: Path,
        zip_folder_path: str,
    ) -> List[Path]:
        """
        Download a ZIP from OneDrive and extract media files to extract_to.

        Args:
            zip_item: OneDrive item dict for the ZIP file
            extract_to: Local directory to extract files into
            zip_folder_path: OneDrive folder path containing the ZIP

        Returns:
            List of Paths to extracted media files (not JSON/XMP)
        """
        zip_name = zip_item["name"]
        zip_subdir = extract_to / zip_name.replace(".zip", "").replace(" ", "_")
        zip_subdir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading ZIP: {zip_name}")
        zip_path_in_onedrive = f"{zip_folder_path}/{zip_name}"

        # Download ZIP content into memory
        zip_bytes = self.client.download_file(zip_path_in_onedrive)
        if not zip_bytes:
            logger.error(f"Failed to download {zip_name}")
            return []

        logger.info(f"Extracting {zip_name} ({len(zip_bytes) / 1024 / 1024:.1f} MB)...")
        extracted_media: List[Path] = []

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                members = zf.infolist()
                logger.info(f"  {len(members)} entries in archive")

                for member in members:
                    member_path = Path(member.filename)
                    ext = member_path.suffix.lower()

                    # Skip directories and unsupported extensions
                    if member.is_dir() or ext not in MEDIA_EXTENSIONS:
                        continue

                    # Flatten path: use only filename (avoid deep nesting)
                    dest_file = zip_subdir / member_path.name
                    # Handle duplicate filenames from different subdirs
                    if dest_file.exists():
                        stem = member_path.stem
                        # Append parent dir name to disambiguate
                        parent_name = member_path.parent.name or "root"
                        dest_file = zip_subdir / f"{stem}__{parent_name}{ext}"

                    with zf.open(member) as src, open(dest_file, "wb") as dst:
                        dst.write(src.read())

                    if ext not in (".json", ".xmp"):
                        extracted_media.append(dest_file)

        except zipfile.BadZipFile as e:
            logger.error(f"Bad ZIP file {zip_name}: {e}")
            return []

        logger.info(f"  Extracted {len(extracted_media)} media files to {zip_subdir}")
        return extracted_media

    def build_synthetic_items(
        self,
        files: List[Path],
        base_path: Path,
        original_zip_name: str,
    ) -> List[Dict]:
        """
        Build synthetic OneDrive-style item dicts from local extracted files.

        The '_local_path' field signals process_item() to skip OneDrive download.
        The '_json_sidecar_path' field points to the co-located Google Takeout JSON.

        Args:
            files: List of local media file paths
            base_path: Root extraction directory (for relative path computation)
            original_zip_name: Name of the source ZIP (for logging)

        Returns:
            List of synthetic item dicts compatible with process_item()
        """
        synthetic_items = []
        for file_path in files:
            ext = file_path.suffix.lower()
            if ext in (".json", ".xmp"):
                continue

            # Look for Google Takeout JSON sidecar
            json_sidecar = self._find_json_sidecar(file_path)

            item = {
                # Standard OneDrive item fields
                "name": file_path.name,
                "id": f"local::{file_path}",  # Unique synthetic ID
                "size": file_path.stat().st_size if file_path.exists() else 0,
                "file": {"mimeType": _mime_type(ext)},
                "parentReference": {"path": f"/drive/root:/{original_zip_name}"},
                # Extended fields for local processing
                "_local_path": str(file_path),
                "_json_sidecar_path": str(json_sidecar) if json_sidecar else None,
                "_source_zip": original_zip_name,
            }
            synthetic_items.append(item)

        logger.info(
            f"Built {len(synthetic_items)} synthetic items from {original_zip_name}"
        )
        return synthetic_items

    def _find_json_sidecar(self, media_path: Path) -> Optional[Path]:
        """
        Locate the Google Takeout JSON sidecar for a media file.

        Google Takeout uses several naming conventions:
          - photo.jpg.json
          - photo.json
          - photo(1).jpg.json  (for edited copies)
        """
        candidates = [
            media_path.parent / (media_path.name + ".json"),
            media_path.parent / (media_path.stem + ".json"),
            # Truncated names (Google Takeout caps filenames at 51 chars)
            media_path.parent / (media_path.name[:47] + ".json"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None


def _mime_type(ext: str) -> str:
    """Return a plausible MIME type for the given extension."""
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
        ".heic": "image/heic", ".heif": "image/heif",
        ".tiff": "image/tiff", ".tif": "image/tiff",
        ".avif": "image/avif", ".dng": "image/x-adobe-dng",
        ".mp4": "video/mp4", ".mov": "video/quicktime",
        ".avi": "video/x-msvideo", ".mkv": "video/x-matroska",
        ".m4v": "video/mp4",
    }
    return mime_map.get(ext, "application/octet-stream")
