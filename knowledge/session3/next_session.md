# Start here next session

Read README.md, AGENTS.md, STATUS.md, then session3/review.md, research.md and both
experiment JSON files. The original user mission/requirements remain in README.

## Decision: do not promote another halo

H3 has near-zero geographic discovery coverage. Keep its immutable TIFF for
reproduction; do not advertise it as a validated improvement. The 100 m terrain
expert beat the other raw-band expert in all four diagnostic quadrants. Neither
has been independently locked-tested or submitted. Do not select thresholds,
blend weights or top-k budgets on these already-inspected quadrants and then
call the same scores an untouched test.

## Ordered next work

1. **Pre-register a new evaluation split before modelling.** Obtain geological
   fault-system IDs if possible (raster connected components are not systems).
   Reserve untouched geographic/survey areas. Fit all normalization, sampling,
   calibration and thresholds within training/inner-selection folds only.
2. **Native DEM discovery experiment.** Extend the existing successful bounded
   3DEP pilot to multiple native 1 m tiles with hashes, CRS/datum and coverage
   masks. Derive cross-profile scarp evidence at native resolution, aggregate to
   100 m only after feature extraction. Add road, drainage, lithologic-contact,
   seam and nodata-edge controls. Compare against the two-band terrain baseline.
3. **Acquisition-aware independent geophysics.** Retrieve GeoDAWN flight/block
   metadata through GDR 1591 / DOI 10.5066/P93LGLVQ. Audit actual asset licenses
   and band meanings. Test whole survey blocks and source-direction nulls;
   do not infer faults from acquisition stripes.
4. **Positive-unlabeled sensitivity and calibration.** Fixed-seed low-weight
   unlabeled bagging, omission simulations and training-only calibration. The
   current 1:3 sampled classifiers are not calibrated fault probabilities.
5. **Candidate only after evidence.** Build a new full-grid artifact only after
   a locked transfer test; retain hash, policy, short Note, single-file ZIP and
   strict gate. Compare existing model output only with leakage-free folds,
   not the all-label legacy model. Preserve all failures and mass/TP/FP/FN.
6. **Authorized competition feedback.** Confirm the single participating entity
   and remaining weekly budget. Record the actual uploaded file hash + score.
   Do not distribute test slots across accounts. Public best-score polling
   cannot establish which TIFF was accepted or recover private results.

## Access and limitations

- Data placement/preparation completed again here with inherited hash pins.
  Large files live in ~/gems_data; a fresh sandbox may need the downloader again.
- GitHub access is available. DrivenData authenticated upload/final selection
  is not; no credentials requested. Eligibility and acceptance are human/legal
  actions and cannot honestly be bypassed as a 'no manual input' promise.
- Local Python HTTPS and browser-binary downloads encountered TLS failures;
  page-tool retrieval and the public git bridge worked. Actions is the existing
  fallback for daily source/browser checks; inspect actual run outcomes.
- No region-wide DEM model, no demonstrated >0.3049, no field-verified discovery,
  no GPU/deep pipeline integration, no organizer-authenticated byte comparison.
- This research pass is not an exhaustive literature review or a full list of
  geothermal resources. Unknowns and missing rights checks remain explicit.
