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
