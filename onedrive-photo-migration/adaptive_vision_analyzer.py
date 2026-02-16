#!/usr/bin/env python3
"""
Adaptive Vision AI Analyzer for Photo Pipeline
Intelligently selects Vision API features per image based on context,
combines with Immich's built-in AI, and writes comprehensive XMP sidecars.

Design goals:
- Exceed Google Photos AI tagging (Japanese-first, hierarchical, portable)
- Minimize API costs by selecting only necessary features per image
- Combine Immich (free, built-in) + Vision AI (paid, adaptive)

Feature selection logic:
  ALL photos    : LABEL_DETECTION + SAFE_SEARCH_DETECTION
  Has GPS       : + LANDMARK_DETECTION
  Travel context: + LANDMARK_DETECTION + WEB_DETECTION
  Has faces     : + FACE_DETECTION (emotion analysis)
  Complex scene : + OBJECT_LOCALIZATION
  Overseas GPS  : + WEB_DETECTION (identify buildings, people, brands)
"""

import json
import logging
import math
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleRequest

logger = logging.getLogger(__name__)

# ============================================================
# Feature Profiles (cost per 1000 images after free tier)
# ============================================================

class FeatureProfile(Enum):
    """Vision API feature profiles with cost tiers"""
    MINIMAL     = "minimal"      # $1.50 - label + safe_search only
    STANDARD    = "standard"     # $3.00 - + object localization
    TRAVEL      = "travel"       # $4.50 - + landmark detection
    PORTRAIT    = "portrait"     # $4.50 - + face detection
    TRAVEL_FULL = "travel_full"  # $6.00 - + landmark + face
    FULL        = "full"         # $9.00 - all 6 features (matches ai-photo-analysis)

PROFILE_FEATURES: Dict[FeatureProfile, List[str]] = {
    FeatureProfile.MINIMAL: [
        "LABEL_DETECTION",
        "SAFE_SEARCH_DETECTION",
    ],
    FeatureProfile.STANDARD: [
        "LABEL_DETECTION",
        "OBJECT_LOCALIZATION",
        "SAFE_SEARCH_DETECTION",
    ],
    FeatureProfile.TRAVEL: [
        "LABEL_DETECTION",
        "LANDMARK_DETECTION",
        "OBJECT_LOCALIZATION",
        "SAFE_SEARCH_DETECTION",
    ],
    FeatureProfile.PORTRAIT: [
        "LABEL_DETECTION",
        "FACE_DETECTION",
        "OBJECT_LOCALIZATION",
        "SAFE_SEARCH_DETECTION",
    ],
    FeatureProfile.TRAVEL_FULL: [
        "LABEL_DETECTION",
        "LANDMARK_DETECTION",
        "FACE_DETECTION",
        "OBJECT_LOCALIZATION",
        "SAFE_SEARCH_DETECTION",
    ],
    FeatureProfile.FULL: [
        "LABEL_DETECTION",
        "LANDMARK_DETECTION",
        "FACE_DETECTION",
        "OBJECT_LOCALIZATION",
        "WEB_DETECTION",
        "SAFE_SEARCH_DETECTION",
    ],
}

# Cost in USD per 1000 images (each feature = $1.50)
PROFILE_COST_PER_1K: Dict[FeatureProfile, float] = {
    p: len([f for f in features if f != "SAFE_SEARCH_DETECTION"]) * 1.50
    for p, features in PROFILE_FEATURES.items()
}

# ============================================================
# Known Tourist Region Bounding Boxes (for GPS-based detection)
# ============================================================

TOURIST_REGIONS = [
    # Japan
    {"name": "京都", "lat": (34.9, 35.2), "lon": (135.6, 135.9)},
    {"name": "奈良", "lat": (34.5, 34.8), "lon": (135.7, 136.0)},
    {"name": "東京都心", "lat": (35.6, 35.75), "lon": (139.6, 139.9)},
    {"name": "鎌倉", "lat": (35.3, 35.4), "lon": (139.5, 139.6)},
    {"name": "日光", "lat": (36.7, 36.9), "lon": (139.5, 139.7)},
    {"name": "富士山", "lat": (35.2, 35.5), "lon": (138.6, 138.9)},
    {"name": "沖縄本島", "lat": (26.0, 26.8), "lon": (127.6, 128.3)},
    {"name": "広島", "lat": (34.3, 34.5), "lon": (132.3, 132.6)},
    # Major overseas destinations
    {"name": "パリ", "lat": (48.7, 49.0), "lon": (2.2, 2.5)},
    {"name": "ローマ", "lat": (41.8, 42.0), "lon": (12.4, 12.6)},
    {"name": "ニューヨーク", "lat": (40.5, 40.9), "lon": (-74.1, -73.7)},
    {"name": "バンコク", "lat": (13.6, 13.9), "lon": (100.4, 100.7)},
    {"name": "バリ島", "lat": (-8.8, -8.3), "lon": (115.0, 115.6)},
    {"name": "ソウル", "lat": (37.4, 37.7), "lon": (126.8, 127.2)},
    {"name": "台北", "lat": (24.9, 25.2), "lon": (121.4, 121.7)},
    {"name": "シンガポール", "lat": (1.2, 1.5), "lon": (103.6, 104.0)},
    {"name": "ロンドン", "lat": (51.3, 51.7), "lon": (-0.3, 0.2)},
    {"name": "プラハ", "lat": (50.0, 50.2), "lon": (14.3, 14.6)},
    {"name": "ドバイ", "lat": (25.0, 25.4), "lon": (55.1, 55.5)},
    {"name": "シドニー", "lat": (-34.1, -33.7), "lon": (150.9, 151.3)},
]

# ============================================================
# Hierarchical Tag Category Map (Japanese)
# ============================================================

CATEGORY_MAP: Dict[str, str] = {
    # 動物
    "Dog": "動物|哺乳類|犬", "Cat": "動物|哺乳類|猫", "Bird": "動物|鳥類",
    "Fish": "動物|魚類", "Insect": "動物|昆虫", "Wildlife": "動物|野生動物",
    "Horse": "動物|哺乳類|馬", "Cow": "動物|哺乳類|牛", "Deer": "動物|哺乳類|鹿",
    "Rabbit": "動物|哺乳類|ウサギ", "Bear": "動物|哺乳類|クマ",
    # 食べ物
    "Food": "食べ物", "Dish": "食べ物", "Cuisine": "食べ物",
    "Sushi": "食べ物|和食|寿司", "Ramen": "食べ物|和食|ラーメン",
    "Sashimi": "食べ物|和食|刺身", "Tempura": "食べ物|和食|天ぷら",
    "Pizza": "食べ物|洋食|ピザ", "Pasta": "食べ物|洋食|パスタ",
    "Cake": "食べ物|スイーツ|ケーキ", "Dessert": "食べ物|スイーツ",
    "Coffee": "食べ物|飲み物|コーヒー", "Tea": "食べ物|飲み物|お茶",
    "Beer": "食べ物|飲み物|ビール",
    # 場所・自然
    "Beach": "場所|自然|海辺", "Ocean": "場所|自然|海",
    "Mountain": "場所|自然|山", "Forest": "場所|自然|森林",
    "River": "場所|自然|川", "Lake": "場所|自然|湖",
    "Waterfall": "場所|自然|滝", "Flower": "場所|自然|花",
    "Garden": "場所|庭園", "Park": "場所|公園",
    # 都市・建築
    "City": "場所|都市", "Building": "場所|建築物",
    "Castle": "場所|建築物|城", "Temple": "場所|建築物|寺院",
    "Shrine": "場所|建築物|神社", "Church": "場所|建築物|教会",
    "Bridge": "場所|建築物|橋", "Tower": "場所|建築物|タワー",
    "Museum": "場所|施設|博物館", "Hotel": "場所|施設|ホテル",
    "Airport": "場所|施設|空港", "Station": "場所|施設|駅",
    "Restaurant": "場所|施設|レストラン",
    # 乗り物
    "Car": "乗り物|自動車", "Train": "乗り物|電車",
    "Airplane": "乗り物|飛行機", "Ship": "乗り物|船",
    "Bicycle": "乗り物|自転車", "Motorcycle": "乗り物|バイク",
    # 人物・イベント
    "Person": "人物", "Child": "人物|子供", "Baby": "人物|赤ちゃん",
    "Wedding": "イベント|結婚式", "Party": "イベント|パーティー",
    "Festival": "イベント|祭り", "Concert": "イベント|コンサート",
    "Sport": "スポーツ", "Fireworks": "イベント|花火",
    # 季節
    "Cherry blossom": "季節|春|桜", "Autumn leaves": "季節|秋|紅葉",
    "Snow": "季節|冬|雪",
    # テクノロジー
    "Smartphone": "テクノロジー|スマートフォン",
    "Computer": "テクノロジー|コンピューター",
    "Camera": "テクノロジー|カメラ",
}

# Labels that suggest portraits (trigger FACE_DETECTION)
PORTRAIT_LABELS = {
    "person", "face", "human", "woman", "man", "child", "baby",
    "people", "group", "crowd", "portrait", "selfie", "smile",
}

# Labels that suggest complex scenes (trigger OBJECT_LOCALIZATION)
COMPLEX_SCENE_LABELS = {
    "city", "street", "market", "store", "restaurant", "kitchen",
    "vehicle", "traffic", "stadium", "shopping",
}

# Likelihood values (Vision API returns strings like "LIKELY", "VERY_LIKELY")
UNSAFE_LIKELIHOODS = {"LIKELY", "VERY_LIKELY"}


# ============================================================
# Translation Cache
# ============================================================

class TranslationCache:
    """Persistent JSON translation cache to minimize DeepL API costs"""

    def __init__(self, cache_path: Path):
        self.cache_path = Path(cache_path)
        self._data: Dict[str, str] = {}
        self._hits = 0
        self._misses = 0
        self.load()

    def load(self):
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                logger.info(f"Translation cache loaded: {len(self._data)} entries")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self._data = {}

    def get(self, english: str) -> Optional[str]:
        result = self._data.get(english.lower())
        if result:
            self._hits += 1
        else:
            self._misses += 1
        return result

    def set(self, english: str, japanese: str):
        self._data[english.lower()] = japanese

    def save(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.cache_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(self.cache_path)

    def stats(self) -> Dict[str, int]:
        return {
            "entries": len(self._data),
            "hits": self._hits,
            "misses": self._misses,
        }


# ============================================================
# Vision API Client (raw HTTP, no heavy SDK)
# ============================================================

class VisionAPIClient:
    """Google Cloud Vision API using service account credentials"""

    VISION_URL = "https://vision.googleapis.com/v1/images:annotate"

    def __init__(self, credentials_json: str, max_labels: int = 20):
        self.max_labels = max_labels
        self._credentials = service_account.Credentials.from_service_account_info(
            json.loads(credentials_json),
            scopes=["https://www.googleapis.com/auth/cloud-vision"],
        )
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

    def _get_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token
        req = GoogleRequest()
        self._credentials.refresh(req)
        self._access_token = self._credentials.token
        self._token_expires_at = time.time() + 3600
        return self._access_token

    def annotate(self, image_path: Path, features: List[str]) -> Dict[str, Any]:
        """Call Vision API with specified features"""
        with open(image_path, "rb") as f:
            import base64
            content = base64.b64encode(f.read()).decode("utf-8")

        feature_objs = [
            {"type": f, "maxResults": self.max_labels}
            for f in features
        ]

        body = {
            "requests": [{
                "image": {"content": content},
                "features": feature_objs,
            }]
        }

        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

        resp = requests.post(self.VISION_URL, json=body, headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json()["responses"][0]

    def estimate_cost_usd(self, features: List[str]) -> float:
        """Estimate cost for one API call (excludes SAFE_SEARCH)"""
        billable = [f for f in features if f != "SAFE_SEARCH_DETECTION"]
        return len(billable) * 0.0015  # $1.50 per 1000 = $0.0015 each


# ============================================================
# DeepL Client
# ============================================================

class DeepLClient:
    """DeepL translation with batch support"""

    FREE_API = "https://api-free.deepl.com/v2/translate"
    PRO_API  = "https://api.deepl.com/v2/translate"

    def __init__(self, api_key: str, free_tier: bool = True):
        self.api_key = api_key
        self.endpoint = self.FREE_API if free_tier else self.PRO_API
        self._chars_used = 0

    def translate_batch(self, texts: List[str]) -> Dict[str, str]:
        """Translate up to 50 texts in one API call"""
        if not texts:
            return {}
        # DeepL max 50 per call
        results: Dict[str, str] = {}
        for i in range(0, len(texts), 50):
            batch = texts[i:i+50]
            payload = {
                "auth_key": self.api_key,
                "text": batch,
                "source_lang": "EN",
                "target_lang": "JA",
            }
            resp = requests.post(self.endpoint, data=payload, timeout=30)
            resp.raise_for_status()
            for original, translation in zip(batch, resp.json()["translations"]):
                results[original] = translation["text"]
                self._chars_used += len(original)
        return results

    @property
    def chars_used(self) -> int:
        return self._chars_used


# ============================================================
# XMP Writer (Immich-compatible sidecar)
# ============================================================

class XMPWriter:
    """
    Writes Immich-compatible XMP sidecar files.

    Immich external library sidecar format: photo.jpg.xmp (NOT photo.xmp)

    Fields written:
        dc:subject              → Japanese flat tags (Immich search)
        lr:hierarchicalSubject  → Hierarchical tags (動物|哺乳類|犬)
        dc:description          → Auto-generated Japanese description
        Iptc4xmpExt:LocationCreatedSublocation → Landmark name
        XMP:Rating              → 0 if unsafe content, 3 otherwise
        photoshop:Instructions  → Analysis metadata (for debugging)
    """

    def __init__(self, exiftool_path: str = "exiftool"):
        self.exiftool_path = exiftool_path

    def write(
        self,
        image_path: Path,
        tags_japanese: List[str],
        tags_hierarchical: List[str],
        landmark_name: Optional[str] = None,
        landmark_lat: Optional[float] = None,
        landmark_lon: Optional[float] = None,
        description_ja: Optional[str] = None,
        emotion_tags: Optional[List[str]] = None,
        is_unsafe: bool = False,
        analysis_profile: str = "",
    ) -> Optional[Path]:
        """Write XMP sidecar file alongside the image"""
        sidecar_path = Path(str(image_path) + ".xmp")

        cmd = [
            self.exiftool_path,
            "-overwrite_original", "-m",
            "-charset", "filename=UTF8",
        ]

        # dc:subject — Immich reads these as tags
        all_tags = list(dict.fromkeys(tags_japanese))  # deduplicate
        if emotion_tags:
            all_tags.extend(emotion_tags)
        if landmark_name:
            all_tags.append(f"📍{landmark_name}" if "📍" not in landmark_name else landmark_name)

        for tag in all_tags:
            cmd.append(f"-XMP-dc:Subject+={tag}")

        # lr:hierarchicalSubject — hierarchical navigation
        for htag in tags_hierarchical:
            cmd.append(f"-XMP-lr:HierarchicalSubject+={htag}")

        # Landmark location fields
        if landmark_name:
            cmd.append(f"-XMP-iptcExt:LocationCreatedSublocation={landmark_name}")

        # Overwrite GPS from landmark if no existing GPS
        if landmark_lat is not None and landmark_lon is not None:
            cmd.append(f"-XMP-exif:GPSLatitude={abs(landmark_lat)}")
            cmd.append(f"-XMP-exif:GPSLongitude={abs(landmark_lon)}")
            cmd.append(f"-XMP-exif:GPSLatitudeRef={'N' if landmark_lat >= 0 else 'S'}")
            cmd.append(f"-XMP-exif:GPSLongitudeRef={'E' if landmark_lon >= 0 else 'W'}")

        # Description
        if description_ja:
            cmd.append(f"-XMP-dc:Description={description_ja}")

        # Rating: 0 = unsafe, 3 = normal (Google Photos style)
        cmd.append(f"-XMP-xmp:Rating={'0' if is_unsafe else '3'}")

        # Analysis provenance
        if analysis_profile:
            cmd.append(f"-XMP-xmp:CreatorTool=AdaptiveVisionAnalyzer/{analysis_profile}")

        # Write to sidecar file (not embedded in image)
        cmd.extend(["-o", str(sidecar_path), str(image_path)])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )
            if result.returncode == 0:
                return sidecar_path
            else:
                logger.error(f"ExifTool XMP write failed: {result.stderr[:200]}")
                return None
        except Exception as e:
            logger.error(f"XMP write error: {e}")
            return None


# ============================================================
# Context Analyzer (pre-classify without Vision API)
# ============================================================

class ImageContextAnalyzer:
    """
    Pre-classifies images using EXIF + filename metadata,
    without making any API calls. Returns a FeatureProfile.
    """

    def __init__(self, home_lat: float = 35.6762, home_lon: float = 139.6503):
        """home_lat/home_lon: user's home location (default: Tokyo)"""
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.home_radius_km = 50  # within 50km = "at home"

    def _gps_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine formula"""
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    def _is_tourist_area(self, lat: float, lon: float) -> Optional[str]:
        """Check if GPS coordinates are within a known tourist region"""
        for region in TOURIST_REGIONS:
            if (region["lat"][0] <= lat <= region["lat"][1] and
                    region["lon"][0] <= lon <= region["lon"][1]):
                return region["name"]
        return None

    def _is_overseas(self, lat: float, lon: float) -> bool:
        """Check if coordinates are outside Japan"""
        in_japan = (24 <= lat <= 46) and (122 <= lon <= 154)
        return not in_japan

    def analyze(
        self,
        image_path: Path,
        exif_gps_lat: Optional[float] = None,
        exif_gps_lon: Optional[float] = None,
        immich_has_faces: bool = False,
    ) -> Tuple[FeatureProfile, Dict[str, Any]]:
        """
        Determine the optimal FeatureProfile for this image.

        Returns:
            (profile, context_info) - profile enum + dict with reasoning
        """
        context: Dict[str, Any] = {
            "has_gps": False,
            "tourist_area": None,
            "is_overseas": False,
            "distance_from_home_km": None,
            "has_faces": immich_has_faces,
            "travel_hint_from_path": False,
        }

        has_gps = exif_gps_lat is not None and exif_gps_lon is not None
        is_tourist = False
        is_overseas = False

        if has_gps:
            context["has_gps"] = True
            dist = self._gps_distance_km(
                self.home_lat, self.home_lon, exif_gps_lat, exif_gps_lon
            )
            context["distance_from_home_km"] = round(dist, 1)

            tourist_area = self._is_tourist_area(exif_gps_lat, exif_gps_lon)
            if tourist_area:
                context["tourist_area"] = tourist_area
                is_tourist = True

            is_overseas = self._is_overseas(exif_gps_lat, exif_gps_lon)
            context["is_overseas"] = is_overseas
            if is_overseas:
                is_tourist = True

        # Check path/folder for travel hints
        path_str = str(image_path).lower()
        travel_keywords = ["travel", "trip", "vacation", "tour", "旅行", "観光", "海外", "abroad"]
        if any(kw in path_str for kw in travel_keywords):
            context["travel_hint_from_path"] = True
            is_tourist = True

        # Determine profile
        if is_tourist and immich_has_faces:
            profile = FeatureProfile.TRAVEL_FULL
        elif is_tourist and is_overseas:
            profile = FeatureProfile.FULL  # overseas: WEB_DETECTION for famous landmarks
        elif is_tourist:
            profile = FeatureProfile.TRAVEL
        elif immich_has_faces:
            profile = FeatureProfile.PORTRAIT
        else:
            profile = FeatureProfile.STANDARD

        context["selected_profile"] = profile.value
        context["estimated_cost_usd"] = PROFILE_COST_PER_1K[profile] / 1000

        return profile, context


# ============================================================
# Result
# ============================================================

@dataclass
class AnalysisResult:
    image_path: Path
    success: bool
    profile_used: FeatureProfile
    context: Dict[str, Any]

    tags_english: List[str] = field(default_factory=list)
    tags_japanese: List[str] = field(default_factory=list)
    tags_hierarchical: List[str] = field(default_factory=list)

    landmark_name: Optional[str] = None
    landmark_lat: Optional[float] = None
    landmark_lon: Optional[float] = None

    face_count: int = 0
    emotion_tags: List[str] = field(default_factory=list)

    description_ja: Optional[str] = None
    is_unsafe: bool = False

    xmp_path: Optional[Path] = None
    error: Optional[str] = None
    estimated_cost_usd: float = 0.0


# ============================================================
# Main Orchestrator
# ============================================================

class AdaptiveVisionAnalyzer:
    """
    Orchestrates adaptive Vision AI analysis:
    1. Pre-classify image (free, using EXIF metadata)
    2. Select optimal Vision API features
    3. Call Vision API with selected features
    4. Translate labels to Japanese (with cache)
    5. Build hierarchical tags
    6. Write XMP sidecar (Immich-compatible)

    Exceeds Google Photos by:
    - Japanese-first tagging (dc:subject)
    - Hierarchical navigation (lr:hierarchicalSubject)
    - Landmark GPS correction
    - Emotion detection on faces
    - Portable XMP (works in Mylio, Lightroom, Digikam, etc.)
    - Privacy: no photos permanently stored by Google AI
    """

    def __init__(
        self,
        vision_credentials_json: str,
        deepl_api_key: str,
        deepl_free_tier: bool = True,
        min_confidence: float = 0.75,
        cache_path: Path = Path("/tmp/translation_cache.json"),
        home_lat: float = 35.6762,   # Tokyo default
        home_lon: float = 139.6503,
        dry_run: bool = False,
    ):
        self.vision = VisionAPIClient(vision_credentials_json)
        self.deepl = DeepLClient(deepl_api_key, free_tier=deepl_free_tier)
        self.cache = TranslationCache(cache_path)
        self.context_analyzer = ImageContextAnalyzer(home_lat=home_lat, home_lon=home_lon)
        self.xmp_writer = XMPWriter()
        self.min_confidence = min_confidence
        self.dry_run = dry_run

        self._total_cost_usd = 0.0
        self._api_calls = 0
        self._results: List[AnalysisResult] = []

    def _parse_gps(self, exif_data: Dict) -> Tuple[Optional[float], Optional[float]]:
        """Extract GPS from EXIF dict (various formats)"""
        lat = exif_data.get("GPSLatitude") or exif_data.get("EXIF:GPSLatitude")
        lon = exif_data.get("GPSLongitude") or exif_data.get("EXIF:GPSLongitude")
        if lat is not None and lon is not None:
            try:
                lat_ref = exif_data.get("GPSLatitudeRef", "N")
                lon_ref = exif_data.get("GPSLongitudeRef", "E")
                lat = float(lat) * (-1 if lat_ref == "S" else 1)
                lon = float(lon) * (-1 if lon_ref == "W" else 1)
                return lat, lon
            except (ValueError, TypeError):
                pass
        return None, None

    def _extract_labels(self, response: Dict, min_confidence: float) -> List[str]:
        labels = []
        for ann in response.get("labelAnnotations", []):
            if ann.get("score", 0) >= min_confidence:
                labels.append(ann["description"])
        return labels

    def _extract_landmarks(self, response: Dict) -> List[Tuple[str, float, Optional[float], Optional[float]]]:
        """Returns list of (name, score, lat, lon)"""
        landmarks = []
        for ann in response.get("landmarkAnnotations", []):
            lat, lon = None, None
            for loc in ann.get("locations", []):
                lat_lng = loc.get("latLng", {})
                lat = lat_lng.get("latitude")
                lon = lat_lng.get("longitude")
                break
            landmarks.append((ann["description"], ann.get("score", 0), lat, lon))
        return landmarks

    def _extract_faces(self, response: Dict) -> Tuple[int, List[str]]:
        """Returns (face_count, emotion_tags_japanese)"""
        faces = response.get("faceAnnotations", [])
        emotions = []
        joy_count = sum(1 for f in faces if f.get("joyLikelihood") in ("LIKELY", "VERY_LIKELY"))
        if joy_count > 0:
            emotions.append("笑顔")
        surprise_count = sum(1 for f in faces if f.get("surpriseLikelihood") in ("LIKELY", "VERY_LIKELY"))
        if surprise_count > 0:
            emotions.append("驚き")
        sorrow_count = sum(1 for f in faces if f.get("sorrowLikelihood") in ("LIKELY", "VERY_LIKELY"))
        if sorrow_count > 0:
            emotions.append("悲しみ")
        return len(faces), emotions

    def _extract_objects(self, response: Dict, min_confidence: float) -> List[str]:
        objects = []
        for obj in response.get("localizedObjectAnnotations", []):
            if obj.get("score", 0) >= min_confidence:
                objects.append(obj["name"])
        return objects

    def _extract_web_entities(self, response: Dict) -> List[str]:
        entities = []
        web = response.get("webDetection", {})
        for entity in web.get("webEntities", []):
            if entity.get("score", 0) >= self.min_confidence and entity.get("description"):
                entities.append(entity["description"])
        return entities[:5]  # limit web entities

    def _is_unsafe(self, response: Dict) -> bool:
        safe = response.get("safeSearchAnnotation", {})
        return any(
            safe.get(field) in UNSAFE_LIKELIHOODS
            for field in ("adult", "violence")
        )

    def _build_hierarchical(self, english_labels: List[str], japanese_labels: List[str]) -> List[str]:
        """Build hierarchical tags by matching against CATEGORY_MAP"""
        hierarchical = []
        for en_label in english_labels:
            hier = CATEGORY_MAP.get(en_label)
            if hier:
                hierarchical.append(hier)
        # Deduplicate parent paths
        seen = set()
        result = []
        for h in hierarchical:
            if h not in seen:
                seen.add(h)
                result.append(h)
        return result

    def _build_description(
        self,
        tags_ja: List[str],
        landmark: Optional[str],
        face_count: int,
        tourist_area: Optional[str],
    ) -> Optional[str]:
        """Generate a brief Japanese description from detected elements"""
        parts = []
        if landmark:
            parts.append(f"{landmark}を含む写真")
        elif tourist_area:
            parts.append(f"{tourist_area}での写真")
        if face_count > 0:
            parts.append(f"{face_count}人が写っています")
        if tags_ja:
            top5 = tags_ja[:5]
            parts.append(f"タグ: {', '.join(top5)}")
        return "。".join(parts) if parts else None

    def _translate_labels(self, english_labels: List[str]) -> Dict[str, str]:
        """Translate using cache first, DeepL for cache misses"""
        cached = {}
        to_translate = []
        for label in english_labels:
            cached_result = self.cache.get(label)
            if cached_result:
                cached[label] = cached_result
            else:
                to_translate.append(label)

        new_translations = {}
        if to_translate and not self.dry_run:
            new_translations = self.deepl.translate_batch(to_translate)
            for en, ja in new_translations.items():
                self.cache.set(en, ja)
            self.cache.save()

        return {**cached, **new_translations}

    def analyze(
        self,
        image_path: Path,
        exif_data: Optional[Dict] = None,
        immich_has_faces: bool = False,
        force_profile: Optional[FeatureProfile] = None,
    ) -> AnalysisResult:
        """
        Analyze a single image with adaptive feature selection.

        Args:
            image_path: Path to local image file
            exif_data: EXIF dict from ExifTool (for GPS pre-classification)
            immich_has_faces: Whether Immich already found faces in this image
            force_profile: Override automatic profile selection
        """
        exif_data = exif_data or {}
        gps_lat, gps_lon = self._parse_gps(exif_data)

        # Step 1: Pre-classify
        profile, context = self.context_analyzer.analyze(
            image_path, gps_lat, gps_lon, immich_has_faces
        )
        if force_profile:
            profile = force_profile
            context["selected_profile"] = profile.value

        result = AnalysisResult(
            image_path=image_path,
            success=False,
            profile_used=profile,
            context=context,
            estimated_cost_usd=context.get("estimated_cost_usd", 0),
        )

        if self.dry_run:
            result.success = True
            logger.info(
                f"[DRY RUN] {image_path.name}: "
                f"profile={profile.value}, "
                f"estimated_cost=${result.estimated_cost_usd:.4f}"
            )
            self._results.append(result)
            return result

        # Step 2: Call Vision API
        features = PROFILE_FEATURES[profile]
        try:
            logger.info(
                f"{image_path.name}: "
                f"profile={profile.value}, "
                f"features={[f[:6] for f in features]}"
            )
            response = self.vision.annotate(image_path, features)
            self._api_calls += 1
            self._total_cost_usd += self.vision.estimate_cost_usd(features)
        except Exception as e:
            result.error = f"Vision API error: {e}"
            logger.error(result.error)
            self._results.append(result)
            return result

        # Step 3: Safety check
        if self._is_unsafe(response):
            result.is_unsafe = True
            logger.warning(f"Unsafe content detected: {image_path.name}")
            result.success = True
            result.xmp_path = self.xmp_writer.write(
                image_path, ["閲覧注意"], [], is_unsafe=True,
                analysis_profile=profile.value,
            )
            self._results.append(result)
            return result

        # Step 4: Extract results
        en_labels = self._extract_labels(response, self.min_confidence)
        en_objects = self._extract_objects(response, self.min_confidence)
        en_web = self._extract_web_entities(response)
        all_english = list(dict.fromkeys(en_labels + en_objects + en_web))

        landmarks = self._extract_landmarks(response)
        if landmarks:
            top = landmarks[0]
            result.landmark_name = top[0]
            result.landmark_lat = top[2]
            result.landmark_lon = top[3]

        if "FACE_DETECTION" in features:
            result.face_count, result.emotion_tags = self._extract_faces(response)

        # Step 5: Translate
        translations = self._translate_labels(all_english)
        result.tags_english = all_english
        result.tags_japanese = [translations.get(e, e) for e in all_english]

        # Step 6: Build hierarchical tags
        result.tags_hierarchical = self._build_hierarchical(all_english, result.tags_japanese)

        # Add tourist area as hierarchical tag
        tourist_area = context.get("tourist_area")
        if tourist_area:
            result.tags_hierarchical.append(f"場所|{tourist_area}")
        if context.get("is_overseas"):
            result.tags_hierarchical.append("旅行|海外")

        # Step 7: Generate description
        result.description_ja = self._build_description(
            result.tags_japanese, result.landmark_name,
            result.face_count, tourist_area,
        )

        # Step 8: Write XMP
        result.xmp_path = self.xmp_writer.write(
            image_path=image_path,
            tags_japanese=result.tags_japanese,
            tags_hierarchical=result.tags_hierarchical,
            landmark_name=result.landmark_name,
            landmark_lat=result.landmark_lat,
            landmark_lon=result.landmark_lon,
            description_ja=result.description_ja,
            emotion_tags=result.emotion_tags,
            is_unsafe=False,
            analysis_profile=profile.value,
        )

        result.success = result.xmp_path is not None
        logger.info(
            f"OK {image_path.name}: "
            f"{len(result.tags_japanese)} tags, "
            f"landmark={result.landmark_name}, "
            f"faces={result.face_count}"
        )

        self._results.append(result)
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics"""
        successful = [r for r in self._results if r.success]
        profile_counts = {}
        for r in self._results:
            k = r.profile_used.value
            profile_counts[k] = profile_counts.get(k, 0) + 1

        return {
            "total": len(self._results),
            "successful": len(successful),
            "failed": len(self._results) - len(successful),
            "total_cost_usd": round(self._total_cost_usd, 4),
            "api_calls": self._api_calls,
            "deepl_chars_used": self.deepl.chars_used,
            "translation_cache": self.cache.stats(),
            "profile_distribution": profile_counts,
            "cost_breakdown_usd_per_profile": {
                k: round(v * PROFILE_COST_PER_1K[FeatureProfile(k)] / 1000, 4)
                for k, v in profile_counts.items()
            },
        }


# ============================================================
# Immich API Helper (query face detection results)
# ============================================================

class ImmichClient:
    """
    Query Immich to check if it has already detected faces,
    smart album assignments, etc. Used for adaptive feature selection.
    """

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
        }

    def get_asset_by_filename(self, filename: str) -> Optional[Dict]:
        """Find an Immich asset by filename"""
        try:
            resp = requests.get(
                f"{self.base_url}/api/search/metadata",
                headers=self.headers,
                params={"originalFileName": filename},
                timeout=10,
            )
            resp.raise_for_status()
            assets = resp.json().get("assets", {}).get("items", [])
            return assets[0] if assets else None
        except Exception as e:
            logger.debug(f"Immich lookup failed for {filename}: {e}")
            return None

    def asset_has_faces(self, asset: Dict) -> bool:
        """Check if Immich has detected faces in this asset"""
        return len(asset.get("people", [])) > 0

    def trigger_library_scan(self, library_id: str) -> bool:
        """Trigger a rescan of an external library"""
        try:
            resp = requests.post(
                f"{self.base_url}/api/library/{library_id}/scan",
                headers=self.headers,
                json={"refreshModifiedFiles": True, "refreshAllFiles": False},
                timeout=30,
            )
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Failed to trigger Immich scan: {e}")
            return False


# ============================================================
# CLI (standalone testing)
# ============================================================

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Adaptive Vision AI Analyzer - standalone test"
    )
    parser.add_argument("image_path", help="Path to image file")
    parser.add_argument("--credentials", default=os.environ.get("GOOGLE_VISION_CREDENTIALS_JSON"))
    parser.add_argument("--deepl-key", default=os.environ.get("DEEPL_API_KEY"))
    parser.add_argument("--deepl-free", action="store_true", default=True)
    parser.add_argument("--confidence", type=float, default=0.75)
    parser.add_argument("--cache", default="/tmp/translation_cache.json")
    parser.add_argument("--profile", choices=[p.value for p in FeatureProfile], default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--home-lat", type=float, default=35.6762)
    parser.add_argument("--home-lon", type=float, default=139.6503)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if not args.credentials or not args.deepl_key:
        print("Error: --credentials and --deepl-key are required")
        sys.exit(1)

    analyzer = AdaptiveVisionAnalyzer(
        vision_credentials_json=args.credentials,
        deepl_api_key=args.deepl_key,
        deepl_free_tier=args.deepl_free,
        min_confidence=args.confidence,
        cache_path=Path(args.cache),
        home_lat=args.home_lat,
        home_lon=args.home_lon,
        dry_run=args.dry_run,
    )

    force_profile = FeatureProfile(args.profile) if args.profile else None
    result = analyzer.analyze(Path(args.image_path), force_profile=force_profile)

    print("\n=== Result ===")
    print(f"Profile: {result.profile_used.value}")
    print(f"Tags (JA): {result.tags_japanese}")
    print(f"Hierarchical: {result.tags_hierarchical}")
    print(f"Landmark: {result.landmark_name}")
    print(f"Faces: {result.face_count}, Emotions: {result.emotion_tags}")
    print(f"Description: {result.description_ja}")
    print(f"XMP written: {result.xmp_path}")
    print(f"Cost: ${result.estimated_cost_usd:.4f}")
    print(f"\nStats: {json.dumps(analyzer.get_stats(), ensure_ascii=False, indent=2)}")
