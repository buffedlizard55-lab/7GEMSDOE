"""Fail-closed GeoTIFF gate; [0,1] is exact, not a tolerance.

Template provenance is checked separately by verify_data.py. This local gate
cannot guarantee server acceptance or diagnose a past rejection without its file.
"""
from __future__ import annotations
import sys
import numpy as np
import rasterio


def validate(candidate: str, template: str) -> list[str]:
    errors = []
    try:
        with rasterio.open(template) as t, rasterio.open(candidate) as s:
            if t.count != 1 or t.crs is None:
                return ["invalid template: needs one band and a CRS"]
            footprint = np.isfinite(t.read(1)) & (t.read_masks(1) > 0)
            if not footprint.any():
                return ["invalid template: empty footprint"]
            if s.count != 1:
                errors.append(f"must be single band, got {s.count}")
            if s.dtypes[0] != "float32":
                errors.append(f"dtype must be float32, got {s.dtypes[0]}")
            if s.crs != t.crs:
                errors.append(f"CRS mismatch: {s.crs} vs {t.crs}")
            if s.transform != t.transform:
                errors.append("geotransform mismatch")
            if s.shape != t.shape:
                return errors + [f"shape mismatch: {s.shape} vs {t.shape}"]
            if s.nodata is None or not np.isnan(s.nodata):
                errors.append("nodata must be declared NaN (project publication policy)")
            arr = s.read(1)
            inside, outside = arr[footprint], arr[~footprint]
            if not np.isfinite(inside).all():
                errors.append("non-finite pixels INSIDE template footprint")
            if np.any((inside < 0) | (inside > 1)):
                errors.append("values outside [0,1]")
            if not np.isnan(outside).all():
                errors.append("pixels OUTSIDE template footprint must all be NaN")
            if np.any(s.read_masks(1)[footprint] == 0):
                errors.append("masked pixels INSIDE template footprint")
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        errors.append(f"cannot validate raster: {exc}")
    return errors


def main():
    if len(sys.argv) not in (2, 3):
        print("usage: validate_submission.py <candidate.tif> [template.tif]")
        return 2
    from paths import TEMPLATE_TIF
    errors = validate(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else str(TEMPLATE_TIF))
    print("FAIL\n - " + "\n - ".join(errors) if errors else
          "PASS: exact grid, float32 [0,1] inside; NaN outside; NaN nodata")
    return int(bool(errors))

if __name__ == "__main__":
    sys.exit(main())
