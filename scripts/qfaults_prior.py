"""QFFDB mapping-scale / certainty prior (session 5, backlog #4, tests H2).

H2 (mapping-scale deficit): coarse (1:250k) or inferred QFFDB traces are
where expert re-mapping yields the most new pixels, because corrected
geometry sits 1-3 px off the old trace.

What this script does (runs on GitHub Actions; the sandbox cannot reach
USGS hosts):
  1. downloads the official Qfaults GIS zip
     https://earthquake.usgs.gov/static/lfs/nshm/qfaults/Qfaults_GIS.zip
  2. reads fault-trace features (fiona; runner-only import),
  3. maps each trace to (scale_class, certainty_class) from its attributes,
     FAILING CLOSED with the observed field list if the expected fields
     are absent (field names are NOT assumed: the session-4 citation rests
     on a feature-service schema + Alaska DGGS metadata, not on this zip),
  4. rasterizes three binary bands on the official competition grid
     (EPSG:32611, 100 m, 3292x3730):
       coarse_trace  = trace mapped at >= 1:250,000 (or unknown scale)
       fine_trace    = trace mapped at < 1:250,000
       inferred_trace= trace flagged inferred / moderately constrained
  5. writes external/qfaults/qfaults_prior_u8.tif (uint8, 3 bands) +
     external/qfaults/qfaults_prior.json manifest with source URL, zip
     sha256, feature count and the observed field list.

Hermetic core (tested in tests/test_qfaults.py): classify_trace() and
rasterize_prior() take plain GeoJSON-like dicts + an affine grid, so no
network, fiona or shapely is needed to test the mapping logic.

License: USGS-authored data are public domain (17 U.S.C. 105); the manifest
records the source URL + retrieval UTC for attribution review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from paths import TEMPLATE_TIF  # noqa: E402

QFAULTS_URL = ("https://earthquake.usgs.gov/static/lfs/nshm/qfaults/"
               "Qfaults_GIS.zip")
OUT_DIR = ROOT / "external" / "qfaults"

# Candidate field names for mapped scale / certainty. The zip schema is
# verified on the runner (observed fields go in the manifest); nothing here
# asserts these names exist until observed.
SCALE_FIELDS = ("MAPPEDSCALE", "MAPPED_SCALE", "mappedscale", "mapped_scale",
                "SCALE", "Scale")
CERTAINTY_FIELDS = ("MAPPEDCERTAINTY", "MAPPED_CERTAINTY", "mappedcertainty",
                    "mapped_certainty", "CERTAINTY", "Certainty",
                    "LOCATIONCERTAINTY", "locationcertainty")
# Scale denominators at or above this are "coarse" (>= 1:250k).
COARSE_DENOM = 250_000


def parse_scale_denominator(value) -> int | None:
    """Parse '1:250,000' / 250000 / '250k' style entries to an int."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and np.isfinite(value):
        return int(value)
    s = str(value).strip().lower().replace(",", "")
    if ":" in s:
        s = s.split(":")[-1]
    s = s.replace(" ", "")
    try:
        if s.endswith("k"):
            return int(float(s[:-1]) * 1000)
        return int(float(s))
    except ValueError:
        return None


def classify_trace(props: dict, scale_field: str | None,
                   certainty_field: str | None) -> dict:
    """Map one trace's attributes to prior classes (pure function)."""
    denom = parse_scale_denominator(props.get(scale_field)) if scale_field else None
    cert = str(props.get(certainty_field, "") or "").strip().lower() if certainty_field else ""
    coarse = denom is None or denom >= COARSE_DENOM
    inferred = any(k in cert for k in ("infer", "moderate", "approximate", "unknown", "poor"))
    # 'well constrained' / 'wellconstrained' is explicitly NOT inferred.
    if "well" in cert:
        inferred = False
    return {"coarse": coarse, "fine": not coarse, "inferred": inferred,
            "scale_denom": denom, "certainty_raw": cert or None}


def rasterize_prior(geometries: list,
                    shape: tuple[int, int],
                    transform: Affine,
                    crs: str = "EPSG:32611") -> np.ndarray:
    """Rasterize [(geometry, class_dict)] onto the grid -> (3, H, W) uint8.

    geometries: iterable of (geojson-geometry-dict, classify_trace() dict).
    Bands: 0 coarse_trace, 1 fine_trace, 2 inferred_trace.
    """
    coarse = [(g, 1) for g, c in geometries if c["coarse"]]
    fine = [(g, 1) for g, c in geometries if c["fine"]]
    inferred = [(g, 1) for g, c in geometries if c["inferred"]]
    out = np.zeros((3,) + shape, dtype=np.uint8)
    for i, shapes in enumerate((coarse, fine, inferred)):
        if shapes:
            out[i] = rasterize(shapes, out_shape=shape, transform=transform,
                               fill=0, default_value=1, dtype="uint8")
    return out


def official_grid():
    with rasterio.open(TEMPLATE_TIF) as src:
        return src.shape, src.transform, str(src.crs)


def download_zip(url: str, dest: Path) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "7GEMSDOE-qfaults/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        h = hashlib.sha256()
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
            f.write(chunk)
    return h.hexdigest()


def build_from_zip(zip_path: Path) -> dict:
    """Runner path: read shapefile with fiona, rasterize, write product."""
    import fiona  # runner-only dependency (see workflow)
    from fiona.transform import transform_geom

    shape, transform, crs = official_grid()
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(td)
        shp = next(iter(Path(td).rglob("*.shp")), None)
        if shp is None:
            raise SystemExit("no .shp found inside Qfaults zip")
        with fiona.open(shp) as col:
            observed_fields = list(col.schema["properties"].keys())
            src_crs = str(col.crs or "")
            scale_field = next((f for f in SCALE_FIELDS if f in col.schema["properties"]), None)
            cert_field = next((f for f in CERTAINTY_FIELDS if f in col.schema["properties"]), None)
            if scale_field is None and cert_field is None:
                raise SystemExit(
                    "Qfaults schema lacks every known scale/certainty field; "
                    f"observed: {observed_fields}. Failing closed (see manifest).")
            feats = []
            for f in col:
                geom = f["geometry"]
                if not geom:
                    continue
                if src_crs and "32611" not in src_crs:
                    geom = transform_geom(col.crs, "EPSG:32611", geom)
                feats.append((geom, classify_trace(
                    dict(f["properties"]), scale_field, cert_field)))
    arr = rasterize_prior(feats, shape, transform, crs)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_tif = OUT_DIR / "qfaults_prior_u8.tif"
    with rasterio.open(out_tif, "w", driver="GTiff", height=shape[0],
                       width=shape[1], count=3, dtype="uint8", crs=crs,
                       transform=transform, compress="lzw",
                       nodata=0) as dst:
        dst.descriptions = ("coarse_trace", "fine_trace", "inferred_trace")
        dst.write(arr)
    return {
        "observed_fields": observed_fields,
        "scale_field": scale_field,
        "certainty_field": cert_field,
        "src_crs": src_crs,
        "n_features": len(feats),
        "coarse_px": int(arr[0].sum()),
        "fine_px": int(arr[1].sum()),
        "inferred_px": int(arr[2].sum()),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", type=Path, default=None,
                    help="local Qfaults zip (default: download official URL)")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.zip is None:
        zip_path = OUT_DIR / "Qfaults_GIS.zip"
        print(f"downloading {QFAULTS_URL}", flush=True)
        sha = download_zip(QFAULTS_URL, zip_path)
        source = QFAULTS_URL
    else:
        zip_path = args.zip
        h = hashlib.sha256()
        h.update(zip_path.read_bytes())
        sha = h.hexdigest()
        source = f"local file {args.zip}"
    stats = build_from_zip(zip_path)
    manifest = {
        "product": "external/qfaults/qfaults_prior_u8.tif",
        "bands": ["coarse_trace", "fine_trace", "inferred_trace"],
        "source": source,
        "zip_sha256": sha,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "rights": "USGS-authored data are public domain (17 U.S.C. 105); "
                  "verify + retain attribution before reuse.",
        "coarse_definition": f"mapped scale denominator >= {COARSE_DENOM} "
                             "(or scale unknown)",
        **stats,
    }
    (OUT_DIR / "qfaults_prior.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
