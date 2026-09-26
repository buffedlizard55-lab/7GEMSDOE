# Session 5 research — overlooked data, geothermal science, final-round strategy

Labels: **[official]** from the organiser/USGS/DOE/university source linked;
**[literature]** peer-reviewed or proceedings; **[measured]** computed in this
repo (script named); **[inference]** our reasoning, open to challenge.
Retrieved 2026-09-26 unless stated. Every numbered source was opened with the
page tool or returned by web search this session; quotes below are verbatim
excerpts for manual re-check.

## 0. Why this session exists

Session 4 built a region-wide lidar scarp pipeline and a decisive H1 upload
candidate, but the H1 upload has not scored yet (uploading needs the
participant's DrivenData session). Session 5 therefore works the rest of the
session-4 backlog that does NOT need the H1 score, and answers the standing
brief: distinct, contrarian-but-scientific strategies to beat 0.3049, grounded
in overlooked free official data. No leaderboard feedback was used to select
anything this session; the v1 test stays decisive.

## 1. New verified sources (for manual review)

| # | Claim used | Label | Source |
|---|---|---|---|
| S1 | GeoDAWN release holds magnetic AND radiometric grids + line data + ternary map + contractor report (DOI 10.5066/P93LGLVQ, Glen & Earney 2024) | [official] | [ScienceBase 657e1d85d34e23d3533209f7](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) · [USGS data page](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) |
| S2 | "aeroradiometric and aeromagnetic data ... provide key information on surface geology and soil composition, and subsurface structure and geology, respectively" | [official] | [GDR 1591](https://gdr.openei.org/submissions/1591) (same sentence on the USGS page) |
| S3 | The 19-band training stack contains NO radiometric band (verified from band tags) | [measured] | `training_features.tif` band tags (`knowledge/02_data_sources.md`) |
| S4 | Radiometric methods "estimate relative amounts of potassium (K), uranium (U), and thorium (Th) in the upper 0.5-1 meter of Earth's crust" | [official] | [USGS ScienceBase radiometric summary](https://www.sciencebase.gov/catalog/item/53f59ad8e4b09d12e0e845cc) |
| S5 | Reference solution = U-Net + Monte-Carlo CV (Prof. Lipor); repo committed Jun 2026 | [official] | [drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution) |
| S6 | Among ~250 categorized Great Basin geothermal fields: step-overs ~32%, terminations 25%, major range-front faults 1%; systems "most abundant ... within and directly northeast of the Walker Lane"; loci "largely correlate with regions of higher strain rates, as derived from GPS" | [literature] | [Faulds & Hinz 2015, OSTI 1724082](https://www.osti.gov/servlets/purl/1724082) |
| S7 | Step-overs host ~47% of producing Nevada systems (Faulds et al. 2021a); permeability rises in interaction zones via complexity, fracture density, breccia vs gouge, stress concentrations | [literature] | [Giddens, SGW 2025](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf) citing Faulds et al. |
| S8 | Most productive upflow "may be confined to narrow conduits, perhaps tens to hundreds of meters wide, along a single" fault; method uses stress state + intersections/terminations | [literature] | [Siler et al. 2019, OSTI 1613266](https://www.osti.gov/pages/servlets/purl/1613266) |
| S9 | INGENIOUS compilation (GDR 1391, doi 10.15121/1881483): 2 m temperature probes, wells/springs temp+chemistry, volcanics, paleo-geothermal features, heat flow, MT conductance, slip/dilation tendency, earthquake density | [official] | [GDR 1391](https://gdr.openei.org/submissions/1391) · [data.gov record](https://catalog.data.gov/dataset/ingenious-great-basin-regional-dataset-compilation) |
| S10 | Quaternary Faults v1/v2 shapefiles in INGENIOUS "supersede" each other; attributes "conform to USGS Qfault Database" | [official] | [GDR 1391](https://gdr.openei.org/submissions/1391) |
| S11 | NBMG free geospatial datasets via Open Data; published-map GIS packages "generally NOT available for free" (license flag) | [official] | [NBMG Maps & Data](https://nbmg.unr.edu/Maps&Data/index.html) |
| S12 | NBMG geothermal GIS downloads (projection documented) + GBCGE Subsurface Database Explorer for wells/springs point data | [official] | [NBMG geothermal data](https://nbmg.unr.edu/geothermal/Data.html) · [GBCGE maps & data](https://gbcge.org/mapsdata/) |
| S13 | TLS-geothermics group maps Quaternary faults with deep learning on elevation/slope/satellite (organiser-cited Hermant et al. 2025 lineage; Mattéo et al. 2021 JGR) | [literature] | [TLS publications](https://www.tls-geothermics.com/scientific-publications/) · organiser About page |
| S14 | Same single submission scored in both rounds; experts review every team's predictions to expand labels for the $250k final | [official] | [Problem page §competition-structure](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#competition-structure) |
| S15 | "You may use the provided set of faults for training ... evaluated ... predicting faults contained in a newly labeled, private set" | [official] | [Competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) |

## 2. Overlooked-data audit (free, official, not in the 19-band stack)

Ranked by expected discovery value per engineering day. "Overlooked" means:
absent from `training_features.tif` AND (to our knowledge) absent from all
seven scored group files' documented inputs.

| Rank | Data | Why it can find faults the bands miss | Access path | Status here |
|---|---|---|---|---|
| 1 | GeoDAWN radiometrics K/Th/U/TC (S1-S4) | Same survey, same flights as the magnetic bands; faults offset lithology and focus alteration; K anomalies trace hydrothermal clay, U mobility traces fluid pathways; edges in ternary space are independent of magnetic edges | ScienceBase item JSON → grid GeoTIFFs (runner) | **H9; `scripts/geodawn_rad.py` + workflow ready, fail-closed** |
| 2 | QFFDB mapped_scale / certainty (session-4 citation) | Directly tests H2 (coarse/inferred traces = re-mapping yield); also de-weights "already well-mapped" ground | Qfaults_GIS.zip (runner) | **`scripts/qfaults_prior.py` + workflow ready, fail-closed** |
| 3 | INGENIOUS wells/springs temp+chemistry, 2 m probes, paleo features (S9) | Independent geothermal observations for the H8 stratification test (do new faults concentrate near geothermal evidence?) | GDR 1391 zips (runner) | Documented; job not yet written |
| 4 | INGENIOUS heat flow, MT conductance, thermal conductivity (S9) | Physical priors for blind systems; conductance may differ from band-17 cond_surf in resolution/lineage | GDR 1391 / linked pages (runner) | Documented; lineage to verify |
| 5 | NBMG/GBCGE subsurface point data (S12) | Denser Nevada well/spring coverage than INGENIOUS alone | Open Data / explorer (runner) | Documented |
| 6 | Sentinel-2 / Landsat optical + thermal | Lineaments, alteration (clay/iron), thermal anomalies; Mattéo 2021 lineage (S13) shows CNNs transfer from optical+topo | Copernicus/USGS (runner) | Documented |
| 7 | Earthquake catalogue with mechanisms (ANSS ComCat) | Bands 10/16 are coarse density/distance; focal mechanisms + swarms resolve active strands | ComCat API (runner) | Documented |
| 8 | NHD hydrology + TIGER/OSM roads | FP controls for lidar (channels, roads), not discovery signals | Public (runner; check OSM licence) | Partially local (cross_max audit) |
| 9 | Lake Lahontan shoreline maps | Paleo-shoreline FP control for lidar steps at constant elevation | Literature/NBMG (runner) | Documented (session 4) |
| 10 | GeoDAWN flight-line (profile) data | Along-line gradients beat gridded bands for narrow dykes/faults; micro-levelling artefacts check | ScienceBase zips (runner) | Documented |

Deliberately EXCLUDED as discovery features: INGENIOUS slip/dilation
tendency and Quaternary Faults v1/v2 (S10) — both are computed from the same
Quaternary compilation as the training labels, so they leak catalogue
geometry and cannot by construction find unmapped faults. Using them would
repeat the catalogue-fitting trap the rules penalise (S14, S15).

## 3. Geothermal science relevant to fault discovery (not vent hunting)

The competition scores FAULTS, not vents or temperature. Geothermal
literature matters only where it predicts WHERE unmapped faults are:

* **Interaction zones, not range fronts (S6, S7):** 32% step-overs, 25%
  terminations, 1% major range fronts. New expert-mapped faults should
  disproportionately be SECONDARY strands (splays, relays, cross-faults) in
  interaction zones — exactly the strands a coarse catalogue omits. This
  sharpens H3's rejection: along-strike continuation of the MAIN trace
  failed, but short cross-connecting segments between overlapping strands
  were never tested (new H10).
* **Narrow conduits (S8):** upflow in conduits tens-to-hundreds of metres
  wide keeps the thin-emission rule (1 px ridges) even for the geothermal
 -motivated truth subset.
* **Strain-rate belts (S6):** geothermal loci follow GPS strain-rate highs.
  Bands 4/7/8 already carry geodetic strain — a cheap corroborating prior,
  not new data. A stratified test (emission skill in high- vs low-strain
  ground) is pre-registered as H11.
* **Walker Lane transition (S6):** "northwestward termination of the Walker
  Lane and diffusion" of extension concentrates activity. The NE quadrant —
  our largest lidar gap (47%, `lidar_gaps.json`) — sits in this transition.
  Gap-filling there is doubly prioritised.

## 4. Hypothesis register — session 5 additions

| ID | Hypothesis | Status / test |
|---|---|---|
| H9 | Radiometric edges (K/Th/U/TC from the same GeoDAWN flights) localise faults independently of the 19 bands | **Open.** Runner job ready; test = pre-registered geographic skill of radiometric-lineament arm vs bands19 (same protocol as `lidar_experiment.json`) |
| H10 | New faults are short cross-connecting segments in step-over / termination interaction zones, not along-strike continuations | Open. Build interaction-zone mask from catalogue geometry (strand overlap + tips); test matched-mass emission inside vs outside |
| H11 | New-fault density follows geodetic strain-rate highs (bands 4/7/8 corroboration) | Open. Stratified skill test; no new data needed |
| H12 | Final-round expert review rewards multi-sensor-verifiable lineaments over metric-optimal dot patterns | Strategic (S14). Emission rule: every emitted pixel must sit on ≥2 independent sensor expressions (e.g. lidar step + magnetic edge). Testable only in the final round; sides with the $250k pool |
| H2 | Mapping-scale deficit (coarse/inferred traces = re-mapping yield) | **Runner job ready** (`qfaults_prior.py`); test = matched emission near coarse vs fine traces |

H1 (lidar scarps) still awaits its leaderboard test. H3 stays rejected as
primary. H4 (SGMC gap) stays queued as the cheap single-upload alternative.
H5 (piedmont bias) now has a tension flag: the v1 emission avoids low relief
(6.5% of emitted on 32.8% of footprint, `lidar_fp_audit.json`) — either the
model correctly ignores basin floors, or it misses subtle piedmont scarps.
H6 (orientation prior) untested. H7 (channel/road/shoreline FPs) partially
measured: loops are minor (483 hole px), but 72% of emitted pixels are
cross-slope dominant — the channel-bank question is now the top FP control.

## 5. Distinct strategies to beat 0.3049 (contrarian but grounded)

Forensics recap (`scored_files_analysis.json`): the leader needs ~4-5x
random coverage at 1-2% density; our best is ~1.9x; blob emission scored
below random; the organiser-like baseline (0.1847) already beats every group
file — catalogue-fitting with a U-Net is the floor, not the ceiling.

1. **Verifiability-first emission (H12).** Optimise for the $250k final
   round, not the $50k initial: emit only thin lineaments with ≥2
   independent sensor expressions. Dot-optimal-for-fixed-truth patterns
   (GEMSDOE3 pindrop) maximise private-set DTI under a coverage model but
   give experts nothing coherent to verify; a coherent scarp+edge
   lineament can ENTER the expanded truth set. Contrarian: deliberately
   sacrifice some public-DTI optimality for final-round label creation.
2. **Radiometric second opinion (H9).** Nobody in the group has used the
   survey's own gamma-ray grids. K/Th/U edges see lithology/alteration the
   magnetics miss; the ternary-gradient lineament field is orthogonal to
   both the 19 bands and the lidar.
3. **Interaction-zone cross-segments (H10).** Stop extending main traces
   (H3 failed); emit short connectors between overlapping strands and
   horsetail splays at tips — the strands catalogues omit and geothermal
   science (S6-S8) says matter.
4. **Scale-deficit targeting (H2).** Concentrate emission where the
   catalogue is weakest (1:250k/inferred ground) instead of where models
   are most confident (usually near well-mapped faults — the 6GEMSDOE
   failure mode: fill 0.32 at 1 px, score 0.0286).
5. **Strain-belt weighting (H11).** Up-weight high geodetic-strain ground
   within the emission budget; test stratified skill before committing.
6. **Gap-first lidar completion.** 24.6% of the footprint (47% of the NE
   quadrant, in the Walker Lane transition) has no lidar; 12,523 catalogue
   pixels (20.5%) sit in gaps. Any lidar-only policy caps recall at ~75%.

## 6. Irregularities / flags (carried + new)

* Carried: SDCF9 0.1563-from-unknown-file; five accounts vs per-entity
  budget; GEMSDOE2 pairing unverified; deadline-time conflict (plan Dec 3
  22:00 UTC); sample-submission == labels; missing magnetic-source-depth
  band. See session-4 review.
* New: NBMG published-map GIS packages are generally NOT free (S11) — any
  SGMC/NBMG vector use must verify the per-asset licence, or restrict to
  USGS-published maps NBMG redistributes for free.
* New: radiometric grids overlap the magnetic survey's acquisition blocks;
  block-aware normalisation (session-2 GeoDAWN finding: 200 m vs 400 m
  line spacing) applies to radiometrics too.
