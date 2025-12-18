#!/usr/bin/env python3
"""
BVE5 to BVE4 Converter
Converts BVE Trainsim 5 map/route files to BVE Trainsim 4 format.

BVE5専用構文を削除し、BVE4からBVE5で変更された構文を元に戻します。
"""

import re
import os
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ConversionResult:
    """変換結果を保持するクラス"""
    success: bool
    original_lines: int
    converted_lines: int
    removed_lines: int
    warnings: List[str]
    errors: List[str]


class BVE5ToBVE4Converter:
    """BVE5からBVE4への変換クラス"""

    # BVE5専用構文（削除対象）
    BVE5_ONLY_PATTERNS = [
        # Repeater関連（BVE5専用）
        r'^\s*Repeater\s*\[',
        r'^\s*Repeater\s*\.',
        r'^\s*Repeater\.Begin\s*\(',
        r'^\s*Repeater\.Begin0\s*\(',
        r'^\s*Repeater\.End\s*\(',

        # Background拡張構文（BVE5専用）
        r'^\s*Background\.Change\s*\(',

        # 変数定義（BVE5専用）
        r'^\s*\$[a-zA-Z_][a-zA-Z0-9_]*\s*=',

        # include文（BVE5専用）
        r'^\s*include\s*[\'"]',
        r'^\s*include\s*\(',

        # Section拡張（BVE5専用部分）
        r'^\s*Section\.SetSpeedLimit\s*\(',

        # SpeedLimit拡張（BVE5専用）
        r'^\s*SpeedLimit\.SetSignal\s*\(',

        # Irregularity（BVE5専用）
        r'^\s*Irregularity\s*\.',

        # Adhesion（BVE5専用）
        r'^\s*Adhesion\s*\.',

        # Sound3D（BVE5専用）
        r'^\s*Sound3D\s*\.',

        # RollingNoise（BVE5専用）
        r'^\s*RollingNoise\s*\.',

        # FlangeNoise（BVE5専用）
        r'^\s*FlangeNoise\s*\.',

        # JointNoise（BVE5専用）
        r'^\s*JointNoise\s*\.',

        # Train関連の一部（BVE5拡張）
        r'^\s*Train\.SetTrack\s*\(',

        # Legacy名前空間（BVE5でBVE4互換用に用意されたもの、そのまま変換）
        # これは変換対象なので削除しない
    ]

    # BVE5からBVE4への構文変換マッピング
    SYNTAX_CONVERSIONS = [
        # ヘッダー変換
        (r'^BveTs\s+Map\s+2\.\d+', 'BveTs Map 1.00'),
        (r'^BveTs\s+Map\s+2\.\d+:\s*utf-8', 'BveTs Map 1.00'),

        # Structure.Load形式変換（BVE5形式→BVE4形式）
        # BVE5: Structure.Load(key, filepath);
        # BVE4: Structure[key].Load(filepath);
        (r'Structure\.Load\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)', r'Structure[\1].Load(\2)'),

        # Structure.Put形式変換
        # BVE5: Structure[key].Put(track, x, y, z, rx, ry, rz, tilt, span);
        # BVE4では一部パラメータが異なる場合がある

        # Track関連の変換
        # BVE5: Track[key].Position(x, y, radiusH, radiusV);
        # BVE4: Track[key].X.Interpolate(x, radiusH); Track[key].Y.Interpolate(y, radiusV);

        # Fog変換
        # BVE5: Fog.Interpolate(density, r, g, b); または Fog.Set(density, r, g, b);
        # BVE4: Legacy.Fog(start, end, r, g, b);
        (r'Fog\.Interpolate\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)',
         r'Legacy.Fog(0, \1, \2, \3, \4)'),
        (r'Fog\.Set\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)',
         r'Legacy.Fog(0, \1, \2, \3, \4)'),

        # CabIlluminance変換
        (r'CabIlluminance\.Interpolate\s*\(\s*([^)]+)\s*\)', r'Legacy.CabIlluminance(\1)'),
        (r'CabIlluminance\.Set\s*\(\s*([^)]+)\s*\)', r'Legacy.CabIlluminance(\1)'),

        # Signal.Load変換
        # BVE5: Signal.Load(key, filepath);
        # BVE4: Signal[key].Load(filepath);
        (r'Signal\.Load\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)', r'Signal[\1].Load(\2)'),

        # Signal.Put変換（一部）
        (r'Signal\.Put\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)', r'Signal[\1].Put(\2, \3)'),

        # Beacon.Put変換（パラメータ数の調整）
        # BVE5では追加パラメータがある場合があるので、基本形式に戻す

        # Station変換
        # BVE5: Station.Load(filepath);
        # BVE4: 直接定義またはファイル参照

        # Sound.Load変換
        (r'Sound\.Load\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)', r'Sound[\1].Load(\2)'),

        # Sound3D.Load変換（BVE5専用なので削除対象だが、Soundに変換できる場合）

        # Curve変換（BVE5形式からBVE4形式へ）
        # BVE5: Curve.Interpolate(radius, cant);
        # BVE4: Curve.BeginTransition(); Curve.Begin(radius, cant);
        (r'(\s*)Curve\.Interpolate\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)', r'\1Curve.BeginTransition();\n\1Curve.Begin(\2, \3)'),
        (r'Curve\.Begin\s*\(\s*([^,)]+)\s*\)', r'Curve.Begin(\1, 0)'),

        # Pitch変換
        (r'Pitch\.Interpolate\s*\(\s*([^)]+)\s*\)', r'Legacy.Pitch(\1)'),
        (r'Pitch\.Set\s*\(\s*([^)]+)\s*\)', r'Legacy.Pitch(\1)'),

        # Turn変換
        (r'Turn\.Interpolate\s*\(\s*([^)]+)\s*\)', r'Legacy.Turn(\1)'),
        (r'Turn\.Set\s*\(\s*([^)]+)\s*\)', r'Legacy.Turn(\1)'),
    ]

    # 変数展開パターン（BVE5の変数を検出）
    VARIABLE_PATTERN = r'\$[a-zA-Z_][a-zA-Z0-9_]*'

    def __init__(self, encoding: str = 'utf-8', output_encoding: str = 'utf-8'):
        """
        初期化

        Args:
            encoding: 入力ファイルのエンコーディング
            output_encoding: 出力ファイルのエンコーディング（'utf-8' or 'shift_jis'）
        """
        self.encoding = encoding
        self.output_encoding = output_encoding
        self.variables = {}  # 変数名と値のマッピング
        self.warnings = []
        self.errors = []

    def _is_bve5_only_syntax(self, line: str) -> bool:
        """BVE5専用構文かどうかを判定"""
        for pattern in self.BVE5_ONLY_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False

    def _extract_variables(self, content: str) -> dict:
        """BVE5の変数定義を抽出"""
        variables = {}
        pattern = r'^\s*\$([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+?)\s*;?\s*$'
        for match in re.finditer(pattern, content, re.MULTILINE):
            var_name = match.group(1)
            var_value = match.group(2).strip().rstrip(';')
            variables[var_name] = var_value
        return variables

    def _expand_variables(self, line: str, variables: dict) -> str:
        """変数を展開（可能な場合）"""
        def replace_var(match):
            var_name = match.group(0)[1:]  # $を除去
            if var_name in variables:
                return variables[var_name]
            else:
                self.warnings.append(f"未定義の変数: ${var_name}")
                return match.group(0)

        return re.sub(self.VARIABLE_PATTERN, replace_var, line)

    def _convert_syntax(self, line: str) -> str:
        """構文を変換"""
        converted = line
        for pattern, replacement in self.SYNTAX_CONVERSIONS:
            converted = re.sub(pattern, replacement, converted, flags=re.IGNORECASE)
        return converted

    def _is_comment_or_empty(self, line: str) -> bool:
        """コメント行または空行かどうかを判定"""
        stripped = line.strip()
        return stripped == '' or stripped.startswith('//')  or stripped.startswith('#')

    def _process_multiline_comment(self, lines: List[str], start_idx: int) -> Tuple[int, bool]:
        """
        複数行コメントを処理

        Returns:
            (終了インデックス, コメント内か)
        """
        in_comment = False
        for i in range(start_idx, len(lines)):
            line = lines[i]
            if '/*' in line:
                in_comment = True
            if '*/' in line:
                return i, False
        return len(lines) - 1, in_comment

    def convert_map_file(self, content: str) -> Tuple[str, ConversionResult]:
        """
        マップファイルを変換

        Args:
            content: 変換元のファイル内容

        Returns:
            (変換後の内容, 変換結果)
        """
        self.warnings = []
        self.errors = []

        # 変数を抽出
        self.variables = self._extract_variables(content)

        lines = content.split('\n')
        converted_lines = []
        removed_count = 0
        in_multiline_comment = False

        i = 0
        while i < len(lines):
            line = lines[i]

            # 複数行コメントの処理
            if '/*' in line and '*/' not in line:
                in_multiline_comment = True
                converted_lines.append(line)
                i += 1
                continue

            if in_multiline_comment:
                converted_lines.append(line)
                if '*/' in line:
                    in_multiline_comment = False
                i += 1
                continue

            # コメント行・空行はそのまま
            if self._is_comment_or_empty(line):
                converted_lines.append(line)
                i += 1
                continue

            # BVE5専用構文は削除
            if self._is_bve5_only_syntax(line):
                self.warnings.append(f"BVE5専用構文を削除: {line.strip()}")
                removed_count += 1
                i += 1
                continue

            # 変数展開
            if re.search(self.VARIABLE_PATTERN, line):
                line = self._expand_variables(line, self.variables)
                self.warnings.append(f"変数を展開: {lines[i].strip()} → {line.strip()}")

            # 構文変換
            converted = self._convert_syntax(line)
            if converted != line:
                self.warnings.append(f"構文を変換: {line.strip()} → {converted.strip()}")

            converted_lines.append(converted)
            i += 1

        result = ConversionResult(
            success=len(self.errors) == 0,
            original_lines=len(lines),
            converted_lines=len(converted_lines),
            removed_lines=removed_count,
            warnings=self.warnings.copy(),
            errors=self.errors.copy()
        )

        return '\n'.join(converted_lines), result

    def convert_file(self, input_path: str, output_path: Optional[str] = None) -> ConversionResult:
        """
        ファイルを変換して保存

        Args:
            input_path: 入力ファイルパス
            output_path: 出力ファイルパス（Noneの場合は入力ファイルに_bve4を付加）

        Returns:
            変換結果
        """
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_bve4{ext}"

        # エンコーディングを自動検出
        encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932', 'euc-jp']
        content = None
        used_encoding = None

        for enc in encodings:
            try:
                with open(input_path, 'r', encoding=enc) as f:
                    content = f.read()
                    used_encoding = enc
                    break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if content is None:
            return ConversionResult(
                success=False,
                original_lines=0,
                converted_lines=0,
                removed_lines=0,
                warnings=[],
                errors=[f"ファイルを読み込めませんでした: {input_path}"]
            )

        # 変換
        converted_content, result = self.convert_map_file(content)

        # 保存（指定されたエンコーディングで出力）
        try:
            with open(output_path, 'w', encoding=self.output_encoding, errors='replace') as f:
                f.write(converted_content)
        except Exception as e:
            result.errors.append(f"ファイルの保存に失敗しました: {str(e)}")
            result.success = False

        return result


class BVE5StructureConverter:
    """BVE5のストラクチャーリストファイルを変換"""

    # BVE5専用構文（ストラクチャーリスト用）
    BVE5_ONLY_STRUCTURE_PATTERNS = [
        r'^\s*Model\s*\[',  # Model定義（BVE5専用）
    ]

    def __init__(self):
        self.warnings = []
        self.errors = []

    def convert_structure_list(self, content: str) -> Tuple[str, ConversionResult]:
        """
        ストラクチャーリストファイルを変換

        Args:
            content: 変換元のファイル内容

        Returns:
            (変換後の内容, 変換結果)
        """
        self.warnings = []
        self.errors = []

        lines = content.split('\n')
        converted_lines = []
        removed_count = 0

        for line in lines:
            # ヘッダー変換
            if re.match(r'^BveTs\s+Structure\s+List\s+2\.\d+', line, re.IGNORECASE):
                converted_lines.append('BveTs Structure List 1.00')
                self.warnings.append(f"ヘッダーを変換: {line.strip()}")
                continue

            # BVE5専用構文の削除
            skip = False
            for pattern in self.BVE5_ONLY_STRUCTURE_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    self.warnings.append(f"BVE5専用構文を削除: {line.strip()}")
                    removed_count += 1
                    skip = True
                    break

            if not skip:
                converted_lines.append(line)

        result = ConversionResult(
            success=len(self.errors) == 0,
            original_lines=len(lines),
            converted_lines=len(converted_lines),
            removed_lines=removed_count,
            warnings=self.warnings.copy(),
            errors=self.errors.copy()
        )

        return '\n'.join(converted_lines), result


class BVE5StationConverter:
    """BVE5の駅リストファイルを変換"""

    def __init__(self):
        self.warnings = []
        self.errors = []

    def convert_station_list(self, content: str) -> Tuple[str, ConversionResult]:
        """
        駅リストファイルを変換

        Args:
            content: 変換元のファイル内容

        Returns:
            (変換後の内容, 変換結果)
        """
        self.warnings = []
        self.errors = []

        lines = content.split('\n')
        converted_lines = []

        for line in lines:
            # ヘッダー変換
            if re.match(r'^BveTs\s+Station\s+List\s+2\.\d+', line, re.IGNORECASE):
                converted_lines.append('BveTs Station List 1.00')
                self.warnings.append(f"ヘッダーを変換: {line.strip()}")
                continue

            converted_lines.append(line)

        result = ConversionResult(
            success=len(self.errors) == 0,
            original_lines=len(lines),
            converted_lines=len(converted_lines),
            removed_lines=0,
            warnings=self.warnings.copy(),
            errors=self.errors.copy()
        )

        return '\n'.join(converted_lines), result


def detect_file_type(filepath: str) -> str:
    """
    ファイルタイプを検出

    Returns:
        'map', 'structure', 'station', 'signal', 'sound', 'train', 'unknown'
    """
    encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
    content = None

    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                content = f.read(500)  # 先頭500文字を読む
                break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if content is None:
        return 'unknown'

    content_lower = content.lower()

    if 'bvets map' in content_lower:
        return 'map'
    elif 'bvets structure list' in content_lower:
        return 'structure'
    elif 'bvets station list' in content_lower:
        return 'station'
    elif 'bvets signal' in content_lower:
        return 'signal'
    elif 'bvets sound' in content_lower:
        return 'sound'
    elif 'bvets train' in content_lower:
        return 'train'

    # 拡張子で判定
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ['.txt', '.map']:
        return 'map'
    elif ext == '.csv':
        return 'structure'

    return 'unknown'


if __name__ == '__main__':
    # テスト用
    test_content = """BveTs Map 2.02

// テストマップ
$distance = 1000;
$radius = 400;

0;
    Track['Rail1'].Position(3.8, 0);
    Structure.Load('ballast', 'structures/ballast.csv');
    Repeater['test'].Begin(0, 'Rail1', 'structure1', 0, 0, 0, 0, 0, 0, 0, 25);

$distance;
    Curve.Interpolate($radius, 0.105);
    Fog.Set(500, 200, 200, 200);

2000;
    Repeater['test'].End();
    Signal.Put(0, -3.8, 4.8);
"""

    converter = BVE5ToBVE4Converter()
    converted, result = converter.convert_map_file(test_content)

    print("=== 変換結果 ===")
    print(converted)
    print("\n=== 統計 ===")
    print(f"成功: {result.success}")
    print(f"元の行数: {result.original_lines}")
    print(f"変換後の行数: {result.converted_lines}")
    print(f"削除された行数: {result.removed_lines}")
    print(f"\n警告 ({len(result.warnings)}):")
    for w in result.warnings:
        print(f"  - {w}")
