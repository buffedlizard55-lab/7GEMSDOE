# 7GEMSDOE — fault discovery lab

**Read this README at the start of every session**, then `AGENTS.md`, `STATUS.md`
and [`knowledge/session2/review.md`](knowledge/session2/review.md).

**Goal:** compete for the top prize in [DOE GEMS / DrivenData #306](https://www.drivendata.org/competitions/306/competition-doe-gems/)
through scientifically grounded discovery of unmapped **geological faults**.
Geothermal vents are the user's broader motivation, not the competition's raster target.
**We have not demonstrated a score above 0.3049.** Best group-reported public score:
0.1563, confirmed as an account best on 2026-09-26. Ranks are dynamic.

## Download first

**[GitHub Pages / executive summary](https://buffedlizard55-lab.github.io/7GEMSDOE/)** ·
[Exact submission instructions](https://buffedlizard55-lab.github.io/7GEMSDOE/how-to-submit.html)

- **New experimental H3:** `downloads/gems7-strike30x3-v2-2b06d45c5b57.tif` (and ZIP).
  Note: `H3 tangent continuation 3km x 300m h0.6; no GBT; experimental | 2b06d45c5b57`.
- **Preserved control:** `downloads/gems7-halo15-gbt-v1-90fb7dc0fc1f.tif` (and ZIP).
- Local strict format PASS is not platform acceptance or evidence of a better score.
  A short Note and full SHA-256 accompany every file; browser downloads verify the hash.
- Sign-in and the upload/final-selection action require an authorized DrivenData session.
  No credentials are requested or stored here. Nothing has been submitted automatically.

## Current evidence and autonomous workflow

The data-placement task was completed: all three rasters are present in `~/gems_data`
and match inherited team hashes. This proves consistent bytes, **not independent
sponsor provenance**. Dropbox TLS failed; the public team git bridge succeeded.
`prepare_data.py` now exists and verifies/extracts features. CPU model training can run
here; there is no integrated U-Net/GPU pipeline in this repo.

H3 tests along-strike continuation against isotropic halos: locked **component** test
DTI 0.02825 vs 0.02516, with considerably less prediction mass. This narrow proxy does
not establish geographic transfer or imply a leaderboard score. H4 successfully processed a bounded native
1 m DEM crop on a runner (4,194,304 valid pixels), not a region-wide trained detector. See `knowledge/session2/`.

A verified refresh captured 106 ranks across three pages and five official-source excerpts.
Daily Actions checks the leaderboard and source excerpts, preserves stale last-good
results on failure, and publishes a public `research-feed` release. The Pages UI loads
that release with a bundled fallback. It never calls a sandbox localhost. GitHub Pages
settings are not writable by this integration (403); legacy root/main publishing remains.
Automatic source checks are not automatic scientific verification.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-repro.txt  # measured versions; requirements.txt is portable
bash scripts/download_competition_data.sh
.venv/bin/python scripts/prepare_data.py
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .venv/bin/python scripts/train_model.py
.venv/bin/python scripts/experiment_structural.py
.venv/bin/python scripts/build_structural_submission.py
.venv/bin/python scripts/build_site.py
.venv/bin/python -m pytest -q
# Optional rebuild of legacy control (does not auto-repackage immutable downloads):
.venv/bin/python scripts/build_submission.py
```

Detailed [requirements matrix](knowledge/session2/requirements_matrix.md) and
[next-session plan](knowledge/session2/next_session.md).

## Limits and next-session priorities

1. **Rules:** three feedback submissions/week per participating entity, one final
   submission across both rounds. Team members cannot submit separate finals
   ([official PDF §3.4](https://docs.nlr.gov/docs/fy26osti/96647.pdf)). Review the group
   registrations; do not multiply the limit across accounts.
2. Implement buffered geographic + fault-system holdouts, matched-mass controls and
   randomized-tangent nulls. Component-only H3 is not enough for model promotion.
3. Extend H4 to multiple verified native 1 m tiles, road/drainage controls, full-grid
   coverage and calibration. Do not equate slope breaks with faults.
4. Implement survey-block holdouts and positive-unlabeled training; normalize within
   training folds. Compare independent terrain and geophysical experts, not more
   untested unions of historical outputs.
5. Record the actual uploaded file hash and its individual score. Public account-best
   scraping cannot recover authenticated submission history or private scores.
6. A GPU and more storage would make deep ensembles practical; code integration,
   validation and training are still necessary. We have ~4 GB RAM and no GPU here.
7. Direct official HTTP downloads may be blocked here. Actions is the alternative;
   failures are recorded, never silently treated as successful verification.
8. Scientific source links and excerpts are checked, but exhaustive accuracy cannot
   honestly be guaranteed. Unknown data licenses, attribution gaps and source conflicts
   are flagged rather than invented away.

## Standing user brief (condensed excerpt; not a verbatim transcript)

> We need to quickly look at the results and our results.
>
> We have a good understanding of how our hypothesis, methodology, calculations, analysis are done so we
> should be able to figure out a way to score higher on the leaderboard using previous results and
> scoring that we have across the sites listed above. We need to come up with distinct and unique
> strategies to score higher in this competition leaderboard. We need to start doing heavy and deep
> research into the part of the project that matters the most, which is the scientific discovery of
> geothermal vents. We should store all of our information and knowledge that we can gather from
> official verified sources. This will serve as a starting point for other projects as well. We need
> to think outside the box but still be grounded in proper scientific research, we are ultimately
> aiming for a top prize that many others are competing for. So it's important to be contrarian but be
> smart about it. We need to find sources of data that others are over looking or areas of the project
> when it comes to geothermal vents. We need to do deep research and critical thinking and come up with
> new hypothesis to test.
>
> 0.3049 is the highest score right now so we need to design a new strategy, research, testing,
> analyzing, and generating submission system than the current website. It should be unique, take
> unique approaches to generating a submission that can score higher than .3049.
>
> The goal of this project is to place top of the leaderboard in this competition. [...] The site
> should be able to generate a TIF file that is required for submission. It should be as easy as
> download to click a File to submit into the competition. This needs to be in the executive summary or
> the very beginning of the site. It should be obvious when you visit the site. [The earlier download
> failed with] "Predicted values must be in range [0, 1]" [and we need] a unique name and a short
> comment to help you or your team tell submissions apart later e.g. clustering with k=25. Create an
> executive summary subpage that explains exactly how to make a submission into the contest.
>
> Work line by line verifying from official verified trusted sources, provide links for manual review.
> There should be no manual input, work on your own to complete tasks. Flag any irregularities for
> review. No hallucinations.
>
> Core Values — **Maximize P(Win)**: in every decision weigh tradeoffs, assess risk, choose the path
> that maximizes the probability of winning. **Own the Outcome**: own results end-to-end, act without
> waiting for permission, treat failure and success as signals and improve.

(De-duplicated submission records: `knowledge/team_results.json`; private email addresses are not needed in the public UI.)

---


## Additional requirements from the user's prompt (de-duplicated, normalized)

This is the standing brief, not a claim that all requested future research is complete:

- Review this repo and the five previous group sites, using the scores listed in
  `knowledge/team_results.json`. Quickly compare with the official leaderboard.
- Research distinct, contrarian but scientifically justified discovery strategies.
  Store official-source knowledge as an auditable, reusable base for other projects.
  Use free public external data, verify rights, provide source links for manual review.
- Make an everyday-use system with current source and results feeds rather than having
  the team manually check every page. Work autonomously; flag irregularities and avoid
  unsupported assertions. “No hallucinations” means evidence-linked claims and explicit
  uncertainty, not a guarantee of omniscience.
- Create a clean, organized, accessible GitHub Pages site. Put a downloadable single-band
  float32 GeoTIFF at the beginning, conforming to the competition CRS, dimensions and
  geotransform, with finite probabilities [0,1] in the template footprint. Prevent the
  reported “Predicted values must be in range [0, 1]” failure. Provide a unique filename,
  short submission comment and a dedicated executive-summary submission guide.
- Understand the overview, problem, About, data tab, reference solution and official
  rules PDF. Train a model, generate predictions and validate them. Complete data
  placement and preparation without requiring the user to download files manually.
  Earlier assertions that GPU training was already ready must be re-verified, not assumed.
- Start with previous-session next steps (H3 structural continuation, H4 native DEM,
  H5 independent priors and later deep models). Explain limitations and needed access.
- Work in three passes: (1) implement and verify; (2) find/fix bugs, omissions and edge
  cases; (3) recheck against the entire request and improve reliability and completeness.
- Open a pull request and merge it if checks and permissions allow. Preserve an explicit
  next-session list, limitations, experiments and observed failures.

**Core Values — Maximize P(Win):** “Maximize the Probability of Winning”: weigh tradeoffs,
assess risk and choose the path that maximizes the probability of success. Set aside
emotions and make the decisions needed for the project's stated goal.

**Own the Outcome:** own results end to end, not just an individual slice. When problems
arise and we have the means to act, act without waiting for permission or assignment.
Treat failure and success as signals, use them to improve and remain accountable to
measured outcomes. These values never override competition rules or evidence integrity.

## Starting links from the brief

- [Competition](https://www.drivendata.org/competitions/306/competition-doe-gems/),
  [problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
  [About](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/),
  [data (sign-in)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/),
  [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).
- [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf).
- [GDR 1391](https://gdr.openei.org/submissions/1391) — broken on direct retrieval.
- The three provided Dropbox raster mirrors and their exact inherited hashes are kept
  in `scripts/download_competition_data.sh`; the demo PDF/OCR inventory and original
  team-site URLs are documented in the knowledge files. Mirrors are not assumed official.
