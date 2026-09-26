# Data inventory (every byte sha256-verified)

Verification: `python scripts/verify_data.py` (all PASS, 2026-09-26).
Pins: `inherited_evidence/data_bridge_manifest.json` (measured from the official
downloads 2026-09-17) and `inherited_evidence/inventory.json` (independent
runner-side inventory 2026-09-14).

## Official competition files

| File | Canonical name | Bytes | sha256 | Notes |
|---|---|---|---|---|
| gems-geodawn-numerical-features.tif | training_features.tif | 418,912,844 | `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5` | 19 bands float32, EPSG:32611, 100 m; nodata −3.4e38 |
| existing_faults.tif | labels.tif | 425,830 | `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093` | int8, nodata −1; 60,988 positive / 5,167,373 valid px |
| example_submission.tif | sample_submission.tif | 1,599,597 | `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc` | float32 template; NaN outside footprint (7,111,787 px); **bit-identical to labels inside footprint (flagged irregularity)** |
| GEMS_96647.pdf (rules) | — | 455,140 | `50d854b1e0239fe6b9648d9fa5c7537bc7b6e5bc10cf6b37a2ff9aa401c36938` | <https://docs.nlr.gov/docs/fy26osti/96647.pdf> |
| Digital-elevation-model-links-JSON.pdf | — | 23,032,446 | `c2996eaf0adcc76bb81975ec21155dbf32ddac3fbbe71f71d89a5ff465f2c775` | scanned PDF (no text layer); URLs OCR-recovered by the sibling repo into `dem_links.json`; 716 tiles confirmed live against the USGS 3DEP bucket |
| 1m_DEM_links.csv | — | — | — | on the login-walled data tab; not yet mirrored — **open item** |

## Download routes

1. **Official Dropbox mirrors** (login-free, linked from the competition page) —
   exact URLs with sha256 verification in `scripts/download_competition_data.sh`.
2. **Sibling-repo git bridge** `buffedlizard55-lab/GEMSDOE` `data/bridge/`
   (parts ≤ 100 MB per GitHub's blob limit; reassembled + hash-verified by
   `scripts/assemble_data_bridge.py`). Used automatically by the download script
   when Dropbox is unreachable (e.g. this sandbox: Dropbox TLS is egress-blocked;
   GitHub works).
3. **DrivenData data tab** <https://www.drivendata.org/competitions/306/competition-doe-gems/data/>
   — authoritative but login-walled. ❌ No DrivenData credentials available in this
   project: that remains the only manual step for files not mirrored (1m_DEM_links.csv).

## Band semantics (measured from the file's band tags)

| # | name | category |
|---|---|---|
| 1 | Magnetic anomaly | magnetic_data |
| 2 | Reduced-to-pole magnetic | magnetic_data |
| 3 | TMI horizontal gradient | magnetic_data |
| 4 | Geodetic second invariant (strain) | geodetic_strain |
| 5 | Isostatic gravity anomaly slope | gravity_data |
| 6 | Tilt angle / total curvature (edge detection) | magnetic_data |
| 7 | Geodetic shear rate | geodetic_strain |
| 8 | Geodetic dilatation rate | geodetic_strain |
| 9 | TMI vertical gradient | magnetic_data |
| 10 | Distance to earthquake (100 km radius, 15° azimuth) | seismic |
| 11 | Isostatic gravity anomaly vertical gradient | gravity_data |
| 12 | Detrended elevation | topographic |
| 13 | Isostatic gravity anomaly | gravity_data |
| 14 | Total magnetic intensity | magnetic_data |
| 15 | Depth to basement (conductive base surface) | subsurface |
| 16 | Earthquake density (100 km radius, 15°) | seismic |
| 17 | Surface conductivity | subsurface |
| 18 | Isostatic gravity anomaly horizontal gradient | gravity_data |
| 19 | Detrended elevation slope | topographic |

The problem page's prose implies ~10 feature groups; the file carries **19 bands**
(measured). Recorded as verified finding #1 of the sibling repo and re-verified here.

## External datasets allowed

Participants may use additional data if licensed for the challenge and shareable
with the sponsor (problem page, "External datasets"). All sources in
`01_science_faults_geothermal.md` are public-domain / CC0 / open-access.

## Storage policy

Large rasters live in `$GEMS_DATA_DIR` (default `~/gems_data`), **not** in git
(418 MB exceeds sensible repo weight and the patchset budget). Committed artifacts
are small: fixtures (~5 MB), submissions (~3 MB), JSON evidence. Reproduce the
data placement anywhere with `scripts/download_competition_data.sh`.
