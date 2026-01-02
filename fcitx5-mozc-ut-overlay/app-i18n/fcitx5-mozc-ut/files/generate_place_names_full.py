#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2025 Overlay Maintainer
# Licensed under the Apache License, Version 2.0

"""
Generate place-names dictionary from Japan Post ZIP code data.
Reads pre-downloaded CSV files (ken_all.csv and jigyosyo.csv).

Usage: python generate_place_names_full.py <ken_all.csv> <jigyosyo.csv>
"""

import csv
import sys
import unicodedata


def kata_to_hira(text):
    """
    Convert katakana to hiragana.
    Handles both full-width and half-width katakana via NFKC normalization.
    """
    # Normalize half-width kana to full-width
    normalized = unicodedata.normalize('NFKC', text)

    result = []
    for ch in normalized:
        code = ord(ch)
        # Katakana (ァ-ン: U+30A1-U+30F3) to Hiragana (ぁ-ん: U+3041-U+3093)
        if 0x30A1 <= code <= 0x30F3:
            result.append(chr(code - 0x60))
        # Special cases
        elif ch == 'ヵ':
            result.append('か')
        elif ch == 'ヶ':
            result.append('け')
        elif ch == 'ヴ':
            result.append('ゔ')
        elif ch == 'ー':
            result.append('ー')
        else:
            result.append(ch)

    return ''.join(result)


def process_ken_all(csv_path):
    """
    Process ken_all.csv (residential addresses).

    CSV format (15 columns):
    0: JIS code
    1: Old ZIP code (5 digits)
    2: ZIP code (7 digits)
    3: Prefecture name (kana) ← Reading
    4: City name (kana)       ← Reading
    5: Town name (kana)       ← Reading
    6: Prefecture name (kanji) ← Surface
    7: City name (kanji)       ← Surface
    8: Town name (kanji)       ← Surface
    9-14: Various flags

    Returns: set of (kana, kanji) tuples
    """
    entries = set()

    try:
        with open(csv_path, 'r', encoding='cp932', errors='replace') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 9:
                    continue

                # Kana columns (reading) - normalize and remove spaces
                pref_kana = unicodedata.normalize('NFKC', row[3]).replace(' ', '').replace('　', '')
                city_kana = unicodedata.normalize('NFKC', row[4]).replace(' ', '').replace('　', '')
                town_kana = unicodedata.normalize('NFKC', row[5]).replace(' ', '').replace('　', '')

                # Kanji columns (surface)
                pref_kanji = row[6].strip()
                city_kanji = row[7].strip()
                town_kanji = row[8].strip()

                # Skip entries with special markers
                if '（' in town_kanji or '以下に掲載がない場合' in town_kanji:
                    town_kanji = ''
                    town_kana = ''

                # Prefecture
                if pref_kana and pref_kanji:
                    entries.add((pref_kana, pref_kanji))

                # City
                if city_kana and city_kanji:
                    entries.add((city_kana, city_kanji))
                    # Prefecture + City
                    entries.add((pref_kana + city_kana, pref_kanji + city_kanji))

                # Town
                if town_kana and town_kanji:
                    entries.add((town_kana, town_kanji))
                    # City + Town
                    entries.add((city_kana + town_kana, city_kanji + town_kanji))
                    # Full address
                    entries.add((pref_kana + city_kana + town_kana,
                                 pref_kanji + city_kanji + town_kanji))

    except Exception as e:
        print(f"Error processing {csv_path}: {e}", file=sys.stderr)

    return entries


def process_jigyosyo(csv_path):
    """
    Process jigyosyo.csv (business/office addresses).

    CSV format (13 columns):
    0: JIS code (5 digits)
    1: Business name (kana)   ← Reading
    2: Business name (kanji)  ← Surface
    3: Prefecture name (kanji)
    4: City name (kanji)
    5: Town name (kanji)
    6: Street address details
    7: ZIP code (7 digits)
    ...

    Returns: set of (kana, kanji) tuples
    """
    entries = set()

    try:
        with open(csv_path, 'r', encoding='cp932', errors='replace') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 8:
                    continue

                # Business name - kana and kanji
                name_kana = unicodedata.normalize('NFKC', row[1]).replace(' ', '').replace('　', '')
                name_kanji = row[2].replace('　', ' ').strip()

                if name_kana and name_kanji and len(name_kanji) >= 2:
                    entries.add((name_kana, name_kanji))

    except Exception as e:
        print(f"Error processing {csv_path}: {e}", file=sys.stderr)

    return entries


def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_place_names_full.py <ken_all.csv> <jigyosyo.csv>",
              file=sys.stderr)
        sys.exit(1)

    ken_all_csv = sys.argv[1]
    jigyosyo_csv = sys.argv[2]

    all_entries = set()

    print(f"Processing {ken_all_csv}...")
    entries = process_ken_all(ken_all_csv)
    print(f"  Found {len(entries)} entries from ken_all")
    all_entries.update(entries)

    print(f"Processing {jigyosyo_csv}...")
    entries = process_jigyosyo(jigyosyo_csv)
    print(f"  Found {len(entries)} entries from jigyosyo")
    all_entries.update(entries)

    print(f"Total unique entries: {len(all_entries)}")
    print("Generating Mozc dictionary entries...")

    # Mozc dictionary format:
    # reading<TAB>left_id<TAB>right_id<TAB>cost<TAB>surface
    # 1847 = proper noun (place name)
    cost = 8000
    output_file = "mozcdic-ut-place-names.txt"

    valid_count = 0
    with open(output_file, 'w', encoding='utf-8') as f:
        for kana, kanji in sorted(all_entries):
            if not kana or not kanji:
                continue

            # Convert katakana to hiragana for reading
            reading = kata_to_hira(kana)

            # Validate reading contains only valid characters
            valid = True
            for ch in reading:
                code = ord(ch)
                # Allow hiragana (ぁ-ゖ), prolonged sound mark (ー), iteration marks
                if not (0x3041 <= code <= 0x3096 or ch in 'ーゝゞ'):
                    valid = False
                    break

            if valid:
                f.write(f"{reading}\t1847\t1847\t{cost}\t{kanji}\n")
                valid_count += 1

    print(f"Written {valid_count} entries to {output_file}")


if __name__ == "__main__":
    main()
