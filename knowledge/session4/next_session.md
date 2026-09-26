# Next session — priorities, open questions, limitations (written 2026-09-26)

Read `README.md` → `AGENTS.md` → `STATUS.md` → this file → `review.md`.

## 0. First action: record leaderboard feedback (needs the user)

1. Upload `downloads/gems7-lidarscarp-ridge-top2pct-dfa04fa218b8.tif` with its
   Note. Record the account, UTC time, filename, SHA-256 and score in
   `knowledge/team_results.json`. This is the decisive H1 test.
2. Record which file produced **SDCF9's 0.1563** (2 submissions) — currently unknown.
3. Resolve team registration: rules §3.4 allow 3 submissions/week per *entity*;
   teammates cannot submit separate finals. We never multiply the budget.

## 1. Decision tree after the H1 upload

| Lidar candidate score | Reading | Next |
|---|---|---|
| ≥ 0.16 (beats group best) | New faults carry lidar scarp evidence; catalogue validation under-states it | Invest: native-resolution CNN on lidar hillshade/curvature (TLS-style), density sweep 1-3%, add Sentinel-2 B8A, fill lidar gaps (25% of footprint) |
| 0.09-0.16 | Weak transfer; roughly the random-to-group range | Combine lidar ridges with the best 19-band field at matched mass; test unsupervised physics score (up/down-facing steps × coherence) |
| < 0.09 | Lidar descriptors trained on the catalogue do not find new faults | Pivot to geophysical-lineament hypothesis (magnetic edge worms) and H4 (SGMC-gap single upload) |

## 2. Engineering backlog (ordered by expected value)

1. **Lidar coverage gaps**: the OCR-recovered inventory covers ~75% of the
   footprint. List the official S3 prefixes for all NV/CA 1 m projects on a
   runner and add missing tiles (or 1/3 arc-second 10 m DEM as fallback).
2. **Native-resolution detector**: the 100 m aggregation discards trace
   geometry. Extract 1 px ridges at 2 m, vectorise, filter by length/strike,
   then rasterise to the grid (runner job).
3. **False-positive controls**: roads (TIGER/OSM are free but check licences),
   channel networks (flow accumulation from the same DEM), paleo-shorelines
   (constant-elevation contours), tile/project seams.
4. **QFFDB attributes** (`mapped_scale`, `mapped_certainty`) rasterised on a
   runner to test H2 (mapping-scale deficit) — official zip:
   https://earthquake.usgs.gov/static/lfs/nshm/qfaults/Qfaults_GIS.zip
5. **Positive-unlabeled training** and survey-block holdouts (still open).
6. Port the reference U-Net to lidar channels if a GPU becomes available.

## 3. Known limitations (do not overclaim)

- All local skill numbers use *catalogue* faults as truth; QFFDB traces can be
  up to 400 m from lidar-mapped faults (Hermant et al. 2025). Not leaderboard estimates.
- The implied truth density (0.31%) assumes the catalogue-gap upload had zero skill.
- The lidar candidate emits nothing where the tile list has no lidar (25% of the footprint).
- The lidar arm was chosen over the pre-written ``both`` arm after seeing the
  pre-registered experiment (deviation recorded in `scripts/lidar_candidates.py`).
- The sandbox cannot reach USGS/DOE hosts directly; external data work runs on
  GitHub Actions and commits compact products. Actions artefacts and release
  assets are not downloadable from the sandbox.
- No DrivenData login: uploading and final selection are the participant's actions.
- ~4 GB RAM, 2 CPUs, no GPU locally.
