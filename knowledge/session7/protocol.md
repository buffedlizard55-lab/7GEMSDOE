# Session 7 protocol — radiometric lineaments and acquisition-bias controls

**Frozen before the H9b measurement on 2026-09-26 UTC.** This protocol does
not authorize a competition upload and does not alter the session-4 H1 decision
tree. The H1 lidar file remains unscored.

## Evidence basis (opened for this session)

Labels are explicit: **[official]** means an organiser or USGS page;
**[measured]** means this repository's output; **[inference]** means a testable
reasoning step, not an established fact.

1. **[official] Competition target and metric.** The organisers state that the
   private test set contains newly expert-labelled faults absent from the
   existing USGS database, and that scoring uses the distance-weighted Tversky
   index. [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
2. **[official] Current public reference point.** Direct retrieval of the
   official leaderboard on 2026-09-26 showed DARD first at 0.3049 and the
   organiser account at 0.1847. Scores are dynamic; the repository feed is the
   timestamped record. [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
3. **[official] Survey design and confounding.** The USGS GeoDAWN release says
   the survey has four north-to-south acquisition blocks (Winnemucca, Fallon,
   Hawthorne, Tonopah), two overlapping survey areas, different line spacing,
   flight-height targets and aircraft. It says the contractor corrected
   radiometrics for aircraft/cosmic background, radon, Compton scattering and
   altitude, while warning actual terrain clearance varies. These facts make a
   future acquisition-block holdout necessary.
   [ScienceBase item / DOI 10.5066/P93LGLVQ](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) ·
   [USGS data catalogue](https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7)
4. **[official] Scientific scope.** USGS describes GeoDAWN aeroradiometrics as
   information about surface geology and soil composition, and magnetics as
   information about subsurface structure/geology. A USGS project page says the
   combined topographic/geophysical data should help fault identification; it
   does not say every radiometric edge is a fault.
   [USGS GeoDAWN project page](https://www.usgs.gov/media/images/geodawn-geoscience-data-acquisition-western-nevada)
5. **[official] Alteration rationale, with scope limit.** A 2025 USGS conference
   record reports that K, K/Th and K/U enhancements mapped known hydrothermal
   alteration in a Montana porphyry setting. That supports testing radiometric
   spatial structure, but it is not Great Basin fault-validation evidence.
   [USGS publication record](https://www.usgs.gov/publications/airborne-radiometric-data-map-alteration-porphyry-copper-systems-elkhorn-district-mt)
6. **[official/literature] Structural prior.** An OSTI-hosted Great Basin study
   reports step-overs/relay ramps, terminations and intersections as common
   geothermal settings, with major range-front faults rare in its categorized
   systems. This motivates H10 later; geothermal occurrence is not the GEMS
   raster target.
   [Faulds & Hinz 2015, OSTI 1724082](https://www.osti.gov/servlets/purl/1724082)

## H9b — pre-registered radiometric-lineament test

**[measured, pending at freeze time]** `scripts/radiometric_lineament_experiment.py`
will compare these arms on exactly the same valid pixels, training samples,
learner, five H4 geographic folds and 1 km test buffers:

* `bands19`: supplied competition bands;
* `rad_raw`: compact K/Th/U/total-count values;
* `rad_lineament`: `rad_raw` plus fixed mask-safe derivatives at 1 and 3
  competition pixels (nominally 100 m and 300 m).

The originally listed optional `bands_plus_lineament` diagnostic was removed
after the first process was killed during pre-measurement feature construction:
retaining the 19 float32 bands and all derivative arrays simultaneously exceeded
the sandbox memory limit. No fold/model result had been printed or written.
The three primary arms are now loaded sequentially. This resource amendment does
not change their features, folds, matched samples, primary statistic, controls or
promotion rule, and it avoids pretending that an unmeasured fused arm succeeded.

The representation is implemented and unit-tested in
`scripts/radiometric_features.py`. It uses normalised convolution around
missing survey cells, suppresses the one-cell derivative rim, and measures
per-channel gradients/absolute Laplacian plus multi-channel edge strength,
orientation/coherence and broad residuals. The scales and feature list are
fixed before model execution.

**Deliberate exclusion:** the compact product independently percentile-quantises
each channel. K/Th, K/U and similar ratios of those bytes would not equal
ratios of the source physical concentrations, so H9b does not calculate them.
A later source-grid experiment may use physically meaningful ratios only if it
preserves verified source units and train-only preprocessing.

**Primary promotion rule:** at both 1% and 2% emission density,
`rad_lineament` must (a) beat both `bands19` and `rad_raw` in pooled
official-kernel coverage skill relative to exact random coverage and (b) beat
the stronger comparator in at least four of five folds. Ridge-NMS is secondary.
No submission is generated even if this rule passes.

**Null/control:** `rad_raw` tests whether derivatives add value; `bands19`
tests whether the independent source adds value beyond the supplied stack.
Identical samples/support prevent a coverage advantage. Catalogue truth still
cannot test transfer to hidden faults.

## Next bias-control gate

Before H9 can influence a candidate policy, isolate the four official
acquisition blocks using observed official outline/flight-path geometry. Do not
invent boundaries from latitude or the figure. A runner may inspect the
official archives, record checksums/schema and fail closed if an acquisition
block cannot be assigned unambiguously. Leave-one-block-out performance is a
stronger test than the present 5x5 folds because survey hardware/specifications
changed by block/area.

## Stop conditions

* Do not package H9b or any H1 follow-up before the H1 score is attributable.
* Do not call catalogue localisation hidden-fault discovery or a leaderboard
  estimate.
* Do not infer source physical concentrations from uint8 ranks.
* Do not call a radiometric/lidar line a verified fault or geothermal vent.
* Preserve negative results and source/acquisition irregularities.
