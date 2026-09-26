# Knowledge base

Verified, source-linked knowledge for the GEMS Prize Challenge. Read
`00_competition_facts.md` first every session.

| file | contents |
|---|---|
| 00_competition_facts.md | rules, metric, prize structure, irregularities — all with sources |
| 01_science_faults_geothermal.md | fault–geothermal science + official data sources (reusable base) |
| 02_data_sources.md | byte-level inventory, sha256 pins, download routes, band semantics |
| 03_metric.md | DTI implementation evidence and economics |
| 04_team_history.md | our accounts, scores, leaderboard snapshot, lessons |
| inherited_evidence/ | machine-measured evidence inherited from the sibling GEMSDOE repo (see provenance below) |
| session6/ | live-feed refresh, reproducible train-to-control replay, ingestion safeguards, three-pass review and next steps |

## session6/ (2026-09-26)

- `review.md` — three-pass implementation audit, live public results, verified local pipeline replay, API permission blockers and irregularities.
- `local_verification.json` — dataset hashes, grid/census, training diagnostics, byte-identical control hash and feed snapshot.
- `next_session.md` — prioritized H1 score decision, runner-data actions, experiments, limitations and stop conditions.

## inherited_evidence/ provenance

Copied verbatim from the public repo
[github.com/buffedlizard55-lab/GEMSDOE](https://github.com/buffedlizard55-lab/GEMSDOE)
(commit of 2026-09-25) `data/evidence/` — artifacts measured by GitHub-hosted
runners against the official downloads, never hand-typed:

* `data_bridge_manifest.json` — sha256 pins of the three official rasters
* `inventory.json` — independent runner-side file inventory
* `labels_summary.json` — label census (60,988 positive px)
* `metric_strategy.json` — the verified DTI strategy table reproduced by our tests
* `rules_quotes.json` + `rules_extracted_text.txt` — verbatim rules extraction
  (sha256 50d854b1… checked against the live PDF 2026-09-21)
* `sciencebase_dois.json`, `qfaults_stats.json`, `shift_robustness.json`,
  `transfer_analysis.json` — supporting measurements

## session4/ (2026-09-26)

- `research.md` — new verified sources (GeoDAWN lidar, NBMG lidar discoveries, scarp
  detection literature, QFFDB accuracy semantics), leaderboard theory, hypothesis register.
- `review.md` — group scores vs leaderboard, score forensics, irregularities, [0,1] root cause.
- `scored_files_analysis.json` — machine output of `scripts/analyze_scored_files.py`.
- `lidar_experiment.json` — pre-registered 5-fold geographic lidar test.
- `lidar_candidate.json` — rule-based density table and candidate statistics.
- `next_session.md` — decision tree, backlog, limitations.
- `../dem_tiles.json` — 716 official 3DEP tile URLs (OCR-recovered inventory, provenance header).
- `../../external/dem/` — region-wide lidar product + per-tile SHA-256 log.
