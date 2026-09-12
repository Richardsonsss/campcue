"""
Generates messy, multi-facility campground export files that mimic what four
regional campground operators would actually hand you: different column
names, different units/formats for the same field, duplicate listings where
two regions both logged the same campground, and a few malformed rows.

Run once to (re)populate data_pipeline/raw_data/ before running clean_and_load.py.
"""
import csv
import random
from pathlib import Path

random.seed(42)

RAW_DIR = Path(__file__).parent / "raw_data"

STATES = ["NY", "VT", "PA", "OH", "MI", "IN", "IL", "WI", "GA", "NC", "TN", "OR", "WA", "CA", "CO"]
CITIES = {
    "NY": ["Lake Placid", "Ithaca", "Watkins Glen"], "VT": ["Stowe", "Killington"],
    "PA": ["Hershey", "Gettysburg"], "OH": ["Hocking Hills", "Mansfield"],
    "MI": ["Traverse City", "Mackinaw City"], "IN": ["Nashville", "Bloomington"],
    "IL": ["Starved Rock", "Galena"], "WI": ["Door County", "Wisconsin Dells"],
    "GA": ["Blue Ridge", "Helen"], "NC": ["Asheville", "Boone"],
    "TN": ["Gatlinburg", "Pigeon Forge"], "OR": ["Bend", "Ashland"],
    "WA": ["Leavenworth", "Mount Rainier"], "CA": ["Big Sur", "Yosemite Valley"],
    "CO": ["Estes Park", "Durango"],
}
AMENITY_POOL = ["wifi", "showers", "electric hookup", "pet friendly", "boat launch",
                "fire pits", "dump station", "laundry", "playground", "general store"]

NAME_PREFIXES = ["Pine", "Cedar", "Whispering", "Blue Heron", "Bear Creek", "Sunset",
                  "Silver Lake", "Maple", "Eagle", "Willow", "Timber", "Rocky Ridge",
                  "River Bend", "Hidden Valley", "Meadow", "Deer Run"]
NAME_SUFFIXES = ["Campground", "RV Resort", "Family Campground", "State Park Campground",
                  "Woods", "Lakeside Camp", "Getaway", "Retreat"]

# Approximate (lat_min, lat_max, lng_min, lng_max) bounding boxes so generated
# coordinates actually land within the state a record claims to be in -
# matters for the Google Maps view rendering sane pins.
STATE_BOUNDS = {
    "NY": (40.5, 45.0, -79.8, -71.9), "VT": (42.7, 45.0, -73.4, -71.5),
    "PA": (39.7, 42.3, -80.5, -74.7), "OH": (38.4, 42.0, -84.8, -80.5),
    "MI": (41.7, 47.5, -90.4, -82.4), "IN": (37.8, 41.8, -88.1, -84.8),
    "IL": (37.0, 42.5, -91.5, -87.5), "WI": (42.5, 47.1, -92.9, -86.8),
    "GA": (30.4, 35.0, -85.6, -80.8), "NC": (33.8, 36.6, -84.3, -75.5),
    "TN": (35.0, 36.7, -90.3, -81.6), "OR": (42.0, 46.3, -124.6, -116.5),
    "WA": (45.5, 49.0, -124.8, -117.0), "CA": (32.5, 42.0, -124.4, -114.1),
    "CO": (37.0, 41.0, -109.1, -102.0),
}


def random_campground_name(used):
    for _ in range(200):
        name = f"{random.choice(NAME_PREFIXES)} {random.choice(NAME_SUFFIXES)}"
        if name not in used:
            used.add(name)
            return name
    # Combination space (16 x 8 = 128) exhausted - fall back to a numbered variant
    n = 2
    while True:
        name = f"{random.choice(NAME_PREFIXES)} {random.choice(NAME_SUFFIXES)} {n}"
        if name not in used:
            used.add(name)
            return name
        n += 1


def random_coords(state):
    lat_min, lat_max, lng_min, lng_max = STATE_BOUNDS[state]
    lat = round(random.uniform(lat_min, lat_max), 4)
    lng = round(random.uniform(lng_min, lng_max), 4)
    return lat, lng


def make_pool(n, used_names):
    rows = []
    for _ in range(n):
        state = random.choice(STATES)
        city = random.choice(CITIES[state])
        lat, lng = random_coords(state)
        amenities = random.sample(AMENITY_POOL, k=random.randint(2, 5))
        rows.append({
            "name": random_campground_name(used_names),
            "city": city,
            "state": state,
            "lat": lat,
            "lng": lng,
            "amenities": amenities,
            "sites": random.randint(15, 220),
            "open": random.random() > 0.08,
        })
    return rows


def write_facility_northeast(rows):
    path = RAW_DIR / "facility_northeast.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Campground Name", "Site City", "Site State", "Latitude", "Longitude",
                    "Amenities", "Capacity", "Status"])
        for r in rows:
            w.writerow([r["name"], r["city"], r["state"], r["lat"], r["lng"],
                        "; ".join(r["amenities"]), r["sites"],
                        "OPEN" if r["open"] else "CLOSED"])


def write_facility_midwest(rows):
    path = RAW_DIR / "facility_midwest.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "city", "state", "lat", "lng", "amenities", "sites", "active"])
        for r in rows:
            # a couple of missing amenity fields to simulate real gaps
            amenities = "; ".join(r["amenities"]) if random.random() > 0.05 else ""
            w.writerow([r["name"], r["city"], r["state"].lower(), r["lat"], r["lng"],
                        amenities, r["sites"], "Y" if r["open"] else "N"])


def write_facility_south(rows):
    path = RAW_DIR / "facility_south.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["CAMPGROUND", "CITY", "STATE", "LAT", "LON", "AMENITIES", "NUM_SITES", "OPEN"])
        for r in rows:
            lat = r["lat"]
            if random.random() < 0.04:
                lat = ""  # simulate a bad export row
            w.writerow([r["name"].upper(), r["city"], r["state"], lat, r["lng"],
                        "; ".join(r["amenities"]), r["sites"], "1" if r["open"] else "0"])


def write_facility_west(rows):
    path = RAW_DIR / "facility_west.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["campground_name", "town", "region_state", "coordinates", "features",
                     "site_count", "is_open"])
        for r in rows:
            coords = f"{r['lat']},{r['lng']}"
            w.writerow([r["name"], r["city"], r["state"], coords,
                        "; ".join(r["amenities"]), r["sites"],
                        "true" if r["open"] else "false"])


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    used_names = set()

    northeast = make_pool(200, used_names)
    midwest = make_pool(200, used_names)
    south = make_pool(200, used_names)
    west = make_pool(150, used_names)

    # Inject duplicate cross-listings so the cleaner has real dedup work to do
    duplicates = random.sample(northeast, 25) + random.sample(midwest, 15)
    west.extend(duplicates)

    write_facility_northeast(northeast)
    write_facility_midwest(midwest)
    write_facility_south(south)
    write_facility_west(west)

    total = len(northeast) + len(midwest) + len(south) + len(west)
    print(f"Wrote 4 facility export files to {RAW_DIR} ({total} raw rows, "
          f"{len(used_names)} unique campgrounds before cleaning).")


if __name__ == "__main__":
    main()
