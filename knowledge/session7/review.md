# Session 7 three-pass review — falsify radiometrics before spending feedback

**Review date:** 2026-09-26 UTC. Target: geological-fault prediction in the
GeoDAWN competition, not direct geothermal-vent classification. No upload,
leaderboard improvement or geological discovery is claimed.

## Pass 1 — implement the next evidence gates end to end

### Current public position and H1 gate

The validated public release feed is timestamped 2026-09-26 22:59:17 UTC,
contains 109 ranks and shows DARD at 0.3049. Known group bests remain extradr19
0.1563 (rank 24), SDCF9 0.1563 (rank 25; file unknown), smashi34 0.1560,
smrtdoog5 0.1193 and wbg1 0.0830. `knowledge/feed.json` is the snapshot; the
[official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
is authoritative and dynamic.

H1 lidar is still unscored. The valid, strict-gated file and Note remain at the
top of the site. No participant credentials are available or requested, so no
competition upload or authenticated file-score attribution occurred. The
session-4 score decision tree remains frozen.

### Autonomous data placement

`bash scripts/download_competition_data.sh` was rerun. Dropbox failed TLS; the
public sibling-repository bridge restored all three rasters and exact inherited
SHA-256 pins. `.venv/bin/python scripts/verify_data.py` passed the 3292×3730,
EPSG:32611, 100 m grid and census. The pins establish consistency with inherited
team bytes, not independent sponsor provenance.

### H9b — pre-registered lineament representation

`scripts/radiometric_features.py` implements 30 fixed features: per-channel
100/300 m gradient and absolute Laplacian, multi-channel edge strength,
structure-tensor orientation/coherence and broad residuals. Normalised
convolution prevents zero-coded source boundaries becoming lineaments; a
one-cell derivative rim is suppressed. The code deliberately refuses physical
K/Th-style claims from independently quantised K/Th/U bytes.

`scripts/radiometric_lineament_experiment.py` ran five common-support geographic
folds, 1 km buffers, fixed samples and LightGBM 4.6.0. Common support:
5,164,300 pixels, 60,894 known-fault pixels.

| Arm | Top-f 1% | Top-f 2% | Ridge 1% | Ridge 2% |
|---|---:|---:|---:|---:|
| bands19 | 0.733505× | 0.642315× | 1.032686× | 0.888580× |
| rad_raw | 0.655382× | 0.611082× | 0.851402× | 0.768970× |
| rad_lineament | 0.565168× | 0.539075× | 0.769739× | 0.737511× |

The lineament arm beat the stronger comparator in 0/5 folds at 1% and 2%; H9b
**failed**. No submission was generated. Full evidence:
`knowledge/session7/radiometric_lineament_experiment.json`.

### Official omitted-channel discovery and runner

The official GeoDAWN ReadMe defines corrected physical radioelements and
contractor Th/K, U/K and U/Th ratios. The already observed official archive
list contained exact ratio GeoTIFFs and `upcont_tmi150`, none present in the 19
supplied-band descriptions. `scripts/geodawn_extensions.py` was written before
measurement with exact member selection, safe archive handling and provenance.

GitHub Actions run
[36279766757](https://github.com/buffedlizard55-lab/7GEMSDOE/actions/runs/36279766757)
succeeded. Both Area 1/2 archives matched ScienceBase-listed sizes and MD5s.
The four-band exact-grid output SHA-256 is
`a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b`;
source member names/grids/ranges and archive SHA-256 values are in
`external/geodawn_extensions/geodawn_extensions.json`.

### H9c — official physical-ratio test

The H9c protocol was frozen before retrieval/measurement. Same support, folds,
samples and learner as H9b:

| Arm | Top-f 1% | Top-f 2% | Role |
|---|---:|---:|---|
| bands19 | 0.733505× | 0.642315× | comparator |
| rad_raw | 0.655382× | 0.611082× | comparator |
| ratios3 | 0.662887× | 0.588166× | primary |
| up150 | 0.398244× | 0.396334× | diagnostic |
| extensions4 | 0.562762× | 0.540199× | diagnostic |

Ratios beat the stronger comparator in 1/5 folds at each target density; H9c
**failed**. Ridge-NMS did not reverse it. `scripts/audit_extension_overlap.py`
then measured up150 versus supplied TMI after robust byte encoding: 0.993329
Pearson rank correlation, 70.65% exact bytes, mean absolute byte difference
1.32 across 5,164,312 common pixels. Up150 is not independent evidence.

Full evidence: `knowledge/session7/geodawn_extension_experiment.json` and
`knowledge/session7/extension_overlap.json`.

## Pass 2 — bug, assumption and edge-case audit

1. **Memory failure made explicit.** The first H9b process was killed before a
   fold result because it retained bands, lidar and all derivative work arrays.
   No result was silently inferred. Feature tensor accumulation was rewritten
   online; experiment arms are loaded sequentially. The diagnostic-only fused
   arm was removed before measurement, while all three primary arms, samples,
   folds and frozen promotion rule remained unchanged. This is recorded in the
   protocol and machine report.
2. **Missing-data edge artifact prevented.** A synthetic test proves a constant
   field bounded by zero-coded missing data does not create a source-edge
   gradient. Inputs with NaN/Inf, wrong shapes or nonpositive scales fail closed.
3. **No fake geochemistry.** Ratios of independently quantised bytes were
   excluded. H9c uses exact contractor ratio members computed upstream from
   physical channels, then clearly labels the committed bytes as ranks rather
   than physical units.
4. **Exact member/provenance checks.** Extension selection is basename-exact,
   case-insensitive and rejects missing/duplicate/unknown-area inputs. Existing
   archive path/symlink/size and ScienceBase size/MD5 guards remain in force.
5. **Support sensitivity exposed.** Session 6's narrow raw-radiometric edge was
   on the bands+lidar intersection. H9b/H9c use the wider radiometric support;
   bands19 then beats raw radiometrics. The earlier result is now labelled
   support-sensitive, not robust discovery evidence.
6. **Objective mismatch retained.** Some derivative folds gained AUC while
   top-f official-kernel coverage fell. Promotion uses the frozen top-f metric,
   not whichever secondary diagnostic looks best.
7. **No post-hoc rescue.** H9 is stopped after raw, lineament and physical-ratio
   screens instead of sweeping scales/mixtures on repeatedly used catalogue
   folds. Acquisition-block holdout is required only if independent evidence
   reopens H9.
8. **Source extremes flagged.** The ratio manifest records unusual source
   extrema, including negative Th/K. Verified transport/schema does not certify
   physical interpretation; contractor quality masks/report remain a review
   requirement.

## Pass 3 — full-request and publication check

* The README remains the persistent project brief, with Maximize P(Win), Own the
  Outcome, top-leaderboard goal, privacy-safe team record, one-click valid TIFF,
  exact Note and executive submission guide. The competition is correctly
  described as fault mapping with geothermal motivation.
* The site is generated from machine evidence and now presents H9b/H9c negative
  results, exact official product provenance and the stop/pivot decision. It
  still places the valid H1 download first and does not present feature rasters
  as submissions.
* Every published submission TIFF was rechecked by the strict validator against
  the template: single-band float32, exact grid/CRS/transform, finite [0,1]
  inside, NaN outside. This directly guards the reported rejection.
* Static relative-link checks found zero missing paths across seven pages. The
  complete hermetic suite passed 140 tests (50 non-failing Rasterio warnings).
  A local Playwright attempt could not download Chromium because outbound TLS
  failed on all mirrors; that local failure is retained. The PR research runner
  then installed Chromium and passed the real-browser suite at 1440/390 px,
  including navigation, viewport overflow, copy Note, file/hash download,
  mismatch blocking and JavaScript-error checks (run 36281074347).
* No second candidate was generated because doing so before H1's score would
  violate the frozen experiment and waste feedback. Autonomous work completed
  every task not requiring a participant's authorized upload session.

## Decision and remaining path

H9 is not the winning primary path on current evidence. Maximize P(Win) now means:

1. obtain and attribute H1's score, then follow the frozen branch;
2. pre-register H10 short cross-connectors in step-over/termination zones with
   matched random-tangent controls and whole-system/geographic holdouts;
3. fill the 24.6% lidar gap, prioritizing the 47.4%-missing NE quadrant;
4. use radiometrics only as corroboration for an independently generated line;
5. reserve untouched systems/geography before more model development.

## Limitations / access still needed

* Authorized participant upload/final-selection access (never credentials in
  the repo/chat) and exact submission receipt/score.
* Team entity-registration and file-score bookkeeping; SDCF9's 0.1563 file is
  unknown and smashi34 pairing is not authenticated.
* Official competition data-tab provenance/checksums and DEM-link CSV remain
  inaccessible without login; inherited hashes are not sponsor signatures.
* GPU/storage for deep models only after spatial protocol integration; random
  pixel AUC is not a substitute.
* Playwright Chromium download is TLS-blocked locally; the hosted runner passed
  the rebuilt pages, but local browser reproduction still needs working browser
  binaries/network.
* Defensible fault-system IDs, independent channel/shoreline controls, missing
  lidar coverage and expert/field validation.
* GDR 1391 remains an excerpt-review warning. Automated source monitoring is
  not scientific verification.

## Primary links for manual review

* [Official competition/problem/metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
* [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
* [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
* [USGS GeoDAWN ScienceBase item / DOI 10.5066/P93LGLVQ](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7)
* [Official GeoDAWN ReadMe](https://www.sciencebase.gov/catalog/file/get/657e1d85d34e23d3533209f7?name=GeoDAWN_ReadMe.pdf)
* [USGS GeoDAWN data catalogue](https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7)
* [USGS GeoDAWN project context](https://www.usgs.gov/media/images/geodawn-geoscience-data-acquisition-western-nevada)
* [USGS radiometric alteration record](https://www.usgs.gov/publications/airborne-radiometric-data-map-alteration-porphyry-copper-systems-elkhorn-district-mt)
* [Faulds & Hinz Great Basin structural settings](https://www.osti.gov/servlets/purl/1724082)
