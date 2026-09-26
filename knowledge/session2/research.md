# Scientific research ledger — 2026-09-26

## Scope and evidence standard

The official [problem statement](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
requires a **fault confidence raster**, not a vent-location catalogue. A mapped fault is
not proof of a productive geothermal resource. Nothing in this session establishes a new
geothermal discovery. See [`../sources.json`](../sources.json) for claim-level excerpts,
source links, proposed uses, dates and license boundaries. These are a starting literature
set, not an exhaustive list of all relevant sources.

## Priority 1: independent information, not another threshold sweep

Group records show 0.1563 for GEMSDOE1 and 0.1560 for GEMSDOE2. The sites describe a
recall-oriented deep ensemble and an additional-family union respectively. The tiny drop
is evidence *against prioritizing more unions of those particular arms*, conditional on
correct artifact attribution. Neither historical TIFF was independently recovered from
the user's submission history. Public best scores cannot authenticate those bytes.

The Pindrop comparison is better identified: nodes `f347b70daa` scored 0.1193 vs dense
`4e03fc9705` at 0.1152, both sites reporting 155,021 emitted pixels. The 0.0041 gain
supports testing placement, but does not imply statistical significance or justify
scaling to a prize-winning score. Catalogue-gap `37f9d5b855` at 0.0830 underperformed.
The two unattributed results (0.0343 and 0.0286) remain user-reported observations.

## H3 — structural continuation (implemented)

[Faulds & Hinz 2015, official OSTI record](https://www.osti.gov/biblio/1724082)
reports stepovers, terminations and intersections as common settings among categorized
geothermal fields. These are **not** probabilities for all fault pixels, and the
study does not prove that blind extrapolation of mapped traces will work.

Our testable inference: incomplete mapped strands may continue preferentially along
local strike, allowing lower false-positive mass than an isotropic halo. Local PCA
estimates a tangent using *only visible labels*. Fixed four-arm test, two selection
seeds and one previously reserved test seed; report retained in
`structural_experiment.json`. Full-region candidate is **experimental**, not promoted
on a claim of geographic generalization. This approach cannot reach isolated faults
far from every catalogue trace. No hidden component pixels enter PCA.

Next falsification: entire fault-system and buffered geographic holdouts, randomly
rotated tangents as null, matched prediction-mass controls, separate near/far strata,
and independent magnetic/gravity corroboration. Do not repeatedly optimize seed 9001.

## H4 — native 1 m DEM information (pilot implemented)

The official [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
links lidar acquisition through 3DEP. Terrain scarps may carry high-frequency information
absent from the 100 m feature raster. We recover an exact USGS bucket URL from the inherited
OCR inventory and attempt a bounded native-resolution crop. The official competition
CSV has **not** been authenticated or mirrored here.

Pilot: 2048×2048 pixels, smooth at 3 m, gradient of slope, exclude 40 m around nodata
and crop boundary. This verifies engineering access and feature construction only.
Roads, river banks, lithological contacts and landslides can produce the same signal.
A region-wide inference layer requires tile overlap, CRS reprojection, spatial holdout,
coverage masks, negative controls, and training/calibration before submission use.
Missing coverage must remain a quality flag, not a prediction of no fault.

## H5 — multi-sensor evidence, not “hot springs = faults”

The official [USGS Nevada play-fairway report](https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and)
describes structural, gravity, magnetic, resistivity, thermal and geochemical evidence
in Gabbs Valley, followed by temperature-gradient drilling. This demonstrates why
independent evidence matters, not that any single magnetic low proves a vent.

Proposed experiment: separate surface-scarp and buried-structure experts; orientation
agreement of gravity/magnetic gradients; geophysical context from existing bands first
(no speculative data download required). Compare to shuffled orientations and single
sensor arms on the same folds. Add heat flow/electrical conductance only after source
version, units, CRS, coverage and license are verified. Coarse priors should not erase
faults in thermally quiet regions: the competition asks for **all faults**.

## H6 — acquisition geometry as a confounder

USGS specifies 200 m east–west flight lines in Area 1, 400 m in Area 2; four acquisition
blocks; variable terrain clearance. Those metadata justify a new falsifiable hypothesis:
models may learn flight-line texture or survey seams rather than faults. Hold out whole
blocks and measure directional spectral artifacts. Include flight-height/resolution
quality where obtainable. Avoid an unconditional east–west suppression rule: real
faults can align with survey lines. This is not yet tested.

## H7 — incomplete-label learning

The sponsor explicitly says known labels are incomplete and potentially inaccurate.
Treat unlabeled pixels as uncertain rather than confirmed negatives. Proposed
positive-unlabeled bagging and label-dropout experiments need fixed seeds, class-prior
sensitivity and training-only normalization. Existing pixel-random AUC is a debugging
monitor. It is not an unbiased estimate of unmapped-fault discovery.

## Rights and dead links

- GeoDAWN USGS page explicitly marks CC0 1.0. Preserve attribution, DOI, original
  resolution, acquisition metadata, byte hash and version on any ingested derivative.
- Other publicly readable papers/datasets are not automatically license-approved.
  Download/access success is not a rights determination.
- GDR 1391 and 1591 returned “No submission found” in direct retrieval. Search indexing
  for 1591 disagrees with direct access; prefer the verified USGS release instead.
- Dropbox URLs are **user-provided mirrors**, not independently verified sponsor URLs.
  Team-manifest hash agreement is reproducibility, not proof of official provenance.
- No claim is made that every scientific source or historical statement in inherited
  documents has been freshly authenticated. Current corrections supersede them.
