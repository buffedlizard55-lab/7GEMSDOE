"""Wide policy sweep on the persisted component-holdout fields.

Uses DATA_DIR/artifacts/component_holdout_fields.npz (written by
tune_components.py) to evaluate many halo/emission combinations with the
official DTI against the hidden components - no retraining needed.

Updates DATA_DIR/artifacts/component_policy_report.json with the best policy.
"""

from __future__ import annotations

import itertools
import json
import sys
import time

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from metric import dtvi  # noqa: E402
from paths import ARTIFACT_DIR  # noqa: E402
from tune_policy import model_emission, proximity_field  # noqa: E402


def main():
    f = np.load(ARTIFACT_DIR / "component_holdout_fields.npz")
    p_map, remaining = f["p_map"], f["remaining"]
    hidden, valid = f["hidden"], f["valid"]
    hidden_f = hidden.astype(np.float64)

    results = []

    def score(name, pred):
        pred = np.where(valid, pred, 0.0).astype(np.float64)
        d = dtvi(pred, hidden_f)
        mass = float(pred.sum())
        results.append({"strategy": name, "DTI": d, "mass": mass})
        print(f"{name:58s} DTI={d:.4f} mass={mass:.0f}", flush=True)
        return d

    best_name, best_dti, best_cfg = None, -1.0, None

    # halos alone
    for r, h in itertools.product([3, 5, 7, 9], [0.2, 0.3, 0.4, 0.5, 0.6]):
        d = score(f"prox r={r} h={h}", proximity_field(remaining, r, h))
        if d > best_dti:
            best_name, best_dti = f"prox r={r} h={h}", d
            best_cfg = {"kind": "prox", "prox_r": r, "prox_h": h}

    # halos + model emission blends
    for (r, h), (tau, s) in itertools.product(
            [(5, 0.4), (7, 0.3), (7, 0.4), (9, 0.3)],
            [(0.4, 0.4), (0.4, 0.6), (0.5, 0.5), (0.5, 0.6), (0.5, 0.8),
             (0.6, 0.8)]):
        prox = proximity_field(remaining, r, h)
        emis = model_emission(p_map, tau, s)
        name = f"blend prox(r={r},h={h}) | model(tau={tau},s={s})"
        d = score(name, np.maximum(prox, emis))
        if d > best_dti:
            best_name, best_dti = name, d
            best_cfg = {"kind": "blend", "prox_r": r, "prox_h": h,
                        "tau": tau, "scale": s}

    results.sort(key=lambda x: -x["DTI"])
    print("\nTOP 10")
    for row in results[:10]:
        print(f"  {row['DTI']:.4f}  {row['strategy']}")

    rep_path = ARTIFACT_DIR / "component_policy_report.json"
    report = json.loads(rep_path.read_text()) if rep_path.exists() else {}
    report["sweep"] = {
        "best_strategy": best_name,
        "best_proxy_dti": best_dti,
        "best_config": best_cfg,
        "n_evaluated": len(results),
        "top10": results[:10],
    }
    rep_path.write_text(json.dumps(report, indent=1))
    print("\nbest:", best_name, "DTI", round(best_dti, 4))
    print("wrote", rep_path)


if __name__ == "__main__":
    t0 = time.time()
    sys.exit(main())
