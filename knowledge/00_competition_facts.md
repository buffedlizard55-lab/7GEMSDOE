> **Historical session-1 notes; superseded where inconsistent.** Fresh claim-level evidence and corrections: [session-2 audit](session2/review.md), [science ledger](session2/research.md), [source registry](sources.json), [dated feed](feed.json). Inherited source/provenance claims are not independently authenticated by being stored here.

# Competition facts (verified line-by-line)

Competition: **The Geologic Enhanced Mapping System (GEMS) Prize Challenge**
DrivenData competition id 306, sponsored by the U.S. DOE Office of Geothermal.

| Fact | Value | Source |
|---|---|---|
| Task | pixel-wise probability of geological faults for the whole GeoDAWN region | [problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| Region | GeoDAWN study area, northwestern Great Basin (NV/CA) | problem page; [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) |
| Grid | 3,292 × 3,730 px, 100 m, EPSG:32611, bounds (243350, 4135550)–(572550, 4508550) | measured from `example_submission.tif` (sha256-pinned, see `data.html`) |
| Submission | single-band GeoTIFF, float32, values in **[0, 1]**, same CRS/shape/geotransform as training data, NaN outside bounds | problem page, submission format section |
| Metric | distance-weighted Tversky index, α=0.2 (FP), β=0.8 (FN), triangular kernel R=300 m (3 px) | problem page, performance metric section |
| Feature stack | `training_features.tif`, 19 bands float32 | measured (scripts/verify_data.py) |
| Labels provided | existing USGS Quaternary faults + INGENIOUS, raster `existing_faults.tif` (60,988 positive px / 5,167,373 valid px) | measured |
| Submission limit | three submissions per week | rules PDF (verbatim quote below) |
| Reference solution | U-Net + Monte-Carlo CV, Tversky loss | [drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution) |
| Forum | [community.drivendata.org/c/gems-prize-challenge/111](https://community.drivendata.org/c/gems-prize-challenge/111) | problem page |

## Prize structure (problem page, verbatim meaning)

* **Initial Prize Round — $50,000**: submissions scored against a *fixed private* set of
  new faults expert-labelled **before** the competition; top 5 win $10,000 each.
* **Final Prize Round — $250,000**: an expert panel reviews *every team's* predictions,
  verifies previously-unmapped faults, expands the label set, and all submissions are
  re-scored against the expanded set. Payout $100K / $70K / $40K / $25K / $15K.
* Competitors pick **one** submission that counts for both rounds, blind to private scores.

## Rules PDF — verbatim sentences (sha256-pinned extraction)

Source: `https://docs.nlr.gov/docs/fy26osti/96647.pdf` (sha256
`50d854b1e0239fe6b9648d9fa5c7537bc7b6e5bc10cf6b37a2ff9aa401c36938`, 455,140 bytes).
Extraction verified verbatim on 2026-09-21 by the sibling repo's
`scripts/verify_rules_quotes.py`; copied here as
`inherited_evidence/rules_extracted_text.txt` and `rules_quotes.json`.

* "Participants will submit a single entry, which will be evaluated in two prize phases using a distance-weighted Tversky index."
* "In Phase 1, submissions will be evaluated against a privately withheld subset of the original new fault dataset compiled by expert reviewers."
* "After Phase 1, expert reviewers will use submitted predictions to revise the new fault dataset."
* "All Phase 1 competitors will be eligible to compete in Phase 2 and will be automatically submitted for consideration."
* "Submissions will be reevaluated against the full, revised new fault dataset using the same distance-weighted Tversky index."
* "The Phase 2 prize pool of $250,000 will be distributed among the top five competitors, as judged by their performance on all fault labels in this updated label set."
* "The labels for this prize come from the USGS Quaternary Fault and Fold Database and from a set of newly identified faults labeled by geology experts at the National Laboratory of the Rockies (NLR) and USGS."
* "Second-round prize rankings will be determined by running the selected final submissions against the complete updated test set created by expert review."
* "The feature data for this prize come from the recently released Geoscience Data Acquisition for Western Nevada (GeoDAWN)"
* "In addition, the feature data also contain U.S. Geological Survey (USGS) Digital Elevation Model (DEM) elevation data at 1-m resolution."
* "You must submit a single GeoTIFF with a single raster layer at 100-meter resolution containing your model's predictions of fault locations for the entirety of the GeoDAWN study area."
* "You can make multiple submissions, subject to the limits specified on the competition website (three submissions per week)."

## Consequence (the single most important fact)

Both prize phases score **new faults** — faults expert-labelled at NLR/USGS that are
**not** in the public USGS database. The downloadable labels are the *existing*
catalogue. Therefore:

1. A submission that merely reproduces the catalogue scores only where the experts'
   new labels happen to coincide with it.
2. Every local DTI computed against the catalogue is a **plumbing monitor**, not a
   leaderboard proxy.
3. Winning requires predicting *unmapped* faults — a scientific-discovery problem,
   not a supervised segmentation problem.

## Known irregularities (flagged for review)

* `example_submission.tif` ("sample submission that predicts total fault absence") is
  bit-identical to the label raster inside the footprint (60,988 pixels at 1.0 in
  both) — measured by hash-pinned inspection in the sibling repo and re-measured here
  (scripts/verify_data.py). The prose says "total fault absence"; the bytes say
  otherwise. It remains the authoritative geometry template either way.
* `https://gdr.openei.org/submissions/1391` (linked from the competition page) returns
  "No submission found" as of 2026-09-26 (verified via fetch). Flagged.
* DrivenData data tab requires login; the three rasters are mirrored on Dropbox
  (linked above the data tab) and were hash-verified byte-identical (see data.html).
