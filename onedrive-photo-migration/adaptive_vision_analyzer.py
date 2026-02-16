#!/usr/bin/env python3
"""
Adaptive Vision AI Analyzer for Photo Pipeline (v2.0 - Full Feature Support)

Intelligently selects Vision API features per image based on comprehensive
content analysis. Supports ALL Vision API features:

  - LABEL_DETECTION       : 一般的なラベル検出 (常時)
  - OBJECT_LOCALIZATION   : 物体検出 (複雑なシーン)
  - FACE_DETECTION        : 顔検出・感情分析 (人物写真)
  - TEXT_DETECTION        : テキスト抽出 (文書・標識)
  - DOCUMENT_TEXT_DETECTION: 詳細テキスト抽出 (文書)
  - LOGO_DETECTION        : ロゴ検出 (製品・イベント)
  - LANDMARK_DETECTION    : ランドマーク検出 (観光地)
  - IMAGE_PROPERTIES      : ドミナントカラー (アート・デザイン)
  - WEB_DETECTION         : Web検索 (海外・有名人)
  - SAFE_SEARCH_DETECTION : セーフサーチ (常時)

Feature selection logic (pre-classification without API calls):
  1. スクリーンショット検出 → TEXT_DETECTION, IMAGE_PROPERTIES
  2. 文書検出 → DOCUMENT_TEXT_DETECTION, TEXT_DETECTION
  3. 観光地GPS → LANDMARK_DETECTION + WEB_DETECTION
  4. 人物/セルフィー → FACE_DETECTION
  5. 製品/イベント → LOGO_DETECTION + OBJECT_LOCALIZATION
  6. 自然/動物 → LABEL_DETECTION + OBJECT_LOCALIZATION
  7. アート/デザイン → IMAGE_PROPERTIES

GitHub Actions で実行、VPS上ではImmich閲覧のみ。
"""

import base64
import json
import logging
import math
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleRequest

logger = logging.getLogger(__name__)


# ============================================================
# Vision API Feature Types
# ============================================================

class VisionFeature(Enum):
    """All available Vision API feature types"""
    LABEL_DETECTION = "LABEL_DETECTION"               # $1.50/1K - 一般ラベル
    OBJECT_LOCALIZATION = "OBJECT_LOCALIZATION"       # $1.50/1K - 物体検出
    FACE_DETECTION = "FACE_DETECTION"                 # $1.50/1K - 顔検出・感情
    TEXT_DETECTION = "TEXT_DETECTION"                 # $1.50/1K - OCR
    DOCUMENT_TEXT_DETECTION = "DOCUMENT_TEXT_DETECTION"  # $1.50/1K - 詳細OCR
    LOGO_DETECTION = "LOGO_DETECTION"                 # $1.50/1K - ロゴ検出
    LANDMARK_DETECTION = "LANDMARK_DETECTION"         # $1.50/1K - ランドマーク
    IMAGE_PROPERTIES = "IMAGE_PROPERTIES"             # $1.50/1K - ドミナントカラー
    WEB_DETECTION = "WEB_DETECTION"                   # $1.50/1K - Web検索
    SAFE_SEARCH_DETECTION = "SAFE_SEARCH_DETECTION"   # Free - セーフサーチ


# Feature cost: $1.50 per 1000 requests (SAFE_SEARCH is free)
FEATURE_COST_USD = {
    f: 0.0 if f == VisionFeature.SAFE_SEARCH_DETECTION else 0.0015
    for f in VisionFeature
}


# ============================================================
# Image Content Type Classification
# ============================================================

class ImageContentType(Enum):
    """Pre-classified image content types"""
    SCREENSHOT = auto()      # スクリーンショット
    DOCUMENT = auto()        # 文書・書類
    PRODUCT = auto()         # 製品写真
    TRAVEL = auto()          # 旅行・観光
    PORTRAIT = auto()        # 人物・ポートレート
    GROUP_PHOTO = auto()     # 集合写真
    NATURE = auto()          # 自然・風景
    FOOD = auto()            # 料理・食べ物
    ART = auto()             # アート・デザイン
    EVENT = auto()           # イベント・行事
    GENERAL = auto()         # 一般


# Content type → Recommended features mapping
CONTENT_TYPE_FEATURES: Dict[ImageContentType, List[VisionFeature]] = {
    ImageContentType.SCREENSHOT: [
        VisionFeature.TEXT_DETECTION,
        VisionFeature.IMAGE_PROPERTIES,
        VisionFeature.SAFE_SEARCH_DETECTION,
    ],
    ImageContentType.DOCUMENT: [
        VisionFeature.DOCUMENT_TEXT_DETECTION,
        VisionFeature.TEXT_DETECTION,
        VisionFeature.SAFE_SEARCH_DETECTION,
    ],
    ImageContentType.PRODUCT: [
        VisionFeature.LOGO_DETECTION,
        VisionFeature.OBJECT_LOCALIZATION,
        VisionFeature.LABEL_DETECTION,
        VisionFeature.IMAGE_PROPERTIES,
        VisionFeature.SAFE_SEARCH_DETECTION,
    ],
    ImageContentType.TRAVEL: [
        VisionFeature.LANDMARK_DETECTION,
        VisionFeature.LABEL_DETECTION,
        VisionFeature.OBJECT_LOCALIZATION,
        VisionFeature.WEB_DETECTION,
        VisionFeature.SAFE_SEARCH_DETECTION,
    ],
    ImageContentType.PORTRAIT: [
        VisionFeature.FACE_DETECTION,
        VisionFeature.LABEL_DETECTION,
        VisionFeature.OBJECT_LOCALIZATION,
        VisionFeature.SAFE_SEARCH_DETECTION,
    ],
    ImageContentType.GROUP_PHOTO: [
        VisionFeature.FACE_DETECTION,
        VisionFeature.LABEL_DETECTION,
        VisionFeature.OBJECT_LOCALIZATION,
        VisionFeature.SAFE_SEARCH_DETECTION,
    ],
    ImageContentType.NATURE: [
        VisionFeature.LABEL_DETECTION,
        VisionFeature.OBJECT_LOCALIZATION,
        VisionFeature.IMAGE_PROPERTIES,
        VisionFeature.SAFE_SEARCH_DETECTION,
    ],
    ImageContentType.FOOD: [
        VisionFeature.LABEL_DETECTION,
        VisionFeature.OBJECT_LOCALIZATION,
        VisionFeature.IMAGE_PROPERTIES,
        VisionFeature.SAFE_SEARCH_DETECTION,
    ],
    ImageContentType.ART: [
        VisionFeature.LABEL_DETECTION,
        VisionFeature.IMAGE_PROPERTIES,
        VisionFeature.TEXT_DETECTION,
        VisionFeature.SAFE_SEARCH_DETECTION,
    ],
    ImageContentType.EVENT: [
        VisionFeature.FACE_DETECTION,
        VisionFeature.LOGO_DETECTION,
        VisionFeature.LABEL_DETECTION,
        VisionFeature.OBJECT_LOCALIZATION,
        VisionFeature.TEXT_DETECTION,
        VisionFeature.SAFE_SEARCH_DETECTION,
    ],
    ImageContentType.GENERAL: [
        VisionFeature.LABEL_DETECTION,
        VisionFeature.OBJECT_LOCALIZATION,
        VisionFeature.SAFE_SEARCH_DETECTION,
    ],
}


# ============================================================
# Filename/Path Pattern Matchers
# ============================================================

# Screenshot indicators
SCREENSHOT_PATTERNS = [
    r'screenshot', r'screen.?shot', r'screen.?capture', r'スクリーンショット',
    r'スクショ', r'画面キャプチャ', r'IMG_\d{4}\.PNG$',  # iOS screenshot pattern
    r'Screenshot_\d{8}', r'Screenshot_\d{4}-\d{2}-\d{2}',  # Android patterns
]

# Document indicators
DOCUMENT_PATTERNS = [
    r'document', r'doc', r'scan', r'書類', r'文書', r'レシート', r'receipt',
    r'invoice', r'請求書', r'contract', r'契約書', r'resume', r'履歴書',
    r'pdf', r'form', r'certificate', r'証明書',
]

# Product/shopping indicators
PRODUCT_PATTERNS = [
    r'product', r'商品', r'製品', r'買い物', r'shopping', r'amazon', r'楽天',
    r'unboxing', r'review', r'レビュー',
]

# Travel/tourism indicators
TRAVEL_PATTERNS = [
    r'travel', r'trip', r'vacation', r'tour', r'旅行', r'観光', r'海外',
    r'abroad', r'holiday', r'sightseeing', r'temple', r'寺', r'神社', r'shrine',
    r'castle', r'城', r'museum', r'博物館',
]

# Portrait/selfie indicators
PORTRAIT_PATTERNS = [
    r'selfie', r'portrait', r'自撮り', r'セルフィー', r'ポートレート',
    r'profile', r'headshot', r'IMG_\d{4}\.HEIC$',  # iPhone selfie
]

# Group photo indicators
GROUP_PATTERNS = [
    r'group', r'集合', r'family', r'家族', r'wedding', r'結婚式',
    r'party', r'パーティー', r'reunion', r'同窓会',
]

# Nature/landscape indicators
NATURE_PATTERNS = [
    r'nature', r'landscape', r'scenery', r'自然', r'風景', r'山', r'mountain',
    r'海', r'beach', r'ocean', r'森', r'forest', r'花', r'flower', r'sunset',
    r'sunrise', r'夕焼け', r'朝焼け',
]

# Food indicators
FOOD_PATTERNS = [
    r'food', r'meal', r'料理', r'ご飯', r'ランチ', r'lunch', r'dinner',
    r'breakfast', r'朝食', r'夕食', r'restaurant', r'レストラン', r'cafe',
    r'カフェ', r'sushi', r'寿司', r'ramen', r'ラーメン',
]

# Art/design indicators
ART_PATTERNS = [
    r'art', r'design', r'デザイン', r'アート', r'illustration', r'イラスト',
    r'painting', r'絵画', r'creative', r'artwork',
]

# Event indicators
EVENT_PATTERNS = [
    r'event', r'イベント', r'festival', r'祭り', r'concert', r'コンサート',
    r'live', r'ライブ', r'ceremony', r'式典', r'graduation', r'卒業',
    r'birthday', r'誕生日', r'christmas', r'クリスマス', r'fireworks', r'花火',
]


# ============================================================
# Known Tourist Regions (GPS bounding boxes)
# ============================================================

TOURIST_REGIONS = [
    # Japan
    {"name": "京都", "lat": (34.9, 35.2), "lon": (135.6, 135.9)},
    {"name": "奈良", "lat": (34.5, 34.8), "lon": (135.7, 136.0)},
    {"name": "東京都心", "lat": (35.6, 35.75), "lon": (139.6, 139.9)},
    {"name": "鎌倉", "lat": (35.3, 35.4), "lon": (139.5, 139.6)},
    {"name": "日光", "lat": (36.7, 36.9), "lon": (139.5, 139.7)},
    {"name": "富士山周辺", "lat": (35.2, 35.5), "lon": (138.6, 138.9)},
    {"name": "沖縄本島", "lat": (26.0, 26.8), "lon": (127.6, 128.3)},
    {"name": "広島", "lat": (34.3, 34.5), "lon": (132.3, 132.6)},
    {"name": "大阪城周辺", "lat": (34.65, 34.7), "lon": (135.5, 135.55)},
    {"name": "金沢", "lat": (36.5, 36.6), "lon": (136.6, 136.7)},
    {"name": "姫路", "lat": (34.83, 34.85), "lon": (134.68, 134.7)},
    # Overseas
    {"name": "パリ", "lat": (48.7, 49.0), "lon": (2.2, 2.5)},
    {"name": "ローマ", "lat": (41.8, 42.0), "lon": (12.4, 12.6)},
    {"name": "ニューヨーク", "lat": (40.5, 40.9), "lon": (-74.1, -73.7)},
    {"name": "ロサンゼルス", "lat": (33.9, 34.2), "lon": (-118.5, -118.1)},
    {"name": "バンコク", "lat": (13.6, 13.9), "lon": (100.4, 100.7)},
    {"name": "バリ島", "lat": (-8.8, -8.3), "lon": (115.0, 115.6)},
    {"name": "ソウル", "lat": (37.4, 37.7), "lon": (126.8, 127.2)},
    {"name": "台北", "lat": (24.9, 25.2), "lon": (121.4, 121.7)},
    {"name": "シンガポール", "lat": (1.2, 1.5), "lon": (103.6, 104.0)},
    {"name": "ロンドン", "lat": (51.3, 51.7), "lon": (-0.3, 0.2)},
    {"name": "プラハ", "lat": (50.0, 50.2), "lon": (14.3, 14.6)},
    {"name": "ドバイ", "lat": (25.0, 25.4), "lon": (55.1, 55.5)},
    {"name": "シドニー", "lat": (-34.1, -33.7), "lon": (150.9, 151.3)},
    {"name": "ベネチア", "lat": (45.4, 45.5), "lon": (12.3, 12.4)},
    {"name": "バルセロナ", "lat": (41.3, 41.5), "lon": (2.1, 2.3)},
    {"name": "香港", "lat": (22.2, 22.5), "lon": (113.8, 114.3)},
    {"name": "上海", "lat": (31.1, 31.4), "lon": (121.3, 121.6)},
    {"name": "北京", "lat": (39.7, 40.1), "lon": (116.2, 116.6)},
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
    "Elephant": "動物|哺乳類|ゾウ", "Lion": "動物|哺乳類|ライオン",
    "Tiger": "動物|哺乳類|トラ", "Monkey": "動物|哺乳類|サル",
    "Penguin": "動物|鳥類|ペンギン", "Eagle": "動物|鳥類|ワシ",
    "Butterfly": "動物|昆虫|蝶", "Spider": "動物|虫|クモ",
    # 食べ物
    "Food": "食べ物", "Dish": "食べ物", "Cuisine": "食べ物",
    "Sushi": "食べ物|和食|寿司", "Ramen": "食べ物|和食|ラーメン",
    "Sashimi": "食べ物|和食|刺身", "Tempura": "食べ物|和食|天ぷら",
    "Udon": "食べ物|和食|うどん", "Soba": "食べ物|和食|そば",
    "Onigiri": "食べ物|和食|おにぎり", "Bento": "食べ物|和食|弁当",
    "Pizza": "食べ物|洋食|ピザ", "Pasta": "食べ物|洋食|パスタ",
    "Burger": "食べ物|洋食|ハンバーガー", "Steak": "食べ物|洋食|ステーキ",
    "Cake": "食べ物|スイーツ|ケーキ", "Dessert": "食べ物|スイーツ",
    "Ice cream": "食べ物|スイーツ|アイスクリーム",
    "Coffee": "食べ物|飲み物|コーヒー", "Tea": "食べ物|飲み物|お茶",
    "Beer": "食べ物|飲み物|ビール", "Wine": "食べ物|飲み物|ワイン",
    "Sake": "食べ物|飲み物|日本酒",
    # 場所・自然
    "Beach": "場所|自然|海辺", "Ocean": "場所|自然|海", "Sea": "場所|自然|海",
    "Mountain": "場所|自然|山", "Forest": "場所|自然|森林", "Tree": "場所|自然|木",
    "River": "場所|自然|川", "Lake": "場所|自然|湖",
    "Waterfall": "場所|自然|滝", "Flower": "場所|自然|花",
    "Garden": "場所|庭園", "Park": "場所|公園",
    "Sky": "場所|自然|空", "Cloud": "場所|自然|雲",
    "Sunset": "場所|自然|夕焼け", "Sunrise": "場所|自然|朝焼け",
    # 都市・建築
    "City": "場所|都市", "Building": "場所|建築物", "Skyscraper": "場所|建築物|高層ビル",
    "Castle": "場所|建築物|城", "Temple": "場所|建築物|寺院",
    "Shrine": "場所|建築物|神社", "Church": "場所|建築物|教会",
    "Mosque": "場所|建築物|モスク", "Cathedral": "場所|建築物|大聖堂",
    "Bridge": "場所|建築物|橋", "Tower": "場所|建築物|タワー",
    "Museum": "場所|施設|博物館", "Hotel": "場所|施設|ホテル",
    "Airport": "場所|施設|空港", "Station": "場所|施設|駅",
    "Restaurant": "場所|施設|レストラン", "Cafe": "場所|施設|カフェ",
    "School": "場所|施設|学校", "Hospital": "場所|施設|病院",
    "Shopping mall": "場所|施設|ショッピングモール",
    # 乗り物
    "Car": "乗り物|自動車", "Train": "乗り物|電車", "Bus": "乗り物|バス",
    "Airplane": "乗り物|飛行機", "Ship": "乗り物|船", "Boat": "乗り物|船",
    "Bicycle": "乗り物|自転車", "Motorcycle": "乗り物|バイク",
    "Taxi": "乗り物|タクシー", "Helicopter": "乗り物|ヘリコプター",
    # 人物・イベント
    "Person": "人物", "People": "人物", "Child": "人物|子供", "Baby": "人物|赤ちゃん",
    "Woman": "人物|女性", "Man": "人物|男性", "Girl": "人物|女の子", "Boy": "人物|男の子",
    "Wedding": "イベント|結婚式", "Party": "イベント|パーティー",
    "Festival": "イベント|祭り", "Concert": "イベント|コンサート",
    "Sport": "スポーツ", "Fireworks": "イベント|花火",
    "Birthday": "イベント|誕生日", "Christmas": "イベント|クリスマス",
    "New Year": "イベント|お正月", "Halloween": "イベント|ハロウィン",
    "Graduation": "イベント|卒業式",
    # 季節
    "Cherry blossom": "季節|春|桜", "Sakura": "季節|春|桜",
    "Autumn leaves": "季節|秋|紅葉", "Maple": "季節|秋|紅葉",
    "Snow": "季節|冬|雪", "Snowman": "季節|冬|雪だるま",
    "Spring": "季節|春", "Summer": "季節|夏", "Autumn": "季節|秋", "Winter": "季節|冬",
    # スポーツ
    "Soccer": "スポーツ|サッカー", "Football": "スポーツ|サッカー",
    "Baseball": "スポーツ|野球", "Basketball": "スポーツ|バスケットボール",
    "Tennis": "スポーツ|テニス", "Golf": "スポーツ|ゴルフ",
    "Swimming": "スポーツ|水泳", "Skiing": "スポーツ|スキー",
    "Running": "スポーツ|ランニング", "Cycling": "スポーツ|サイクリング",
    # テクノロジー
    "Smartphone": "テクノロジー|スマートフォン", "Phone": "テクノロジー|スマートフォン",
    "Computer": "テクノロジー|コンピューター", "Laptop": "テクノロジー|ノートパソコン",
    "Camera": "テクノロジー|カメラ", "Television": "テクノロジー|テレビ",
    "Robot": "テクノロジー|ロボット",
    # アート・ファッション
    "Art": "アート", "Painting": "アート|絵画", "Sculpture": "アート|彫刻",
    "Fashion": "ファッション", "Clothing": "ファッション|服",
    "Dress": "ファッション|ドレス", "Suit": "ファッション|スーツ",
    "Jewelry": "ファッション|ジュエリー", "Watch": "ファッション|時計",
}

# Likelihood values for unsafe content
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
        return {"entries": len(self._data), "hits": self._hits, "misses": self._misses}


# ============================================================
# Vision API Client
# ============================================================

class VisionAPIClient:
    """Google Cloud Vision API using service account credentials"""

    VISION_URL = "https://vision.googleapis.com/v1/images:annotate"

    def __init__(self, credentials_json: str, max_results: int = 30):
        self.max_results = max_results
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

    def annotate(self, image_path: Path, features: List[VisionFeature]) -> Dict[str, Any]:
        """Call Vision API with specified features"""
        with open(image_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

        feature_objs = []
        for feat in features:
            obj = {"type": feat.value}
            if feat in (VisionFeature.LABEL_DETECTION, VisionFeature.OBJECT_LOCALIZATION,
                        VisionFeature.TEXT_DETECTION, VisionFeature.LOGO_DETECTION,
                        VisionFeature.LANDMARK_DETECTION, VisionFeature.WEB_DETECTION):
                obj["maxResults"] = self.max_results
            feature_objs.append(obj)

        body = {"requests": [{"image": {"content": content}, "features": feature_objs}]}
        headers = {"Authorization": f"Bearer {self._get_token()}", "Content-Type": "application/json"}

        resp = requests.post(self.VISION_URL, json=body, headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json()["responses"][0]

    def estimate_cost_usd(self, features: List[VisionFeature]) -> float:
        return sum(FEATURE_COST_USD[f] for f in features)


# ============================================================
# DeepL Client
# ============================================================

class DeepLClient:
    """DeepL translation with batch support"""

    FREE_API = "https://api-free.deepl.com/v2/translate"
    PRO_API = "https://api.deepl.com/v2/translate"

    def __init__(self, api_key: str, free_tier: bool = True):
        self.api_key = api_key
        self.endpoint = self.FREE_API if free_tier else self.PRO_API
        self._chars_used = 0

    def translate_batch(self, texts: List[str]) -> Dict[str, str]:
        if not texts:
            return {}
        results: Dict[str, str] = {}
        for i in range(0, len(texts), 50):  # DeepL max 50 per call
            batch = texts[i:i+50]
            payload = {"auth_key": self.api_key, "text": batch, "source_lang": "EN", "target_lang": "JA"}
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
# XMP Writer
# ============================================================

class XMPWriter:
    """Writes Immich-compatible XMP sidecar files"""

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
        extracted_text: Optional[str] = None,
        detected_logos: Optional[List[str]] = None,
        dominant_colors: Optional[List[str]] = None,
        is_unsafe: bool = False,
        content_type: str = "",
        features_used: Optional[List[str]] = None,
    ) -> Optional[Path]:
        """Write XMP sidecar file alongside the image"""
        sidecar_path = Path(str(image_path) + ".xmp")

        cmd = [self.exiftool_path, "-overwrite_original", "-m", "-charset", "filename=UTF8"]

        # dc:subject — Immich reads these as tags
        all_tags = list(dict.fromkeys(tags_japanese))  # deduplicate
        if emotion_tags:
            all_tags.extend(emotion_tags)
        if landmark_name:
            all_tags.append(f"📍{landmark_name}")
        if detected_logos:
            all_tags.extend([f"🏷️{logo}" for logo in detected_logos[:5]])
        if dominant_colors:
            all_tags.extend([f"🎨{color}" for color in dominant_colors[:3]])

        for tag in all_tags:
            cmd.append(f"-XMP-dc:Subject+={tag}")

        # lr:hierarchicalSubject — hierarchical navigation
        for htag in tags_hierarchical:
            cmd.append(f"-XMP-lr:HierarchicalSubject+={htag}")

        # Landmark location
        if landmark_name:
            cmd.append(f"-XMP-iptcExt:LocationCreatedSublocation={landmark_name}")
        if landmark_lat is not None and landmark_lon is not None:
            cmd.extend([
                f"-XMP-exif:GPSLatitude={abs(landmark_lat)}",
                f"-XMP-exif:GPSLongitude={abs(landmark_lon)}",
                f"-XMP-exif:GPSLatitudeRef={'N' if landmark_lat >= 0 else 'S'}",
                f"-XMP-exif:GPSLongitudeRef={'E' if landmark_lon >= 0 else 'W'}",
            ])

        # Description
        if description_ja:
            cmd.append(f"-XMP-dc:Description={description_ja}")

        # Extracted text (for screenshots/documents)
        if extracted_text and len(extracted_text) < 500:
            cmd.append(f"-XMP-photoshop:CaptionWriter=OCR")
            cmd.append(f"-XMP-photoshop:Headline={extracted_text[:200]}")

        # Rating: 0 = unsafe, 3 = normal
        cmd.append(f"-XMP-xmp:Rating={'0' if is_unsafe else '3'}")

        # Analysis provenance
        features_str = ",".join(features_used or [])
        cmd.append(f"-XMP-xmp:CreatorTool=AdaptiveVision/{content_type}[{features_str}]")

        # Write to sidecar file
        cmd.extend(["-o", str(sidecar_path), str(image_path)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            if result.returncode == 0:
                return sidecar_path
            else:
                logger.error(f"ExifTool XMP write failed: {result.stderr[:200]}")
                return None
        except Exception as e:
            logger.error(f"XMP write error: {e}")
            return None


# ============================================================
# Adaptive Image Classifier (pre-classification without API)
# ============================================================

class AdaptiveImageClassifier:
    """
    Pre-classifies images using metadata, filename, and path patterns
    WITHOUT making any API calls. Returns recommended features.
    """

    def __init__(self, home_lat: float = 35.6762, home_lon: float = 139.6503):
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.home_radius_km = 50
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        return {
            "screenshot": [re.compile(p, re.IGNORECASE) for p in SCREENSHOT_PATTERNS],
            "document": [re.compile(p, re.IGNORECASE) for p in DOCUMENT_PATTERNS],
            "product": [re.compile(p, re.IGNORECASE) for p in PRODUCT_PATTERNS],
            "travel": [re.compile(p, re.IGNORECASE) for p in TRAVEL_PATTERNS],
            "portrait": [re.compile(p, re.IGNORECASE) for p in PORTRAIT_PATTERNS],
            "group": [re.compile(p, re.IGNORECASE) for p in GROUP_PATTERNS],
            "nature": [re.compile(p, re.IGNORECASE) for p in NATURE_PATTERNS],
            "food": [re.compile(p, re.IGNORECASE) for p in FOOD_PATTERNS],
            "art": [re.compile(p, re.IGNORECASE) for p in ART_PATTERNS],
            "event": [re.compile(p, re.IGNORECASE) for p in EVENT_PATTERNS],
        }

    def _match_patterns(self, text: str, category: str) -> bool:
        return any(p.search(text) for p in self._compiled_patterns.get(category, []))

    def _gps_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    def _is_tourist_area(self, lat: float, lon: float) -> Optional[str]:
        for region in TOURIST_REGIONS:
            if (region["lat"][0] <= lat <= region["lat"][1] and
                    region["lon"][0] <= lon <= region["lon"][1]):
                return region["name"]
        return None

    def _is_overseas(self, lat: float, lon: float) -> bool:
        return not ((24 <= lat <= 46) and (122 <= lon <= 154))

    def _detect_aspect_ratio_type(self, width: int, height: int) -> Optional[str]:
        """Detect content type from aspect ratio"""
        if width == 0 or height == 0:
            return None
        ratio = height / width
        if ratio > 2.0:  # Very tall = phone screenshot scroll capture
            return "screenshot"
        if ratio > 1.5:  # Tall = document scan
            return "document"
        return None

    def classify(
        self,
        image_path: Path,
        exif_data: Optional[Dict] = None,
        image_width: int = 0,
        image_height: int = 0,
        immich_has_faces: bool = False,
    ) -> Tuple[ImageContentType, List[VisionFeature], Dict[str, Any]]:
        """
        Classify image and determine which Vision API features to use.

        Returns:
            (content_type, features, context_dict)
        """
        exif_data = exif_data or {}
        context: Dict[str, Any] = {
            "detection_reasons": [],
            "has_gps": False,
            "tourist_area": None,
            "is_overseas": False,
            "has_faces": immich_has_faces,
        }

        # Text to analyze: filename + folder path
        analysis_text = f"{image_path.name} {str(image_path.parent)}"
        detected_types: Set[ImageContentType] = set()

        # 1. Check filename/path patterns
        if self._match_patterns(analysis_text, "screenshot"):
            detected_types.add(ImageContentType.SCREENSHOT)
            context["detection_reasons"].append("filename_screenshot")

        if self._match_patterns(analysis_text, "document"):
            detected_types.add(ImageContentType.DOCUMENT)
            context["detection_reasons"].append("filename_document")

        if self._match_patterns(analysis_text, "product"):
            detected_types.add(ImageContentType.PRODUCT)
            context["detection_reasons"].append("filename_product")

        if self._match_patterns(analysis_text, "travel"):
            detected_types.add(ImageContentType.TRAVEL)
            context["detection_reasons"].append("filename_travel")

        if self._match_patterns(analysis_text, "portrait"):
            detected_types.add(ImageContentType.PORTRAIT)
            context["detection_reasons"].append("filename_portrait")

        if self._match_patterns(analysis_text, "group"):
            detected_types.add(ImageContentType.GROUP_PHOTO)
            context["detection_reasons"].append("filename_group")

        if self._match_patterns(analysis_text, "nature"):
            detected_types.add(ImageContentType.NATURE)
            context["detection_reasons"].append("filename_nature")

        if self._match_patterns(analysis_text, "food"):
            detected_types.add(ImageContentType.FOOD)
            context["detection_reasons"].append("filename_food")

        if self._match_patterns(analysis_text, "art"):
            detected_types.add(ImageContentType.ART)
            context["detection_reasons"].append("filename_art")

        if self._match_patterns(analysis_text, "event"):
            detected_types.add(ImageContentType.EVENT)
            context["detection_reasons"].append("filename_event")

        # 2. Check aspect ratio
        if image_width > 0 and image_height > 0:
            ratio_type = self._detect_aspect_ratio_type(image_width, image_height)
            if ratio_type == "screenshot":
                detected_types.add(ImageContentType.SCREENSHOT)
                context["detection_reasons"].append("aspect_ratio_tall")
            elif ratio_type == "document":
                detected_types.add(ImageContentType.DOCUMENT)
                context["detection_reasons"].append("aspect_ratio_document")

        # 3. Check EXIF for camera model (no camera = screenshot)
        camera_model = exif_data.get("Model") or exif_data.get("EXIF:Model")
        if not camera_model and image_path.suffix.lower() in (".png", ".webp"):
            # PNG/WebP without camera model is likely screenshot
            detected_types.add(ImageContentType.SCREENSHOT)
            context["detection_reasons"].append("no_camera_model")

        # 4. Check GPS for tourist areas
        gps_lat = exif_data.get("gps_lat") or exif_data.get("GPSLatitude")
        gps_lon = exif_data.get("gps_lon") or exif_data.get("GPSLongitude")

        if gps_lat is not None and gps_lon is not None:
            try:
                lat = float(gps_lat)
                lon = float(gps_lon)
                context["has_gps"] = True

                tourist_area = self._is_tourist_area(lat, lon)
                if tourist_area:
                    context["tourist_area"] = tourist_area
                    detected_types.add(ImageContentType.TRAVEL)
                    context["detection_reasons"].append(f"gps_tourist_{tourist_area}")

                if self._is_overseas(lat, lon):
                    context["is_overseas"] = True
                    detected_types.add(ImageContentType.TRAVEL)
                    context["detection_reasons"].append("gps_overseas")

                dist = self._gps_distance_km(self.home_lat, self.home_lon, lat, lon)
                context["distance_from_home_km"] = round(dist, 1)
                if dist > 100:
                    detected_types.add(ImageContentType.TRAVEL)
                    context["detection_reasons"].append("gps_far_from_home")
            except (ValueError, TypeError):
                pass

        # 5. Immich face detection
        if immich_has_faces:
            detected_types.add(ImageContentType.PORTRAIT)
            context["detection_reasons"].append("immich_faces")

        # Determine primary content type and features
        if not detected_types:
            content_type = ImageContentType.GENERAL
        elif len(detected_types) == 1:
            content_type = list(detected_types)[0]
        else:
            # Priority order when multiple types detected
            priority = [
                ImageContentType.DOCUMENT,      # Documents need OCR priority
                ImageContentType.SCREENSHOT,    # Screenshots need OCR
                ImageContentType.EVENT,         # Events need full analysis
                ImageContentType.TRAVEL,        # Travel needs landmarks
                ImageContentType.GROUP_PHOTO,   # Group needs faces
                ImageContentType.PORTRAIT,      # Portraits need faces
                ImageContentType.PRODUCT,       # Products need logos
                ImageContentType.FOOD,
                ImageContentType.NATURE,
                ImageContentType.ART,
                ImageContentType.GENERAL,
            ]
            for ct in priority:
                if ct in detected_types:
                    content_type = ct
                    break
            else:
                content_type = ImageContentType.GENERAL

        # Get base features for content type
        features = list(CONTENT_TYPE_FEATURES.get(content_type, CONTENT_TYPE_FEATURES[ImageContentType.GENERAL]))

        # Add extra features based on context
        if context.get("is_overseas") and VisionFeature.WEB_DETECTION not in features:
            features.append(VisionFeature.WEB_DETECTION)
            context["detection_reasons"].append("added_web_overseas")

        if immich_has_faces and VisionFeature.FACE_DETECTION not in features:
            features.append(VisionFeature.FACE_DETECTION)
            context["detection_reasons"].append("added_face_immich")

        # Ensure SAFE_SEARCH is always included
        if VisionFeature.SAFE_SEARCH_DETECTION not in features:
            features.append(VisionFeature.SAFE_SEARCH_DETECTION)

        # Calculate estimated cost
        context["content_type"] = content_type.name
        context["features"] = [f.value for f in features]
        context["estimated_cost_usd"] = sum(FEATURE_COST_USD[f] for f in features)

        return content_type, features, context


# ============================================================
# Analysis Result
# ============================================================

@dataclass
class AnalysisResult:
    image_path: Path
    success: bool
    content_type: ImageContentType
    features_used: List[VisionFeature]
    context: Dict[str, Any]

    tags_english: List[str] = field(default_factory=list)
    tags_japanese: List[str] = field(default_factory=list)
    tags_hierarchical: List[str] = field(default_factory=list)

    landmark_name: Optional[str] = None
    landmark_lat: Optional[float] = None
    landmark_lon: Optional[float] = None

    face_count: int = 0
    emotion_tags: List[str] = field(default_factory=list)

    extracted_text: Optional[str] = None
    detected_logos: List[str] = field(default_factory=list)
    dominant_colors: List[str] = field(default_factory=list)
    web_entities: List[str] = field(default_factory=list)

    description_ja: Optional[str] = None
    is_unsafe: bool = False

    xmp_path: Optional[Path] = None
    error: Optional[str] = None
    cost_usd: float = 0.0

    @property
    def feature_profile(self) -> str:
        return self.content_type.name


# ============================================================
# Main Adaptive Analyzer
# ============================================================

class AdaptiveVisionAnalyzer:
    """
    Adaptive Vision AI Analyzer - selects features per-image based on content.

    All Vision API features supported:
    - LABEL_DETECTION, OBJECT_LOCALIZATION, FACE_DETECTION
    - TEXT_DETECTION, DOCUMENT_TEXT_DETECTION, LOGO_DETECTION
    - LANDMARK_DETECTION, IMAGE_PROPERTIES, WEB_DETECTION
    - SAFE_SEARCH_DETECTION (always free)

    Runs on GitHub Actions (not VPS).
    """

    def __init__(
        self,
        vision_credentials_json: str,
        deepl_api_key: str,
        deepl_free_tier: bool = True,
        confidence_threshold: float = 0.70,
        cache_path: Optional[str] = None,
        home_lat: float = 35.6762,
        home_lon: float = 139.6503,
        dry_run: bool = False,
    ):
        self.vision = VisionAPIClient(vision_credentials_json)
        self.deepl = DeepLClient(deepl_api_key, free_tier=deepl_free_tier)
        self.cache = TranslationCache(Path(cache_path or "/tmp/translation_cache.json"))
        self.classifier = AdaptiveImageClassifier(home_lat=home_lat, home_lon=home_lon)
        self.xmp_writer = XMPWriter()
        self.confidence_threshold = confidence_threshold
        self.dry_run = dry_run

        self._total_cost_usd = 0.0
        self._api_calls = 0
        self._results: List[AnalysisResult] = []

    # ── Response extractors ──

    def _extract_labels(self, response: Dict, min_score: float) -> List[str]:
        return [a["description"] for a in response.get("labelAnnotations", []) if a.get("score", 0) >= min_score]

    def _extract_objects(self, response: Dict, min_score: float) -> List[str]:
        return [o["name"] for o in response.get("localizedObjectAnnotations", []) if o.get("score", 0) >= min_score]

    def _extract_landmarks(self, response: Dict) -> List[Tuple[str, float, Optional[float], Optional[float]]]:
        landmarks = []
        for ann in response.get("landmarkAnnotations", []):
            lat, lon = None, None
            for loc in ann.get("locations", []):
                lat_lng = loc.get("latLng", {})
                lat, lon = lat_lng.get("latitude"), lat_lng.get("longitude")
                break
            landmarks.append((ann["description"], ann.get("score", 0), lat, lon))
        return landmarks

    def _extract_faces(self, response: Dict) -> Tuple[int, List[str]]:
        faces = response.get("faceAnnotations", [])
        emotions = []
        if sum(1 for f in faces if f.get("joyLikelihood") in ("LIKELY", "VERY_LIKELY")) > 0:
            emotions.append("笑顔")
        if sum(1 for f in faces if f.get("surpriseLikelihood") in ("LIKELY", "VERY_LIKELY")) > 0:
            emotions.append("驚き")
        if sum(1 for f in faces if f.get("sorrowLikelihood") in ("LIKELY", "VERY_LIKELY")) > 0:
            emotions.append("悲しみ")
        if sum(1 for f in faces if f.get("angerLikelihood") in ("LIKELY", "VERY_LIKELY")) > 0:
            emotions.append("怒り")
        return len(faces), emotions

    def _extract_text(self, response: Dict) -> Optional[str]:
        full_text = response.get("fullTextAnnotation", {})
        if full_text:
            return full_text.get("text", "")[:1000]  # Limit length
        text_anns = response.get("textAnnotations", [])
        if text_anns:
            return text_anns[0].get("description", "")[:1000]
        return None

    def _extract_logos(self, response: Dict, min_score: float) -> List[str]:
        return [l["description"] for l in response.get("logoAnnotations", []) if l.get("score", 0) >= min_score]

    def _extract_colors(self, response: Dict) -> List[str]:
        """Extract dominant colors as Japanese names"""
        props = response.get("imagePropertiesAnnotation", {})
        colors = props.get("dominantColors", {}).get("colors", [])
        color_names = []
        for c in colors[:5]:  # Top 5 colors
            rgb = c.get("color", {})
            r, g, b = rgb.get("red", 0), rgb.get("green", 0), rgb.get("blue", 0)
            name = self._rgb_to_japanese_color(r, g, b)
            if name and name not in color_names:
                color_names.append(name)
        return color_names[:3]

    def _rgb_to_japanese_color(self, r: int, g: int, b: int) -> Optional[str]:
        """Convert RGB to Japanese color name"""
        # Simple color classification
        if r > 200 and g < 100 and b < 100:
            return "赤"
        if r < 100 and g > 200 and b < 100:
            return "緑"
        if r < 100 and g < 100 and b > 200:
            return "青"
        if r > 200 and g > 200 and b < 100:
            return "黄色"
        if r > 200 and g > 100 and b < 100:
            return "オレンジ"
        if r > 200 and g < 150 and b > 200:
            return "ピンク"
        if r > 150 and g < 100 and b > 150:
            return "紫"
        if r > 200 and g > 200 and b > 200:
            return "白"
        if r < 50 and g < 50 and b < 50:
            return "黒"
        if 100 < r < 180 and 100 < g < 180 and 100 < b < 180:
            return "グレー"
        if r > 150 and g > 100 and b < 100:
            return "茶色"
        if r < 100 and g > 150 and b > 150:
            return "シアン"
        return None

    def _extract_web_entities(self, response: Dict, min_score: float) -> List[str]:
        web = response.get("webDetection", {})
        entities = []
        for entity in web.get("webEntities", []):
            if entity.get("score", 0) >= min_score and entity.get("description"):
                entities.append(entity["description"])
        return entities[:10]

    def _is_unsafe(self, response: Dict) -> bool:
        safe = response.get("safeSearchAnnotation", {})
        return any(safe.get(f) in UNSAFE_LIKELIHOODS for f in ("adult", "violence"))

    # ── Translation & hierarchical tags ──

    def _translate_labels(self, english_labels: List[str]) -> Dict[str, str]:
        cached, to_translate = {}, []
        for label in english_labels:
            c = self.cache.get(label)
            if c:
                cached[label] = c
            else:
                to_translate.append(label)

        new_translations = {}
        if to_translate and not self.dry_run:
            new_translations = self.deepl.translate_batch(to_translate)
            for en, ja in new_translations.items():
                self.cache.set(en, ja)
            self.cache.save()

        return {**cached, **new_translations}

    def _build_hierarchical(self, english_labels: List[str]) -> List[str]:
        hierarchical = []
        seen = set()
        for en in english_labels:
            hier = CATEGORY_MAP.get(en)
            if hier and hier not in seen:
                seen.add(hier)
                hierarchical.append(hier)
        return hierarchical

    def _build_description(
        self,
        tags_ja: List[str],
        landmark: Optional[str],
        face_count: int,
        tourist_area: Optional[str],
        extracted_text: Optional[str],
        content_type: ImageContentType,
    ) -> Optional[str]:
        parts = []
        if content_type == ImageContentType.SCREENSHOT and extracted_text:
            parts.append("スクリーンショット")
        elif content_type == ImageContentType.DOCUMENT and extracted_text:
            parts.append("文書")
        elif landmark:
            parts.append(f"{landmark}を含む写真")
        elif tourist_area:
            parts.append(f"{tourist_area}での写真")

        if face_count > 0:
            parts.append(f"{face_count}人が写っています")
        if tags_ja:
            parts.append(f"タグ: {', '.join(tags_ja[:5])}")
        return "。".join(parts) if parts else None

    # ── Main analyze method ──

    def analyze(
        self,
        image_path: Path,
        exif_data: Optional[Dict] = None,
        immich_has_faces: bool = False,
        force_profile: Optional[str] = None,
        image_width: int = 0,
        image_height: int = 0,
    ) -> AnalysisResult:
        """
        Analyze an image with adaptive feature selection.

        Features are selected based on:
        - Filename patterns (screenshot, document, product, etc.)
        - GPS location (tourist areas, overseas)
        - Aspect ratio (tall = document/screenshot)
        - EXIF camera model (no camera = screenshot)
        - Immich face detection results
        """
        exif_data = exif_data or {}

        # Step 1: Classify and select features
        content_type, features, context = self.classifier.classify(
            image_path=image_path,
            exif_data=exif_data,
            image_width=image_width,
            image_height=image_height,
            immich_has_faces=immich_has_faces,
        )

        result = AnalysisResult(
            image_path=image_path,
            success=False,
            content_type=content_type,
            features_used=features,
            context=context,
            cost_usd=context.get("estimated_cost_usd", 0),
        )

        if self.dry_run:
            result.success = True
            logger.info(f"[DRY RUN] {image_path.name}: type={content_type.name}, features={len(features)}, cost=${result.cost_usd:.4f}")
            self._results.append(result)
            return result

        # Step 2: Call Vision API
        try:
            logger.info(f"{image_path.name}: type={content_type.name}, features={[f.value[:4] for f in features]}")
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
            logger.warning(f"Unsafe content: {image_path.name}")
            result.success = True
            result.xmp_path = self.xmp_writer.write(
                image_path, ["閲覧注意"], [], is_unsafe=True,
                content_type=content_type.name,
                features_used=[f.value for f in features],
            )
            self._results.append(result)
            return result

        # Step 4: Extract results based on features used
        all_english = []

        if VisionFeature.LABEL_DETECTION in features:
            labels = self._extract_labels(response, self.confidence_threshold)
            all_english.extend(labels)

        if VisionFeature.OBJECT_LOCALIZATION in features:
            objects = self._extract_objects(response, self.confidence_threshold)
            all_english.extend(objects)

        if VisionFeature.LANDMARK_DETECTION in features:
            landmarks = self._extract_landmarks(response)
            if landmarks:
                top = landmarks[0]
                result.landmark_name = top[0]
                result.landmark_lat = top[2]
                result.landmark_lon = top[3]
                all_english.append(top[0])

        if VisionFeature.FACE_DETECTION in features:
            result.face_count, result.emotion_tags = self._extract_faces(response)

        if VisionFeature.TEXT_DETECTION in features or VisionFeature.DOCUMENT_TEXT_DETECTION in features:
            result.extracted_text = self._extract_text(response)

        if VisionFeature.LOGO_DETECTION in features:
            result.detected_logos = self._extract_logos(response, self.confidence_threshold)
            all_english.extend(result.detected_logos)

        if VisionFeature.IMAGE_PROPERTIES in features:
            result.dominant_colors = self._extract_colors(response)

        if VisionFeature.WEB_DETECTION in features:
            result.web_entities = self._extract_web_entities(response, self.confidence_threshold)
            all_english.extend(result.web_entities)

        # Deduplicate
        all_english = list(dict.fromkeys(all_english))

        # Step 5: Translate
        translations = self._translate_labels(all_english)
        result.tags_english = all_english
        result.tags_japanese = [translations.get(e, e) for e in all_english]

        # Step 6: Build hierarchical tags
        result.tags_hierarchical = self._build_hierarchical(all_english)
        tourist_area = context.get("tourist_area")
        if tourist_area:
            result.tags_hierarchical.append(f"場所|{tourist_area}")
        if context.get("is_overseas"):
            result.tags_hierarchical.append("旅行|海外")

        # Step 7: Generate description
        result.description_ja = self._build_description(
            result.tags_japanese, result.landmark_name,
            result.face_count, tourist_area, result.extracted_text, content_type,
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
            extracted_text=result.extracted_text,
            detected_logos=result.detected_logos,
            dominant_colors=result.dominant_colors,
            is_unsafe=False,
            content_type=content_type.name,
            features_used=[f.value for f in features],
        )

        result.success = result.xmp_path is not None
        logger.info(
            f"OK {image_path.name}: {len(result.tags_japanese)} tags, "
            f"type={content_type.name}, cost=${result.cost_usd:.4f}"
        )

        self._results.append(result)
        return result

    def get_stats(self) -> Dict[str, Any]:
        successful = [r for r in self._results if r.success]
        type_counts = {}
        for r in self._results:
            k = r.content_type.name
            type_counts[k] = type_counts.get(k, 0) + 1

        feature_usage = {}
        for r in self._results:
            for f in r.features_used:
                feature_usage[f.value] = feature_usage.get(f.value, 0) + 1

        return {
            "total": len(self._results),
            "successful": len(successful),
            "failed": len(self._results) - len(successful),
            "total_cost_usd": round(self._total_cost_usd, 4),
            "api_calls": self._api_calls,
            "deepl_chars_used": self.deepl.chars_used,
            "translation_cache": self.cache.stats(),
            "content_type_distribution": type_counts,
            "feature_usage": feature_usage,
        }


# ============================================================
# Immich Client (unchanged from v1)
# ============================================================

class ImmichClient:
    """Query Immich for face detection, trigger library scan"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    def get_asset_by_filename(self, filename: str) -> Optional[Dict]:
        try:
            resp = requests.get(
                f"{self.base_url}/api/search/metadata",
                headers=self.headers, params={"originalFileName": filename}, timeout=10,
            )
            resp.raise_for_status()
            assets = resp.json().get("assets", {}).get("items", [])
            return assets[0] if assets else None
        except Exception as e:
            logger.debug(f"Immich lookup failed: {e}")
            return None

    def asset_has_faces(self, asset: Dict) -> bool:
        return len(asset.get("people", [])) > 0

    def trigger_library_scan(self, library_id: str) -> bool:
        try:
            resp = requests.post(
                f"{self.base_url}/api/library/{library_id}/scan",
                headers=self.headers,
                json={"refreshModifiedFiles": True, "refreshAllFiles": False},
                timeout=30,
            )
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Failed to trigger scan: {e}")
            return False


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Adaptive Vision AI Analyzer v2.0")
    parser.add_argument("image_path", help="Path to image file")
    parser.add_argument("--credentials", default=os.environ.get("GOOGLE_VISION_CREDENTIALS_JSON"))
    parser.add_argument("--deepl-key", default=os.environ.get("DEEPL_API_KEY"))
    parser.add_argument("--deepl-free", action="store_true", default=True)
    parser.add_argument("--confidence", type=float, default=0.70)
    parser.add_argument("--cache", default="/tmp/translation_cache.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--home-lat", type=float, default=35.6762)
    parser.add_argument("--home-lon", type=float, default=139.6503)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if not args.credentials or not args.deepl_key:
        print("Error: --credentials and --deepl-key required")
        sys.exit(1)

    analyzer = AdaptiveVisionAnalyzer(
        vision_credentials_json=args.credentials,
        deepl_api_key=args.deepl_key,
        deepl_free_tier=args.deepl_free,
        confidence_threshold=args.confidence,
        cache_path=args.cache,
        home_lat=args.home_lat,
        home_lon=args.home_lon,
        dry_run=args.dry_run,
    )

    result = analyzer.analyze(Path(args.image_path))

    print("\n=== Result ===")
    print(f"Content Type: {result.content_type.name}")
    print(f"Features Used: {[f.value for f in result.features_used]}")
    print(f"Tags (JA): {result.tags_japanese}")
    print(f"Hierarchical: {result.tags_hierarchical}")
    print(f"Landmark: {result.landmark_name}")
    print(f"Faces: {result.face_count}, Emotions: {result.emotion_tags}")
    print(f"Logos: {result.detected_logos}")
    print(f"Colors: {result.dominant_colors}")
    print(f"Text: {result.extracted_text[:100] if result.extracted_text else None}...")
    print(f"Description: {result.description_ja}")
    print(f"XMP: {result.xmp_path}")
    print(f"Cost: ${result.cost_usd:.4f}")
    print(f"\nStats: {json.dumps(analyzer.get_stats(), ensure_ascii=False, indent=2)}")
