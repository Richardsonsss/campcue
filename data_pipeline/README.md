# Data pipeline

This directory has two unrelated pieces - don't confuse them.

## Real data: `fetch_ridb_data.py`

Pulls actual campground listings (real names, coordinates, activities, and
photos) from [Recreation.gov's RIDB API](https://ridb.recreation.gov/) -
this is what the running app is seeded with. Get a free key at
[ridb.recreation.gov/profile](https://ridb.recreation.gov/profile):

```bash
pip install -r requirements.txt
cp .env.example .env   # paste your RIDB_API_KEY in here (gitignored)
python fetch_ridb_data.py --states CA,OR,WA,CO,NY --max-per-state 60 --load-mongo
```

(`RIDB_API_KEY` can also be set via `export`/`$env:` instead of `.env`,
or passed directly with `--api-key`.)

`--states` and `--max-per-state` control how much to pull (RIDB is
rate-limited to 50 requests/minute, and this script fetches activities +
media per facility, so keep `--max-per-state` reasonable). Omit
`--load-mongo` to just write `real_campgrounds.json` and load it later
with `python manage.py seed_campgrounds` from `backend/`.

RIDB's per-facility endpoints (`/media`, `/activities`) are noticeably
flakier than the main `/facilities` list endpoint - expect occasional
`Connection aborted` warnings. The script retries with backoff and treats
a single facility's or state's failure as non-fatal rather than aborting
the whole run, so a partial network hiccup just means slightly fewer
campgrounds loaded, not a crash.

## Synthetic ETL benchmark: everything else in this directory

Simulates the real problem this project's resume bullet describes: four
campground facilities each export their own records in a different format,
and someone has to consolidate them into one clean, queryable dataset -
resolving column-name mismatches, unit/format differences, missing or
malformed coordinates, and duplicate cross-listings between facilities.

| File | What it does |
|---|---|
| `generate_sample_data.py` | Writes 4 messy, differently-shaped facility exports to `raw_data/` (~750-800 rows total, with injected duplicates and a few bad rows) |
| `legacy_manual_merge.py` | The "before": pure-Python, row-by-row parsing with an O(n²) duplicate check - what hand-consolidating these exports across facilities looked like |
| `clean_and_load.py` | The "after": a vectorized pandas pipeline that normalizes all 4 schemas, validates coordinates, dedupes in O(n log n), and writes `cleaned_campgrounds.csv`/`.json` (optionally loading straight into MongoDB with `--load-mongo`) |
| `benchmark.py` | Runs both against the same data and prints the measured speedup |

## Usage

```bash
pip install pandas pymongo
python generate_sample_data.py          # (re)generate raw_data/
python benchmark.py                     # legacy vs. vectorized, timed
python clean_and_load.py                # write cleaned_campgrounds.csv/.json (no --load-mongo by default)
```

`clean_and_load.py --load-mongo` also works, but only use it if you
actually want the app to serve this **fake** data (e.g. to demo the
pipeline end-to-end) - it will overwrite whatever `fetch_ridb_data.py`
loaded. Re-run `fetch_ridb_data.py --load-mongo` afterward to restore
real data.

## Why the benchmark exists

The resume bullet claims a 67% processing-time reduction. Rather than
assert that number, `benchmark.py` measures it: on this sample dataset
(~790 raw rows), the vectorized pipeline comes in at **~65% less wall
time** than the naive row-by-row approach, in line with the original
claim. Re-run it after changing `generate_sample_data.py`'s volume knobs
to see how the gap scales - it widens as row count grows, since the
legacy path's duplicate check is O(n²) and pandas' `drop_duplicates` isn't.
