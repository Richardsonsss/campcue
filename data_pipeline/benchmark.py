"""
Runs both the legacy manual-style merge and the vectorized pandas pipeline
against the same raw exports and reports the measured speedup, so the
"cut processing time by X%" claim is backed by a real number instead of an
assertion. Run generate_sample_data.py first if raw_data/ is empty.
"""
from pathlib import Path

import clean_and_load
import legacy_manual_merge

RAW_DIR = Path(__file__).parent / "raw_data"


def main():
    if not any(RAW_DIR.glob("*.csv")):
        raise SystemExit("No raw data found - run generate_sample_data.py first.")

    legacy = legacy_manual_merge.run()
    vectorized = clean_and_load.run(load_mongo=False)

    improvement = (1 - vectorized["elapsed_seconds"] / legacy["elapsed_seconds"]) * 100

    print(f"{'':22}{'legacy (manual-style)':>24}{'vectorized (pandas)':>22}")
    print(f"{'raw rows processed':22}{legacy['raw_rows']:>24}{vectorized['raw_rows']:>22}")
    print(f"{'clean records out':22}{legacy['clean_records']:>24}{vectorized['clean_records']:>22}")
    print(f"{'elapsed seconds':22}{legacy['elapsed_seconds']:>24.4f}{vectorized['elapsed_seconds']:>22.4f}")
    print()
    print(f"Processing time reduced by {improvement:.1f}% "
          f"on {legacy['raw_rows']} raw records across 4 facility files.")


if __name__ == "__main__":
    main()
