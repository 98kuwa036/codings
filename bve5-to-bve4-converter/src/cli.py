#!/usr/bin/env python3
"""
BVE5 to BVE4 Converter - Command Line Interface
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List

from converter import (
    BVE5ToBVE4Converter,
    BVE5StructureConverter,
    BVE5StationConverter,
    detect_file_type,
    ConversionResult
)


def print_result(filepath: str, result: ConversionResult, verbose: bool = False):
    """変換結果を表示"""
    status = "✓" if result.success else "✗"
    print(f"{status} {filepath}")
    print(f"  元の行数: {result.original_lines} → 変換後: {result.converted_lines} (削除: {result.removed_lines})")

    if verbose or not result.success:
        if result.warnings:
            print(f"  警告 ({len(result.warnings)}):")
            for w in result.warnings[:10]:  # 最初の10件のみ表示
                print(f"    - {w}")
            if len(result.warnings) > 10:
                print(f"    ... 他 {len(result.warnings) - 10} 件")

        if result.errors:
            print(f"  エラー ({len(result.errors)}):")
            for e in result.errors:
                print(f"    - {e}")


def convert_single_file(input_path: str, output_path: str = None, verbose: bool = False, output_encoding: str = 'utf-8') -> bool:
    """単一ファイルを変換"""
    if not os.path.exists(input_path):
        print(f"エラー: ファイルが見つかりません: {input_path}")
        return False

    file_type = detect_file_type(input_path)

    if file_type == 'map':
        converter = BVE5ToBVE4Converter(output_encoding=output_encoding)
        result = converter.convert_file(input_path, output_path)
    elif file_type == 'structure':
        converter = BVE5StructureConverter()
        # ファイルを読み込んで変換
        encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
        content = None
        for enc in encodings:
            try:
                with open(input_path, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if content:
            converted, result = converter.convert_structure_list(content)
            if output_path is None:
                base, ext = os.path.splitext(input_path)
                output_path = f"{base}_bve4{ext}"
            with open(output_path, 'w', encoding=output_encoding, errors='replace') as f:
                f.write(converted)
        else:
            result = ConversionResult(False, 0, 0, 0, [], ["ファイルを読み込めませんでした"])
    elif file_type == 'station':
        converter = BVE5StationConverter()
        encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
        content = None
        for enc in encodings:
            try:
                with open(input_path, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if content:
            converted, result = converter.convert_station_list(content)
            if output_path is None:
                base, ext = os.path.splitext(input_path)
                output_path = f"{base}_bve4{ext}"
            with open(output_path, 'w', encoding=output_encoding, errors='replace') as f:
                f.write(converted)
        else:
            result = ConversionResult(False, 0, 0, 0, [], ["ファイルを読み込めませんでした"])
    else:
        print(f"警告: 不明なファイルタイプです: {input_path}")
        print("  マップファイルとして処理します...")
        converter = BVE5ToBVE4Converter(output_encoding=output_encoding)
        result = converter.convert_file(input_path, output_path)

    print_result(input_path, result, verbose)

    if output_path:
        print(f"  出力: {output_path}")

    return result.success


def convert_directory(input_dir: str, output_dir: str = None, recursive: bool = False, verbose: bool = False, output_encoding: str = 'utf-8') -> tuple:
    """ディレクトリ内のファイルを変換"""
    if not os.path.isdir(input_dir):
        print(f"エラー: ディレクトリが見つかりません: {input_dir}")
        return 0, 0

    # 対象ファイル拡張子
    target_extensions = {'.txt', '.map', '.csv'}

    success_count = 0
    fail_count = 0

    if recursive:
        files = []
        for root, dirs, filenames in os.walk(input_dir):
            for filename in filenames:
                if Path(filename).suffix.lower() in target_extensions:
                    files.append(os.path.join(root, filename))
    else:
        files = [
            os.path.join(input_dir, f)
            for f in os.listdir(input_dir)
            if Path(f).suffix.lower() in target_extensions
        ]

    print(f"変換対象ファイル数: {len(files)}")
    print()

    for filepath in files:
        # 出力パスを計算
        if output_dir:
            rel_path = os.path.relpath(filepath, input_dir)
            base, ext = os.path.splitext(rel_path)
            out_path = os.path.join(output_dir, f"{base}_bve4{ext}")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
        else:
            out_path = None

        if convert_single_file(filepath, out_path, verbose, output_encoding):
            success_count += 1
        else:
            fail_count += 1

        print()

    return success_count, fail_count


def main():
    parser = argparse.ArgumentParser(
        description='BVE5 から BVE4 へのデータコンバーター',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 単一ファイルを変換
  python cli.py route.txt

  # 出力ファイル名を指定
  python cli.py route.txt -o route_bve4.txt

  # ディレクトリ内のファイルを一括変換
  python cli.py ./bve5_data/ -d

  # サブディレクトリも含めて再帰的に変換
  python cli.py ./bve5_data/ -d -r

  # 詳細出力モード
  python cli.py route.txt -v

対応ファイル形式:
  - マップファイル (.txt, .map)
  - ストラクチャーリスト (.csv)
  - 駅リスト (.csv)

変換内容:
  - BVE5専用構文の削除 (Repeater, 変数, include等)
  - BVE5構文からBVE4構文への変換
  - ヘッダーのバージョン変更 (2.xx → 1.00)
  - 文字エンコーディングの変換 (UTF-8 → Shift_JIS)
"""
    )

    parser.add_argument('input', help='変換するファイルまたはディレクトリのパス')
    parser.add_argument('-o', '--output', help='出力ファイルパス（単一ファイル変換時）')
    parser.add_argument('-d', '--directory', action='store_true',
                        help='入力をディレクトリとして処理')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='サブディレクトリも再帰的に処理')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='詳細な出力を表示')
    parser.add_argument('--output-dir', help='出力ディレクトリ（ディレクトリ変換時）')
    parser.add_argument('-e', '--encoding', choices=['utf-8', 'shift_jis', 'cp932'],
                        default='utf-8', help='出力ファイルのエンコーディング（デフォルト: utf-8）')
    parser.add_argument('--version', action='version', version='BVE5 to BVE4 Converter v1.0.0')

    args = parser.parse_args()

    print("=" * 60)
    print("BVE5 to BVE4 Converter")
    print("=" * 60)
    print(f"出力エンコーディング: {args.encoding}")
    print()

    if args.directory:
        success, fail = convert_directory(
            args.input,
            args.output_dir,
            args.recursive,
            args.verbose,
            args.encoding
        )
        print("=" * 60)
        print(f"完了: 成功 {success} 件, 失敗 {fail} 件")
        sys.exit(0 if fail == 0 else 1)
    else:
        success = convert_single_file(args.input, args.output, args.verbose, args.encoding)
        print()
        print("=" * 60)
        print("完了" if success else "エラーが発生しました")
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
