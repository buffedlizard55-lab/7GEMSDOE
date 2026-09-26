"""Format gate for competition submissions.

Verifies a candidate GeoTIFF against the official sample submission template
(example_submission.tif), checking every requirement from the problem page
(submission format section):

  * single band, float32
  * same CRS (EPSG:32611), same shape, same geotransform
  * finite values strictly inside [0, 1] everywhere inside the footprint
  * NaN exactly outside the template footprint (and nowhere inside it)

Exit code 0 = PASS. This is the gate that prevents the platform error
"Predicted values must be in range [0, 1]" (which fires when NaN sits inside
the scored footprint or any value escapes [0, 1]).
"""

from __future__ import annotations

import sys

import numpy as np
import rasterio

TOL = 1e-6


def validate(candidate: str, template: str) -> list[str]:
    errors: list[str] = []
    with rasterio.open(template) as t:
        t_meta = {
            "crs": t.crs, "transform": t.transform,
            "height": t.height, "width": t.width,
        }
        t_arr = t.read(1)
        footprint = np.isfinite(t_arr)

    with rasterio.open(candidate) as s:
        if s.count != 1:
            errors.append(f"must be single band, got {s.count}")
        if s.dtypes[0] != "float32":
            errors.append(f"dtype must be float32, got {s.dtypes[0]}")
        if s.crs != t_meta["crs"]:
            errors.append(f"CRS mismatch: {s.crs} vs {t_meta['crs']}")
        if (s.height, s.width) != (t_meta["height"], t_meta["width"]):
            errors.append(
                f"shape mismatch: {(s.height, s.width)} vs "
                f"{(t_meta['height'], t_meta['width'])}")
        if s.transform != t_meta["transform"]:
            errors.append(f"geotransform mismatch: {s.transform} vs "
                          f"{t_meta['transform']}")
        arr = s.read(1)

        inside = arr[footprint]
        outside = arr[~footprint]
        n_bad_inside = int((~np.isfinite(inside)).sum())
        if n_bad_inside:
            errors.append(
                f"{n_bad_inside} non-finite pixels INSIDE the template "
                f"footprint (platform rejects: 'Predicted values must be in "
                f"range [0, 1]')")
        fin = inside[np.isfinite(inside)]
        if fin.size and (fin.min() < -TOL or fin.max() > 1 + TOL):
            errors.append(
                f"values outside [0,1]: min={fin.min()}, max={fin.max()}")
        n_bad_outside = int(np.isfinite(outside).sum())
        if n_bad_outside:
            errors.append(
                f"{n_bad_outside} finite pixels OUTSIDE the template "
                f"footprint (must be NaN)")
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: validate_submission.py <candidate.tif> [template.tif]")
        return 2
    from paths import TEMPLATE_TIF
    template = sys.argv[2] if len(sys.argv) > 2 else str(TEMPLATE_TIF)
    errors = validate(sys.argv[1], template)
    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("PASS: format matches the official template; values in [0, 1]; "
          "NaN exactly outside the footprint")
    return 0


if __name__ == "__main__":
    sys.exit(main())
