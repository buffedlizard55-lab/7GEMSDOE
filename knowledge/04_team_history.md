> **Historical session-1 notes; superseded where inconsistent.** Fresh claim-level evidence and corrections: [session-2 audit](session2/review.md), [science ledger](session2/research.md), [source registry](sources.json), [dated feed](feed.json). Inherited source/provenance claims are not independently authenticated by being stored here.

# Team submission history & leaderboard snapshot

## Our accounts (from group records; ranks verified on the public leaderboard 2026-09-26)

| Account | Email | Site used | Best public DW-Tversky | Rank (of 50) | Notes from submission log |
|---|---|---|---|---|---|
| extradr19 | (omitted) | GEMSDOE1 | 0.1563 | #23 | 2 submissions; adopted ensemble, skeleton floor 0.1 |
| smashi34 | (omitted) | GEMSDOE2 | 0.1560 | #24 | 1 submission |
| smrtdoog5 | (omitted) | GEMSDOE3 | 0.1193 | #40 | "1 · SUBMIT FIRST" f347b70daa — Pindrop nodes |
| SDCF9 | (omitted) | GEMSDOE3 | 0.1152 | #41 | "3 · CONTROL · UPLOAD LAST" 4e03fc9705 — Pindrop dense ridge control |
| wbg1 | (omitted) | GEMSDOE3 | 0.0830 | #50 | 2 submissions; "2 · SUBMIT SECOND" 37f9d5b855 — Pindrop catalogue-gap target SECOND SYSTEM |
| (unrecorded) | — | 6GEMSDOE | 0.0286 | — | score from group records; account not recorded |
| (unrecorded) | — | GEMSDOE4 | 0.0343 | — | score from group records; account not recorded |

Group record of sites:
[GEMSDOE](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html) ·
[GEMSDOE2](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html) ·
[GEMSDOE3](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html) ·
[GEMSDOE4](https://buffedlizard55-lab.github.io/GEMSDOE4/) ·
[6GEMSDOE](https://buffedlizard55-lab.github.io/6GEMSDOE/)

## Leaderboard snapshot (public, 2026-09-26, top + neighbours)

| # | participant | best public DW-Tversky | submissions |
|---|---|---|---|
| 1 | DARD | **0.3049** | 10 |
| 2 | alexoktaba | 0.2993 | 13 |
| 3 | HardcoreTechGod | 0.2854 | 6 |
| 4 | mzoorob | 0.2843 | 15 |
| 5 | joeyfezster | 0.2589 | 12 |
| 6 | GrigorSargsyan | 0.2504 | 5 |
| 14 | doegemsDrivendata | 0.1847 | 5 |
| 23 | **extradr19 (us)** | 0.1563 | 2 |
| 24 | **smashi34 (us)** | 0.1560 | 1 |
| 40 | **smrtdoog5 (us)** | 0.1193 | 1 |
| 41 | **SDCF9 (us)** | 0.1152 | 1 |
| 50 | **wbg1 (us)** | 0.0830 | 2 |

50 ranked participants; median ≈ 0.152. `doegemsDrivendata` (#14, 0.1847) has an unverified identity; do not treat this as an authenticated sponsor baseline. Our gap to #1: **0.1486**.

## Lessons carried forward

1. Catalogue DTI is a plumbing monitor; both prize rounds score NEW faults.
2. Detection, not emission width, was the binding constraint in the sibling repo's
   miss-distance audit (median unseen-fault pixel 2.2 km from anything emitted).
3. Format bugs cost real submissions platform-wide ("Predicted values must be in
   range [0, 1]" = NaN inside the scored footprint). The format gate here is
   mandatory and tested.
4. A wider, softer emission beats a thin skeleton under the new-fault proxies
   measured in this repo (0.0249 vs 0.0090 proxy DTI) — the opposite of what
   catalogue DTI suggests. Contrarian but measured.
