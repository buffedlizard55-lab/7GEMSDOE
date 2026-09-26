> **Historical session-1 notes; superseded where inconsistent.** Fresh claim-level evidence and corrections: [session-2 audit](session2/review.md), [science ledger](session2/research.md), [source registry](sources.json), [dated feed](feed.json). Inherited source/provenance claims are not independently authenticated by being stored here.

# Science notes: faults as indicators of geothermal resources

Grounded in official sources (links inline). This is the starting knowledge base
for the scientific-discovery side of the project — reusable for other projects.

## Why faults matter for geothermal

* Faults are fractures with measurable displacement; fault *traces* are their surface
  intersections (competition [About page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)).
* Fractured crust provides fluid pathways; geothermal resources cluster where active
  or recent faulting keeps permeability open — e.g. the Steamboat plants near Reno
  sit inside the GeoDAWN study area (About page, USGS image caption).
* Faults act as **conduits for fluids**, concentrating geothermal energy, minerals,
  hydrocarbons and groundwater (About page).

## Tectonic setting of the GeoDAWN region

* The surveys span "areas of major resource potential associated with the **Walker
  Lane** and western **Great Basin**" ([USGS GeoDAWN release, DOI
  10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ)).
* Walker Lane is a diffuse dextral shear zone accommodating ~20–25 % of
  Pacific–North America relative plate motion; the Great Basin is extending
  (Basin-and-Range normal faulting). Both regimes produce dense, often buried,
  fault systems — the target population of this competition.
* Most faults in the region "are more subtle, and many are hidden below the surface,
  requiring geophysical data to detect" (competition About page).

## Detection methods named by the sponsor

From the About page: field observations (scarps, offset layers, slickensides),
seismic reflection, gravity and magnetic anomalies, remote sensing and elevation
data, and computational methods — **edge detection, Hough transforms, deep
learning** on topographic/geophysical data. Two sponsor-cited references:

* Mattéo et al. 2021, automatic fault mapping with deep learning, *JGR Solid Earth*
  126, e2020JB021269 — <https://doi.org/10.1029/2020JB021269>
* Hermant, Kiersnowski & Bellanger 2025, deep learning to map Quaternary faults in
  the western USA, Stanford Geothermal Workshop —
  <https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2025/Hermant.pdf>

## Where unmapped ("blind") faults hide — working hypotheses

1. **Basin fill / alluvium**: range-front normal faults continue under valley fill;
   magnetic/gravity gradients and basement-depth contrasts (band 15 of the feature
   stack) expose them. GeoDAWN Area-2 flight specs were chosen "primarily with a
   focus on geothermal resources" (GeoDAWN release).
2. **Along-strike extensions** of mapped strands (fault tips are systematically
   under-mapped at 1:24k/100 m scales).
3. **Splays and stepovers** of mapped systems — the private label set was built by
   experts re-examining exactly these data.
4. **Geodetically active, geologically unmapped** structures: the stack carries GPS/InSAR
   strain-rate bands (dilatation, shear, second invariant) and seismicity bands;
   strain concentrations without a catalogue trace are prime candidates.
5. **Lineaments in derivative fields**: tilt/total-curvature (band 6), TMI horizontal
   gradient (band 3), isostatic gravity horizontal gradient (band 18) are literal
   edge-detector products — coherent linear features ≥2 km long, off-catalogue, are
   expert-style discoveries.

## Official data sources for the science (all verified reachable 2026-09-26)

| Source | What it gives | Link |
|---|---|---|
| USGS Quaternary Fault & Fold Database (QFFDB) | the existing-catalogue labels' origin; GIS download 16 MB; 5 age-class layers | [faults page](https://www.usgs.gov/programs/earthquake-hazards/faults) · [GIS zip](https://earthquake.usgs.gov/static/lfs/nshm/qfaults/Qfaults_GIS.zip) · [KML](https://earthquake.usgs.gov/static/lfs/nshm/qfaults/qfaults.kmz) · [citation DOI 10.5066/P9BCVRCK](https://doi.org/10.5066/P9BCVRCK) |
| USGS GeoDAWN release | airborne magnetics + radiometrics, 149,030 line-km, 51,857 km², CC0 | [DOI 10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ) |
| Great Basin heat-flow maps (DeAngelo et al. 2022, INGENIOUS) | heat flow + supporting data | [DOI 10.5066/P9BZPVUC](https://doi.org/10.5066/P9BZPVUC) |
| Regional geophysical maps of the Great Basin (Glen et al. 2022) | gravity/magnetics context beyond GeoDAWN | [DOI 10.5066/P9Z6SA1Z](https://doi.org/10.5066/P9Z6SA1Z) |
| Electrical conductance maps of the Great Basin (Peacock & Bedrosian 2022) | conductance — proxy for fluids/clay/basin depth | [DOI 10.5066/P9TWT2LU](https://doi.org/10.5066/P9TWT2LU) |
| Slip/dilation tendency on Great Basin Quaternary faults (Siler 2022) | fault-stress favorability shapefiles | [DOI 10.5066/P9YL58W6](https://doi.org/10.5066/P9YL58W6) |
| INGENIOUS regional dataset compilation (Ayling et al. 2022, on GDR) | the compilation behind part of the labels | [DOI 10.15121/1881483](https://doi.org/10.15121/1881483) |
| INGENIOUS project page | goals, team, publications | [gbcge.org/current-projects/ingenious](https://gbcge.org/current-projects/ingenious/) |
| Crustal strain rates, western US (Kreemer & Young 2022) | strain-rate context for the geodetic bands | [DOI 10.1785/0220220153](https://doi.org/10.1785/0220220153) |
| DOE Geothermal Data Repository (GDR) | free archive of all DOE-OG-funded data (764 TB) | [gdr.openei.org](https://gdr.openei.org/) · [about](https://gdr.openei.org/about) |
| DOE Office of Geothermal technical resources | GDR, NGDS, GeoVision, Nat'l Geologic Map DB, OSTI | [energy.gov/hgeo/geothermal/technical-resources](https://www.energy.gov/hgeo/geothermal/technical-resources) |
| USGS 3DEP lidar (1 m DEMs for the region) | scarp detection at 1 m | [apps.nationalmap.gov/3dep](https://apps.nationalmap.gov/) (linked from GeoDAWN release text) |
| Competition forum | participant Q&A | [community.drivendata.org/c/gems-prize-challenge/111](https://community.drivendata.org/c/gems-prize-challenge/111) |

Flagged: `https://gdr.openei.org/submissions/1391` currently returns "No submission
found" (verified 2026-09-26). The GeoDAWN-area GDR holdings are searchable from the
GDR home page instead.
