# H9c pre-registration — official ratios omitted from the supplied stack

**Frozen before product retrieval and measurement on 2026-09-26 UTC.** H9b's
multiscale derivatives failed their frozen promotion rule. Inspection of the
already checksum-verified official archive member list then exposed a distinct,
previously unused test: contractor-generated physical radioelement ratio grids
and an upward-continued magnetic grid.

## Source fact and non-overlap audit

The official [GeoDAWN ReadMe](https://www.sciencebase.gov/catalog/file/get/657e1d85d34e23d3533209f7?name=GeoDAWN_ReadMe.pdf)
defines corrected K (%K), Th (ppm), U (ppm), and `thk_ratio` (Th/K), `uk_ratio`
(U/K), and `uth_ratio` (U/Th) in the radiometric profile data. The
checksum-verified Area 1/2 TIFF archives observed in
`external/geodawn_rad/geodawn_rad.json` contain exact members for `thk`, `uk`,
`uth`, and `upcont_tmi150`. None of those four names/semantics appears in the
19 supplied-band descriptions measured from `training_features.tif`.

This matters because H9b correctly refused to divide independently quantised
K/Th/U bytes: those quotients would not be physical ratios. H9c retrieves the
contractor's ratio grids calculated upstream from physical measurements. The
compact H9c product will again store only robust uint8 ranks, so it preserves
ordering, not physical units. `upcont_tmi150` is a transform of an existing
magnetic sensor, not independent evidence; it is a diagnostic arm, not the H9c
primary arm.

Primary source: [USGS ScienceBase GeoDAWN release, DOI 10.5066/P93LGLVQ](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7).

## Frozen arms and protocol

All arms use the exact H9b common support, five 5×5-block geographic folds,
1 km test buffer, sampled indices, learner and top-f official-kernel statistic:

* `bands19` — supplied baseline;
* `rad_raw` — K/Th/U/total count compact ranks;
* `ratios3` — contractor Th/K, U/K, U/Th compact ranks (**primary**);
* `up150` — upward-continued TMI only (diagnostic);
* `extensions4` — ratios plus up150 (diagnostic).

No derivative expansion is used: H9b found that fixed 100/300 m derivative
features underperformed raw channels in all five folds. This is one planned
physical-source ablation, not a post-hoc edge-scale sweep.

**Promotion rule:** `ratios3` must exceed both `bands19` and `rad_raw` pooled at
1% and 2%, and beat the stronger comparator in at least four of five folds at
both densities. Ridge-NMS is secondary. `up150`/`extensions4` cannot pass the
ratio promotion rule or become submission policies in this test.

## Controls, interpretation and stop conditions

* Identical support/samples prevent source coverage from giving one arm an
  easier denominator.
* Catalogue labels are not hidden faults; passing would justify acquisition-
  block validation, not a leaderboard claim.
* Ratio anomalies may represent lithology, soils, moisture or alteration and
  are not fault/vent verification.
* Upward continuation can suppress shallow magnetic noise but cannot create an
  independent sensor.
* The two survey areas/four acquisition blocks have different specifications;
  leave-one-block-out remains mandatory before candidate influence.
* No submission is built. H1 remains the only pending decisive upload.
