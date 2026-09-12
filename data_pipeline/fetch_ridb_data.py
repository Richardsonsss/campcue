"""
Pulls real campground data from Recreation.gov's Recreation Information
Database (RIDB) API - the authoritative source for U.S. federal recreation
areas (national parks, forests, BLM land, Army Corps sites, etc.) - and
writes it to real_campgrounds.json in the same shape clean_and_load.py
produces, so seed_campgrounds.py can load either one.

This is the app's actual data source. It's separate from
generate_sample_data.py / clean_and_load.py / legacy_manual_merge.py,
which are a deliberately synthetic benchmark demonstrating the pandas ETL
pipeline (see README.md) - not a source of real campground listings.

Get a free API key at https://ridb.recreation.gov/profile, then:
    export RIDB_API_KEY=your-key-here      (or set it in .env / pass --api-key)
    python fetch_ridb_data.py --states CA,OR,WA,CO,NY --max-per-state 60

Rate limit: 50 requests/minute (enforced client-side below).
"""
import argparse
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

API_BASE = "https://ridb.recreation.gov/api/v1"
OUT_JSON = Path(__file__).parent / "real_campgrounds.json"

MIN_REQUEST_INTERVAL = 60 / 45  # stay under 50 req/min with margin


class RateLimiter:
    def __init__(self, min_interval):
        self.min_interval = min_interval
        self._last_call = 0.0

    def wait(self):
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.monotonic()


def _get(session, limiter, path, params=None, retries=4):
    last_error = None
    for attempt in range(retries):
        limiter.wait()
        try:
            resp = session.get(f"{API_BASE}{path}", params=params or {}, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s, 8s backoff
    raise last_error


def fetch_facilities_for_state(session, limiter, state, max_records):
    """Paginate /facilities for one state, filtered to campgrounds."""
    facilities = []
    offset = 0
    page_size = 50
    while len(facilities) < max_records:
        data = _get(session, limiter, "/facilities", {
            "state": state,
            "activity": "CAMPING",
            "limit": page_size,
            "offset": offset,
            "full": "true",
        })
        page = data.get("RECDATA", [])
        if not page:
            break
        for facility in page:
            facility_type = (facility.get("FacilityTypeDescription") or "").lower()
            if "campground" in facility_type or "camping" in facility_type:
                facilities.append(facility)
        offset += page_size
        total = data.get("METADATA", {}).get("RESULTS", {}).get("TOTAL_COUNT", 0)
        if offset >= total:
            break
    return facilities[:max_records]


def fetch_media(session, limiter, facility_id, embedded_media):
    """Prefer media embedded via full=true; fall back to a dedicated call.
    A single facility's media lookup failing (RIDB's per-facility endpoints
    are flakier than /facilities) shouldn't abort the whole run - log it and
    move on with no photos for that one."""
    if embedded_media:
        urls = [m["URL"] for m in embedded_media if m.get("MediaType") == "Image" and m.get("URL")]
        if urls:
            return urls[:6]
    try:
        data = _get(session, limiter, f"/facilities/{facility_id}/media")
    except requests.exceptions.RequestException as exc:
        print(f"  warning: media lookup failed for facility {facility_id}: {exc}")
        return []
    return [
        m["URL"] for m in data.get("RECDATA", [])
        if m.get("MediaType") == "Image" and m.get("URL")
    ][:6]


def fetch_activities(session, limiter, facility_id, embedded_activities):
    # RIDB returns activity names upper-cased (e.g. "CAMPING"); lowercase
    # them to match the rest of the app's amenity convention (and so the
    # $all filter, which lowercases its query params, actually matches).
    if embedded_activities:
        return sorted({
            a["ActivityName"].lower() for a in embedded_activities if a.get("ActivityName")
        })
    try:
        data = _get(session, limiter, f"/facilities/{facility_id}/activities")
    except requests.exceptions.RequestException as exc:
        print(f"  warning: activities lookup failed for facility {facility_id}: {exc}")
        return []
    return sorted({
        a["ActivityName"].lower() for a in data.get("RECDATA", []) if a.get("ActivityName")
    })


def to_title_case(text):
    """RIDB mixes ALL CAPS and properly-cased names/cities across records -
    normalize everyone to "First Letter Of Each Word Capitalized"."""
    return (text or "").strip().title()


def extract_city_state(facility, fallback_state):
    addresses = facility.get("FACILITYADDRESS") or []
    for addr in addresses:
        city = (addr.get("City") or "").strip()
        state = (addr.get("AddressStateCode") or fallback_state).strip().upper()
        if city:
            return city, state
    return "", fallback_state


def facility_to_record(session, limiter, facility, fallback_state):
    lat = facility.get("FacilityLatitude")
    lng = facility.get("FacilityLongitude")
    if not lat or not lng:
        return None

    city, state = extract_city_state(facility, fallback_state)
    facility_id = facility.get("FacilityID")

    return {
        "name": to_title_case(facility.get("FacilityName")),
        "city": to_title_case(city),
        "state": state,
        "lat": float(lat),
        "lng": float(lng),
        "amenities": fetch_activities(session, limiter, facility_id, facility.get("ACTIVITY")),
        "photos": fetch_media(session, limiter, facility_id, facility.get("MEDIA")),
        "sites": len(facility.get("CAMPSITE") or []),
        "open": bool(facility.get("Enabled", True)),
        "source_facility": "recreation.gov",
        "external_id": facility_id,
        "description": (facility.get("FacilityDescription") or "")[:1000],
        "reservation_url": facility.get("FacilityReservationURL", ""),
    }


def load_into_mongo(records):
    from pymongo import GEOSPHERE, MongoClient

    client = MongoClient("mongodb://localhost:27017")
    collection = client["campground_reviews"]["campgrounds"]
    collection.delete_many({})
    for record in records:
        record["location"] = {"type": "Point", "coordinates": [record["lng"], record["lat"]]}
        record["avg_rating"] = 0.0
        record["review_count"] = 0
    if records:
        collection.insert_many(records)
    collection.create_index([("location", GEOSPHERE)])
    print(f"Loaded {collection.count_documents({})} real campgrounds into MongoDB.")


def run(api_key, states, max_per_state):
    session = requests.Session()
    # Requests get spaced out by the rate limiter, which lets keep-alive
    # connections go stale and get reset by RIDB's load balancer - close
    # each connection instead of reusing it.
    session.headers.update({"apikey": api_key, "Accept": "application/json", "Connection": "close"})
    limiter = RateLimiter(MIN_REQUEST_INTERVAL)

    records = []
    seen_ids = set()

    for state in states:
        print(f"Fetching campgrounds in {state}...")
        try:
            facilities = fetch_facilities_for_state(session, limiter, state, max_per_state)
        except requests.exceptions.RequestException as exc:
            print(f"  warning: skipping {state}, facility list request failed: {exc}")
            continue
        for facility in facilities:
            facility_id = facility.get("FacilityID")
            if facility_id in seen_ids:
                continue
            seen_ids.add(facility_id)
            record = facility_to_record(session, limiter, facility, state)
            if record and record["name"]:
                records.append(record)
        print(f"  {state}: {len(facilities)} campground facilities")

    OUT_JSON.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"\nWrote {len(records)} real campgrounds to {OUT_JSON}")
    with_photos = sum(1 for r in records if r["photos"])
    print(f"{with_photos}/{len(records)} have at least one real photo")
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--states", default="CA,OR,WA,CO,NY,VT,NC,TN,GA,MI",
        help="Comma-separated 2-letter state codes",
    )
    parser.add_argument("--max-per-state", type=int, default=60)
    parser.add_argument("--api-key", default=os.environ.get("RIDB_API_KEY", ""))
    parser.add_argument("--load-mongo", action="store_true",
                         help="Also load the fetched records straight into MongoDB")
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit(
            "No RIDB API key. Get a free one at https://ridb.recreation.gov/profile "
            "and set RIDB_API_KEY or pass --api-key."
        )

    fetched = run(args.api_key, [s.strip().upper() for s in args.states.split(",")], args.max_per_state)
    if args.load_mongo:
        load_into_mongo(fetched)
