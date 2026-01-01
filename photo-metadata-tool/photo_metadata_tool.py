#!/usr/bin/env python3
"""
Google Photos Takeout Metadata Fixer (Enhanced)
Google Photo Takeoutのデータを整理し、Exif/メタデータを復元するツール
Immichへの移行に最適化されています。

主な機能強化点:
- マルチスレッド並列処理による高速化
- タイムゾーン補正（UTC -> JST等）
- 長いファイル名のJSON切り詰め問題への対応
- 動画(MP4/MOV)およびHEICのメタデータ書き込み対応
- 堅牢なエラーハンドリング
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
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

# 外部ライブラリチェック
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
except ImportError:
    print("エラー: Pillowが必要です。インストールしてください: pip install Pillow")
    sys.exit(1)

# piexifはオプション（ExifToolがない場合のフォールバック用）
try:
    import piexif
    HAS_PIEXIF = True
except ImportError:
    HAS_PIEXIF = False

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==========================================
# 定数・設定
# ==========================================

# 対応拡張子
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.tiff', '.tif'}
HEIC_EXTENSIONS = {'.heic', '.heif'}
RAW_EXTENSIONS = {'.dng', '.cr2', '.nef', '.arw', '.raf', '.orf', '.rw2', '.pef', '.srw'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.3gp', '.m4v', '.mpg'}

# exiftoolで書き込み可能な拡張子
EXIFTOOL_WRITABLE = IMAGE_EXTENSIONS | HEIC_EXTENSIONS | RAW_EXTENSIONS | VIDEO_EXTENSIONS

# 処理ログファイル名
PROCESSING_LOG_FILE = '.photo_metadata_processed.json'

# Google Takeoutのファイル名切り詰め閾値（推定）
JSON_TRUNCATE_LENGTH = 46


@dataclass
class ProcessStats:
    """処理統計"""
    total_files: int = 0
    processed: int = 0
    skipped: int = 0
    errors: int = 0
    date_updated: int = 0
    gps_updated: int = 0
    video_updated: int = 0
    start_time: float = 0.0

    def get_duration(self):
        return time.time() - self.start_time


class ExifToolWrapper:
    """exiftool操作ラッパー（スレッドセーフな呼び出し）"""

    def __init__(self):
        self.path = shutil.which('exiftool')
        self.available = self.path is not None
        if not self.available:
            logger.warning("⚠️ exiftoolが見つかりません。動画・HEIC・RAWの処理や、高度なメタデータ書き込みが制限されます。")
            logger.warning("  インストール推奨: https://exiftool.org/ (Mac: brew install exiftool, Win: 公式サイト)")

    def read_metadata(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """メタデータを読み込む"""
        if not self.available:
            return None
        try:
            # -n: 数値で出力, -json: JSON形式
            cmd = [self.path, '-json', '-n', '-G', str(file_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data[0] if data else None
        except Exception as e:
            logger.debug(f"ExifTool read error {file_path}: {e}")
        return None

    def write_metadata(self, file_path: Path, tags: Dict[str, Any], dry_run: bool = False) -> bool:
        """メタデータを書き込む"""
        if not self.available:
            return False
        
        cmd = [self.path, '-overwrite_original', '-m'] # -m: マイナーエラー無視
        
        # UTF-8ファイル名対応
        if os.name == 'nt':
            cmd.append('-charset')
            cmd.append('filename=UTF8')

        for key, value in tags.items():
            if value is None:
                continue
            # datetimeオブジェクトの場合はフォーマット
            if isinstance(value, datetime):
                value = value.strftime('%Y:%m:%d %H:%M:%S')
            cmd.append(f'-{key}={value}')
        
        cmd.append(str(file_path))

        if dry_run:
            logger.info(f"[DRY RUN] ExifTool: {' '.join(cmd)}")
            return True

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode != 0:
                logger.error(f"ExifTool write error {file_path.name}: {result.stderr.strip()}")
                return False
            return True
        except Exception as e:
            logger.error(f"ExifTool execution failed: {e}")
            return False


class PhotoFixer:
    """メイン処理クラス"""

    def __init__(self, target_dir: str, args):
        self.target_dir = Path(target_dir).resolve()
        self.args = args
        self.exiftool = ExifToolWrapper()
        self.stats = ProcessStats()
        
        # タイムゾーン設定 (デフォルトはJST +9)
        self.tz_offset = timezone(timedelta(hours=args.timezone))
        
        # ログ管理（スレッドセーフにするため辞書操作は注意が必要だが、今回は簡易実装）
        self.processed_log = self._load_log()

    def _load_log(self) -> Dict[str, Any]:
        log_path = self.target_dir / PROCESSING_LOG_FILE
        if log_path.exists() and not self.args.ignore_history:
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    return json.load(f).get('processed', {})
            except:
                pass
        return {}

    def _save_log(self):
        if self.args.dry_run:
            return
        log_path = self.target_dir / PROCESSING_LOG_FILE
        data = {
            'last_run': datetime.now().isoformat(),
            'processed': self.processed_log
        }
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"ログ保存失敗: {e}")

    def find_json_for_file(self, file_path: Path) -> Optional[Path]:
        """
        画像ファイルに対応するJSONファイルを探す
        ファイル名切り詰め問題に対応したロジックを含む
        """
        # パターン1: 完全一致 (image.jpg -> image.jpg.json)
        json_path = file_path.with_suffix(file_path.suffix + '.json')
        if json_path.exists():
            return json_path

        # パターン2: 拡張子置換 (image.jpg -> image.json)
        json_path = file_path.with_suffix('.json')
        if json_path.exists():
            return json_path

        # パターン3: ファイル名切り詰め対策 (Google Takeoutの仕様)
        # ファイル名が長い場合、JSON側で短縮されている可能性がある
        stem = file_path.stem
        
        # 拡張子を含めたファイル名が長い場合、Takeoutは途中で切って .json をつける
        full_name = file_path.name
        if len(full_name) > JSON_TRUNCATE_LENGTH:
            # 前方一致で探す
            prefix = stem[:30] # 最初の30文字は合っているはず
            candidates = list(file_path.parent.glob(f"{prefix}*.json"))
            
            # 候補の中で最も確からしいものを探す（簡易ロジック）
            for cand in candidates:
                # 候補が画像自体の名前から派生しているかチェック
                if cand.stem in full_name:
                    return cand
                
                # Takeoutは "VeryLongFileName.j.json" のようになることもある
                # ここは厳密にやるとキリがないので、prefixが十分長く一致していれば採用
                if cand.name.startswith(full_name[:JSON_TRUNCATE_LENGTH]):
                    return cand

        return None

    def parse_json_metadata(self, json_path: Path) -> Dict[str, Any]:
        """Google JSONをパースし、UTC日時をローカルタイム(指定TZ)に変換"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            meta = {}
            
            # 日時の取得 (photoTakenTime優先)
            timestamp = None
            if 'photoTakenTime' in data and 'timestamp' in data['photoTakenTime']:
                timestamp = int(data['photoTakenTime']['timestamp'])
            elif 'creationTime' in data and 'timestamp' in data['creationTime']:
                timestamp = int(data['creationTime']['timestamp'])
            
            if timestamp:
                # UTCから指定タイムゾーンへ変換
                dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                dt_local = dt_utc.astimezone(self.tz_offset)
                # EXIF書き込み用にtzinfoを削除（Naïveなdatetimeにする）
                meta['datetime'] = dt_local.replace(tzinfo=None)
            
            # GPS情報
            if 'geoData' in data:
                geo = data['geoData']
                lat = geo.get('latitude', 0.0)
                lon = geo.get('longitude', 0.0)
                alt = geo.get('altitude', 0.0)
                # 0,0 は位置情報なしとみなす
                if lat != 0.0 or lon != 0.0:
                    meta['gps'] = {'lat': lat, 'lon': lon, 'alt': alt}
            
            meta['title'] = data.get('title')
            meta['description'] = data.get('description', '')
            
            return meta
        except Exception as e:
            logger.warning(f"JSON解析エラー {json_path.name}: {e}")
            return {}

    def process_file(self, file_path: Path) -> str:
        """単一ファイルの処理（スレッドで実行される）"""
        try:
            # 既に処理済みかチェック
            if str(file_path) in self.processed_log and not self.args.force:
                return "skipped"

            # 対象ファイルかチェック
            ext = file_path.suffix.lower()
            if ext not in EXIFTOOL_WRITABLE:
                return "ignored"

            # JSONを探す
            json_path = self.find_json_for_file(file_path)
            if not json_path:
                return "no_json"

            # メタデータ取得
            meta = self.parse_json_metadata(json_path)
            if not meta.get('datetime'):
                return "no_date_in_json"

            # 書き込み処理
            success = False
            is_video = ext in VIDEO_EXTENSIONS
            
            if self.exiftool.available:
                # --- ExifToolを使用するルート (推奨) ---
                tags = {}
                dt = meta['datetime']
                
                # 一般的な日付タグ
                tags['DateTimeOriginal'] = dt
                tags['CreateDate'] = dt
                tags['ModifyDate'] = dt
                
                # 動画用タグ
                if is_video:
                    tags['QuickTime:CreateDate'] = dt
                    tags['QuickTime:ModifyDate'] = dt
                    tags['Keys:CreationDate'] = dt
                
                # GPSタグ
                if 'gps' in meta and not self.args.no_gps:
                    gps = meta['gps']
                    tags['GPSLatitude'] = gps['lat']
                    tags['GPSLongitude'] = gps['lon']
                    tags['GPSAltitude'] = gps['alt']
                    # 参照系タグはExifToolが自動計算してくれることが多いが念のため
                    tags['GPSLatitudeRef'] = 'N' if gps['lat'] >= 0 else 'S'
                    tags['GPSLongitudeRef'] = 'E' if gps['lon'] >= 0 else 'W'

                # 説明文 (UserComment / Caption-Abstract)
                if meta.get('description'):
                    tags['UserComment'] = meta['description']
                    tags['ImageDescription'] = meta['description']
                    if is_video:
                        tags['QuickTime:Description'] = meta['description']

                success = self.exiftool.write_metadata(file_path, tags, self.args.dry_run)
                
            elif ext in IMAGE_EXTENSIONS and HAS_PIEXIF and not is_video:
                # --- Pillow/PieExifを使用するルート (画像のみ・ExifToolなし) ---
                # ※注: このルートは簡易的であり、HEICや動画には非対応
                success = self._write_with_piexif(file_path, meta)
            else:
                return "tool_unavailable"

            if success:
                # ログ更新
                if not self.args.dry_run:
                    self.processed_log[str(file_path)] = {
                        'processed_at': datetime.now().isoformat(),
                        'src_json': str(json_path.name)
                    }
                return "updated"
            else:
                return "error"

        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            return "error"

    def _write_with_piexif(self, file_path: Path, meta: Dict) -> bool:
        """Pillow/Piexifを使った書き込み（ExifToolがない場合のバックアップ）"""
        if self.args.dry_run:
            logger.info(f"[DRY RUN] Piexif write: {file_path.name}")
            return True
        try:
            img = Image.open(file_path)
            exif_dict = piexif.load(img.info.get("exif", b""))
            
            dt_str = meta['datetime'].strftime("%Y:%m:%d %H:%M:%S")
            exif_dict['0th'][piexif.ImageIFD.DateTime] = dt_str
            exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = dt_str
            exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = dt_str

            # GPS書き込み（Piexifは複雑なため、ここでは省略するか簡易実装にとどめる）
            # 実用上はExifTool推奨
            
            exif_bytes = piexif.dump(exif_dict)
            img.save(file_path, exif=exif_bytes)
            return True
        except Exception:
            return False

    def organize_files(self, file_path: Path, meta: Dict):
        """(オプション) ファイルを年月フォルダに移動"""
        if not self.args.organize or not meta.get('datetime'):
            return

        dt = meta['datetime']
        folder_name = dt.strftime('%Y/%Y-%m')
        dest_dir = self.args.organize / folder_name
        dest_path = dest_dir / file_path.name

        if self.args.dry_run:
            logger.info(f"[DRY RUN] Move: {file_path.name} -> {dest_dir}")
            return

        dest_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(file_path), str(dest_path))
            # 関連ファイルも移動
            for suffix in ['.json', '.xmp']:
                sidecar = file_path.with_suffix(file_path.suffix + suffix)
                if sidecar.exists():
                    shutil.move(str(sidecar), str(dest_dir / sidecar.name))
        except Exception as e:
            logger.error(f"Move failed: {e}")

    def run(self):
        """実行メインループ（並列処理）"""
        self.stats.start_time = time.time()
        
        # ファイルリストアップ
        logger.info(f"📂 ディレクトリをスキャン中: {self.target_dir}")
        all_files = []
        for root, _, files in os.walk(self.target_dir):
            for f in files:
                path = Path(root) / f
                if path.suffix.lower() in EXIFTOOL_WRITABLE:
                    all_files.append(path)
        
        self.stats.total_files = len(all_files)
        logger.info(f"📷 対象ファイル数: {self.stats.total_files}")
        logger.info(f"⚡ 並列スレッド数: {self.args.threads}")
        logger.info(f"🌍 タイムゾーン設定: UTC{self.args.timezone:+d}")

        # 並列処理実行
        with ThreadPoolExecutor(max_workers=self.args.threads) as executor:
            # Futureオブジェクトとパスの辞書
            future_to_file = {executor.submit(self.process_file, f): f for f in all_files}
            
            for future in as_completed(future_to_file):
                f = future_to_file[future]
                try:
                    status = future.result()
                    
                    if status == "updated":
                        self.stats.processed += 1
                        logger.info(f"✅ Updated: {f.name}")
                    elif status == "skipped":
                        self.stats.skipped += 1
                        if self.args.verbose:
                            logger.info(f"⏭️ Skipped (Processed): {f.name}")
                    elif status == "no_json":
                        if self.args.verbose:
                            logger.warning(f"⚠️ No JSON: {f.name}")
                    elif status == "error":
                        self.stats.errors += 1
                        logger.error(f"❌ Error: {f.name}")
                        
                except Exception as e:
                    logger.error(f"Thread error {f.name}: {e}")
                    self.stats.errors += 1

        # 完了処理
        self._save_log()
        duration = self.stats.get_duration()
        
        print("\n" + "="*50)
        print(f"🎉 処理完了 ({duration:.1f}秒)")
        print(f"  総ファイル数: {self.stats.total_files}")
        print(f"  更新成功:     {self.stats.processed}")
        print(f"  スキップ:     {self.stats.skipped}")
        print(f"  エラー:       {self.stats.errors}")
        print("="*50)


def main():
    parser = argparse.ArgumentParser(description='Google Photos Metadata Fixer')
    parser.add_argument('target_dir', help='処理対象のフォルダパス')
    parser.add_argument('--timezone', type=int, default=9, help='タイムゾーンオフセット (時間)。日本は 9 (デフォルト)')
    parser.add_argument('--threads', type=int, default=os.cpu_count() or 4, help='並列処理スレッド数')
    parser.add_argument('--dry-run', action='store_true', help='変更を行わずシミュレーションのみ行う')
    parser.add_argument('--force', action='store_true', help='処理済みフラグを無視して全ファイルを再処理')
    parser.add_argument('--no-gps', action='store_true', help='GPS情報を書き込まない')
    parser.add_argument('--ignore-history', action='store_true', help='過去の処理履歴をロードしない')
    parser.add_argument('--organize', type=Path, help='(オプション) 指定パスに年月フォルダを作成して移動')
    parser.add_argument('--verbose', '-v', action='store_true', help='詳細ログを表示')

    args = parser.parse_args()

    if not Path(args.target_dir).exists():
        print(f"エラー: 指定されたディレクトリが存在しません: {args.target_dir}")
        sys.exit(1)

    fixer = PhotoFixer(args.target_dir, args)
    fixer.run()

if __name__ == '__main__':
    main()
