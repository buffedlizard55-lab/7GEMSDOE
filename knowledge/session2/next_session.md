# Next session — start with README and this checklist

## First: protect the experiment

- Keep H3 seed 9001 frozen; do not tune further against its reported result.
- Preserve original control `90fb7dc0fc1f…` and experimental H3 `2b06d45c5b57…`.
- Verify the entity's registration before further public submissions; 3/week/entity,
  one final prediction map for both rounds. No autonomous account actions were taken.
- If an authorized participant uploads, retain exact file SHA + individual score.
  Public account-best polling cannot supply that mapping automatically.

## Highest-value modelling work

1. Add fault-system and buffered spatial holdouts. H3 is a near-catalogue prior, not
   a detector of isolated unmapped structures. Compare matched-mass, random-tangent
   and short-/long-range controls without leakage. Store all outcomes including losses.
2. Extend the successful USGS 1m pilot to multiple tiles with native derivatives,
   nodata/seam/road/drainage controls. Pilot CRS is NAD83 EPSG:26911; reproject to
   WGS84 UTM11 EPSG:32611 before combining with the template. Keep coverage masks.
3. Train independent terrain and geophysical experts on identical folds. Test
   orientation agreement, survey-block transfer and positive-unlabeled sampling.
4. Replace whole-footprint median/percentile normalization with fold-fitted statistics
   for strict validation. Current GBT AUC is pixel-random, not independent geography.
5. Integrate organizer reference deep model only after reproducible folds and storage/
   compute budgets are set. A GPU would accelerate training, but code is not ready here.

## Evidence and operational upkeep

- Inspect latest `research-feed` release, timestamps and failed source checks; scheduled
  Actions are best effort. Prefer explicit stale indicators to fictitious current data.
- Data pins verify team-mirror consistency, not official origin. Authenticated comparison
  against organizer data is still outstanding; never request credentials in chat.
- Full region DEM storage, feature computation and calibrated inference are not done.
- No local proxy permits a claim that we can exceed 0.3049; final prize needs genuine
  generalization and later expert verification, not another wider emission rule alone.
