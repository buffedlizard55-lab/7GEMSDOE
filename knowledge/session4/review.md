# Session 4 review — group results vs the official leaderboard (2026-09-26)

Scope: this repository, the five earlier group repositories/sites, their scored
files, and the official public leaderboard. Facts are labelled **[official]**,
**[team record]** (a group repo says so) or **[inference]** (our model-based
reasoning, open to challenge).

## Standing

| Participant | Public score | Source |
|---|---|---|
| DARD (leader) | 0.3049 | [official] [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), ~19:00 UTC 2026-09-26 |
| alexoktaba / HardcoreTechGod / mzoorob | 0.2993 / 0.2854 / 0.2843 | [official] same snapshot |
| doegemsDrivendata (likely organiser baseline) | 0.1847 | [official] account name; role is an [inference] |
| extradr19 · SDCF9 · smashi34 | 0.1563 · 0.1563 · 0.1560 | [official] account bests |
| smrtdoog5 · wbg1 | 0.1193 · 0.0830 | [official] account bests |

Best group score 0.1563 is **below the organiser-like baseline (0.1847)** and
0.1486 short of the leader. Cosmetic changes cannot close a ~2x gap.

## What the scored files say (reproducible: `scripts/analyze_scored_files.py`)

Files are vendored in `external/scored/` with source commit, path and SHA-256
(`external/scored/manifest.json`). Densities are off-catalogue emitted pixels over
scored pixels; fill = emitted share of pixels at that distance from a known fault.

| File | Account [team record] | Score | Density | Fill @1 px | Fill >50 px | Dispersion | Skill vs random [inference] |
|---|---|---|---|---|---|---|---|
| `gemsdoe1-ens12-7f00890a.tif` | GEMSDOE1 / extradr19 | 0.1563 | 3.26% | 0.099 | 0.019 | 5.08 | x1.90 |
| `gemsdoe2-dual-union-f68e590f.tif` | GEMSDOE2 / smashi34 (pairing unverified) | 0.1560 | 3.45% | 0.115 | 0.020 | 4.89 | x1.89 |
| `gemsdoe3-pindrop-nodes-f347b70daa.tif` | GEMSDOE3 / smrtdoog5 | 0.1193 | 3.04% | 0.051 | 0.030 | 12.85 | x1.45 |
| `gemsdoe3-pindrop-ridge-4e03fc9705.tif` | GEMSDOE3 / SDCF9 | 0.1152 | 3.04% | 0.109 | 0.019 | 4.83 | x1.40 |
| `gemsdoe3-pindrop-discovery-37f9d5b855.tif` | GEMSDOE3 / wbg1 | 0.0830 | 3.04% | 0.040 | 0.029 | 12.84 | x1.00 (reference) |
| `gemsdoe4-combined-237f0063.tif` | GEMSDOE4 / not recorded | 0.0343 | 5.06% | 0.095 | 0.039 | 2.29 | x0.41 |
| `gems6-hgb88-topk03-33cec71ff0.tif` | 6GEMSDOE / not recorded | 0.0286 | 2.57% | 0.322 | 0.000 | 2.55 | x0.35 |
| `gemsdoe3-sgmc-gap-7251c22bb4.tif` | never uploaded | — | 1.21% | 0.000 | 0.010 | 4.82 | — |

### Exact random baseline [derived, verified by simulation]

For independent emission at density *f*, each truth pixel's expected kernel
credit is c(f) = Σ w·P(best emitted kernel level = w) (25 kernel offsets with
d < 3 px). DTI_random(f, ρ) = cρ / (0.2cρ + 0.2f + 0.8ρ). Implemented in
`scripts/random_baseline.py`; `tests/test_random_baseline.py` checks it against
Monte-Carlo runs of the official metric code (≤6% tolerance).

### Inferences (each rests on the stated assumption)

1. If the near-uniform catalogue-gap upload (0.0830) had **zero skill**, the
   public truth density is ρ ≈ **0.31%** of scored pixels (≈16k pixels if
   region-wide). Random emission would then peak near **0.083 at f ≈ 3%**.
2. Our best file is only **~1.9x random coverage**. The leader's 0.3049 needs
   ~**4-5x random** at 1-2% density (8x at 0.5%). That is a localisation problem,
   not a calibration problem.
3. The two **below-random** uploads are the two most **blob-like** (dispersion
   2.3-2.6) and/or near-catalogue concentrated (6GEMSDOE fill 0.32 at 1 px).
   Line-like fields (dispersion ~5) scored best. Rule adopted: emit thin lines.
4. Near-catalogue enrichment is not where the new truth concentrates: moderate
   enrichment (fill ~0.10 at 1 px) coexists with the best scores; heavy
   concentration is the worst result. Catalogue-holdout proxies previously
   over-predicted leaderboard scores by 2-7x (sessions 2-3), so they are never
   used alone for selection.

If the reference file had positive skill, ρ is lower and every multiple rises;
the ranking of files does not change.

## Irregularities to resolve (flagged, not assumed away)

- **SDCF9 now shows 0.1563 with 2 submissions** on the leaderboard, but the only
  recorded SDCF9 file (ridge control 4e03fc9705) scored 0.1152. The file behind
  0.1563 is not recorded anywhere we can read. Record filename + SHA-256 for
  every upload (`knowledge/team_results.json`).
- **Five group accounts vs the rules:** official rules §3.4 allow three
  submissions per week *per participating entity*; team members cannot submit
  separate final entries ([rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)).
  If these accounts are one entity, the budget is 3/week in total. Team
  registration is the participant's responsibility; we do not multiply budgets.
- GEMSDOE2 file ↔ smashi34 score pairing is unverified (group-reported).
- **Deadline time differs between official sources:** the competition page says
  "Dec. 3, 2026, 11:59 p.m. UTC"; rules A.1 say "by 5:00 p.m. ET on the prize
  submission deadline date" (= 22:00 UTC). §1.2 defers dates to the website, but
  the safe plan is the earlier time: final selection by **Dec 3, 2026 22:00 UTC**.
- Problem page wording says the sample submission "predicts total fault
  absence", but the supplied example file equals the training labels inside the
  footprint (measured: 60,988 positive pixels). The listed "magnetic source
  depth" feature matches no band tag. Both noted since session 2.

## The "Predicted values must be in range [0, 1]" rejection — root cause

Team evidence ([GEMSDOE `sanitize.json`](https://github.com/buffedlizard55-lab/GEMSDOE/blob/cceebbdcf9a7d2890bb0665defcb54dfc66ae452/data/evidence/runs/ens12-adopted-floor0.1-w0/sanitize.json)):
a file with **3,061 NaN pixels inside the template footprint** (and 1,540 finite
pixels outside it) was rejected with this message; the same map with those
pixels filled (SHA-256 7f00890a…) was accepted and scored 0.1563. All seven
scored group files have **NaN exactly outside and finite [0, 1] everywhere inside**.
So the server treats NaN inside the footprint as out of range. Our strict gate
(`scripts/validate_submission.py`) rejects exactly that layout.
