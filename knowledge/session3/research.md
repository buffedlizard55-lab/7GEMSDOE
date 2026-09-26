# Session 3: evidence → hypotheses → falsification (2026-09-26)

## Scope and evidence standards

The official [problem and submission contract](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
was retrieved in full with the page tool today. The target is geological faults;
geothermal potential and vents are different downstream targets. The current
[first leaderboard page](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
shows DARD 0.3049, extradr19 0.1563. These are public account bests, not verified
scores of the files currently published on team sites. The 0.1486 gap does not tell
us which feature causes the leader's advantage. We have no leader model or private labels.

Facts below are source-specific, not a guarantee that every sentence in the wider
repository or linked literature is correct. A retrieved abstract is not a full-paper
review; public availability is not automatically a license for dataset redistribution.
No new external dataset was ingested into the models in this session.

## Source and hypothesis ledger

| Verified observation / source | Interpretation proposed here (not established fact) | Concrete test / rejection condition | Data and rights gate |
|---|---|---|---|
| [Faulds & Hinz 2015, OSTI 1724082](https://www.osti.gov/biblio/1724082): abstract reports ~32% stepovers, 25% terminations and 22% intersections among nearly 250 categorized geothermal fields | Branching/relay geometry may identify permeability-favorable structures missed by simple distance buffers. These percentages are NOT pixel probabilities and NOT the fraction of all faults in these settings. | Extract endpoints/junctions from terrain-supported traces, compare matched-mass continuation and random-tangent controls. Reject any claimed isolated-discovery capability if predictions vanish on buffered geography. This session's H3 test does vanish almost everywhere. | Abstract and linked paper readable; any inventory data requires its own license and spatial-coverage check. |
| [USGS Nevada play fairway report, 2019](https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and): Gabbs Valley combines structural, gravity, magnetic, thermal, resistivity and geochemical evidence; drilling up to 124°C at 152 m; no surface hot springs/fumaroles/paleo-geothermal deposits | Do not gate fault discovery on hot-spring presence. Consider separate surface-scarp and buried-basin experts; geothermal indicators are supporting context, not fault labels. | Compare independently trained terrain and geophysics models on identical geography before blending. This session's raw 100 m terrain expert wins all four folds; this is not yet proof of a 1 m DEM advantage. | Report verified; associated layer rights/coverage must be checked separately. DOI 10.2172/1724080. |
| [GDR 1591, USGS GeoDAWN](https://gdr.openei.org/submissions/1591): describes flight details, geophysical data and metadata, with CC BY 4.0 link; links to [DOI 10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ) | Flight-line geometry and acquisition metadata may be more valuable than more derivatives of the same gridded bands. Distinguish source anisotropy from structural anisotropy. | Retrieve raw line metadata; test whole survey-block transfer and residual orientation relative to acquisition lines. Compare with shuffled-orientation controls. Do not remove every flight-parallel geological feature. | Landing record accessible today. Verify actual linked files, hashes, coverage and their individual terms before ingestion; retain Glen/Earney attribution. The existing USGS record states CC0, while GDR displays CC BY: retain both statements, do not silently assume all assets have identical terms. |
| [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), existing source registry: different line spacings in acquisition areas | Random pixels may allow models to learn survey identity rather than transferable geological signatures. | Fold-fit all learned preprocessing; hold out flight blocks; report performance by acquisition block and missing-data quality. Raw-band histogram models this session fit bins and missing routing on training only, but blocks remain geographic quadrants rather than survey polygons. | Exact source band semantics need audit: mirrored TIFF descriptions are not an authoritative dictionary. |
| [Official challenge About page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/), existing ledger: subtle scarps and complementary remote sensing | Multi-scale native DEM profiles, not coarse slope alone, are a plausible next independent signal. | Multi-tile native-resolution gradients, break-in-slope persistence and cross-profile asymmetry; road/drainage/seam negatives. Preserve coverage masks and test entire withheld tiles. | Previous session verified one bounded 3DEP crop; this is not full-region DEM coverage. NAD83/WGS84 alignment must be explicit. |

## Contrarian priorities, grounded rather than speculative

1. **Spend on independent evidence, not more halos.** H3 is near-catalogue completion;
   its poor transfer is geometrically expected when its sources are removed. This is
   not proof that faults lack directional continuity. Use it as a small auxiliary
   channel only after an independent detector passes validation.
2. **Terrain-first, not terrain-only.** The two-band terrain baseline beats the
   17-band geophysical baseline in these folds. Next test native 1 m information,
   with explicit false-scarp controls, rather than assume more bands are better.
3. **Acquisition metadata as a negative control.** Official raw flight information
   is a candidate underused input; we cannot verify that competitors overlook it.
   Survey-edge and striping diagnostics could prevent confident false discoveries.
4. **Positive-unlabeled sensitivity.** The official catalogue is incomplete. Current
   models treat unlabeled pixels as negatives; test bagged low-weight unlabeled
   samples and omission simulations. Do not turn a geothermal site inventory into
   fault truth. Do not infer the unknown class prior from public leaderboard probing.
5. **Two goals, two evidence layers.** Fault raster scoring is the competition
   deliverable. A future geothermal resource atlas should separately retain heat,
   permeability, geochemistry, uncertainty and direct verification evidence. No
   generated fault pixel constitutes a confirmed resource or drilling recommendation.

## Previous sites reviewed again

Page-tool retrieval succeeded for the beginning of all five supplied sites. Direct
Python HTTPS retrieval failed; `team_site_review.json` preserves those failed network
attempts, not fabricated HTML hashes. Existing group result records remain unchanged.

- [GEMSDOE](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html): adopted
  recall field, 172,974 positive pixels, current artifact prefix `7f00890a`.
- [GEMSDOE2](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html): dual-family
  union, current prefix `f68e590f`; site itself reports mixed performance across proxies.
- [GEMSDOE3](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html): three
  155,021-pixel Pindrop arms, matching the user's three reported prefixes. Nodes beat
  dense by 0.0041 in the group report, but no authenticated artifact-score receipt exists.
- [GEMSDOE4](https://buffedlizard55-lab.github.io/GEMSDOE4/): lineament features,
  independent-compilation proxy and union; current prefix `237f0063`.
- [6GEMSDOE](https://buffedlizard55-lab.github.io/6GEMSDOE/): 88-channel HGB and top-3%
  hard predictions; current prefix `33cec71ff0`.

### Irregularities: do not propagate these claims

- Some sites assert that the [0,1] error **means** NaN inside the template. That is a
  plausible cause, not a diagnosis without the actual rejected TIFF. Negative values,
  overflow and infinities also fail. Our strict validator checks all these conditions.
- 6GEMSDOE's claim that every fractional confidence should be hardened does not
  follow from the formula for arbitrary pixel changes. Increasing a false-positive
  pixel without improving TP lowers DTI (now a regression test). Uniform scaling of
  a fixed field is a different question.
- Pindrop's spacing argument ensures nonzero kernel support in certain 1D cases,
  not preservation of weighted TP or universal optimality. A two-pixel gap has kernel
  weight 1/3, not 1. Sparse-placement gains must be measured, not assumed.
- A sibling site's claim to be the sole canonical entry does not establish actual
  team registration, eligibility or an obligation to delete other repositories.
  No repositories/accounts were deleted or modified. Respect entity-wide limits.
- GDR 1591's previous failed retrieval is superseded by today's successful page-tool
  retrieval. GDR 1391 has not been newly verified; do not conflate the two record IDs.
- Raw expert diagnostic scores and H3 scores are not comparable with the actual
  leaderboard population. New fault discovery still needs withheld geography and
  external evidence, then authorized rules-compliant feedback.
