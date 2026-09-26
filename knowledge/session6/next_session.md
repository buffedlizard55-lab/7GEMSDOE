# Next session — priority order, limitations, and stop conditions

Start with `README.md` → `AGENTS.md` → `STATUS.md` → this file →
[`review.md`](review.md) → session-4's still-governing
[H1 score decision tree](../session4/next_session.md). Read the current feed and
file manifests before using old scores.

## 1. First decide whether H1 has an actual score

The H1 candidate is `downloads/gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.tif`
(SHA-256 begins `36c3a3f341c8`). No agent upload has happened. An authorized
participant must use the official [DrivenData submission form](https://www.drivendata.org/competitions/306/competition-doe-gems/).
Do not request, copy, or store their password/session token. Record only the
participant/account, UTC time, file hash, Note and public score in
`knowledge/team_results.json` after the participant reports the outcome; flag
any mismatch between the uploaded hash and this candidate.

Follow the frozen thresholds in
[`../session4/next_session.md`](../session4/next_session.md):

* **>= 0.16:** invest in an independently validated native-resolution lidar
  detector and fill gaps before combination work.
* **0.09–<0.16:** test lidar + best supplied-band map at matched emission mass;
  do not tune thresholds on public feedback.
* **<0.09:** pivot priority toward geophysical lineaments and the SGMC-gap arm.

These are decision rules, not predictions. Until a score is logged, do not
package or submit a second file: it would confound the H1 test and use limited
feedback budget.

## 2. Retrieve the independent inputs (blocked in this session)

The repository integration cannot call GitHub `workflow_dispatch` (both
attempts returned HTTP 403, “Resource not accessible by integration”). The
existing [QFFDB workflow](../../.github/workflows/qfaults.yml) and
[GeoDAWN-radiometric workflow](../../.github/workflows/geodawn-rad.yml) remain
ready for an authorized repository operator to dispatch, or for a permitted
push-triggered run. Inspect the resulting observed file listings, manifest,
CRS, checksums, rights note and coverage before using a product. The code now
fails closed on QFFDB archive traversal/missing CRS and ambiguous radiometric
files; a runner failure is an outcome to record, not a reason to guess a schema.

If products land:

1. Run H9 on the exact pre-registered spatial folds and matched-mass budgets in
   `knowledge/session5/next_session.md`, comparing radiometrics alone against
   bands19 and lidar, with survey/acquisition blocks held out where their
   boundaries are available.
2. Run H2 only after observing actual QFFDB scale/certainty fields and
   definitions in the downloaded data. Unknown class stays unknown; do not
   equate an undocumented field to mapping scale.
3. Inspect per-asset licences before reuse. USGS public-domain status does not
   automatically establish the terms of a separately mirrored derivative.

## 3. Continue experiments that do not require a new upload

* H10 interaction-zone connectors and H11 strain stratification remain open.
  Write the protocol before measuring, use spatial/system holdouts and
  matched-mass controls, and explicitly note that catalogue-based tests do not
  measure private-truth leaderboard performance.
* Measure/validate an independent channel-network and shoreline control before
  any H1 v2 cleanup; the prior FP audit showed threshold-only filtering was a
  small change.
* Reserve whole geographic areas and fault systems for the final test. Existing
  four-quadrant diagnostics are not untouched final validation; raster-connected
  components are not verified fault-system IDs.
* Continue regional lidar coverage audit and prioritise the NE/Walker Lane gap;
  do not claim 100% 1 m coverage from the present product.

## 4. Maintain the current-results feed and provenance

The daily Actions research refresh succeeded in this session. The latest
observed feed had 107 ranked entries at 2026-09-26 21:12:55 UTC and one source
check (`ingenious-gdr1391`) that requires review. The sandbox could not download
the release asset directly, but its authenticated GitHub API returned the
release body and that body passed JSON/rank/score checks. Keep the stale-last-good
behavior; do not erase the last valid rows when refresh fails. Distinguish
automated excerpt checks from scientific source verification.

## 5. Open limitations and irregularities

* **Submission/auth:** no DrivenData session/data-tab access or private
  submission history. The data tab redirected to login. Upload + final selection
  need an authorized participant. No credentials are stored in the repository.
* **Data provenance:** local rasters matched inherited team SHA pins through a
  public sibling-repository bridge after Dropbox TLS failed. They were not
  independently authenticated against sponsor-published checksums. The official
  1m DEM links CSV is still not available locally.
* **Runner permissions:** integration HTTP 403 blocked both manual workflow
  dispatches; QFFDB/radiometric outputs do not yet exist.
* **Team bookkeeping:** SDCF9's leaderboard best 0.1563 does not match the only
  file we have attributed to that account (0.1152); obtain file/hash attribution.
  Verify participant entity/team registration and follow official rules §3.4
  (three feedback submissions weekly per participating entity, one final
  selection across both rounds). Never multiply submission budgets by accounts.
* **Science:** no new geothermal vent or fault has been field-verified. Fault
  mapping is only an indicator task; a predicted line is not ground-truth.
* **Compute:** local CPU pipeline replay works; no GPU/U-Net training was run in
  this session. A high random-pixel AUC is not evidence of geographic transfer.
* **Deadline:** rules PDF and competition page have differed in stated times;
  retain the safer earlier deadline noted in the prior decision log and verify
  the current official deadline before final selection.

## Stop conditions

Do not claim a leaderboard improvement without an attributable public score.
Do not claim new discoveries without expert/field verification. Do not use
catalogue-derived slip/dilation or fault vectors as independent discovery
features. Do not promote an H1 follow-up until the H1 score is recorded. Every
new hypothesis needs a cited scientific rationale, a frozen test, a null/control,
a spatially honest evaluation, and a stated transfer limitation.
