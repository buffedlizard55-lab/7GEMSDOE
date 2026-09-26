"""Canonical data locations.

Large official rasters live OUTSIDE the git repo (they are re-downloadable,
see scripts/download_competition_data.sh). The repo commits only small,
auditable artifacts.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# External data dir (not committed). Override with GEMS_DATA_DIR.
DATA_DIR = Path(os.environ.get("GEMS_DATA_DIR", Path.home() / "gems_data"))

FEATURES_TIF = DATA_DIR / "training_features.tif"
LABELS_TIF = DATA_DIR / "existing_faults.tif"
TEMPLATE_TIF = DATA_DIR / "example_submission.tif"
CACHE_NPZ = DATA_DIR / "features_cache.npz"
NORM_JSON = DATA_DIR / "norm_stats.json"
ARTIFACT_DIR = DATA_DIR / "artifacts"

DOCS_DOWNLOADS = REPO_ROOT / "docs" / "downloads"


def ensure_data() -> None:
    missing = [p for p in (FEATURES_TIF, LABELS_TIF, TEMPLATE_TIF) if not p.exists()]
    if missing:
        raise SystemExit(
            "Missing official competition rasters:\n  "
            + "\n  ".join(str(p) for p in missing)
            + "\nRun scripts/download_competition_data.sh (see file header for "
            "sources and sha256 pins) and re-run."
        )
