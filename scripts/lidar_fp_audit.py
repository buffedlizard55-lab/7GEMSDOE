"""False-positive control audit of the session-4 lidar candidate (backlog #3).

Session 4 noted visible false-positive classes in the lidar-only ridge
emission: closed loops (hills, shorelines), arcuate range-front edges and
channel banks. This script QUANTIFIES them from the committed lidar
descriptors + candidate, without touching leaderboard feedback:

* loop pixels: holes enclosed by the binary emission
  (binary_fill_holes(emission) - emission),
* channel-bank-like emission: emitted pixels with high cross-slope gradient
  (cross_max) relative to the emission background,
* facing coherence: upface/downface/cross_max and coh100 distributions for
  emitted vs background ridge pixels,
* relief stratification (H5 piedmont-bias input): emission share by relief
  class vs footprint share.

It then PRE-REGISTERS a v2 filter policy (rule form + numeric thresholds
fixed from background descriptor quantiles only -- no catalogue-label
tuning, no leaderboard tuning) and reports the would-be emission counts.
The v2 file itself is NOT packaged until the v1 upload scores: v2 exists as
code + frozen policy so the H1 test stays decisive.

Output: knowledge/session5/lidar_fp_audit.json (small, committed).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_fill_holes

ROOT = Path(__file__).resolve().parents[1]
LIDAR = ROOT / "external" / "dem" / "lidar_scarp_features_u8.tif"
LIDAR_META = ROOT / "external" / "dem" / "lidar_scarp_features.json"
CANDIDATE = ROOT / "downloads" / "gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.tif"

import sys
sys.path.insert(0, str(ROOT / "scripts"))
from paths import TEMPLATE_TIF, ensure_data  # noqa: E402

# Pre-registered v2 filter (rule form frozen here; numeric cutoffs are fixed
# from background quantiles computed below, never from leaderboard scores):
#   drop an emitted pixel if it is channel-bank-like
#     (cross_max_q > CROSS_Q and coh100_q < COH_Q)
#   or if it sits in extreme relief with low coherence
#     (relief_q > RELIEF_Q and coh100_q < COH_Q)
# Quantile rule (frozen): CROSS_Q = 90th pct of cross_max over background
# ridge pixels; COH_Q = 25th pct of coh100 over background ridge pixels;
# RELIEF_Q = 97.5th pct of relief over background ridge pixels.
CROSS_PCT, COH_PCT, RELIEF_PCT = 90.0, 25.0, 97.5


def dequant_note() -> dict:
    return json.loads(LIDAR_META.read_text())["quantisation"]


def main() -> None:
    ensure_data()
    with rasterio.open(TEMPLATE_TIF) as src:
        footprint = np.isfinite(src.read(1))
    with rasterio.open(CANDIDATE) as src:
        cand = src.read(1)
    emitted = np.isfinite(cand) & (cand > 0) & footprint

    with rasterio.open(LIDAR) as src:
        meta = json.loads(LIDAR_META.read_text())
        bands = meta["bands"]
        idx = {name: i + 1 for i, name in enumerate(bands)}
        cross = src.read(idx["cross_max"]).astype(np.float32)
        coh = src.read(idx["coh100"]).astype(np.float32)
        relief = src.read(idx["relief"]).astype(np.float32)
        upface = src.read(idx["upface_max"]).astype(np.float32)
        downface = src.read(idx["downface_max"]).astype(np.float32)
        valid = src.read(idx["valid"]) > 0

    # Background = lidar-covered footprint pixels that are NOT emitted.
    bg = footprint & valid & ~emitted

    def pct(x: np.ndarray, mask: np.ndarray, qs=(10, 25, 50, 75, 90, 97.5)):
        v = x[mask]
        return {str(q): round(float(np.percentile(v, q)), 2) for q in qs}

    audit = {
        "emitted_px": int(emitted.sum()),
        "background_px": int(bg.sum()),
        "cross_max_emitted_pct": pct(cross, emitted),
        "cross_max_background_pct": pct(cross, bg),
        "coh100_emitted_pct": pct(coh, emitted),
        "coh100_background_pct": pct(coh, bg),
        "relief_emitted_pct": pct(relief, emitted),
        "relief_background_pct": pct(relief, bg),
        "upface_emitted_pct": pct(upface, emitted),
        "downface_emitted_pct": pct(downface, emitted),
    }

    # Closed loops: holes fully enclosed by emission.
    holes = binary_fill_holes(emitted) & ~emitted & footprint
    audit["loop_hole_px"] = int(holes.sum())
    audit["loop_hole_fraction_of_emitted"] = round(
        float(holes.sum()) / float(emitted.sum()), 4)

    # Facing dominance among emitted pixels (q units).
    dom_cross = emitted & (cross >= upface) & (cross >= downface)
    audit["emitted_cross_dominant_px"] = int(dom_cross.sum())
    audit["emitted_cross_dominant_fraction"] = round(
        float(dom_cross.sum()) / float(emitted.sum()), 4)

    # Relief stratification (H5 input): emission share vs footprint share.
    rq = np.percentile(relief[footprint & valid], [33.33, 66.67])
    classes = {}
    for name, m in (
        ("low", relief < rq[0]),
        ("mid", (relief >= rq[0]) & (relief < rq[1])),
        ("high", relief >= rq[1]),
    ):
        fp = int((footprint & valid & m).sum())
        em = int((emitted & m).sum())
        classes[name] = {
            "footprint_share": round(fp / int((footprint & valid).sum()), 4),
            "emitted_px": em,
            "emitted_share": round(em / int(emitted.sum()), 4),
        }
    audit["relief_classes_q33_q67"] = [round(float(rq[0]), 1), round(float(rq[1]), 1)]
    audit["relief_stratification"] = classes

    # Freeze v2 cutoffs from BACKGROUND quantiles only.
    cross_q = float(np.percentile(cross[bg], CROSS_PCT))
    coh_q = float(np.percentile(coh[bg], COH_PCT))
    relief_q = float(np.percentile(relief[bg], RELIEF_PCT))
    v2_drop_channel = emitted & (cross > cross_q) & (coh < coh_q)
    v2_drop_relief = emitted & (relief > relief_q) & (coh < coh_q)
    v2_drop = v2_drop_channel | v2_drop_relief
    audit["v2_policy"] = {
        "rule": "drop emitted px if (cross_max>CROSS_Q and coh100<COH_Q) "
                "or (relief>RELIEF_Q and coh100<COH_Q)",
        "cutoff_source": "background (non-emitted, lidar-covered) quantiles only; "
                         "no catalogue-label or leaderboard tuning",
        "CROSS_Q": round(cross_q, 2),
        "COH_Q": round(coh_q, 2),
        "RELIEF_Q": round(relief_q, 2),
        "would_drop_channel_px": int(v2_drop_channel.sum()),
        "would_drop_relief_px": int(v2_drop_relief.sum()),
        "would_drop_total_px": int(v2_drop.sum()),
        "would_keep_px": int(emitted.sum()) - int(v2_drop.sum()),
        "status": "PRE-REGISTERED ONLY: v2 file is not packaged until the v1 "
                  "upload scores, so the H1 test stays decisive.",
    }

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "lidar_product": str(LIDAR.relative_to(ROOT)),
            "candidate": str(CANDIDATE.relative_to(ROOT)),
            "quantisation": "q units (1..255); 0 = no lidar; see lidar_scarp_features.json",
        },
        **audit,
    }
    out = ROOT / "knowledge" / "session5" / "lidar_fp_audit.json"
    out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({
        "emitted_px": audit["emitted_px"],
        "loop_hole_px": audit["loop_hole_px"],
        "emitted_cross_dominant_fraction": audit["emitted_cross_dominant_fraction"],
        "relief_stratification": audit["relief_stratification"],
        "v2_policy": audit["v2_policy"],
    }, indent=1))


if __name__ == "__main__":
    main()
