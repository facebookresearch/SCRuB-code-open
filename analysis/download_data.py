#!/usr/bin/env python3
"""Verify that the required data file is in place.

The SCRuBEval annotation dataset is available at:

    https://anonymous-hf.up.railway.app/a/9yop355zrs2p/

Download task2_human_judgments.csv from that page and place it in the
data/ directory at the root of this repository, then run the analysis
scripts.

Usage:
    python analysis/download_data.py
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR  = REPO_ROOT / "data"
TARGET    = DATA_DIR / "task2_human_judgments.csv"

DATA_URL = "https://anonymous-hf.up.railway.app/a/9yop355zrs2p/"


def main() -> None:
    if TARGET.exists():
        print(f"OK: {TARGET} found ({TARGET.stat().st_size:,} bytes).")
        print("You can now run the analysis scripts:")
        print("  python analysis/compute_irr.py")
        print("  python analysis/plot_rank_score_scatter.py")
        print("  python analysis/plot_dimension_scorecard.py")
    else:
        print(f"Data file not found: {TARGET}")
        print()
        print("Please download task2_human_judgments.csv from:")
        print(f"  {DATA_URL}")
        print()
        print(f"Then place it at: {TARGET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
