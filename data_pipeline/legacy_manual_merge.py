"""
Baseline "before" process: what consolidating the four facility exports looked
like before this pipeline existed. Pure Python, row-by-row, no vectorization -
each row is parsed field-by-field and checked against every row seen so far
for duplicates, the way someone eyeballing/copy-pasting across spreadsheets
would. This exists so clean_and_load.py's speedup can be measured against a
real baseline instead of an asserted number - see benchmark.py.
"""
import csv
import time
from pathlib import Path

RAW_DIR = Path(__file__).parent / "raw_data"

FILES = [
    ("facility_northeast.csv", "northeast"),
    ("facility_midwest.csv", "midwest"),
    ("facility_south.csv", "south"),
    ("facility_west.csv", "west"),
]


def parse_amenities(raw):
    if not raw:
        return []
    parts = []
    for chunk in raw.split(";"):
        chunk = chunk.strip().lower()
        if chunk:
            parts.append(chunk)
    return parts


def parse_bool(raw, facility):
    raw = (raw or "").strip().lower()
    if facility == "northeast":
        return raw == "open"
    if facility == "midwest":
        return raw == "y"
    if facility == "south":
        return raw == "1"
    if facility == "west":
        return raw == "true"
    return False


def row_to_record(row, facility):
    if facility == "northeast":
        lat_raw, lng_raw = row.get("Latitude"), row.get("Longitude")
        try:
            lat, lng = float(lat_raw), float(lng_raw)
        except (TypeError, ValueError):
            return None
        return {
            "name": row.get("Campground Name", "").strip(),
            "city": row.get("Site City", "").strip(),
            "state": row.get("Site State", "").strip().upper(),
            "lat": lat, "lng": lng,
            "amenities": parse_amenities(row.get("Amenities", "")),
            "sites": int(row.get("Capacity") or 0),
            "open": parse_bool(row.get("Status"), facility),
        }
    if facility == "midwest":
        lat_raw, lng_raw = row.get("lat"), row.get("lng")
        try:
            lat, lng = float(lat_raw), float(lng_raw)
        except (TypeError, ValueError):
            return None
        return {
            "name": row.get("name", "").strip(),
            "city": row.get("city", "").strip(),
            "state": row.get("state", "").strip().upper(),
            "lat": lat, "lng": lng,
            "amenities": parse_amenities(row.get("amenities", "")),
            "sites": int(row.get("sites") or 0),
            "open": parse_bool(row.get("active"), facility),
        }
    if facility == "south":
        lat_raw, lng_raw = row.get("LAT"), row.get("LON")
        try:
            lat, lng = float(lat_raw), float(lng_raw)
        except (TypeError, ValueError):
            return None
        return {
            "name": row.get("CAMPGROUND", "").strip().title(),
            "city": row.get("CITY", "").strip(),
            "state": row.get("STATE", "").strip().upper(),
            "lat": lat, "lng": lng,
            "amenities": parse_amenities(row.get("AMENITIES", "")),
            "sites": int(row.get("NUM_SITES") or 0),
            "open": parse_bool(row.get("OPEN"), facility),
        }
    if facility == "west":
        coords = row.get("coordinates", "")
        try:
            lat_str, lng_str = coords.split(",")
            lat, lng = float(lat_str), float(lng_str)
        except (ValueError, AttributeError):
            return None
        return {
            "name": row.get("campground_name", "").strip(),
            "city": row.get("town", "").strip(),
            "state": row.get("region_state", "").strip().upper(),
            "lat": lat, "lng": lng,
            "amenities": parse_amenities(row.get("features", "")),
            "sites": int(row.get("site_count") or 0),
            "open": parse_bool(row.get("is_open"), facility),
        }
    return None


def is_duplicate(record, seen_records):
    for existing in seen_records:
        if (existing["name"].strip().lower() == record["name"].strip().lower()
                and existing["city"].strip().lower() == record["city"].strip().lower()
                and existing["state"].strip().lower() == record["state"].strip().lower()):
            return True
    return False


def run():
    started = time.perf_counter()
    seen_records = []
    total_raw_rows = 0
    skipped = 0

    for filename, facility in FILES:
        path = RAW_DIR / filename
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_raw_rows += 1
                record = row_to_record(row, facility)
                if record is None:
                    skipped += 1
                    continue
                if is_duplicate(record, seen_records):
                    continue
                seen_records.append(record)

    elapsed = time.perf_counter() - started
    return {
        "elapsed_seconds": elapsed,
        "raw_rows": total_raw_rows,
        "clean_records": len(seen_records),
        "skipped_bad_rows": skipped,
    }


if __name__ == "__main__":
    stats = run()
    print("Legacy manual-style merge:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
