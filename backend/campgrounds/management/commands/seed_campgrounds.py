"""
Loads campground data into MongoDB and (re)builds the 2dsphere index the
/campgrounds/nearby/ endpoint depends on. Run after the data pipeline
instead of --load-mongo when you'd rather go through Django's own tooling:
`python manage.py seed_campgrounds`.

Prefers data_pipeline/real_campgrounds.json (real listings pulled from
Recreation.gov by fetch_ridb_data.py). Falls back to
data_pipeline/cleaned_campgrounds.json - the synthetic ETL-benchmark
dataset from clean_and_load.py - only if the real one hasn't been
generated yet, with a loud warning, since that data is fake.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from pymongo import GEOSPHERE

from campgrounds.db import campgrounds_collection

DATA_PIPELINE_DIR = Path(__file__).resolve().parents[4] / "data_pipeline"
REAL_JSON = DATA_PIPELINE_DIR / "real_campgrounds.json"
SYNTHETIC_JSON = DATA_PIPELINE_DIR / "cleaned_campgrounds.json"


class Command(BaseCommand):
    help = "Load campground data into MongoDB and create the geospatial index."

    def handle(self, *args, **options):
        if REAL_JSON.exists():
            source = REAL_JSON
        elif SYNTHETIC_JSON.exists():
            source = SYNTHETIC_JSON
            self.stdout.write(self.style.WARNING(
                f"{REAL_JSON.name} not found - loading {SYNTHETIC_JSON.name} instead, "
                "which is SYNTHETIC benchmark data (fake names/locations), not real "
                "campgrounds. Run data_pipeline/fetch_ridb_data.py to seed real data."
            ))
        else:
            raise CommandError(
                f"Neither {REAL_JSON} nor {SYNTHETIC_JSON} found. Run "
                "data_pipeline/fetch_ridb_data.py (real data) or "
                "data_pipeline/clean_and_load.py (synthetic demo data) first."
            )

        records = json.loads(source.read_text(encoding="utf-8"))
        for record in records:
            record["location"] = {"type": "Point", "coordinates": [record["lng"], record["lat"]]}
            record.setdefault("avg_rating", 0.0)
            record.setdefault("review_count", 0)

        collection = campgrounds_collection()
        collection.delete_many({})
        if records:
            collection.insert_many(records)
        collection.create_index([("location", GEOSPHERE)])

        self.stdout.write(self.style.SUCCESS(
            f"Loaded {collection.count_documents({})} campgrounds into MongoDB."
        ))
