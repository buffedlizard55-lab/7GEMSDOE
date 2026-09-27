"""The published-fault shortcut is closed, and the site still leads with the upload.

Two things must not silently regress after session 8:

1. **Label provenance.** Inside the competition footprint the shipped training
   raster exhausts the published INGENIOUS/QFFDB record (a handful of residual
   pixels, not tens of thousands). If a future change makes that residual large
   again, someone has moved the footprint or the comparison -- either way the
   "published faults we overlooked" claim would need re-opening, so it must fail
   loudly here.
2. **One-click generate/download + pre-upload check.** The acceptance criteria
   require the submission file to be reachable at the very top of the site with
   an explicit Note and a link to the step-by-step guide.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
HOWTO = ROOT / "how-to-submit.html"
PROVENANCE = ROOT / "knowledge" / "session8" / "label_provenance.json"
SOURCES = ROOT / "knowledge" / "sources.json"
MIN_PACKAGEABLE_PX = 20_000


def _data_dir() -> Path | None:
    for candidate in (Path.home() / "gems_data", ROOT / "data"):
        if (candidate / "existing_faults.tif").exists():
            return candidate
    return None


def test_audit_closes_the_published_fault_shortcut():
    """Re-measure, do not trust the stored JSON."""
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    if _data_dir() is None:
        pytest.skip("competition labels not placed")
    pytest.importorskip("rasterio")
    import label_provenance
    rep = label_provenance.audit()
    prog = rep["sources"]["ingenious_v2_not_in_labels"]
    assert prog["px_grid"] > MIN_PACKAGEABLE_PX, "the compilation should have a large grid-wide residual"
    assert prog["px_in_footprint_far_from_labels"] < MIN_PACKAGEABLE_PX, (
        "published fault traces that the shipped labels miss are back inside the footprint; "
        "re-open the H12 hypothesis before shipping any candidate built from them"
    )
    assert rep["packaged"] is False
    # the shipped labels must remain a subset of the compilation
    for key in ("ingenious_v1_trace", "ingenious_v2_trace"):
        assert rep["sources"][key]["labels_within_1px"] == 1.0
    assert rep["sources"]["qfaults_any_band"]["labels_within_1px"] > 0.99


def test_stored_provenance_artifact_matches_the_schema():
    rep = json.loads(PROVENANCE.read_text())
    assert rep["shipped_labels_px"] == 60988
    assert rep["sources"]["ingenious_v2_not_in_labels"]["px_in_footprint"] < 100
    assert rep["effect"].startswith("no 'published faults we overlooked'")


def test_index_leads_with_generate_download_and_check():
    html = INDEX.read_text()
    for needle in ('id="generate-tif"', 'id="generate-status"', 'id="generate-sha"',
                   'id="validate-file"', 'id="validate-report"',
                   'assets/submission_payload.js', 'assets/submit_ui.js',
                   'how-to-submit.html', 'downloads/gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.tif',
                   'Predicted values must be in range'):
        assert needle in html, f"index.html lost {needle}"
    # the generation hero must come before any other card so it is the first thing seen
    assert html.index('id="generate"') < html.index('id="check-file"')
    for needle in ('Submissions', 'Note', 'weekly', 'Dec 3, 2026'):
        assert needle in HOWTO.read_text(), f"how-to-submit.html lost {needle}"


def test_new_sources_are_official_and_licensed():
    sources = {s["id"]: s for s in json.loads(SOURCES.read_text())}
    for sid in ("gdr-383", "gdr-616", "gdr-1351", "gdr-1526", "gdr-1501", "osti-1148722", "drivendata-968"):
        s = sources[sid]
        assert s["url"].startswith("https://"), sid
        assert "openei.org" in s["url"] or "osti.gov" in s["url"] or "drivendata.org" in s["url"], sid
        assert s["claim"] and s["license"] and s["verification"], sid
        assert s["reviewed_utc"] >= "2026-09-27", sid
