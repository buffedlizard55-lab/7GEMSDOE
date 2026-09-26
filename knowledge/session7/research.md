# Session 7 research — radiometric falsification and the next winning path

**Date:** 2026-09-26 UTC. Labels: **[official]** organiser/USGS/DOE;
**[measured]** reproducible output in this repo; **[inference]** a testable
strategy, not a fact. This is not a claim of a new fault, geothermal vent or
leaderboard gain.

## 1. Current position and target

* **[official]** Direct retrieval of the public leaderboard still put DARD first
  at **0.3049**. The validated automated feed has 109 ranks at
  2026-09-26 22:59:17 UTC. The known group best remains **0.1563**. See
  `knowledge/feed.json` and the [official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
* **[official]** The target is newly expert-labelled geological faults absent
  from the existing USGS fault database; the metric is distance-weighted
  Tversky. [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
* **[measured]** H1 lidar remains the only unscored decisive upload. H9b/H9c
  generated no submission and failed their frozen geographic promotion rules.

## 2. New official-source facts checked this session

| ID | Verified claim | Source | Consequence |
|---|---|---|---|
| S7-1 | GeoDAWN has two overlapping survey areas and four acquisition blocks (Winnemucca, Fallon, Hawthorne, Tonopah), different flight spacing/heights and different aircraft; contractor corrections include altitude | [USGS ScienceBase DOI 10.5066/P93LGLVQ](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) | Geographic folds do not isolate hardware/specification shifts; block holdout is mandatory before an H9 feature can influence a candidate |
| S7-2 | Official radiometric profile fields include corrected K (%K), Th/U (ppm), total count and contractor Th/K, U/K, U/Th ratios | [Official GeoDAWN ReadMe](https://www.sciencebase.gov/catalog/file/get/657e1d85d34e23d3533209f7?name=GeoDAWN_ReadMe.pdf) | Test contractor ratios; do not invent ratios from independently quantised bytes |
| S7-3 | Official archives contain exact Area 1/2 TIFFs for `thk`, `uk`, `uth`, and `upcont_tmi150` | [USGS ScienceBase item](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) plus checksum-verified observed listing in `external/geodawn_rad/geodawn_rad.json` | H9c is a genuine omitted-channel test; upstream archives matched official listed size/MD5 |
| S7-4 | USGS says aeroradiometric data inform surface geology/soil composition; magnetics inform subsurface structure/geology | [USGS data catalogue](https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7) | Radiometric boundaries are indirect fault evidence and have surface confounders |
| S7-5 | A USGS 2025 conference record used K and physical K/Th, K/U enhancements to map known hydrothermal alteration in a Montana porphyry setting | [USGS publication record](https://www.usgs.gov/publications/airborne-radiometric-data-map-alteration-porphyry-copper-systems-elkhorn-district-mt) | Scientific rationale for physical ratios, but not direct Great Basin fault-transfer evidence |
| S7-6 | Great Basin study reports step-overs/relay ramps, terminations and intersections as common geothermal structural settings, while major range-front faults were rare in its categorized systems | [Faulds & Hinz 2015, OSTI 1724082](https://www.osti.gov/servlets/purl/1724082) | H10 cross-connectors remains more scientifically motivated than extending only major range fronts; geothermal occurrence is not the scored target |

## 3. H9b result — fixed lineament derivatives fail

**[measured]** `scripts/radiometric_lineament_experiment.py` tested raw
K/Th/U/total-count ranks plus 30 fixed mask-safe 100/300 m derivative features.
All arms used 5,164,300 common pixels, 60,894 catalogue positives, identical
samples, five geographic folds and 1 km buffers.

| Arm | Pooled skill at 1% | Pooled skill at 2% | Ridge-NMS at 1% | Ridge-NMS at 2% |
|---|---:|---:|---:|---:|
| bands19 | 0.734× | 0.642× | 1.033× | 0.889× |
| raw K/Th/U/TC | 0.655× | 0.611× | 0.851× | 0.769× |
| raw + lineaments | 0.565× | 0.539× | 0.770× | 0.738× |

Lineaments beat the stronger comparator in **0/5 folds at every density**;
the rule fails. The derivative expansion raised AUC in some folds while harming
top-f metric coverage—an important reminder that ranking all pixels and finding
high-value thin traces are different objectives.

The prior H9 raw screen had shown a narrow radiometric edge on the smaller
bands+lidar common footprint. H9b removes the lidar-coverage restriction and
reverses that comparison: bands19 beat raw radiometrics at 1%/2%. Thus the old
edge was **support-sensitive**, not robust independent discovery evidence.

Full machine report:
`knowledge/session7/radiometric_lineament_experiment.json`.

## 4. H9c result — official physical ratios also fail

**[measured]** The runner downloaded both official TIFF archives, matched the
ScienceBase size/MD5 records, selected exact member names, and wrote a compact
four-band product on the exact competition grid. Product SHA-256:
`a35a9c6d2a14786f…`; manifest:
`external/geodawn_extensions/geodawn_extensions.json`.

| Arm | Pooled skill at 1% | Pooled skill at 2% | Role |
|---|---:|---:|---|
| bands19 | 0.734× | 0.642× | comparator |
| raw K/Th/U/TC | 0.655× | 0.611× | comparator |
| official Th/K, U/K, U/Th | 0.663× | 0.588× | primary |
| TMI upward-continued 150 m | 0.398× | 0.396× | diagnostic |
| ratios + up150 | 0.563× | 0.540× | diagnostic |

The ratio arm beat the stronger comparator in only **1/5 folds** at 1% and
1/5 at 2%; the rule fails. It slightly exceeds raw channels pooled at 1% but
loses at 2% and never beats bands19 pooled. Ridge thinning does not reverse the
result (ratios: 0.795×/0.745× at 1%/2%; bands19: 1.033×/0.889×).

`TMI_up150` is almost redundant with supplied band 14 after compact encoding:
Pearson rank correlation **0.993329**, 70.65% exact byte agreement and mean
absolute difference 1.32 bytes across 5,164,312 pixels. This explains why it is
not independent evidence. Reproduce with `scripts/audit_extension_overlap.py`;
report: `knowledge/session7/extension_overlap.json`.

Full H9c report: `knowledge/session7/geodawn_extension_experiment.json`.

## 5. Decision — stop tuning radiometrics, protect feedback budget

**[inference]** H9 now has three negative/weak screens: raw-channel promotion
failed, fixed lineaments failed all fold comparisons, and official physical
ratios failed. More edge scales or post-hoc ratio mixtures would be multiple
comparison tuning on incomplete catalogue truth. That does not maximize P(Win).

Decision:

1. **Do not package any H9 candidate.** Preserve H9 as possible corroboration
   only after a separately discovered line exists.
2. **Get the H1 lidar score before another upload.** It is the only experiment
   with strong local geographic catalogue skill (ridge 1.81× random at 1%,
   1.47× at 2%) and the frozen decision tree already defines the response.
3. **Next score-independent experiment: H10 interaction-zone connectors.**
   Pre-register geometric cross-connector generation and matched random-tangent
   controls before measuring. Avoid direct label leakage and reserve whole fault
   systems/geography.
4. **Next independent data: gap-first lidar completion, not more radiometric
   transforms.** Lidar currently misses 24.6% of the footprint and 20.5% of
   catalogue pixels; the NE quadrant gap is 47.4%.
5. **Final-round strategy: sensor corroboration, not sensor union.** A candidate
   line should originate from an independently validated terrain/structural
   detector; radiometric agreement may annotate confidence but cannot rescue a
   weak line detector based on these results.

## 6. Irregularities and uncertainty retained

* No authenticated DrivenData session or per-file score history is available.
  H1 cannot be auto-uploaded; credentials are neither requested nor stored.
* The source ratios include physically unusual extremes (for example negative
  minimum Th/K in the observed grid). The files/checksums are verified, but
  source processing/quality flags require contractor-report review before any
  physical interpretation.
* Acquisition-block geometry is not yet rasterized. Since H9b/H9c failed, block
  validation is no longer priority work unless a future independent reason
  reopens H9.
* SDCF9's current public best 0.1563 remains unattributed to a file. Team entity
  registration and the one-final-submission rule remain manual governance
  checks, not facts inferred from account names.
* No new geological fault or geothermal vent has been field/expert verified.
