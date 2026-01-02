#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2025 Overlay Maintainer
# Licensed under the Apache License, Version 2.0

"""
Generate place-names dictionary from Japan Post ZIP code data.
Includes both ken_all.zip (residential addresses) and jigyosyo.zip (business addresses).
"""

import csv
import io
import urllib.request
import zipfile


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
    3: Prefecture name (kana)
    4: City name (kana)
    5: Town name (kana)
    6: Prefecture name (kanji)
    7: City name (kanji)
    8: Town name (kanji)
    9-14: Various flags
    """
    entries = set()
    reader = csv.reader(io.StringIO(csv_content))

    for row in reader:
        if len(row) < 9:
            continue

        prefecture = row[6].strip()
        city = row[7].strip()
        town = row[8].strip()

        # Skip entries with special markers
        if '（' in town or '以下に掲載がない場合' in town:
            town = ''

        # Add prefecture
        if prefecture:
            entries.add(prefecture)

        # Add city
        if city:
            entries.add(city)
            # Add prefecture + city
            entries.add(prefecture + city)

        # Add town (if valid)
        if town and town not in ('', '以下に掲載がない場合'):
            entries.add(town)
            # Add city + town
            entries.add(city + town)
            # Add full address
            entries.add(prefecture + city + town)

    return entries


def process_jigyosyo(csv_content):
    """
    Process jigyosyo.csv (business/office addresses).

    Format (13 columns):
    0: JIS code (5 digits)
    1: Business name (kana)
    2: Business name (kanji)
    3: Prefecture name
    4: City name
    5: Town name
    6: Street address details
    7: ZIP code (7 digits)
    8: Old ZIP code (5 digits)
    9: Handling post office
    10: Type code
    11: Multiple numbers flag
    12: Modification code
    """
    entries = set()
    reader = csv.reader(io.StringIO(csv_content))

    for row in reader:
        if len(row) < 8:
            continue

        business_name = row[2].strip()
        prefecture = row[3].strip()
        city = row[4].strip()
        town = row[5].strip()
        street = row[6].strip()

        # Add business name (companies, organizations, etc.)
        if business_name:
            # Clean up business name
            business_name = business_name.replace('　', ' ').strip()
            if len(business_name) >= 2:
                entries.add(business_name)

        # Add address components
        if prefecture:
            entries.add(prefecture)
        if city:
            entries.add(city)
            entries.add(prefecture + city)
        if town:
            entries.add(town)
            entries.add(city + town)
        if street:
            # Add street if it's meaningful
            clean_street = street.replace('　', '').strip()
            if len(clean_street) >= 2 and not clean_street.isdigit():
                entries.add(clean_street)

    return entries


def generate_mozc_entries(entries, cost=8000):
    """
    Generate Mozc dictionary entries.

    Format: reading<TAB>left_id<TAB>right_id<TAB>cost<TAB>surface
    For place names, we use id=1847 (proper noun, place name)
    """
    import unicodedata

    output = []

    for entry in sorted(entries):
        if not entry or len(entry) < 2:
            continue

        # Generate reading (hiragana)
        # For simplicity, we just use the entry as-is for reading
        # In production, you'd want to use MeCab or similar for proper readings
        reading = entry

        # Convert katakana to hiragana for reading
        reading_chars = []
        for char in entry:
            code = ord(char)
            # Katakana to Hiragana conversion
            if 0x30A1 <= code <= 0x30F6:
                reading_chars.append(chr(code - 0x60))
            else:
                reading_chars.append(char)
        reading = ''.join(reading_chars)

        # Format: reading\tleft_id\tright_id\tcost\tsurface
        # Using 1847 for place names (proper noun)
        output.append(f"{reading}\t1847\t1847\t{cost}\t{entry}")

    return output


def main():
    # URLs for Japan Post data
    ken_all_url = "https://www.post.japanpost.jp/zipcode/dl/kogaki/zip/ken_all.zip"
    jigyosyo_url = "https://www.post.japanpost.jp/zipcode/dl/jigyosyo/zip/jigyosyo.zip"

    all_entries = set()

    # Process ken_all (residential addresses)
    print("Processing ken_all.zip (residential addresses)...")
    ken_all_csv = download_and_extract(ken_all_url, "ken_all.csv")
    if ken_all_csv:
        entries = process_ken_all(ken_all_csv)
        print(f"  Found {len(entries)} entries from ken_all")
        all_entries.update(entries)

    # Process jigyosyo (business addresses)
    print("Processing jigyosyo.zip (business addresses)...")
    jigyosyo_csv = download_and_extract(jigyosyo_url, "jigyosyo.csv")
    if jigyosyo_csv:
        entries = process_jigyosyo(jigyosyo_csv)
        print(f"  Found {len(entries)} entries from jigyosyo")
        all_entries.update(entries)

    print(f"Total unique entries: {len(all_entries)}")

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
