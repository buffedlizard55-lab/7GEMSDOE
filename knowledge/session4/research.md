# Session 4 research — lidar scarp evidence, leaderboard theory, hypotheses

Labels: **[official]** from the organiser/USGS/DOE/university source linked;
**[literature]** peer-reviewed; **[measured]** computed in this repo (script
named); **[inference]** our reasoning. Retrieved 2026-09-26 unless stated.

## 1. New verified sources (for manual review)

| Claim used | Label | Source |
|---|---|---|
| GeoDAWN partners (USGS Earth MRI, 3DEP, DOE Geothermal Technologies Office, NRCS, BLM) flew airborne geophysics **and 3DEP lidar**; "the new topographic and geophysical data should help identify the faults in the region" | [official] | [USGS GeoDAWN image page](https://www.usgs.gov/media/images/geodawn-geoscience-data-acquisition-western-nevada) |
| The lidar collected under GeoDAWN is published as "GeoDAWN West Central Nevada EarthMRI Data" (OPR + point clouds) | [official] | [OEDI 7592, DOI 10.15121/1992093](https://data.openei.org/submissions/7592) · [data.gov record](https://catalog.data.gov/dataset/geodawn-west-central-nevada-earthmri-data) |
| Lidar lets researchers "see and analyze faults where they intersect the surface" | [official] | [USGS featured story on GeoDAWN](https://www.usgs.gov/news/featured-story/usgs-and-eere-collaborating-strengthen-americas-energy-and-resource) |
| NBMG's Reno-area lidar revealed "more than two dozen previously unknown faults"; "We can use LIDAR to discover previously unknown earthquake faults" (J. Faulds) | [official, university] | [UNR Nevada Today, "Finding faults"](https://www.unr.edu/nevada-today/nevada-stories/walker-lane) |
| Regional-scale scarp detection from ≤2 m lidar by curvature template matching (diffusion-degraded scarp model) | [literature] | Sare, Hilley & DeLong 2019, JGR Solid Earth 124, 1016-1035, [doi:10.1029/2018JB016886](https://doi.org/10.1029/2018JB016886); Hilley et al. 2010 GRL [doi:10.1029/2009GL042044](https://doi.org/10.1029/2009GL042044); Scarplet (MIT) [doi:10.21105/joss.01066](https://doi.org/10.21105/joss.01066) |
| Central Walker Lane scarps can be subtle (< 0.5 m) in Holocene fans; lidar used to map them | [literature] | "Late Quaternary slip rates for faults of the central Walker Lane (Nevada, USA)", Geosphere, [doi:10.1130/GES02088.1](https://doi.org/10.1130/ges02088.1) (open access) |
| Youthful scarps are best expressed where faults leave the range front onto piedmont slopes, including Lahontan lacustrine deposits; shoreline reworking is a confounder | [literature] | "A paleoseismic transect across the northwestern Basin and Range Province", Geosphere 13(3):782, [GeoScienceWorld](https://pubs.geoscienceworld.org/gsa/geosphere/article/13/3/782/208051/A-paleoseismic-transect-across-the-northwestern) |
| QFFDB traces carry `mapped_scale` and `mapped_certainty` (well / moderately constrained / inferred); 1:250,000 mapping is accurate to ~450 ft (~137 m, > 1 grid cell) | [official] | [USGS Qfaults feature-service schema](https://services.arcgis.com/hVnyNvwbpFFPDV5j/arcgis/rest/services/CA_Injection_Stations_WFL1/FeatureServer/3) (field list) · national attribute guidelines as reproduced by [Alaska DGGS MP141 metadata](https://dggs.alaska.gov/webpubs/metadata/MP141.faq.html) |
| NBMG compiled a Quaternary-fault database for INGENIOUS (part of the training labels) | [official abstract] | [2022 Basin and Range Earthquake Summit abstracts, Koehler](https://geology.utah.gov/docs/haz/2022_abstracts_geology.pdf) |
| USGS 3DEP products have no use restrictions (acknowledgement requested) | [official] | [3DEP about](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services) |

Note: author lists of the two Geosphere articles were not verified in this
session, so they are cited by title and DOI/link only.

## 2. Leaderboard theory (details: `review.md`, `scored_files_analysis.json`)

* Exact random baseline for the official metric: `scripts/random_baseline.py`
  [measured against Monte-Carlo runs of `scripts/metric.py`].
* Implied public truth density ≈ 0.31% if the catalogue-gap upload had zero skill
  [inference]; best group file ≈ 1.9x random coverage; the leader needs ≈ 4-5x.
* Blob-like emission scored below random; thin line-like emission scored best
  [measured on group files + inference]. Emission policy now thins to 1 px ridges.

## 3. Hypothesis register

| ID | Hypothesis | Status / test |
|---|---|---|
| H1 | Most new expert-mapped faults are lidar-visible scarps missing from the QFFDB/INGENIOUS catalogue; 1 m lidar evidence localises them far better than the 100 m bands | **Testing.** Region-wide lidar product built (706/716 official tiles). Pre-registered block-CV comparison in `lidar_experiment.json`; decisive test is a leaderboard upload |
| H2 | Mapping-scale deficit: coarse (1:250k) or inferred QFFDB traces are where re-mapping yields most new pixels (corrected geometry 1-3 px off the old trace) | Open. Needs QFFDB attributes rasterised (runner job); test by matched emission near coarse vs fine traces |
| H3 | Along-strike continuation of catalogue traces | **Rejected as primary** (session 3: pooled geographic DTI 0.000125) |
| H4 | Geologic-map faults absent from the Quaternary catalogue (SGMC) are part of the new truth | Open. The never-uploaded SGMC-gap file (1.21% density) is a cheap single-upload test |
| H5 | Piedmont bias: new faults concentrate on alluvial piedmonts (subtle scarps) rather than bedrock ranges or basin floors | Open. Stratify lidar-model emission by relief/slope class |
| H6 | Orientation prior: new faults share the local strike distribution of known faults (NNE Basin-and-Range normal faults; NW dextral Walker Lane) | Open. Lidar strike channel vs local catalogue strike |
| H7 | Channel banks, roads, shorelines and tile seams are the dominant lidar false positives | **Confirmed visually** for channel banks; facing channels (up/down/cross-slope) added to separate them; tile-seam artefact found and fixed |
| H8 | Label-generation bias toward geothermal prospects (experts reviewed geothermal-relevant areas more densely) | Open, contrarian. Needs public geothermal-site data; test by stratified emission |

## 4. Defects found and fixed this session (why the tests exist)

1. **Tile-seam artefact** [measured]: scipy's default even reflection makes a
   V-shaped surface at tile edges, so smoothed-slope differences produced a
   spurious "scarp" equal to the regional slope along every 10 km seam. Fixed with
   odd (point) reflection padding; regression test on a tilted plane.
2. **Curvature elevation bias** [measured]: scipy's truncated second-derivative
   Gaussian kernel does not sum to zero, so LoG(raw elevation) = −0.176 on a flat
   1500 m surface (σ = 3 px). v1 curvature channels were elevation proxies. v2
   applies LoG to the 10-50 m band-passed surface; regression test at 200/1500/3000 m.
3. **Orientation bias** [measured]: a regional fan gradient rotated the
   structure-tensor strike by ~16°; fixed by using band-passed gradients.
