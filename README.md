# 7GEMSDOE

**Goal: win the DOE GEMS Prize Challenge** ([DrivenData #306](https://www.drivendata.org/competitions/306/competition-doe-gems/)) —
map the *unmapped* geological faults that indicate geothermal resources in the GeoDAWN region, and beat
the public-leaderboard leader (**0.3049** DW-Tversky; our best so far **0.1563**, rank #23 of 50).

**Live site (GitHub Pages): <https://buffedlizard55-lab.github.io/7GEMSDOE/>** — the home page carries the
one-click **submission.tif** download (format-gated, values strictly in [0, 1]) and the executive summary.

Read this README at the start of every session. Status log: [`STATUS.md`](STATUS.md). Verified knowledge:
[`knowledge/`](knowledge/) (start with `knowledge/00_competition_facts.md`).

---

## North-star prompt (verbatim, per team agreement — 2026-09-26)

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

(Full group message with account list, scores and links: `knowledge/04_team_history.md`.)

---

## How this repo answers the prompt

| Requirement | Where |
|---|---|
| One-click, format-valid **submission.tif** at the very top of the site | `docs/index.html` → `docs/downloads/submission.tif` (values in [0, 1], NaN outside footprint, gate PASS) |
| Executive summary subpage for submitting | `docs/how-to-submit.html` |
| Unique name + Note for submissions | `docs/downloads/submission_meta.json` → `suggested_submission_note` |
| Distinct strategy targeting > 0.3049 | `docs/strategy.html` + `scripts/tune_*.py` (pseudo-new-fault proxies) |
| Deep research from official verified sources, reusable knowledge base | `knowledge/01_science_faults_geothermal.md`, `docs/research.html` |
| Organized, auditable data table with official links + hashes | `docs/data.html`, `knowledge/02_data_sources.md`, `scripts/verify_data.py` |
| No manual input for data placement | `scripts/download_competition_data.sh` (Dropbox mirrors → git-bridge fallback, sha256-verified) |
| Metric exactness | `scripts/metric.py` + `tests/test_metric.py` (reproduces the verified table bit-for-bit) |
| Flag irregularities | `knowledge/00_competition_facts.md` §irregularities |

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
bash scripts/download_competition_data.sh        # official rasters → ~/gems_data (hash-verified)
.venv/bin/python scripts/verify_data.py          # ALL CHECKS PASS
.venv/bin/python scripts/extract_features.py     # 27-channel per-pixel matrix
.venv/bin/python scripts/train_model.py          # blind-fault detector (no distance feature)
.venv/bin/python scripts/tune_components.py      # pseudo-new-fault holdout
.venv/bin/python scripts/sweep_halos.py          # policy sweep on the holdout
.venv/bin/python scripts/build_submission.py     # → docs/downloads/submission.tif (format-gated)
.venv/bin/python -m pytest tests/ -q             # full test suite
```

## Current limitations (own the outcome — what is blocking the top prize)

1. **No GPU in this sandbox** (2 vCPU / 4 GB): deep models (U-Net reference architecture and
   stronger) must train on a GPU runner. Pipeline is ready for it; proxies are ready to judge it.
2. **No DrivenData credentials**: `1m_DEM_links.csv` (and the data tab itself) stay login-walled.
   The three rasters are mirrored and hash-verified without login.
3. **1 m DEM scarp detection not yet run**: 716 tile URLs recovered upstream; downloading +
   scarp extraction is the single biggest untried lever (H4).
4. **Dropbox is egress-blocked in this sandbox**; the download script falls back to the sibling
   repo's git bridge automatically (same bytes, same hashes).
5. Local proxies rank strategies but cannot predict the private-set score; only live submissions do
   (budget: 3/week/account × 5 accounts).

## Next session checklist

- [ ] H3 along-strike extrapolation layer (structure tensor on the fault mask)
- [ ] H4 3DEP 1 m DEM download + scarp/lineament extraction
- [ ] H5 external priors (QFFDB age classes, slip/dilation tendency, heat flow, conductance)
- [ ] H7 GPU-runner U-Net training + pseudo-label loop
- [ ] Submit v1 artifact on one account (Note: `halo r15/h0.6 + blind GBT v1 (7GEMSDOE)`), keep a control
- [ ] Mirror `1m_DEM_links.csv` once credentials are available
