# Session 5 review — three-pass audit (2026-09-26)

Scope: this repository at session 5, the five group sites/scores, the
official leaderboard snapshot re-checked this session, and every new
artifact built here. Labels: **[official]**, **[team record]**,
**[measured]** (script named), **[inference]**.

## Standing (re-checked 2026-09-26 via page tool)

| Participant | Public score | Change since session 4 |
|---|---|---|
| DARD (leader) | 0.3049 | none (10 submissions) |
| alexoktaba / HardcoreTechGod / mzoorob | 0.2993 / 0.2854 / 0.2843 | none on bests |
| doegemsDrivendata (likely organiser baseline) | 0.1847 | none |
| extradr19 · SDCF9 · smashi34 | 0.1563 · 0.1563 · 0.1560 | none on bests; SDCF9 file behind 0.1563 STILL unrecorded |
| smrtdoog5 · wbg1 | 0.1193 · 0.0830 | none |

Group best 0.1563 remains below the organiser-like 0.1847 baseline and
0.1486 short of the leader. The session-4 H1 candidate
(`gems7-lidarscarp-ridge-top2pct-36c3a3f341c8`) is still NOT YET SCORED —
no upload was made by the agent (no credentials; uploading is the
participant's action).

## What session 5 measured (all local, no leaderboard feedback used)

1. **Lidar gaps** (`scripts/lidar_gaps.py` → `lidar_gaps.json`):
   1,272,913 gap px = 24.63% of the footprint. Catalogue density 0.98% in
   gaps vs 1.24% covered — gaps are mildly fault-poor but still hold 12,523
   catalogue pixels (20.5% of all known faults). NE quadrant is 47.4% gap
   (fill priority #1); SW/SE are <8%. Candidate emits 0 px in gaps
   (verified, as designed). Consequence: every lidar-only policy caps
   recall at ~75% of the footprint, and the gap sits disproportionately in
   the Walker Lane transition where geothermal science expects activity
   (`research.md` S6).
2. **FP audit** (`scripts/lidar_fp_audit.py` → `lidar_fp_audit.json`):
   closed loops are minor (483 hole px, 0.6% of emission) — the visual
   worry from session 4 does not survive measurement. But 72.1% of emitted
   pixels are cross-slope dominant (channel-bank-like signature), and
   emission strongly favours high relief (53.8% of emitted on 33.7% of the
   footprint) while avoiding low relief (6.5% on 32.8%). The v2 cleanup
   filter (background-quantile cutoffs, frozen, no label/leaderboard
   tuning) would drop only 1,580 px (2.1%) — honest result: threshold
   tweaks are not the lever; channel-network and shoreline controls are.
   V2 is pre-registered as code+policy ONLY; no file is packaged, so the
   H1 upload stays a decisive single-variable test.
3. **Group-site re-read**: GEMSDOE (recall ensemble 0.1563), GEMSDOE2
   (dual-family union 0.1560), GEMSDOE3 (pindrop trio), GEMSDOE4
   (lineament+proxy 0.0343), 6GEMSDOE (HGB top-3% 0.0286). No site
   documents radiometric, QFFDB-attribute, or interaction-zone inputs —
   the session-5 hypotheses attack ground the group has not tried.

## What session 5 built (verified)

* `scripts/qfaults_prior.py` + `.github/workflows/qfaults.yml`: official
  QFFDB zip → 3-band scale/certainty prior on the official grid.
  Fail-closed on schema mismatch; hermetic tests 6/6 pass.
* `scripts/geodawn_rad.py` + `.github/workflows/geodawn-rad.yml`: official
  GeoDAWN release (DOI 10.5066/P93LGLVQ) → K/Th/U/TC uint8 product.
  Fail-closed on filename mismatch; hermetic tests 5/5 pass (incl. the
  fixed f-string syntax defect found in pass 1).
* `tests/test_session5_audits.py`: JSON-contract regression tests for both
  audit outputs (skip cleanly without data placement; CI stays hermetic).
* Docs: `research.md` (15 verified sources, overlooked-data audit, 4 new
  hypotheses, 6 strategies), this review, `next_session.md`.
* Full suite: **119 passed** (107 session-4 + 11 new session-5 + 1
  data-dependent test that skips without data placement).

## Pass 2 — bugs, assumptions, edge cases found and fixed

1. `geodawn_rad.py` f-string nested-quote SyntaxError (py3.11): fixed by
   hoisting `safe_name`; caught by test collection, now passing.
2. QFFDB field names NOT assumed: session 4 cited a feature-service schema
   + Alaska metadata as proxies, never the zip itself. The script records
   observed fields and fails closed when all candidates are absent.
3. Radiometric filenames NOT assumed: ScienceBase names are unverified
   from the sandbox, so selection is pattern-based with the full observed
   listing dumped on mismatch.
4. `valid`-band lookup in `lidar_gaps.py` does not assume band position:
   name lookup first, documented position as fallback.
5. No new submission file packaged: with v1 unscored, a v2 file would
   confound the H1 test and spend the entity's 3/week budget without
   evidence. Policy frozen instead.
6. Private email addresses stay out of the public UI (standing rule);
   team records keyed by site/account in `team_results.json`.

## Pass 3 — recheck against the original request

* Previous-session next steps first: H1 upload still needs the user (not
  actionable by the agent); backlog #1 partially (gap geography measured,
  runner enumeration still open), #3 partially (audit + frozen policy;
  channel/shoreline controls still open), #4 (runner job ready). #2
  (native-res detector), #5 (PU/survey-block), #6 (U-Net port) carried.
* Submission-ready site: all 4 downloads re-validated PASS (strict gate);
  executive guide `how-to-submit.html` current (recommended file = H1
  candidate + Note + [0,1] root-cause section). No manual input required
  to reproduce: data script + audits + tests all ran autonomously.
* No hallucinations: every factual claim links a primary source opened
  this session or a repo script; assumptions are labelled [inference] and
  fail-closed where network/schema is unverified.
* PR + merge: recorded below after CI.

## Minor irregularity found in pass 2 (flagged, not blocking)

* The lidar product manifest (`external/dem/lidar_scarp_features.json`)
  states `grid_cells_with_lidar = 3,892,964`, but a direct read of the
  committed `valid` band gives 3,894,460 valid pixels, all inside the
  footprint (+1,496 px, +0.04%). Session-5 gap numbers use the direct
  measurement. Likely cause: the runner counted cells before final
  footprint masking or with a different validity rule. Harmless at this
  magnitude; the next `dem_merge.py` run should reconcile the manifest
  definition.

## Remaining limitations (no silent progress claimed)

* No H1 score yet — the single most valuable datum is still missing.
* Runner jobs are code-complete but UNEXECUTED (workflows trigger on
  dispatch / `[run-qfaults]` / `[run-rad]` markers; no run happened this
  session). Products do not exist yet.
* Sandbox has no GPU, ~4 GB RAM, and no direct USGS/ScienceBase/DrivenData
  egress (curl TLS fails; page/search tools + Actions are the routes).
* Radiometric altitude masks, acquisition-block boundaries, and per-asset
  licences are unverified until the runner reads the release.
* No field verification of any predicted fault; no private labels.
