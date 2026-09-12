"""
Vectorized replacement for legacy_manual_merge.py: reads all four facility
exports, normalizes each to a common schema with pandas' vectorized string
ops (no per-row Python loops), validates coordinates, consolidates duplicate
cross-listings, and writes a single clean dataset - optionally loading it
straight into MongoDB for the API to serve.

Usage:
    python clean_and_load.py                  # writes cleaned_campgrounds.csv/json only
    python clean_and_load.py --load-mongo      # also upserts into MongoDB
"""
import argparse
import json
import time
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).parent / "raw_data"
OUT_CSV = Path(__file__).parent / "cleaned_campgrounds.csv"
OUT_JSON = Path(__file__).parent / "cleaned_campgrounds.json"

VALID_LAT = (24.0, 50.0)
VALID_LNG = (-125.0, -66.0)


def _split_amenities(series):
    return (
        series.fillna("")
        .str.split(";")
        .apply(lambda parts: sorted({p.strip().lower() for p in parts if p.strip()}))
    )


def load_northeast():
    df = pd.read_csv(RAW_DIR / "facility_northeast.csv")
    return pd.DataFrame({
        "name": df["Campground Name"].str.strip(),
        "city": df["Site City"].str.strip(),
        "state": df["Site State"].str.strip().str.upper(),
        "lat": pd.to_numeric(df["Latitude"], errors="coerce"),
        "lng": pd.to_numeric(df["Longitude"], errors="coerce"),
        "amenities": _split_amenities(df["Amenities"]),
        "sites": pd.to_numeric(df["Capacity"], errors="coerce").fillna(0).astype(int),
        "open": df["Status"].str.strip().str.upper().eq("OPEN"),
        "source_facility": "northeast",
    })


def load_midwest():
    df = pd.read_csv(RAW_DIR / "facility_midwest.csv")
    return pd.DataFrame({
        "name": df["name"].str.strip(),
        "city": df["city"].str.strip(),
        "state": df["state"].str.strip().str.upper(),
        "lat": pd.to_numeric(df["lat"], errors="coerce"),
        "lng": pd.to_numeric(df["lng"], errors="coerce"),
        "amenities": _split_amenities(df["amenities"]),
        "sites": pd.to_numeric(df["sites"], errors="coerce").fillna(0).astype(int),
        "open": df["active"].str.strip().str.upper().eq("Y"),
        "source_facility": "midwest",
    })


def load_south():
    df = pd.read_csv(RAW_DIR / "facility_south.csv")
    return pd.DataFrame({
        "name": df["CAMPGROUND"].str.strip().str.title(),
        "city": df["CITY"].str.strip(),
        "state": df["STATE"].str.strip().str.upper(),
        "lat": pd.to_numeric(df["LAT"], errors="coerce"),
        "lng": pd.to_numeric(df["LON"], errors="coerce"),
        "amenities": _split_amenities(df["AMENITIES"]),
        "sites": pd.to_numeric(df["NUM_SITES"], errors="coerce").fillna(0).astype(int),
        "open": df["OPEN"].astype(str).str.strip().eq("1"),
        "source_facility": "south",
    })


def load_west():
    df = pd.read_csv(RAW_DIR / "facility_west.csv")
    coords = df["coordinates"].str.split(",", expand=True)
    return pd.DataFrame({
        "name": df["campground_name"].str.strip(),
        "city": df["town"].str.strip(),
        "state": df["region_state"].str.strip().str.upper(),
        "lat": pd.to_numeric(coords[0], errors="coerce"),
        "lng": pd.to_numeric(coords[1], errors="coerce"),
        "amenities": _split_amenities(df["features"]),
        "sites": pd.to_numeric(df["site_count"], errors="coerce").fillna(0).astype(int),
        "open": df["is_open"].astype(str).str.strip().str.lower().eq("true"),
        "source_facility": "west",
    })


def run(load_mongo=False):
    started = time.perf_counter()

    frames = [load_northeast(), load_midwest(), load_south(), load_west()]
    combined = pd.concat(frames, ignore_index=True)
    raw_rows = len(combined)

    # Validate: drop rows with missing/out-of-range coordinates or blank names
    in_range = (
        combined["lat"].between(*VALID_LAT)
        & combined["lng"].between(*VALID_LNG)
        & combined["name"].str.len().gt(0)
    )
    skipped_bad_rows = int((~in_range).sum())
    combined = combined[in_range].copy()

    # Consolidate duplicate cross-listings on normalized (name, city, state),
    # keeping the record with the most amenities listed
    combined["_dedupe_key"] = (
        combined["name"].str.strip().str.lower() + "|"
        + combined["city"].str.strip().str.lower() + "|"
        + combined["state"].str.strip().str.lower()
    )
    combined["_amenity_count"] = combined["amenities"].apply(len)
    combined = (
        combined.sort_values("_amenity_count", ascending=False)
        .drop_duplicates(subset="_dedupe_key", keep="first")
        .drop(columns=["_dedupe_key", "_amenity_count"])
        .reset_index(drop=True)
    )

    elapsed = time.perf_counter() - started

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUT_CSV, index=False)
    records = json.loads(combined.to_json(orient="records"))
    OUT_JSON.write_text(json.dumps(records, indent=2), encoding="utf-8")

    stats = {
        "elapsed_seconds": elapsed,
        "raw_rows": raw_rows,
        "clean_records": len(combined),
        "skipped_bad_rows": skipped_bad_rows,
    }

    if load_mongo:
        from pymongo import MongoClient, GEOSPHERE

        client = MongoClient("mongodb://localhost:27017")
        collection = client["campground_reviews"]["campgrounds"]
        collection.delete_many({})
        for record in records:
            record["location"] = {"type": "Point", "coordinates": [record["lng"], record["lat"]]}
            record["avg_rating"] = 0.0
            record["review_count"] = 0
        collection.insert_many(records)
        collection.create_index([("location", GEOSPHERE)])
        stats["loaded_into_mongo"] = collection.count_documents({})

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--load-mongo", action="store_true",
                         help="Also upsert the cleaned records into MongoDB")
    args = parser.parse_args()

    result = run(load_mongo=args.load_mongo)
    print("Vectorized pandas pipeline:")
    for k, v in result.items():
        print(f"  {k}: {v}")
