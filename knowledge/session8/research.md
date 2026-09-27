# Session 8 research — geothermal-vent science, official data, and what it changes

Scope: the user's standing brief asks for heavy deep research into the scientific
discovery of geothermal vents, stored from official verified sources as a
reusable base, with clean tables and links for manual verification. This file
collects what was verified **this session**, states the verification level of
every row, and records only the conclusions that the evidence supports. The
long-form structural-geology background from earlier sessions stays in
`knowledge/01_science_faults_geothermal.md`; source rows are mirrored into
`knowledge/sources.json` so the site can render them.

Verification legend: **[F]** = page fetched and read with the agent page-fetch
tool this session; **[S]** = search-index excerpt of the official page (not
fetched); **[M]** = measured by our own scripts from committed artifacts.

---

## 1. The single most useful scientific result: where geothermal systems sit in a fault network

Faulds and co-workers catalogued the **structural setting** of >400 Great Basin
geothermal systems (250+ assigned). The ranking is stable across three
independent official records (GDR dataset page, OSTI record, GRC paper), which
matters because it is the closest thing the literature offers to a prior on
*which fault strands* matter.

| Setting | Share of catalogued systems | Verbatim / source | Verification |
| --- | --- | --- | --- |
| Step-overs / relay ramps in normal fault zones | **~32 %** | "step-overs or relay ramps in normal fault zones serve as the most favorable setting, hosting ~32% of the systems" — [GDR 383](https://gdr.openei.org/submissions/383) | [F] |
| Intersections of normal faults with strike-slip / oblique-slip faults | **22 %** | "multiple minor faults connect major structures and fluids can flow readily through highly fractured, dilational quadrants" — [GDR 383](https://gdr.openei.org/submissions/383) | [F] |
| Normal-fault terminations / tip-lines (horse-tailing) | **22–25 %** | "horse-tailing generates closely-spaced faults and increased permeability" — [GDR 383](https://gdr.openei.org/submissions/383); 25 % in the [2014 GSA abstract](https://gsa.confex.com/gsa/2014AM/webprogram/Paper248671.html) | [F]/[S] |
| Accommodation zones (intermeshing opposite dips) | **8–9 %** | belt of intermeshing oppositely dipping normal faults | [F] |
| Major normal faults (displacement maxima) | **6 %** | rare: clay gouge + periodic stress release | [F] |
| Displacement transfer zones (Walker Lane) | **5 %** | strike-slip terminating into normal-fault arrays | [F] |
| Transtensional pull-aparts | **4 %** | Walker Lane kinematics | [F] |
| Power-producing systems | step-overs ~41 %, intersections ~26 %, accommodation ~26 % | of 27 Great Basin plants: complexity correlates with exploitability; [GRC 1030540](https://publications.mygeoenergynow.org/grc/1030540.pdf) | [S] |

Corroboration: [OSTI 1148722](https://www.osti.gov/biblio/1148722) (426 systems
analysed, eight settings) **[S]**; a 2026 Stanford Geothermal Workshop abstract
re-counts 403 known systems as step-overs ~27.5 %, intersections 22.1 %,
terminations 16.6 %, accommodation 5.7 %
([IGA record 38284](https://pangea.stanford.edu/ERE/db/IGAstandard/record_detail.php?id=38284)) **[S]**.

**Why this belongs in the submission pipeline.** It does not change what the
metric scores (fault pixels), but it changes *where a detector's weakest
predictions deserve to be trusted*: an ambiguous lineament that terminates in a
step-over, or links two overlapping fault tips, is the configuration the
regional inventory says hosts fluids. That is the scientific basis for the
previously planned **H10 interaction-zone connector arm** — and, symmetrically,
a reason to distrust isolated lineaments far from any structural interaction.

**Limits.** Percentages describe *catalogued geothermal systems*, not faults, and
not the competition's hidden labels. They cannot be converted into a per-pixel
probability without an additional assumption, and none is made here.

---

## 2. Official, free, verified data located this session

All rows are DOE Geothermal Data Repository (GDR) or OSTI records; GDR content
is published under CC-BY-4.0 unless the record says otherwise.

| ID (`sources.json`) | Dataset | Contents | Licence / access | Verification |
| --- | --- | --- | --- | --- |
| `gdr-383` | [Structural and Tectonic Controls of Geothermal Activity in the Basin and Range Province](https://gdr.openei.org/submissions/383) (Faulds, Hinz & Kreemer 2012) | Inventory of >400 systems; 2012 NZ Geothermal Workshop paper (303 kB) | CC-BY-4.0 badge on the page, publicly accessible | [F] |
| `gdr-616` | [Nevada Great Basin Play Fairway Analysis Regional Data](https://gdr.openei.org/submissions/616), DOI [10.15121/1225261](https://doi.org/10.15121/1225261) (Faulds, NBMG 2015) | 96,000 km² transect: structural settings, fault recency/slip/dilation potential, strain rates, earthquake density, gravity, temperature at 3 km, permeability + favourability models, **springs and wells**, exploration opportunity, error layers; DOE contract EE0006731 | CC-BY-4.0 (JSON-LD on the page), publicly accessible | [S] |
| `gdr-1351` | [Machine Learning Model Geotiffs](https://gdr.openei.org/submissions/1351), DOI [10.15121/1897036](https://doi.org/10.15121/1897036) (Faulds, Brown, Smith, Queen & Treitel 2021) | ANN / ELM / Bayesian NN / PCA / NMF favourability models, model input feature grids, positive and negative training sites; one 590.94 MB zip | CC-BY-4.0 badge on the page, publicly accessible | [F] |
| — | "Potential structures" submission (Nevada ML project) | Potential structural-setting **ellipses, centroids, distance-to-centroid raster** | Listed on the [GDR search page](https://gdr.openei.org/search?q=raster) and in OSTI related-dataset lists | [S] — page not opened |
| — | [Geochemistry and paleo-geothermal features](https://www.osti.gov/dataexplorer/biblio/dataset/1832126) (Faulds & Ayling) | Geochemistry + **paleo-geothermal features (sinter, travertine, tufa)** shapefiles = fossil vent fields | DOE record | [S] |
| `gdr-1526` | [GeoDAWN Northwestern Elko County, Nevada EarthMRI Data](https://gdr.openei.org/submissions/1526) (USGS NGP 2023) | **OPR** (raster) + **LPC** (point cloud) lidar from the GeoDAWN acquisition | Publicly accessible per GDR listing | [S] |
| `gdr-1501` | [GeoDAWN West Central Nevada EarthMRI Data](https://gdr.openei.org/submissions/1501) (USGS NGP 2023) | **OPR** + **LPC** lidar, western Nevada block | Publicly accessible per GDR listing | [S] |
| `gdr-1391` | [INGENIOUS Great Basin Regional Dataset Compilation](https://gdr.openei.org/submissions/1391), DOI [10.15121/1881483](https://doi.org/10.15121/1881483) (Ayling et al. 2022) | Quaternary-fault compilations v1 (2022) and v2 (2023-06-27, "supersedes v1"), study-area boundary, paleo-geothermal, wells/springs, geodetics, seismicity, 2 m probes | CC-BY-4.0, publicly accessible | [F] + [M] (v1/v2 zips downloaded and rasterised by our runner) |
| `osti-1148722` | [Structural Inventory of Great Basin Geothermal Systems](https://www.osti.gov/biblio/1148722) | Independent official record of the same inventory (426 systems, eight settings) | OSTI record; dataset view at `/dataexplorer/biblio/dataset/1148722` | [S] |
| `drivendata-968` | [GEMS About page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/) | Organiser framing (GeoDAWN survey, hidden faults) and the two cited papers below | Competition terms | [F] |

Identified but **not verified** this session: a 2025 USGS favour-ability mapping
data release for the Great Basin (Mordensky & DeAngelo 2025) referenced by
*Favorability mapping for hydrothermal power resource assessments of the Great
Basin, USA* ([ScienceDirect S0375650525002019](https://www.sciencedirect.com/science/article/pii/S0375650525002019)) **[S]**.
It is a candidate for the next session's source review, not a claim.

### Reuse value beyond this competition

For a vent/exploration project the durable assets are: the structural-setting
ranking (§1) as an evidence-weighting prior; `gdr-616` favourability, heat at
3 km, springs/wells and error layers as region-scale features; `gdr-1351`
positive/negative site definitions and model rasters as a baseline to beat;
`gdr-1391` paleo-geothermal features and well/spring inventories for surface
manifestations; `gdr-1501`/`gdr-1526` for native-resolution lidar where 3DEP
coverage is missing. All are free, official and licence-clean for reuse with
attribution.

---

## 3. The organisers' own cited literature

| Paper | What it says | Relevance to our pipeline |
| --- | --- | --- |
| Mattéo et al. 2021, JGR Solid Earth, [10.1029/2020JB021269](https://doi.org/10.1029/2020JB021269) | Automatic fault mapping from topography with deep learning | The method family of the public reference solution; establishes that DEM-based segmentation is the expected bar, so a submission must add something else |
| Hermant, Kiersnowski & Bellanger 2025, [Stanford SGW paper](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Hermant.pdf) | U-Net-style (siUNET/FaultSEG) fault mapping on **10 m** DEMs in northern central Nevada; false positives concentrate on stream/canyon boundaries; models find faults the USGS map missed (expert-confirmed) | Validates DEM/lidar-scarp detection as a discovery method; names the dominant confuser (fluvial edges) that our false-positive audit also sees |

---

## 4. Measured this session: what the shipped labels actually are **[M]**

`scripts/label_provenance.py` (result: `knowledge/session8/label_provenance.json`):

| Quantity | Value |
| --- | --- |
| Shipped label pixels inside the footprint | 60,988 |
| Footprint pixels | 5,167,373 |
| INGENIOUS v2 trace pixels inside the footprint | 60,982 |
| …that are farther than 1 px from a shipped label | **4** |
| Shipped labels within 1 px of an INGENIOUS v1 / v2 trace | 100 % / 100 % |
| Shipped labels within 1 px of the QFFDB-derived raster | 99.95 % |
| Grid-wide INGENIOUS v2 pixels not in the labels | 108,131 — **100 % of them outside the footprint** |

Conclusion: inside the scored region the shipped training raster **exhausts the
published record** (QFFDB and INGENIOUS agree to within a handful of pixels), so
the expert "new fault dataset" the prize scores cannot be a copy of published
catalogues. Any submission mass placed exactly on a shipped label pixel is a
guaranteed false positive under the scored set. This is the strongest single
piece of strategy evidence in the repository, and it retires the whole family of
"reuse an official compilation" candidates before they cost a feedback slot.

---

## 5. Hypothesis register after session 8

| Hypothesis | Status | Evidence |
| --- | --- | --- |
| Known-fault proximity predicts new faults | **Rejected (held-out blocks)** | `emission_policy_experiment.json`: proximity field sits below the random-emission baseline; catalogue-concentrated group uploads scored below random |
| Published catalogues contain the scored faults | **Rejected** | §4 (4 residual pixels) |
| Emission policy (ridge NMS vs raw vs kernel-matched) is the main lever | **Not supported** | H14: policies within noise at equal budget; ridge arm was degenerate at first and documented as such |
| Thin-line lidar/DEM scarp detection transfers to new faults | **Open — this is the H1 upload** | local folds say lidar ≫ bands19; leaderboard unknown |
| Interaction zones (step-overs, tips, intersections) are where ambiguous lineaments are most likely real | **Open — H10** | regional inventory §1; needs a frozen geometric protocol and matched-mass controls |
| GeoDAWN lidar holds (GDR 1501/1526) can close the 24.6 % coverage gap | **Open — enumeration not run** | GDR listings §2; needs file inventory + overlap check against `knowledge/dem_tiles_gap.json` |

## 6. Manual review checklist (click-through)

1. <https://gdr.openei.org/submissions/383> — structural-setting percentages.
2. <https://gdr.openei.org/submissions/616> — play-fairway layers, CC-BY-4.0, EE0006731.
3. <https://gdr.openei.org/submissions/1351> — ML geotiffs, DOI 10.15121/1897036.
4. <https://gdr.openei.org/submissions/1526> and <https://gdr.openei.org/submissions/1501> — GeoDAWN lidar inventory (check file formats/sizes before planning a download).
5. <https://gdr.openei.org/submissions/1391> — INGENIOUS v1/v2 and the CC-BY-4.0 DOI used by our H12 measurement.
6. <https://www.osti.gov/biblio/1148722> — independent record of the inventory.
7. <https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/> — organiser framing and cited papers.
