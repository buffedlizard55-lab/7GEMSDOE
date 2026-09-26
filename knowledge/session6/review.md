# Session 6 review — pipeline replay, live feed and source-ingestion safeguards

**Review date:** 2026-09-26 UTC. This is an evidence note, not a claim that the
competition score improved. The standing competition target is fault mapping,
not direct geothermal-vent classification ([official problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)).

## Pass 1 — implement and verify

### Current competition / team position

The automated public feed retrieved from the repository's `research-feed`
release is timestamped **2026-09-26 21:12:55 UTC**, contains **107 ranked
entries**, and records DARD at **0.3049**. It places the team's known public
bests at extradr19 **0.1563 (rank 24)**, SDCF9 **0.1563 (rank 25)**, smashi34
**0.1560 (rank 26)**, smrtdoog5 **0.1193 (rank 41)** and wbg1 **0.0830 (rank
50)**. See the saved, machine-readable snapshot `knowledge/feed.json` and the
[official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
A separate official-page retrieval later in this review still showed DARD at
0.3049 and SDCF9 at 0.1563; leaderboard scores are public bests and can change.

The current best known group public score is 0.1486 below the leader. The
SDCF9 leaderboard best is still not paired with a known file: the recorded
GEMSDOE3 dense control is 0.1152, so the file that earned 0.1563 remains an
unresolved irregularity. The file-to-score pairing for smashi34 is also not
fully authenticated. The private email addresses in the user's pasted results
are intentionally not copied into public project files.

The official problem page says new expert-labeled faults form the initial
private test truth and submissions are subsequently reviewed to expand the
fault labels for the final prize round. This validates the project's emphasis
on auditable, geologically interpretable candidate traces, but it does **not**
prove that interpretability alone increases a score or that any emitted trace
is a real fault.

### Data placement, training, and end-to-end reproduction

* `bash scripts/download_competition_data.sh` completed autonomously. Dropbox
  TLS failed; the script's public sibling-repository bridge succeeded. All
  three files passed inherited SHA-256 pins. These pins establish byte
  consistency with inherited team evidence, **not independent sponsor
  provenance**.
* `scripts/verify_data.py` passed: 3,292 x 3,730, EPSG:32611, 100 m; 19
  feature bands; 5,167,373 valid pixels; 60,988 positive known-fault pixels.
  `scripts/prepare_data.py` completed and reported 58,171 imputed band-pixels.
* CPU retraining (`scripts/train_model.py`, seed 20260926) completed in 71 s:
  304,940 sampled rows, 27 features, random-pixel holdout AUC 0.9172875 and
  Brier 0.0976630. This holdout is **not spatially independent** and is only a
  training-pipeline diagnostic; it is not a leaderboard estimate.
* `scripts/build_submission.py --no-publish` rebuilt the legacy control and
  passed its strict format gate. Its SHA-256
  `90fb7dc0fc1f6e7d3dbb20927417c6af7d110ca41167329d792c75c145f75b6a` exactly
  matched the preserved published control byte-for-byte. The replay did not
  overwrite or publish a download.
* The recommended H1 candidate (`gems7-lidarscarp-ridge-top2pct-36c3a3f341c8`)
  remains **unscored**. No file was uploaded, no new candidate was packaged,
  and no result above 0.3049 is claimed.

Machine evidence and full hashes: [`local_verification.json`](local_verification.json).

### Up-to-date feed and irregularities

* The scheduled research refresh succeeded on GitHub Actions and published a
  timestamped feed. Its latest run in this review found 107 ranks and flagged
  the official GDR 1391 source excerpt as `REVIEW_excerpt_missing`; the stale
  bundled snapshot was refreshed from the validated release-body JSON. The
  direct release-asset URL failed with EOF, so the API body was used instead.
* The direct DrivenData data tab currently resolves to login; no credentials
  were accessed. The project still does not hold an authenticated competition
  session or the official DEM-link CSV.
* Explicit `workflow_dispatch` attempts for both QFFDB and radiometric jobs
  returned HTTP 403 `Resource not accessible by integration`. No external
  product is claimed to have been downloaded by those jobs. The official source
  record for INGENIOUS GDR 1391 also remains an excerpt-review flag, not a
  verified correction.
* The current results and sources feed is machine-checked, not a substitute for
  checking scientific meaning, licenses, or file-to-score provenance.

### Hardening implemented this pass

* QFFDB ZIP ingestion now rejects absolute/traversal paths and symbolic links
  before extraction. It also refuses to rasterize a layer with a missing or
  unparseable CRS instead of silently assuming coordinates are EPSG:32611.
* GeoDAWN radiometric ingestion now fails closed when a preferred channel has
  multiple matching files, preventing results from depending on API listing
  order. Quantisation excludes NaN and infinite cells before calculating
  percentile bounds; temporary download filenames are reduced to safe
  basenames.
* New hermetic tests cover these input irregularities. See
  `scripts/qfaults_prior.py`, `scripts/geodawn_rad.py`,
  `tests/test_qfaults.py` and `tests/test_geodawn_rad.py`.

## Pass 2 — bug, assumption and edge-case review

* ZIP traversal is checked for both POSIX and Windows separators/absolute
  paths; extraction accepts ordinary nested files and rejects symlinks. No
  archive member is extracted before the full member list passes validation.
* CRS handling uses parsed CRS objects, not the previous substring test for
  `"32611"`; missing CRS now stops the job. Geometry reprojecting remains
  runner-only and still must be checked against the observed QFFDB layer schema.
* Radiometric selection reports ambiguity rather than silently selecting the
  first listing result. A listing with one unambiguous match per channel is
  still required before a data product can be built. Finite-value tests verify
  NaN/Inf never leak into byte quantisation.
* A label-derived random-pixel AUC is explicitly not treated as spatial
  discovery skill. The experimental H1 candidate remains the only decisive
  leaderboard test under the prior decision tree; a second upload would confound
  it and spend feedback budget without new evidence.
* The feed's GDR 1391 excerpt status is left flagged rather than manually
  rewritten as verified. No private credentials or email addresses were added.
* The complete hermetic suite passes (**124 passed**, 50 non-failing Rasterio
  pending-deprecation warnings); a second static audit found zero broken relative
  links across the seven generated site pages.

## Pass 3 — full-request check / outcome

* The repo's mission, sources, previous group results, official leaderboard,
  downloadable submission and submission-format guide remain in place. This
  review updated the bundled leaderboard snapshot and records the reproducible
  local train-to-control replay.
* Submission rejection guard remains exact: a single-band float32 GeoTIFF on
  the template grid, finite predictions in [0,1] inside the footprint, and
  NaN outside, as enforced by `scripts/validate_submission.py`.
* The H1 file is ready for an authorized participant to submit with the Note
  recorded in `downloads/lidar_meta.json`; this agent did not and cannot submit
  through the absent DrivenData login. No leaderboard gain is asserted.
* The code improvements are source-ingestion safety/ambiguity safeguards only;
  they do not change a prediction policy and have no claimed score effect.

## Evidence-linked source links for manual review

* [Official competition overview / rules entry](https://www.drivendata.org/competitions/306/competition-doe-gems/)
* [Official problem description and prize structure](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
* [Official About page (GeoDAWN context and fault definitions)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
* [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
* [Competition data tab (sign-in required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
* [DOE/USGS competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
* [USGS GeoDAWN ScienceBase release](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7)
* [USGS GeoDAWN data page](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
* [USGS QFFDB download referenced by the H2 runner](https://earthquake.usgs.gov/static/lfs/nshm/qfaults/Qfaults_GIS.zip)
* [GDR INGENIOUS source record — current excerpt check needs review](https://gdr.openei.org/submissions/1391)
