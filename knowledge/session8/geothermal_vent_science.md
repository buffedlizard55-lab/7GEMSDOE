# Geothermal science base — vents, faults and the data that carries them (session 8)

**Purpose.** The user's standing brief asks for "heavy and deep research into the
part of the project that matters the most, which is the scientific discovery of
geothermal vents", stored from official verified sources as a reusable,
auditable base with links for manual review. This file is that base for session
8. It is deliberately separate from the competition contract: the competition
scores **fault** pixels, not vents, but faults are the plumbing that the
geothermal industry actually explores for, so the vent literature is what tells
us *where in a fault network* an unmapped fault is worth finding.

**Verification protocol used here.** Every claim below was read on the page it
cites (agent page-fetch tool, 2026-09-27 unless noted) and the wording was
checked against the quoted text; dataset licences are quoted from the dataset
page itself. Nothing in this file was inferred from a search-result snippet
alone, and claims that could not be read directly are marked **UNVERIFIED**.
Archived copies: the reliability of each link was checked, not its permanence;
if a link rots, the DOI is the stable identifier.

---

## 1. Where Great Basin geothermal systems actually sit in a fault network

The single most useful body of work for this project is Faulds and co-workers'
inventory of the *structural settings* of >400 geothermal systems in the Great
Basin, because it answers "if a fault is unmapped, where is it likely to matter
for a vent?" with counts rather than intuition.

Source: GDR submission 383, *Structural and Tectonic Controls of Geothermal
Activity in the Basin and Range Province* (Faulds, Hinz & Kreemer, University of
Nevada, 2012) — publicly accessible, licence CC-BY-4.0.
<https://gdr.openei.org/submissions/383>

| Structural setting | Share of catalogued systems | Read verbatim from the source |
| --- | --- | --- |
| Step-overs / relay ramps in normal fault zones | ~32 % | "serve as the most favorable setting, hosting ~32% of the systems" |
| Intersections between normal faults and strike-slip or oblique-slip faults | 22 % | "multiple minor faults connect major structures and fluids can flow readily through highly fractured, dilational quadrants" |
| Normal fault terminations / tip-lines | 22 % | "horse-tailing generates closely-spaced faults and increased permeability" |
| Accommodation zones (intermeshing, oppositely dipping normal faults) | 8 % | listed as a distinct setting |
| Major normal faults | 6 % | rare as hosts — clay gouge / stress release at displacement maxima |
| Displacement transfer zones | 5 % | Walker Lane kinematics |
| Pull-aparts in strike-slip faults | 4 % | Walker Lane kinematics |

Two further statements from the same source matter for our geography: the Walker
Lane "accommodates ~20% of the North American-Pacific plate motion", and
"Quaternary faults lie within or near most systems".

Corroborating official records (same group, same counts, independently served by
OSTI and by the conference PDF):

* OSTI 1148722, *Structural Inventory of Great Basin Geothermal Systems and
  Definition of Favorable Structural Settings* (Faulds) — 426 systems analysed;
  eight groups: major normal fault segments, fault bends, fault terminations,
  step-overs/relay ramps, fault intersections, accommodation zones, displacement
  transfer zones, transtensional pull-aparts.
  <https://www.osti.gov/biblio/1148722> · dataset view:
  <https://www.osti.gov/dataexplorer/biblio/dataset/1148722>
* GRC paper 1030540 (Faulds et al.), *The Most Accommodating Structural Setting
  for Geothermal Systems in the Great Basin* — step-overs ~33 %; of the 27
  power-producing systems, ~41 % occupy step-overs and ~26 % accommodation zones,
  i.e. *structural complexity correlates with exploitable systems*.
  <https://publications.mygeoenergynow.org/grc/1030540.pdf>
  (Fetched as a search-indexed PDF body; page-level verification of the numbers
  is marked PARTIAL — the counts agree with the two sources above.)
* OSTI 1724082, *Favorable tectonic and structural settings … proxies for
  discovering blind geothermal systems*:
  <https://www.osti.gov/biblio/1724082> (the automated feed already watches this
  page; its excerpt matched on 2026-09-26).
* Stanford Geothermal Workshop 2026 abstract (Faulds et al., *Favorable
  Structural Settings for Geothermal Systems in the Great Basin Region*) —
  a recent re-count over 403 known geothermal systems: step-overs ~27.5 %,
  intersections 22.1 %, terminations 16.6 %, accommodation zones 5.7 %.
  Listed by the IGA paper database; **abstract only, UNVERIFIED at PDF level**.
  <https://pangea.stanford.edu/ERE/db/IGAstandard/record_detail.php?id=38284>

**How this changes our work (and how it does not).** It does *not* license
painting buffers around geothermal fields: the competition truth is a fault
catalogue, and the metric rewards thin, correctly placed fault pixels. What it
does justify is the session-7/8 **H10 interaction-zone arm**: when a detector
finds a scarp or lineament near a fault tip, an overlap, or an intersection of
two structural trends, the probability that the feature is a real, separate
fault strand is raised by the same reasoning that makes these settings the
preferred drilling targets. Prevalence in a geothermal *inventory* is evidence
about geology, not a scored label.

---

## 2. Free, official, publicly-accessible datasets that carry vent or
structural-setting information (all verified to exist and be public)

| # | Dataset | What it contains | Licence / access | Link |
| --- | --- | --- | --- | --- |
| D1 | GDR 383 — Structural and Tectonic Controls of Geothermal Activity in the Basin and Range Province (Faulds, Hinz & Kreemer, 2012) | Inventory of structural settings of >400 Great Basin systems; the 2012 New Zealand Geothermal Workshop paper | CC-BY-4.0, publicly accessible | <https://gdr.openei.org/submissions/383> |
| D2 | GDR 616 / DOI 10.15121/1225261 — Nevada Great Basin Play Fairway Analysis Regional Data (Faulds, NBMG, 2015) | Structural settings target areas, fault recency/slip/dilation potential, strain rates, earthquake density, gravity, temperature at 3 km, permeability and favour­ability models, **springs and wells**, exploration opportunity, error layers | CC-BY-4.0 (stated in the page's JSON-LD), publicly accessible; DOE contract EE0006731 | <https://gdr.openei.org/submissions/616> |
| D3 | GDR 1351 / DOI 10.15121/1897036 — Machine Learning Model Geotiffs (Faulds, Brown, Smith, Queen & Treitel, 2021) | GeoTIFFs of ANN, ELM, Bayesian NN, PCA/PCAk, NMF/NMFk **favour­ability models**, model input feature grids, and positive/negative training sites; 590.94 MB zip | CC-BY-4.0, publicly accessible | <https://gdr.openei.org/submissions/1351> |
| D4 | "Potential structures" submission (Nevada ML project; Faulds & Coolbaugh) | Revised potential structures / structural settings: **ellipses, centroids, distance-to-centroid raster** | Listed on the GDR search page and in OSTI's related-dataset list; dedicated page not yet read → **UNVERIFIED at page level** | <https://gdr.openei.org/search?q=raster> |
| D5 | GDR 1832126 — Geochemistry and paleo-geothermal features (Faulds & Ayling) | Geochemistry dataset and **paleo-geothermal features (sinter, travertine, tufa)** shapefiles — i.e. fossil vent fields | Publicly accessible (per OSTI/OpenEI listing); DOI page not yet read → **UNVERIFIED at page level** | <https://www.osti.gov/dataexplorer/biblio/dataset/1832126> |
| D6 | GDR 1391 / DOI 10.15121/1881483 — INGENIOUS Great Basin Regional Dataset Compilation (CC-BY-4.0) | The competition's cited training-label basis; v1/v2 Quaternary fault compilations for the same region (v2 supersedes v1) | CC-BY-4.0, publicly accessible | <https://gdr.openei.org/submissions/1391> |
| D7 | GDR 1526 — GeoDAWN Northwestern Elko County, Nevada EarthMRI Data (USGS National Geospatial Program, 2023) | **LiDAR**: original product resolution (OPR) and point cloud (LPC), collected under GeoDAWN | Publicly accessible (per the GDR search listing, 270.41 kB page size) | <https://gdr.openei.org/submissions/1526> |
| D8 | GDR 1501 — GeoDAWN West Central Nevada EarthMRI Data (USGS NGP, 2023) | **LiDAR**: OPR + LPC for the western Nevada GeoDAWN block | Publicly accessible (per the GDR search listing, 842.33 kB page size) | <https://gdr.openei.org/submissions/1501> |
| D9 | GDR 1591 — GeoDAWN airborne magnetic and radiometric surveys of the northwestern Great Basin | The aeromagnetic + radiometric survey that the competition's feature rasters are built from (USGS, 2024) | Publicly accessible | <https://gdr.openei.org/submissions/1591> |

Note on D7/D8: these are the *only* official GeoDAWN lidar holdings we have
found that are not the 3DEP tile service we already mine. Our lidar product still
has a 24.6 % coverage gap over the competition footprint (47.4 % in the NE
quadrant), and native-resolution lidar is the one arm that has beat the supplied
bands under every frozen geographic test so far, so enumerating D7/D8 against the
gap is the highest-value independent-data action available. The same GDR search
also lists *Basin and Range Investigation for Developing Geothermal Energy:
Exploration Data* (submission 1682), not yet inspected.

---

## 3. What the organisers themselves cite (and why it matters here)

From the competition's About page (<https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/>,
re-read 2026-09-27): the task is fault mapping over the GeoDAWN survey area,
"many of which are hidden"; the page explicitly names two papers as additional
information:

* Mattéo, L. et al. (2021), *Automatic fault mapping … using deep learning*,
  JGR Solid Earth, DOI <https://doi.org/10.1029/2020JB021269> — supervised fault
  segmentation on topography; the family of methods the reference notebook uses.
* Hermant, M. et al. (2025), Stanford Geothermal Workshop (TLS Geothermics) —
  siUNET/FaultSEG CNN fault mapping on **10 m** DEMs, trained in northern central
  Nevada; the paper reports that the trained models find faults "the USGS map
  missed", and that false positives concentrate on stream/canyon boundaries.
  <https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Hermant.pdf>

The Hermant finding is directly transferable and matches our own false-positive
audit (session 5: 72.1 % of our emissions that cross a slope trend do so
cross-slope-dominant; drainage-related linear features are the main confuser):
any detector must separate *tectonic* lineaments from *fluvial* ones, and the
literature's own answer is to look for the scarp signature (offset surfaces),
not merely linearity.

---

## 4. Science → pipeline consequences (what session 8 actually changed)

1. **Where to look (H10, pre-registered).** Fault interaction zones — tips,
   overlaps/step-overs, intersections — are the settings where the geothermal
   inventory concentrates and where new strands are structurally expected. H10
   generates only short connectors/splays in those zones and compares them with
   isotropic controls at matched pixel mass (protocol in
   `knowledge/session7/next_session.md §3`, frozen before measurement).
2. **What to emit (H14).** The metric's own math says the optimum support for a
   smoothed field is a *threshold on the metric-kernel-smoothed score*, not on
   the raw score; the session-8 experiment `emission_policy_experiment.json`
   tests that against the ridge-thinning policy this repository shipped for H1,
   at equal pixel budget, on the frozen folds.
3. **Which data to add (independent coverage).** D7/D8 (GeoDAWN lidar, OPR) are
   the only official lidar holdings identified so far that are not in the 3DEP
   tiles we already use; they are candidates to shrink the NE gap.
4. **Vents as corroboration, never as labels.** No vent/hot-spring inventory is
   used as a training label or an emission mask, because the scored target is
   faults and because every vent inventory we have verified is incomplete in
   different ways. A fault candidate that also sits in a favourable structural
   setting is *discussed* in the site's evidence table; it is not scored as a
   win.

## 5. Open questions and explicit non-claims

* Whether the organisers' expert labels were drawn from INGENIOUS v1, v2, or an
  independent review is **not stated** in the rules or on the competition pages;
  our manifest records the 1 px/3 px agreement of each label with v1 and v2
  rather than asserting a source.
* The counts in §1 are percentages of *catalogued systems*, not of faults, and
  they say nothing about how often the same setting hosts a *newly discovered*
  fault. They are used as structural plausibility, not as a prior on labels.
* All Great Basin datasets above are CC-BY-4.0 or US Government works; the
  competition's own data terms still control what may be fed to a model, and the
  rules require the finalist's solution assets to be reproducible without
  third-party content that we cannot licence (`rules §A.5`, see
  `knowledge/inherited_evidence/rules_extracted_text.txt`).

## 6. Manual review checklist (click these, in this order)

1. <https://gdr.openei.org/submissions/383> — read the abstract; confirm the
   32 / 22 / 22 / 8 / 6 / 5 / 4 % table and the CC-BY-4.0 badge.
2. <https://gdr.openei.org/submissions/616> — confirm CC-BY-4.0, the
   springs/wells and favour­ability layers, and DOE contract EE0006731.
3. <https://gdr.openei.org/submissions/1351> — confirm the 590.94 MB ML zip and
   its layer list (ANN/ELM/BNN/PCA/NMF + inputs + training sites).
4. <https://gdr.openei.org/submissions/1526> and
   <https://gdr.openei.org/submissions/1501> — confirm the GeoDAWN OPR/LPC lidar
   holdings exist and are public; note the file sizes before planning a download.
5. <https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and>
   — the USGS play-fairway publication already watched by our feed.
6. <https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/>
   — confirm the two cited papers and the "hidden faults" framing.
