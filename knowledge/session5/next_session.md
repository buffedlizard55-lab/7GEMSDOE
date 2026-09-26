# Next session — priorities, open questions, limitations (written 2026-09-26)

Read `README.md` → `AGENTS.md` → `STATUS.md` → this file →
`knowledge/session5/review.md`, then session-4 decision tree
(`knowledge/session4/next_session.md` — still authoritative for the H1
upload outcome).

## 0. First actions (in order)

1. **Record the H1 upload score** (needs the participant): upload
   `downloads/gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.tif` with its
   Note; record account, UTC time, filename, SHA-256, score in
   `knowledge/team_results.json`. Then follow the session-4 decision tree
   (≥0.16 invest / 0.09–0.16 combine / <0.09 pivot).
2. **Dispatch the two runner jobs** (Actions → Run workflow, or push a
   commit whose message starts with the marker):
   * QFFDB prior: `[run-qfaults]` → `external/qfaults/`
   * Radiometrics: `[run-rad]` → `external/geodawn_rad/`
   Inspect each manifest's observed-fields/file-list before trusting the
   product; record licence notes.
3. **Record SDCF9's 0.1563 file** (2 submissions; file behind the score is
   still unknown) and resolve team registration vs rules §3.4 (3/week per
   entity; one final).

## 1. Experiment queue (pre-registered forms; run after data lands)

1. H9 radiometric skill: same 5-fold geographic protocol as
   `lidar_experiment.json` — arm `rad` (K/Th/U/TC lineaments + context)
   vs `bands19` vs `lidar` vs `all`; promotion rule mirrors session 4
   (beat bands19 pooled at f=1%,2% AND ≥4/5 folds).
2. H2 scale-deficit: matched-mass emission near coarse/inferred vs fine
   QFFDB traces; enrichment statistic on held-out catalogue geometry.
3. H10 interaction-zone cross-segments: build strand-overlap/tip mask from
   catalogue geometry; matched-mass test inside vs outside.
4. H11 strain stratification: skill in high- vs low-geodetic-strain
   ground (bands 4/7/8; no new data).
5. V2 cleanup: package `lidar_fp_audit.json`'s frozen policy ONLY after
   v1 scores (keeps H1 decisive); expected delta is small (~2% pixels).

## 2. Engineering backlog (carried + new, ordered)

1. Lidar gap fill: runner enumeration of 3DEP S3 NV/CA 1 m projects
   intersecting the NE-quadrant gap (47%); 10 m fallback documented.
2. Channel-network + shoreline FP controls from DEM flow accumulation /
   constant-elevation analysis (the 72% cross-dominant flag needs this,
   not tighter thresholds).
3. INGENIOUS geothermal-observation job (wells/springs, 2 m probes,
   paleo features) for the H8 stratification test. Exclude
   slip/dilation-tendency + fault shapefiles as features (catalogue
   leakage — see session-5 research §2).
4. Native-resolution (2 m) ridge extraction + vectorisation (carried).
5. Positive-unlabeled training + survey-block holdouts (carried).
6. U-Net port to lidar/radiometric channels if a GPU appears (carried).
7. SGMC-gap upload (H4) stays the cheap alternative single upload.

## 3. Known limitations (do not overclaim)

* Runner products do not exist yet; radio altitude masks, block
  boundaries and per-asset licences are unverified.
* All local skill numbers use catalogue truth (up to 400 m from
  lidar-mapped faults); the implied truth density (0.31%) assumes the
  catalogue-gap upload had zero skill.
* Sandbox: ~4 GB RAM, 2 CPUs, no GPU, no direct USGS/ScienceBase/
  DrivenData egress (page/search tools + Actions only).
* No DrivenData login: uploads + final selection are the participant's.
* Deadline plan: final selection by Dec 3, 2026 22:00 UTC (rules A.1
  "5:00 p.m. ET" is earlier than the website's 23:59 UTC).
