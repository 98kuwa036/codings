#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2025 Overlay Maintainer
# Licensed under the Apache License, Version 2.0

"""
Generate place-names dictionary from Japan Post ZIP code data.
Includes both ken_all.zip (residential addresses) and jigyosyo.zip (business addresses).

Generates proper (reading, surface) pairs using kana columns from the CSV data.
"""

import csv
import io
import urllib.request
import zipfile


def katakana_to_hiragana(text):
    """
    Convert katakana to hiragana using standard library.
    カタカナ（ァ-ヶ）をひらがな（ぁ-ゖ）に変換
    """
    result = []
    for char in text:
        code = ord(char)
        # Katakana (U+30A1-U+30F6) to Hiragana (U+3041-U+3096)
        if 0x30A1 <= code <= 0x30F6:
            result.append(chr(code - 0x60))
        # Katakana punctuation (U+30FC: ー) keep as is or convert
        elif code == 0x30FC:  # ー (prolonged sound mark)
            result.append('ー')
        else:
            result.append(char)
    return ''.join(result)


def normalize_kana(text):
    """
    Normalize kana text for Mozc dictionary.
    - Convert katakana to hiragana
    - Remove spaces and special characters
    """
    if not text:
        return ''

    # Convert to hiragana
    hiragana = katakana_to_hiragana(text)

    # Remove spaces (both full-width and half-width)
    hiragana = hiragana.replace('　', '').replace(' ', '')

    return hiragana


def download_and_extract(url, filename):
    """Download a ZIP file and extract the CSV content."""
    print(f"Downloading {url}...")
    with urllib.request.urlopen(url) as response:
        zip_data = response.read()

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        for name in zf.namelist():
            if name.upper().endswith('.CSV'):
                with zf.open(name) as f:
                    # Read as Shift-JIS (CP932) which Japan Post uses
                    return f.read().decode('cp932')
    return None


def process_ken_all(csv_content):
    """
    Process ken_all.csv (residential addresses).

    Format (15 columns):
    0: JIS code
    1: Old ZIP code (5 digits)
    2: ZIP code (7 digits)
    3: Prefecture name (kana) ← USE THIS FOR READING
    4: City name (kana)       ← USE THIS FOR READING
    5: Town name (kana)       ← USE THIS FOR READING
    6: Prefecture name (kanji) ← Surface
    7: City name (kanji)       ← Surface
    8: Town name (kanji)       ← Surface
    9-14: Various flags

    Returns: list of (reading, surface) tuples
    """
    entries = []
    seen = set()
    reader = csv.reader(io.StringIO(csv_content))

    for row in reader:
        if len(row) < 9:
            continue

        # Kana (reading)
        pref_kana = row[3].strip()
        city_kana = row[4].strip()
        town_kana = row[5].strip()

        # Kanji (surface)
        pref_kanji = row[6].strip()
        city_kanji = row[7].strip()
        town_kanji = row[8].strip()

        # Skip entries with special markers in town
        if '（' in town_kanji or '以下に掲載がない場合' in town_kanji:
            town_kanji = ''
            town_kana = ''

        # Convert kana to hiragana for reading
        pref_reading = normalize_kana(pref_kana)
        city_reading = normalize_kana(city_kana)
        town_reading = normalize_kana(town_kana)

        # Add prefecture
        if pref_reading and pref_kanji:
            key = (pref_reading, pref_kanji)
            if key not in seen:
                entries.append(key)
                seen.add(key)

        # Add city
        if city_reading and city_kanji:
            key = (city_reading, city_kanji)
            if key not in seen:
                entries.append(key)
                seen.add(key)

            # Add prefecture + city
            full_reading = pref_reading + city_reading
            full_surface = pref_kanji + city_kanji
            key = (full_reading, full_surface)
            if key not in seen:
                entries.append(key)
                seen.add(key)

        # Add town (if valid)
        if town_reading and town_kanji:
            key = (town_reading, town_kanji)
            if key not in seen:
                entries.append(key)
                seen.add(key)

            # Add city + town
            ct_reading = city_reading + town_reading
            ct_surface = city_kanji + town_kanji
            key = (ct_reading, ct_surface)
            if key not in seen:
                entries.append(key)
                seen.add(key)

            # Add full address (prefecture + city + town)
            full_reading = pref_reading + city_reading + town_reading
            full_surface = pref_kanji + city_kanji + town_kanji
            key = (full_reading, full_surface)
            if key not in seen:
                entries.append(key)
                seen.add(key)

    return entries


def process_jigyosyo(csv_content):
    """
    Process jigyosyo.csv (business/office addresses).

    Format (13 columns):
    0: JIS code (5 digits)
    1: Business name (kana)   ← USE THIS FOR READING
    2: Business name (kanji)  ← Surface
    3: Prefecture name (kanji)
    4: City name (kanji)
    5: Town name (kanji)
    6: Street address details
    7: ZIP code (7 digits)
    8: Old ZIP code (5 digits)
    9: Handling post office
    10: Type code
    11: Multiple numbers flag
    12: Modification code

    Note: jigyosyo.csv doesn't have separate kana columns for addresses,
    only for business names.

    Returns: list of (reading, surface) tuples
    """
    entries = []
    seen = set()
    reader = csv.reader(io.StringIO(csv_content))

    for row in reader:
        if len(row) < 8:
            continue

        business_kana = row[1].strip()
        business_kanji = row[2].strip()

        # Add business name with proper reading
        if business_kana and business_kanji:
            # Clean up
            business_kana = business_kana.replace('　', ' ').strip()
            business_kanji = business_kanji.replace('　', ' ').strip()

            # Convert kana to hiragana
            reading = normalize_kana(business_kana)

            if len(reading) >= 2 and len(business_kanji) >= 2:
                key = (reading, business_kanji)
                if key not in seen:
                    entries.append(key)
                    seen.add(key)

    return entries


def generate_mozc_entries(entries, cost=8000):
    """
    Generate Mozc dictionary entries.

    Format: reading<TAB>left_id<TAB>right_id<TAB>cost<TAB>surface

    For place names, we use id=1847 (proper noun, place name)
    For organization names, we use id=1848 (proper noun, organization)
    """
    output = []

    for reading, surface in entries:
        if not reading or not surface:
            continue

        # Skip if reading contains non-hiragana characters (except ー)
        valid_reading = True
        for char in reading:
            code = ord(char)
            # Allow hiragana (ぁ-ゖ), prolonged sound mark (ー), and some punctuation
            if not (0x3041 <= code <= 0x3096 or char in 'ーゝゞ'):
                valid_reading = False
                break

        if not valid_reading:
            continue

        # Format: reading\tleft_id\tright_id\tcost\tsurface
        # Using 1847 for place names (proper noun)
        output.append(f"{reading}\t1847\t1847\t{cost}\t{surface}")

    return output


def main():
    # URLs for Japan Post data
    ken_all_url = "https://www.post.japanpost.jp/zipcode/dl/kogaki/zip/ken_all.zip"
    jigyosyo_url = "https://www.post.japanpost.jp/zipcode/dl/jigyosyo/zip/jigyosyo.zip"

    all_entries = []

    # Process ken_all (residential addresses)
    print("Processing ken_all.zip (residential addresses)...")
    ken_all_csv = download_and_extract(ken_all_url, "ken_all.csv")
    if ken_all_csv:
        entries = process_ken_all(ken_all_csv)
        print(f"  Found {len(entries)} entries from ken_all")
        all_entries.extend(entries)

    # Process jigyosyo (business addresses)
    print("Processing jigyosyo.zip (business addresses)...")
    jigyosyo_csv = download_and_extract(jigyosyo_url, "jigyosyo.csv")
    if jigyosyo_csv:
        entries = process_jigyosyo(jigyosyo_csv)
        print(f"  Found {len(entries)} entries from jigyosyo")
        all_entries.extend(entries)

    print(f"Total entries: {len(all_entries)}")

    # Generate Mozc dictionary format
    print("Generating Mozc dictionary entries...")
    mozc_entries = generate_mozc_entries(all_entries)

    # Write output
    output_file = "mozcdic-ut-place-names.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(mozc_entries))
        f.write('\n')

    print(f"Written {len(mozc_entries)} entries to {output_file}")


if __name__ == "__main__":
    main()
