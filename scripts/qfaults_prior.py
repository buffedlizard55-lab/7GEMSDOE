"""QFFDB mapping-scale / certainty prior (session 5, backlog #4, tests H2).

H2 (mapping-scale deficit): coarse (1:250k) or lower-certainty QFFDB traces are
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
       lower_certainty_trace= trace flagged inferred / moderately constrained / poor / unknown
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
import stat
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

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
SCALE_FIELDS = ("mapped_scale", "MAPPEDSCALE", "SCALE", "scale")
CERTAINTY_FIELDS = ("mapped_certainty", "MAPPEDCERTAINTY", "CERTAINTY",
                    "certainty", "locationcertainty")


def find_field(fields, candidates):
    """Resolve a known schema field case-insensitively, preserving its spelling."""
    lookup = {str(field).casefold(): str(field) for field in fields}
    for candidate in candidates:
        if candidate.casefold() in lookup:
            return lookup[candidate.casefold()]
    return None
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
    low_certainty = any(k in cert for k in (
        "infer", "moderate", "approximate", "unknown", "poor"))
    # 'well constrained' / 'wellconstrained' is explicitly not low certainty.
    if "well" in cert:
        low_certainty = False
    return {"coarse": coarse, "fine": not coarse,
            "low_certainty": low_certainty,
            "scale_denom": denom, "certainty_raw": cert or None}


def rasterize_prior(geometries: list,
                    shape: tuple[int, int],
                    transform: Affine,
                    crs: str = "EPSG:32611") -> np.ndarray:
    """Rasterize [(geometry, class_dict)] onto the grid -> (3, H, W) uint8.

    geometries: iterable of (geojson-geometry-dict, classify_trace() dict).
    Bands: 0 coarse_trace, 1 fine_trace, 2 lower_certainty_trace.
    """
    coarse = [(g, 1) for g, c in geometries if c["coarse"]]
    fine = [(g, 1) for g, c in geometries if c["fine"]]
    low_certainty = [(g, 1) for g, c in geometries if c["low_certainty"]]
    out = np.zeros((3,) + shape, dtype=np.uint8)
    for i, shapes in enumerate((coarse, fine, low_certainty)):
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


def parse_layer_crs(value):
    """Parse a Fiona CRS value without stringifying mapping-style CRS objects."""
    from rasterio.crs import CRS

    if value is None or value == "" or value == {}:
        raise ValueError("missing CRS")
    return CRS.from_user_input(value)


def safe_extract_zip(archive: zipfile.ZipFile, destination: Path) -> None:
    """Extract only regular files whose paths remain below destination.

    Source archives are remote inputs: reject traversal, absolute paths, and
    symbolic links rather than relying on archive-library normalization.
    """
    root = destination.resolve()
    members = archive.infolist()
    seen_targets = set()
    for member in members:
        posix = PurePosixPath(member.filename)
        windows = PureWindowsPath(member.filename)
        if (posix.is_absolute() or windows.is_absolute() or windows.drive
                or ".." in posix.parts or ".." in windows.parts):
            raise ValueError(f"unsafe archive path: {member.filename!r}")
        target = (root / Path(*posix.parts)).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"archive path escapes destination: {member.filename!r}")
        if target in seen_targets:
            raise ValueError(f"duplicate archive path: {member.filename!r}")
        seen_targets.add(target)
        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ValueError(f"symbolic link not allowed in archive: {member.filename!r}")
    archive.extractall(root, members=members)


def build_from_zip(zip_path: Path) -> dict:
    """Runner path: read shapefile with fiona, rasterize, write product."""
    import fiona  # runner-only dependency (see workflow)
    from fiona.transform import transform_geom
    from rasterio.crs import CRS

    shape, transform, crs = official_grid()
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(zip_path) as z:
            safe_extract_zip(z, Path(td))
        shp = next(iter(Path(td).rglob("*.shp")), None)
        if shp is None:
            raise SystemExit("no .shp found inside Qfaults zip")
        with fiona.open(shp) as col:
            observed_fields = list(col.schema["properties"].keys())
            crs_input = col.crs_wkt or col.crs
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            (OUT_DIR / "observed_schema.json").write_text(json.dumps({
                "status": "inspection_started",
                "archive_name": Path(zip_path).name,
                "layer": str(shp.name),
                "observed_fields": observed_fields,
                "source_crs": str(crs_input or ""),
            }, indent=1))
            src_crs = str(crs_input or "")
            try:
                source_crs = parse_layer_crs(crs_input)
            except Exception as exc:
                raise SystemExit(f"missing or unparseable Qfaults CRS {src_crs!r}: {exc}") from exc
            target_crs = CRS.from_epsg(32611)
            scale_field = find_field(col.schema["properties"], SCALE_FIELDS)
            cert_field = find_field(col.schema["properties"], CERTAINTY_FIELDS)
            schema_report = {
                "status": "schema_observed",
                "archive_name": Path(zip_path).name,
                "layer": str(shp.name),
                "observed_fields": observed_fields,
                "source_crs": src_crs,
                "scale_field": scale_field,
                "certainty_field": cert_field,
            }
            (OUT_DIR / "observed_schema.json").write_text(
                json.dumps(schema_report, indent=1))
            if scale_field is None and cert_field is None:
                raise SystemExit(
                    "Qfaults schema lacks every known scale/certainty field; "
                    f"observed: {observed_fields}. Failing closed (see manifest).")
            feats = []
            attribute_counts = Counter()
            for f in col:
                props = dict(f["properties"])
                for field in (scale_field, cert_field):
                    if field is not None:
                        value = props.get(field)
                        if value is not None and str(value).strip():
                            attribute_counts[f"{field}={str(value).strip()}"] += 1
                geom = f["geometry"]
                if not geom:
                    continue
                if source_crs != target_crs:
                    geom = transform_geom(crs_input, target_crs.to_string(), geom)
                feats.append((geom, classify_trace(props, scale_field, cert_field)))
            schema_report["attribute_value_counts"] = dict(
                sorted(attribute_counts.items()))
            (OUT_DIR / "observed_schema.json").write_text(
                json.dumps(schema_report, indent=1))
    arr = rasterize_prior(feats, shape, transform, crs)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_tif = OUT_DIR / "qfaults_prior_u8.tif"
    with rasterio.open(out_tif, "w", driver="GTiff", height=shape[0],
                       width=shape[1], count=3, dtype="uint8", crs=crs,
                       transform=transform, compress="lzw",
                       nodata=0) as dst:
        dst.descriptions = ("coarse_trace", "fine_trace", "lower_certainty_trace")
        dst.write(arr)
    return {
        "observed_fields": observed_fields,
        "scale_field": scale_field,
        "certainty_field": cert_field,
        "src_crs": src_crs,
        "n_features": len(feats),
        "coarse_px": int(arr[0].sum()),
        "fine_px": int(arr[1].sum()),
        "lower_certainty_px": int(arr[2].sum()),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", type=Path, default=None,
                    help="local Qfaults zip (default: download official URL)")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.zip is None:
        print(f"downloading {QFAULTS_URL}", flush=True)
        with tempfile.TemporaryDirectory(prefix="qfaults-source-") as td:
            zip_path = Path(td) / "Qfaults_GIS.zip"
            sha = download_zip(QFAULTS_URL, zip_path)
            stats = build_from_zip(zip_path)
        source = QFAULTS_URL
    else:
        zip_path = args.zip
        h = hashlib.sha256()
        h.update(zip_path.read_bytes())
        sha = h.hexdigest()
        source = f"local file {args.zip}"
        stats = build_from_zip(zip_path)
    out_tif = OUT_DIR / "qfaults_prior_u8.tif"
    with rasterio.open(out_tif) as product:
        grid = {
            "width": product.width,
            "height": product.height,
            "crs": str(product.crs),
            "transform": list(product.transform)[:6],
            "dtype": product.dtypes[0],
        }
    product_hash = hashlib.sha256(out_tif.read_bytes()).hexdigest()
    manifest = {
        "product": "external/qfaults/qfaults_prior_u8.tif",
        "bands": ["coarse_trace", "fine_trace", "lower_certainty_trace"],
        "source": source,
        "zip_sha256": sha,
        "product_sha256": product_hash,
        "grid": grid,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "rights": "USGS-authored source data; verify source attribution and terms before reuse.",
        "coarse_definition": f"mapped scale denominator >= {COARSE_DENOM} "
                             "(or scale unknown / mixed-scale)",
        "limitations": [
            "QFFDB is an existing fault catalogue, not an independent discovery signal; direct model use risks catalogue/label leakage.",
            "lower_certainty_trace means source certainty contains inferred, moderate, approximate, poor or unknown; it is not a verified probability.",
            "Use for catalogue-gap/sensitivity analysis only unless spatial overlap and source-independence controls are passed.",
        ],
        **stats,
    }
    (OUT_DIR / "qfaults_prior.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
