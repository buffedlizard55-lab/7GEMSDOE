# The metric: distance-weighted Tversky index (DTI)

Official definition: [problem page, Performance metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric).
Implementation: `scripts/metric.py`. Tests: `tests/test_metric.py` (24 passing:
brute-force cross-check, algebraic identities, and bit-level reproduction of the
inherited verified table on the real competition fixture window).

Parameters: **α = 0.2 (false positives), β = 0.8 (false negatives),
R = 300 m triangular kernel (3 px)**.

## Closed form (proven in tests)

With the identity `TP_w + FN_w = |G|` and α = 1 − β = 0.2:

    DTI = TP_w / (0.2·(TP_w + FP_w) + 0.8·|G|)

## Measured anchors (fixture window, 5,154 truth px / 261,835 valid px)

From `inherited_evidence/metric_strategy.json`, reproduced exactly by the test
suite:

| strategy | DTI |
|---|---|
| all zeros | 0.0000 |
| all ones (blanket) | **0.0956** — the floor any real model must beat |
| uniform p=0.05 … 0.5 | 0.0390 … 0.0888 (nearly flat — uniform mass buys nothing) |
| exact catalogue copy | 0.9999 (vs the catalogue — NOT the scored population) |
| catalogue dilated r=1/2/3 | 0.8818 / 0.7336 / 0.5887 |
| triangular ramp r=3/5/8 | 0.8118 / 0.6223 / 0.4504 |
| precise 25 % of faults | 0.5545 — the metric rewards precision against the catalogue |

## Economics against the SCORED population (new faults)

* β/α = 4: missing a true fault costs 4× an equal false positive. Recall-leaning
  strategies are favored **if** the mass lands near real structure.
* The 300 m kernel gives partial credit for near misses and absorbs label
  mis-registration — wide soft emissions are robust to position error.
* Component-holdout proxy (this repo, `scripts/tune_components.py` +
  `sweep_halos.py`): hiding 20 % of catalogue fault pixels as pseudo-new faults,
  DTI rises monotonically with halo width up to r≈15 px / h≈0.6 (0.0249 vs
  0.0090 for the bare catalogue, vs 0.0118 blanket) — see `strategy.html`.
* The platform's private new-fault population is different from any local proxy;
  proxies rank strategies, they do not predict scores.
