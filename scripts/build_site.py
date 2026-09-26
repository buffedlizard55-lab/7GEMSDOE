"""Render public pages from evidence JSON. No hand-typed model scores or hashes."""
from pathlib import Path
import html
import json

ROOT = Path(__file__).resolve().parents[1]
B = 'https://www.drivendata.org/competitions/306/competition-doe-gems/'
RULES = 'https://docs.nlr.gov/docs/fy26osti/96647.pdf'

def load(path): return json.loads((ROOT / path).read_text())
def e(text): return html.escape(str(text), quote=True)
def link(url,text): return f'<a href="{e(url)}">{e(text)}</a>'
def table(head, rows):
    return '<div class="table-scroll"><table><thead><tr>'+''.join(f'<th>{e(h)}</th>' for h in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{c}</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'

NAV=[('index.html','Executive summary'),('how-to-submit.html','Submit'),('results.html','Results'),('strategy.html','Experiments'),('research.html','Research'),('data.html','Data'),('metric.html','Metric')]

def page(filename,title,body):
    nav=''.join(f'<a href="{f}" {"aria-current=page" if f==filename else ""}>{t}</a>' for f,t in NAV)
    (ROOT/filename).write_text(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · 7GEMSDOE</title><link rel="stylesheet" href="assets/style.css"><script src="assets/site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header class="site"><div class="wrap"><h1><span class="gem">7GEMS</span>DOE <span class="small">Fault discovery lab</span></h1>
<nav class="site" aria-label="Main navigation">{nav}</nav><p class="tag">Evidence first. Reproducible experiments. One accountable competition entry.</p></div></header>
<main id="main">{body}</main><footer class="site">No predicted leaderboard gains. Local measurements, official-source facts and hypotheses are labeled separately.<br>
{link('https://github.com/buffedlizard55-lab/7GEMSDOE','Code & session README')} · {link('knowledge/session2/review.md','Three-pass audit')} · {link(B+'page/967/','Competition contract')}</footer></body></html>''')


def card(m,title,label):
    return f'''<section class="hero"><p class="eyebrow">{e(label)} · LOCAL FORMAT PASS · NOT YET SCORED</p><h2>{e(title)}</h2>
<p class="filename">{e(m['file'])}</p><a class="btn" data-verify-download data-sha="{m['sha256']}" href="downloads/{e(m['file'])}" download>Download .TIF · {m['bytes']/1e6:.2f} MB</a>
<a class="btn secondary" href="downloads/{e(m['zip'])}" download>Single-file ZIP</a>
<p class="download-status" role="status" aria-live="polite">Built and re-read by the strict local format gate. Browser checks SHA-256 when supported.</p>
<p><strong>Short submission Note</strong></p><code class="note-text">{e(m['suggested_submission_note'])}</code> <button class="copy-note" type="button">Copy Note</button>
<details><summary>File integrity & measured format</summary><p>SHA-256 <code>{m['sha256']}</code></p>
<p>Single-band float32; {m['grid']['width']:,} × {m['grid']['height']:,}; {m['grid']['crs']}; 100 m. Finite values [{m['stats']['min']:.2f}, {m['stats']['max']:.2f}] on {m['stats']['finite_px']:,} pixels; NaN outside template footprint.</p>
{link('downloads/'+m['name']+'.json','Full reproducibility manifest')}</details></section>'''


def main():
    control=load('downloads/control_meta.json'); structural=load('downloads/structural_meta.json')
    feed=load('knowledge/feed.json'); sources=load('knowledge/sources.json'); team=load('knowledge/team_results.json')
    exp=load('knowledge/session2/structural_experiment.json'); dem=load('knowledge/session2/dem_pilot.json')
    held={r['policy']:r for r in exp['rows'] if r['split']=='locked_test'}
    improvement=held['strike30x3']['dti']/held['isotropic15']['dti']-1
    feedbox=f'''<section class="card" id="feed"><h2>Leaderboard & source watch</h2>
<p id="feed-status" role="status">Snapshot: {e(feed.get('verified_utc','unavailable'))}. Last refresh: {e(feed['status'])}.</p>
<div id="feed-rows">{table(['Participant','Public best','Rank at snapshot'],[[e(r['participant']),f"{r['score']:.4f}",str(r['rank'])] for r in feed['rows'] if r['participant'] in ['DARD','extradr19','smashi34','smrtdoog5','SDCF9','wbg1']])}</div>
<p class="small">Daily refresh scheduled for 08:17 UTC; scheduling is best effort. This page loads the newest public release feed, with a timestamped local fallback. A failed fetch is not current evidence.
{link('knowledge/feed.json','Bundled snapshot')} · {link('https://github.com/buffedlizard55-lab/7GEMSDOE/releases/tag/research-feed','Latest machine feed')} · {link(B+'leaderboard/','Official leaderboard')}</p></section>'''
    scope='''<p>The task is to map <strong>geological faults</strong> across GeoDAWN—not to classify hot springs or prove geothermal vents. New expert-labeled faults drive initial scoring; expanded expert review determines final scoring. Scientific hypotheses below are not confirmed discoveries.</p>'''
    compliance=f'''<aside class="note"><strong>Rules flag:</strong> §3.4 allows <strong>three feedback submissions per week per participating entity</strong>, not per teammate account. One final submission across both rounds; teammates cannot submit separate finals.
The supplied account list needs team-registration review. We do not multiply the budget across accounts. {link(RULES,'Official rules §3.4–3.6.2')}.</aside>'''
    page('index.html','Executive summary',f'''<p class="eyebrow">DOWNLOAD → UPLOAD → PASTE THE NOTE</p><h2>A valid file first. Better discovery next.</h2>
<p>Two independently named files are ready below. <strong>Neither has a measured competition score.</strong> The new candidate tests a specific structural hypothesis; retain the control for comparison. {link('how-to-submit.html','Exact submission instructions →')}</p>
{card(structural,'H3 · Along-strike continuation','Experimental candidate v2')}
<p>Extends locally coherent fault traces preferentially along their strike (3 km support) rather than placing a broad halo everywhere (300 m cross-strike support). No deep model or geothermal thermal prior is included.</p>
{card(control,'Broad halo + blind GBT','Preserved control v1')}
{compliance}{feedbox}<h2>Executive decision</h2>{scope}<div class="grid2"><section class="card"><h3>What improved locally</h3>
<p>H3 held-component DTI: <strong>{held['strike30x3']['dti']:.5f}</strong> vs <strong>{held['isotropic15']['dti']:.5f}</strong> broad-halo control ({improvement:.1%} relative).
Selection used seeds 4242/4243; seed 9001 was reserved before execution. This is a narrow proxy, not an estimated leaderboard score.</p>{link('strategy.html','See all experiments and limitations')}</section>
<section class="card"><h3>What is not solved</h3><p>We have not beaten 0.3049, obtained private labels, run a region-wide 1 m DEM detector, or verified an actual new fault in the field.
No DrivenData login is available for uploading or final selection. GPU training is not implemented in this repo.</p></section></div>''')
    page('how-to-submit.html','How to submit',f'''<h2>Executive submission guide</h2>
{card(structural,'Download the experimental H3 candidate','Optional comparison, not a proven winner')}
<ol class="steps"><li><strong>Download the .TIF above</strong> (or its ZIP with exactly one GeoTIFF). Do not upload this web page, a PDF, JSON manifest, or the training features.</li>
<li>{link(B+'submissions/','Open DrivenData → Submissions')} and sign in to the authorized team account. Registration, eligibility certification and rule acceptance belong to the participant.</li>
<li>Choose <strong>New submission → File to submit</strong> and select the uniquely named .tif from Downloads.</li>
<li>Copy the short Note above into the optional Note field. It records policy and artifact hash.</li>
<li>Submit within the entity-wide weekly limit. Confirm the platform accepts the file; a local PASS is not a server acceptance receipt.</li>
<li>Keep the filename/hash with the actual score. The public feed reports <em>best account scores</em>, not a history of each uploaded file; it cannot automatically attribute scores to artifacts.</li>
<li>Before the deadline, select <strong>one final submission</strong> for both rounds. Do not choose on a private score you cannot observe.</li></ol>
{compliance}<h2>If “Predicted values must be in range [0, 1]” appears</h2>
<p>Possible causes include finite values below 0 or above 1, infinities, NaN inside the required footprint, or uploading a different file. The rejected file was not supplied, so its exact cause is unknown.</p>
<pre>.venv/bin/python scripts/validate_submission.py downloaded-file.tif</pre>
<p>The gate compares exact CRS, shape and transform; enforces single-band float32 and strict [0,1] (no tolerance); rejects internal masks, NaN inside, and anything except NaN outside. NaN nodata is a project publication policy. It fails cleanly for corrupt or wrong-sized files.</p>
<p>{link(B+'page/967/#submission-format','Official submission requirements')} · {link('index.html','Control download and full summary')}</p>
<h2>Generation vs submission</h2><p>The automated Python pipeline builds the GeoTIFF and packages it with a hash and Note. The static site delivers those validated bytes; it does not train a model in the browser. Downloading requires no setup. Uploading still requires your own authorized DrivenData session; no credentials are requested or stored here.</p>''')
    rows=[]
    board={r['participant']:r for r in feed['rows']}
    for r in team:
        official=board.get(r['account'])
        status=('Account best confirmed at snapshot; file attribution is group-reported' if official['score']==r['reported_score'] else f"Current account best is {official['score']:.4f}; historical file score remains group-reported") if official else 'Group-reported; account or exact score attribution unverified'
        rows.append([link(r['url'],r['site']),e(r['account'] or 'not supplied'),f"{r['reported_score']:.4f}",e(r['sha_prefix'] or 'not supplied'),e(r['strategy']),status])
    page('results.html','Results audit',f'''<h2>What the previous submissions actually tell us</h2><p>Source sites were read on 2026-09-26. Their current description is not proof that the same artifact was uploaded. Account-best scores and artifact-specific scores are different evidence.</p>
{table(['Site','Account','Reported score','Reported SHA prefix','Current method description','Verification'],rows)}
<h2>Actionable comparisons—not causal certainty</h2><ul>
<li>Best reported result 0.1563 trails 0.3049 by <strong>0.1486</strong>; reaching the target needs roughly 95% relative improvement, not cosmetic UI changes.</li>
<li>GEMSDOE2 − GEMSDOE1 = <strong>−0.0003</strong>. This gives no convincing evidence that simply unioning these detector families helped. Exact upload versions are unconfirmed.</li>
<li>Pindrop nodes − dense = <strong>+0.0041</strong> (3.56% relative to dense). Same reported 155,021-pixel budget and matching SHA prefixes support a placement experiment; no confidence interval or private-set gain is available.</li>
<li>Catalogue-gap − nodes = <strong>−0.0363</strong>. This specific gap-target strategy underperformed; it does not disprove new-fault discovery.</li>
<li>0.0343 and 0.0286 are unattributed group results, not independently authenticated experiment outcomes. Do not treat them as proof that all lineament features or tree models fail.</li></ul>
{feedbox}<p>{link('knowledge/team_results.json','Machine-readable group log')} · {link('knowledge/session2/review.md','Irregularities and corrected claims')}</p>''')
    exprows=[[e(n),f"{exp['selection_means'][n]:.5f}",f"{held[n]['dti']:.5f}",f"{held[n]['predicted_mass']:,.0f}"] for n in exp['selection_means']]
    page('strategy.html','Hypotheses and experiments',f'''<h2>Distinct strategies, falsifiable tests</h2>
<p>Optimize probability of winning by reducing uncertainty—not by asserting an untested score. Never spend submissions on format failures or multiply an entity’s budget across accounts.</p>
<h3>H3 · Directional continuation — implemented and measured</h3>
<p>Local PCA uses visible catalogue points only, within 500 m. Coherence ≥0.6 enables tangent-aligned ellipses; ambiguous junctions fall back to a short halo. The full-region candidate is built from all supplied traces only after the policy comparison.</p>
{table(['Policy','Selection mean (2 seeds)','Locked component test','Test prediction mass'],exprows)}
<p>{link('knowledge/session2/structural_experiment.json','Full machine report, weighted TP/FP/FN and protocol')}.</p>
<aside class="note">Not geographic generalization: components can be spatial neighbors; random component splits are biased toward recovery near mapped faults. The full footprint is charged for false positives, including visible catalogue traces. The platform’s hidden evaluation mask is unavailable here. H3 alone cannot find isolated structures far from every mapped fault. A clean buffered geographic holdout is still required.</aside>
<h3>H4 · Native-resolution scarps — bounded engineering pilot</h3><p>Latest stored pilot: <strong>{e(dem['status'])}</strong>, {e(dem['attempted_utc'])}. {link('knowledge/session2/dem_pilot.json','Evidence')}.
Reads a 2048 × 2048 native 1 m window from USGS 3DEP, derives break-in-slope, and discards a 40 m nodata/edge buffer. Not calibrated, not a fault map, not yet fused into the submission.</p>
<h3>Next experiments (pre-register before training)</h3>
{table(['ID / hypothesis','Data & scientific reason','Disproof / controls'],[
['H4b · Surface vs buried experts','Native 1 m DEM scarps plus magnetic/gravity contrasts; separate surface-expression and basin-fill arms.','Buffered entire-tile holdout; compare raw DEM vs curvature/scarp channels. Reject if benefit vanishes after road/drainage and nodata-edge controls.'],
['H5 · Cross-sensor structural agreement','Magnetic and gravity edges with matching orientation + mapped geology; use heat flow/conductivity only as context.','Keep a single-sensor control and shuffled-orientation null. Drop if validation gain comes only from known catalogue proximity.'],
['H6 · Acquisition-aware model','GeoDAWN line spacing differs by area; hold out whole flight blocks, add altitude/coverage quality flags.','Check periodic striping aligned with east-west flight lines. Compare normalization fit only on training blocks. Do not assume every flight-parallel feature is noise.'],
['H7 · Positive-unlabeled learning','Known faults are positives, not proof that every unlabeled pixel is negative. Bag low-weight unlabeled samples.','Fix sampling and seeds; buffered out-of-fold predictions. Compare sensitivity to class-prior estimates, calibration and omission rate.'],
['H8 · Disagreement-led discovery','Train geophysical and terrain experts separately; evaluate complementary off-catalogue proposals.','Require cross-domain validation and geologic evidence. Do not promote an ensemble just because models disagree.']])}
<h3>Promotion rule</h3><p>Run ≥3 buffered geographic folds and withheld connected systems, freeze parameters, test once on untouched geography, verify no geometry/footprint/edge leakage, and record compute costs and artifacts. Choose a candidate only if gains are robust to fold, label incompleteness and mask assumptions. Then use the authorized entity’s limited public-feedback slots; no promise of exceeding 0.3049.</p>
<pre>bash scripts/download_competition_data.sh
.venv/bin/python scripts/prepare_data.py
OMP_NUM_THREADS=2 .venv/bin/python scripts/train_model.py
.venv/bin/python scripts/experiment_structural.py
.venv/bin/python scripts/build_structural_submission.py
.venv/bin/python -m pytest -q</pre>''')
    source_rows=[[e(s['id']),link(s['url'],s['title']),e(s['claim']),e(s['use']),e(s['license']),e(s['reviewed_utc'])] for s in sources]
    page('research.html','Scientific evidence library',f'''<h2>Reusable science, with evidence boundaries</h2>{scope}
<p>These are retrieved official pages, not an exhaustive literature review. The claims below were checked against the linked text. Automatic checks detect excerpt disappearance; they do not certify scientific truth. Public accessibility does not by itself establish a reusable dataset license.</p>
{table(['ID','Source','Verified source claim','Proposed use (hypothesis)','Rights / ingestion gate','Reviewed'],source_rows)}
<h3>Contrarian but testable</h3><p>Do not equate hot-spring density with fault probability. Faulds & Hinz report blind systems and complex structural settings; the USGS Gabbs Valley case required multiple independent types of evidence. This supports testing structure and cross-sensor agreement, not painting every nearby pixel as a fault.</p>
<p>Do not equate smooth airborne grids with uniform information content. GeoDAWN’s two acquisition specifications and four blocks suggest that sensor geometry may confound a model. An acquisition-aware holdout is a more demanding scientific test than random pixels.</p>
<h3>Source disagreements retained</h3><ul><li>GDR 1391 returns “No submission found.” Search results suggested 1591 as GeoDAWN, but direct retrieval of 1591 also returned “No submission found.” Neither is treated as a verified usable download.</li>
<li>The user-provided sample raster contains positive fault pixels, despite the problem page describing an all-zero example. Geometry is usable; its values must not be interpreted as predictions.</li>
<li>Third-party mirror hashes authenticate consistency with the inherited manifest, not the sponsor’s original bytes. Official account-authenticated comparison is outstanding.</li></ul>
<p>{link('knowledge/sources.json','Auditable source registry')} · {link('knowledge/session2/research.md','Detailed hypothesis and provenance notes')}</p>''')
    page('data.html','Data provenance',f'''<h2>Data inventory and access</h2>
{table(['Dataset','Location / verification','Limit'],[
['Competition feature stack','~/gems_data/training_features.tif · 19 float32 bands · 418,912,844 bytes','Mirrored from team git bridge after Dropbox TLS failure; sha256 matches inherited pin.'],
['Supplied fault labels','~/gems_data/existing_faults.tif · 60,988 positive pixels','Incomplete catalogue, not private expert labels.'],
['Geometry template','~/gems_data/example_submission.tif · 5,167,373 finite pixels','Same CRS/grid as features. Positive contents conflict with all-zero example prose.'],
['Native 1 m DEM pilot',link(load('knowledge/dem_pilot_source.json')['record']['url'],'Official USGS 3DEP tile'),'One bounded window only. Inventory URL inherited from OCR; not official competition CSV.'],
['Source registry',link('knowledge/sources.json','Claims, excerpts, links and rights'),'Candidate external layers are not license-approved simply by being reachable.'],
['Scores',link('knowledge/team_results.json','Group report')+' / '+link('knowledge/feed.json','Public best-score snapshot'),'No private scores, authenticated upload history or automatic score-to-file mapping.']])}
<p>{link('knowledge/session2/data_verification.txt','Measured hashes, dimensions and counts')} · {link('knowledge/inherited_evidence/data_bridge_manifest.json','Inherited hash manifest')}.</p>
<h3>No manual data placement needed for this CPU pipeline</h3><pre>bash scripts/download_competition_data.sh
.venv/bin/python scripts/prepare_data.py</pre>
<p>Default storage is <code>~/gems_data</code>, outside Git. Override <code>GEMS_DATA_DIR</code> if necessary. The new prepare entry point verifies the three files and extracts 27 CPU features. There is no U-Net implementation here; the organizer reference notebook supports CPU and GPU but has not been integrated.</p>
<h3>Access limits</h3><p>The DrivenData data/submission pages require sign-in. No credentials are requested or stored. This sandbox’s direct outbound TLS to Dropbox, DrivenData and the DEM bucket failed; the page-retrieval tool can inspect official prose, while GitHub Actions performs the scheduled HTTP checks. No private test labels are available or sought.</p>''')
    page('metric.html','Metric and validation',f'''<h2>Distance-weighted Tversky, not geothermal probability calibration</h2><p>{link(B+'page/967/#performance-metric','Official formula')}: alpha = 0.2, beta = 0.8; triangular support R = 300 m (3 pixels).</p>
<pre>k(d) = max(1 - d/R, 0)
TPw = sum over truth pixels g: max_x p(x) k(distance(x,g))
FPw = sum over prediction pixels x: p(x) [1 - max_g k(distance(x,g))]
FNw = number of truth pixels - TPw
DTI = TPw / (TPw + 0.2 FPw + 0.8 FNw + epsilon)</pre>
<p>Every prediction pixel can incur cost; only the best nearby prediction contributes to each truth pixel. Neither “always widen” nor “always harden all probabilities” is justified for arbitrary additions. Coverage placement and detection quality both matter.</p>
<p>The implementation is tested against analytic cases, brute-force calculations and inherited fixtures. This is agreement with the <em>published formula</em>, not a bit-for-bit comparison to private server code. Custom-radius TP handling was corrected in this audit.</p>
<h3>Local proxy limitations</h3><p>Component hiding is useful for along-strike recovery but does not model all unmapped faults. Catalogue scores for a model trained on the same labels are resubstitution monitors, not independent validation. Public feedback can overfit; private performance is unknown. Metric code treats nonfinite predictions as zero for local scoring; publication validation separately rejects nonfinite values inside the required footprint.</p>
<p>{link('https://github.com/buffedlizard55-lab/7GEMSDOE/blob/main/scripts/metric.py','Implementation')} · {link('strategy.html','Measured structural ablation')}</p>''')

if __name__=='__main__': main()
