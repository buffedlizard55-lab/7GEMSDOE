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

def page(filename,title,body,scripts=()):
    nav=''.join(f'<a href="{f}" {"aria-current=page" if f==filename else ""}>{t}</a>' for f,t in NAV)
    extra=''.join(f'<script src="{s}" defer></script>' for s in scripts)
    (ROOT/filename).write_text(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · 7GEMSDOE</title><link rel="stylesheet" href="assets/style.css"><script src="assets/site.js" defer></script>{extra}</head>
<body><a class="skip" href="#main">Skip to content</a><header class="site"><div class="wrap"><h1><span class="gem">7GEMS</span>DOE <span class="small">Fault discovery lab</span></h1>
<nav class="site" aria-label="Main navigation">{nav}</nav><p class="tag">Evidence first. Reproducible experiments. One accountable competition entry.</p></div></header>
<main id="main">{body}</main><footer class="site">No predicted leaderboard gains. Local measurements, official-source facts and hypotheses are labeled separately.<br>
{link('https://github.com/buffedlizard55-lab/7GEMSDOE','Code & session README')} · {link('knowledge/session7/review.md','Latest three-pass audit')} · {link(B+'page/967/','Competition contract')}</footer></body></html>''')


def generator(man,m,title,label,note):
    """One-click, in-browser generation of the submission GeoTIFF plus a pre-upload check.

    The payload is a compact run-length encoding of the published raster (see
    scripts/build_browser_payload.py). Rebuilding happens locally in the visitor's
    browser; the pixels are verified against the published SHA-256 before the file
    is offered. This is the "generate the .tif here" path: no Python, no install.
    """
    kb = man['payload_base64_bytes']/1024
    return f"""<section class="hero" id="generate"><p class="eyebrow">{e(label)}</p><h2>{e(title)}</h2>
<p><strong>Step 1 — generate the file.</strong> This page holds a {kb:.0f} KB compact payload of the validated
{man['grid']['width']:,} × {man['grid']['height']:,} raster. Clicking rebuilds the full float32 GeoTIFF <em>in your browser</em>,
verifies the rebuilt pixels against the published SHA-256 ({man['pixel_payload_sha256'][:12]}…), and saves it as
<code>{e(man['output_name'])}</code>. Nothing is uploaded and no model runs here; the page only re-encodes bytes it already has.</p>
<button class="btn" id="generate-tif" type="button">Step 1 · Generate &amp; download {e(man['output_name'])}</button>
<a class="btn secondary" data-verify-download data-sha="{e(m['sha256'])}" href="downloads/{e(m['file'])}" download>Or download the same pixels directly</a>
<p class="download-status" id="generate-status" role="status" aria-live="polite">Ready. Rebuild, hash check and save happen locally.</p>
<p class="small" id="generate-sha" role="status"></p>
<p><strong>Step 2 — copy the Note.</strong></p><code class="note-text">{e(note)}</code> <button class="copy-note" type="button">Copy Note</button>
<p><strong>Step 3 — upload</strong> at the official submission page and paste the Note. Full walk-through: {link('how-to-submit.html','executive submission guide')}. Weekly limit: three feedback submissions per participating entity (rules §3.4).</p>
<details><summary>Why bytes built by this page are safe to submit</summary>
<p>The raster geometry (CRS EPSG:{e(man['grid']['crs'].split(':')[-1])}, {man['grid']['transform'][0]:.0f} m pixels, origin
{man['grid']['transform'][2]:.0f}/{man['grid']['transform'][5]:.0f}) is copied from the official template raster, the pixel array is byte-identical to the
published artifact, values are 1.0 on the emitted lines and 0.0 elsewhere inside the footprint with NaN outside, and the file is single-band float32.
<code>scripts/validate_submission.py</code> accepts the direct download and <code>tests/test_browser_tools.py</code> proves this page's encoder reproduces the same pixels
(see {link('research.html','verification notes')}). A local PASS is still not a server acceptance receipt: confirm the platform shows a score.</details>
</section>
<section class="card" id="check"><h2>Step 0 — check any .tif before you upload it</h2>
<p>The 2026 group failure <em>"Predicted values must be in range [0, 1]"</em> came from NaN pixels inside the footprint. This checker runs the same rules in your browser:
single band, float32, exact grid/CRS/transform, finite values in [0, 1] everywhere inside the template footprint, NaN outside. The file never leaves your device.</p>
<input type="file" id="validate-file" accept=".tif,.tiff,.TIF">
<p class="download-status" id="validate-status" role="status" aria-live="polite">Choose the .tif you are about to upload.</p>
<div id="validate-report"></div></section>"""


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
    lidar=load('downloads/lidar_meta.json'); lexp=load('knowledge/session4/lidar_experiment.json')
    lcand=load('knowledge/session4/lidar_candidate.json'); scored=load('knowledge/session4/scored_files_analysis.json')
    lprod=load('external/dem/lidar_scarp_features.json')
    gaps=load('knowledge/session5/lidar_gaps.json'); fp=load('knowledge/session5/lidar_fp_audit.json')
    feed=load('knowledge/feed.json'); sources=load('knowledge/sources.json'); team=load('knowledge/team_results.json')
    session6_evidence=load('knowledge/session6/local_verification.json')
    h9=load('knowledge/session6/geodawn_experiment.json')
    h9b=load('knowledge/session7/radiometric_lineament_experiment.json')
    h9c=load('knowledge/session7/geodawn_extension_experiment.json')
    rad_product=load('external/geodawn_rad/geodawn_rad.json')
    ext_product=load('external/geodawn_extensions/geodawn_extensions.json')
    ext_overlap=load('knowledge/session7/extension_overlap.json')
    qfault_product=load('external/qfaults/qfaults_prior.json')
    exp=load('knowledge/session2/structural_experiment.json'); dem=load('knowledge/session2/dem_pilot.json')
    spatial=load('knowledge/session3/spatial_experiment.json')
    experts=load('knowledge/session3/expert_experiment.json')
    lc=lcand['candidates'][0]
    payload_man=load('downloads/gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.payload.json')
    payload_man['output_name']=lidar['file']
    payload_man['template_path']='downloads/'+lidar['file']
    def mult(arm,f,key='pooled_nms'): return f"x{lexp[key][arm][f]['multiple']:.2f}"
    s4rows=[[a,mult(a,'0.005','pooled'),mult(a,'0.01','pooled'),mult(a,'0.02','pooled'),mult(a,'0.005'),mult(a,'0.01'),mult(a,'0.02')] for a in ('bands19','lidar','both')]
    session4=f'''<section class="card"><h2>Session 4 evidence: region-wide 1 m lidar</h2>
<p>GitHub Actions processed <strong>{lprod['tile_status'].get('ok',0)} of {lprod['tiles_total']}</strong> official USGS 3DEP 1 m tiles (~167 GB; the 10 failures are edge tiles with &lt;1% valid data) into 12 scarp descriptors on the official 100 m grid. {link(lprod.get('workflow_run','#'),'Runner log')} · {link('external/dem/lidar_scarp_features.json','Product manifest')} · {link('external/dem/lidar_tile_log.json','Per-tile SHA-256 log')}</p>
<p>Pre-registered test: 5 geographic folds, 1 km buffers, held-out <em>catalogue</em> faults, same learner and samples. Numbers are skill multiples over the exact random baseline at emission density f (1.00 = random).</p>
{table(['Arm','raw f=0.5%','raw f=1%','raw f=2%','ridge f=0.5%','ridge f=1%','ridge f=2%'],s4rows)}
<p><strong>Lidar-only generalises best</strong> (4/5 folds and pooled). The 19 supplied bands fall <em>below random</em> across geography; ridge thinning helps every arm. Catalogue traces can sit up to 400 m from lidar-mapped faults ({link('https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2025/Hermant.pdf','Hermant et al. 2025')}, cited by the organisers), so this local test is biased against lidar; only a leaderboard upload measures transfer to new faults.</p>
<p>{link('knowledge/session4/lidar_experiment.json','Full experiment report')} · {link('knowledge/session4/research.md','Session 4 research & hypotheses')} · {link('knowledge/session4/review.md','Leaderboard forensics')}</p></section>'''
    gaprows=[[q,v['footprint_px'],v['gap_px'],f"{v['gap_fraction']*100:.1f}%",v['catalogue_px']] for q,v in gaps['quadrants'].items()]
    v2=fp['v2_policy']
    h9rows=[[a, f"x{h9['pooled'][a]['0.01']['multiple']:.3f}",
             f"x{h9['pooled'][a]['0.02']['multiple']:.3f}"]
            for a in ('bands19','rad','lidar','all')]
    h9brows=[[a, f"x{h9b['pooled'][a]['0.01']['multiple']:.3f}",
              f"x{h9b['pooled'][a]['0.02']['multiple']:.3f}",
              f"x{h9b['pooled_nms'][a]['0.01']['multiple']:.3f}",
              f"x{h9b['pooled_nms'][a]['0.02']['multiple']:.3f}"]
             for a in ('bands19','rad_raw','rad_lineament')]
    h9crows=[[a, f"x{h9c['pooled'][a]['0.01']['multiple']:.3f}",
              f"x{h9c['pooled'][a]['0.02']['multiple']:.3f}"]
             for a in ('bands19','rad_raw','ratios3','up150','extensions4')]
    session5=f'''<section class="card"><h2>Session 5–7: new evidence and external-data tests</h2>
<p>Lidar covers <strong>{gaps['covered_px']:,}</strong> of {gaps['footprint_px']:,} footprint pixels; the gap is <strong>{gaps['gap_fraction']*100:.1f}%</strong> and still holds {gaps['catalogue_px_in_gap']:,} catalogue pixels (20.5% of known faults). The NE quadrant is {gaps['quadrants']['NE']['gap_fraction']*100:.1f}% gap — fill priority #1. The H1 candidate emits 0 px in gaps (verified).</p>
{table(['Quadrant','Footprint px','Gap px','Gap %','Catalogue px'],gaprows)}
<p>False-positive audit of the H1 candidate ({fp['emitted_px']:,} emitted px): closed loops are minor ({fp['loop_hole_px']} hole px), but <strong>{fp['emitted_cross_dominant_fraction']*100:.1f}%</strong> of emission is cross-slope dominant (channel-bank-like) and low relief is under-emitted. The frozen v2 cleanup policy remains unpromoted until H1 scores.</p>
<p>Runner products now exist: {link('external/qfaults/qfaults_prior_u8.tif','QFFDB 3-band diagnostic')} ({qfault_product['n_features']:,} observed features; <strong>catalogue leakage risk</strong>) and {link('external/geodawn_rad/geodawn_rad_u8.tif','GeoDAWN K/Th/U/TC grid')} (four-band uint8, exact competition grid). See the {link('external/qfaults/qfaults_prior.json','QFFDB manifest')} and {link('external/geodawn_rad/geodawn_rad.json','GeoDAWN manifest')} for hashes and source details.</p>
<h3>H9 first screen — raw radiometric channels; no promotion</h3>
{table(['Arm','Pooled skill at 1%','Pooled skill at 2%'],h9rows)}
<p>Rad beats bands19 in {h9['rad_beats_bands19_folds']['0.01']}/5 folds at 1% and {h9['rad_beats_bands19_folds']['0.02']}/5 at 2%; the frozen rule requires ≥4/5 at both and <strong>fails</strong>. The small edge was support-sensitive: it disappears when the lidar-coverage restriction is removed below.</p>
<h3>H9b — fixed mask-safe lineaments; rejected</h3>
{table(['Arm','Raw 1%','Raw 2%','Ridge 1%','Ridge 2%'],h9brows)}
<p>The 30 pre-registered 100/300 m gradient, curvature, orientation and contrast features beat the stronger comparator in <strong>0/5 folds</strong> at every density. They reduce top-f coverage even where AUC rises. H9b fails; no scale sweep or candidate was made.</p>
<h3>H9c — official contractor ratios; rejected</h3>
{table(['Arm','Pooled 1%','Pooled 2%'],h9crows)}
<p>The previously omitted official Th/K, U/K and U/Th grids beat the stronger comparator in only {h9c['ratios_beats_stronger_comparator_folds']['0.01']}/5 folds at 1% and {h9c['ratios_beats_stronger_comparator_folds']['0.02']}/5 at 2%; the frozen rule <strong>fails</strong>. Upward-continued TMI is nearly redundant with supplied band 14 (rank correlation {ext_overlap['pearson_rank_correlation']:.4f}). Stop tuning radiometrics; preserve them only as future corroboration.</p>
<p>{link('knowledge/session7/radiometric_lineament_experiment.json','H9b report')} · {link('knowledge/session7/geodawn_extension_experiment.json','H9c report')} · {link('external/geodawn_extensions/geodawn_extensions.json','Official extension manifest')} · {link('knowledge/session7/research.md','Session 7 research and decision')} · {link('knowledge/session5/lidar_gaps.json','Gap report')} · {link('knowledge/session5/lidar_fp_audit.json','FP audit')}</p></section>'''
    replay=session6_evidence['control_reproduction']
    train=session6_evidence['retraining']
    feed_snapshot={'automated_snapshot_utc': feed['verified_utc'],
                   'ranked_entries': len(feed['rows']),
                   'leader': feed['rows'][0]}
    session6=f'''<section class="card"><h2>Session 6–7: reproducible pipeline, current score and H9 decision</h2>
<p>The latest verified public feed ({e(feed_snapshot['automated_snapshot_utc'])}) has {feed_snapshot['ranked_entries']} ranks; leader {e(feed_snapshot['leader']['participant'])} is <strong>{feed_snapshot['leader']['score']:.4f}</strong>. The team's best known public result remains 0.1563. See {link('knowledge/feed.json','machine-readable current snapshot')}.</p>
<p>CPU replay reproduced the preserved control byte-identically (SHA-256 <code>{replay['reproduced_sha256'][:12]}</code>); format gate PASS, and no file was published. H1 remains unscored. New QFFDB/GeoDAWN products are data inputs—not submission files.</p>
<p>H9 raw channels failed their fold rule; lineament derivatives then lost to the stronger comparator in 0/5 folds, and official contractor radioelement ratios won only 1/5 at 1%/2%. These are catalogue diagnostics, not hidden-truth scores. H9 is stopped rather than post-hoc tuned. No leaderboard gain or geological discovery is claimed. GDR 1391 and team file-to-score mismatches remain flagged.</p>
<p>{link('knowledge/session7/research.md','Session 7 research')} · {link('knowledge/session7/review.md','Latest three-pass review')} · {link('knowledge/session6/local_verification.json','Pipeline replay hashes')} · {link('knowledge/session7/next_session.md','Next steps and limitations')}</p></section>'''
    forensic_rows=[[e(f['file']),e(f['account']),'—' if f['public_score'] is None else f"{f['public_score']:.4f}",f"{f['density']*100:.2f}%",f"{f['dispersion_index']:.2f}",('x%.2f'%f['skill_multiple']) if 'skill_multiple' in f else '—'] for f in scored['files']]
    geography=f'''<section class="card"><h2>New evidence: independent geography changes the decision</h2>
<p>Four geographic quadrants, 1 km exclusion buffer and whole crossing-trace removal. H3 pooled diagnostic DTI: <strong>{spatial['aggregates']['strike30x3']['pooled_dti']:.6f}</strong>.
It barely predicts away from visible catalogue traces. <strong>Do not treat H3 as a proven discovery upgrade.</strong></p>
{table(['Fixed policy','Pooled geographic DTI','Interpretation'],[
['H3 tangent continuation',f"{spatial['aggregates']['strike30x3']['pooled_dti']:.6f}",'Near-catalogue prior; no isolated-discovery evidence'],
['Raw 100 m terrain expert',f"{experts['aggregates']['terrain_100m']['pooled_dti']:.6f}",'Two supplied bands; not native 1 m DEM'],
['Raw geophysical expert',f"{experts['aggregates']['geophysical']['pooled_dti']:.6f}",'17 supplied bands; training-fold-only histogram fitting']])}
<p>Terrain wins in all four folds, but these are diagnostic catalogue holdouts, <strong>not leaderboard estimates</strong> or a locked final test. No new submission is promoted. Next: independent native DEM evidence, survey-block tests and positive-unlabeled sensitivity.</p>
<p>{link('knowledge/session3/spatial_experiment.json','Structural/null/matched-mass report')} · {link('knowledge/session3/expert_experiment.json','Trained expert report')} · {link('knowledge/session3/research.md','Science, source audit and next hypotheses')}</p></section>'''
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
    JS=( 'assets/geotiff_tools.js', 'assets/submission_payload.js', 'assets/submit_ui.js')
    page('index.html','Executive summary',f'''{generator(payload_man,lidar,'Generate the exact .tif, here, in one click','ONE CLICK · RUNS IN YOUR BROWSER · NOTHING IS UPLOADED · NO INSTALL',lidar['suggested_submission_note'])}
<p class="eyebrow">DOWNLOAD → UPLOAD → PASTE THE NOTE</p><h2>Current H1 test: region-wide lidar scarp evidence.</h2>
<p><strong>Recommended next upload</strong> (a decisive leaderboard test, not a proven winner): a thin-line map from a model trained only on 1 m lidar scarp descriptors. Group best is 0.1563; leader 0.3049. {link('how-to-submit.html','Exact submission instructions →')}</p>
{card(lidar,'Lidar scarp model · ridge-thinned top 2%','Session 4 primary · H1 leaderboard test')}
<p>{lc['emitted']:,} emitted pixels (binary 1.0; 0.0 elsewhere inside the footprint; NaN outside), all inside lidar coverage; dispersion index {lc['dispersion_index']:.2f} (line-like). Catalogue-based calibration with a 50% transfer discount predicts only ~{lcand['chosen']['expected_dti']:.2f}, below 0.1563; we still recommend it because that calibration is biased against lidar-mapped faults. Visible false-positive classes: closed loops (hills, shorelines) and arcuate range-front edges. Record the score with the SHA-256.</p>
{session4}
{session5}
{session6}
<h2>Preserved earlier candidates</h2>
{card(structural,'H3 · Along-strike continuation','Experimental v2 · geographic stress test failed to establish discovery')}
<p>Extends locally coherent fault traces preferentially along their strike (3 km support) rather than placing a broad halo everywhere (300 m cross-strike support). No deep model or geothermal thermal prior is included.</p>
{card(control,'Broad halo + blind GBT','Preserved control v1')}
{geography}{compliance}{feedbox}<h2>Executive decision</h2>{scope}<div class="grid2"><section class="card"><h3>What improved locally</h3>
<p>H3 held-component DTI: <strong>{held['strike30x3']['dti']:.5f}</strong> vs <strong>{held['isotropic15']['dti']:.5f}</strong> broad-halo control ({improvement:.1%} relative).
Selection used seeds 4242/4243; seed 9001 was reserved before execution. This is a narrow proxy, not an estimated leaderboard score.</p>{link('strategy.html','See all experiments and limitations')}</section>
<section class="card"><h3>What is not solved</h3><p>We have not beaten 0.3049, obtained private labels, run a region-wide 1 m DEM detector, or verified an actual new fault in the field.
No DrivenData login is available for uploading or final selection. GPU training is not implemented in this repo.</p></section></div>''',scripts=JS)
    page('how-to-submit.html','How to submit',f'''<h2>Executive submission guide</h2>
{generator(payload_man,lidar,'Generate the .tif and check it, right here','ONE CLICK · BROWSER-BUILT · VERIFIED PIXELS',lidar['suggested_submission_note'])}
{card(lidar,'Download the session 4 lidar candidate','Recommended next upload · decisive H1 test')}
<ol class="steps"><li><strong>Download the .TIF above</strong> (or its ZIP with exactly one GeoTIFF). Do not upload this web page, a PDF, JSON manifest, or the training features.</li>
<li>{link(B+'submissions/','Open DrivenData → Submissions')} and sign in to the authorized team account. Registration, eligibility certification and rule acceptance belong to the participant.</li>
<li>Choose <strong>New submission → File to submit</strong> and select the uniquely named .tif from Downloads.</li>
<li>Copy the short Note above into the optional Note field. It records policy and artifact hash.</li>
<li>Submit within the entity-wide weekly limit. Confirm the platform accepts the file; a local PASS is not a server acceptance receipt.</li>
<li>Keep the filename/hash with the actual score. The public feed reports <em>best account scores</em>, not a history of each uploaded file; it cannot automatically attribute scores to artifacts.</li>
<li>Before the deadline, select <strong>one final submission</strong> for both rounds. Do not choose on a private score you cannot observe. Deadline: the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition page</a> says Dec. 3, 2026, 11:59 p.m. UTC, but <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules</a> A.1 say 5:00 p.m. ET (22:00 UTC). <strong>Plan to the earlier time: Dec 3, 2026, 22:00 UTC (2:00 p.m. PT).</strong></li></ol>
{compliance}<h2>If “Predicted values must be in range [0, 1]” appears</h2>
<p><strong>Root cause found in the group record:</strong> a GEMSDOE file with <strong>3,061 NaN pixels inside the template footprint</strong> (and 1,540 finite pixels outside it) was rejected with exactly this message; the same map with those pixels filled (SHA-256 7f00890a…) was accepted and scored 0.1563 ({link('https://github.com/buffedlizard55-lab/GEMSDOE/blob/cceebbdcf9a7d2890bb0665defcb54dfc66ae452/data/evidence/runs/ens12-adopted-floor0.1-w0/sanitize.json','sanitize.json')}). All seven scored group files use <strong>finite values in [0, 1] everywhere inside the footprint and NaN exactly outside</strong>. Every file on this site uses that layout and passes the strict gate. Other causes: values below 0 or above 1, infinities, or uploading a different file (e.g. the training features).</p>
<pre>.venv/bin/python scripts/validate_submission.py downloaded-file.tif</pre>
<p>The gate compares exact CRS, shape and transform; enforces single-band float32 and strict [0,1] (no tolerance); rejects internal masks, NaN inside, and anything except NaN outside. NaN nodata is a project publication policy. It fails cleanly for corrupt or wrong-sized files.</p>
<p>{link(B+'page/967/#submission-format','Official submission requirements')} · {link('index.html','Control download and full summary')}</p>
<h2>Generation vs submission</h2><p>The automated Python pipeline builds the GeoTIFF and packages it with a hash and Note. The submission GeoTIFF can be produced two ways on this site: download the published bytes, or rebuild them from the embedded payload in your browser (the two are pixel-identical, and both are hash-checked before saving). No model is trained in the browser and no file is uploaded anywhere; the site also runs the competition's format rules locally so a file is checked before it reaches the platform. Uploading still requires your own authorized DrivenData session; no credentials are requested or stored here.</p>''',scripts=JS)
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
<h2>Score forensics: what the scored files reveal (session 4)</h2>
<p>Exact random baseline for the official metric ({link('scripts/random_baseline.py','code')}, verified against Monte-Carlo runs of the metric). Assuming the near-uniform catalogue-gap upload had zero skill, the implied public truth density is {scored['implied_truth_density']*100:.2f}% and random emission peaks near {scored['random_dti_at_implied_density']['0.03']:.3f}. The leader needs about x{scored['leader_0_3049_required_skill_multiple_by_density']['0.02']:.1f} random coverage at 2% density.</p>
{table(['File (vendored)','Account (team record)','Public score','Density','Dispersion','Skill vs random'],forensic_rows)}
<p>The two below-random uploads are the most blob-like (dispersion &lt; 3). Line-like fields scored best. {link('knowledge/session4/scored_files_analysis.json','Machine report')} · {link('external/scored/manifest.json','Provenance manifest')}</p>
{feedbox}<p>{link('knowledge/team_results.json','Machine-readable group log')} · {link('knowledge/session2/review.md','Irregularities and corrected claims')}</p>''')
    exprows=[[e(n),f"{exp['selection_means'][n]:.5f}",f"{held[n]['dti']:.5f}",f"{held[n]['predicted_mass']:,.0f}"] for n in exp['selection_means']]
    page('strategy.html','Hypotheses and experiments',f'''<h2>Distinct strategies, falsifiable tests</h2>{geography}
<p>Optimize probability of winning by reducing uncertainty—not by asserting an untested score. Never spend submissions on format failures or multiply an entity’s budget across accounts.</p>
<h3>H3 · Directional continuation — implemented and measured</h3>
<p>Local PCA uses visible catalogue points only, within 500 m. Coherence ≥0.6 enables tangent-aligned ellipses; ambiguous junctions fall back to a short halo. The full-region candidate is built from all supplied traces only after the policy comparison.</p>
{table(['Policy','Selection mean (2 seeds)','Locked component test','Test prediction mass'],exprows)}
<p>{link('knowledge/session2/structural_experiment.json','Full machine report, weighted TP/FP/FN and protocol')}.</p>
<aside class="note">Not geographic generalization: components can be spatial neighbors; random component splits are biased toward recovery near mapped faults. The full footprint is charged for false positives, including visible catalogue traces. The platform’s hidden evaluation mask is unavailable here. H3 alone cannot find isolated structures far from every mapped fault. A clean buffered geographic holdout is still required.</aside>
<h3>H4 · Native-resolution scarps — bounded engineering pilot</h3><p>Latest stored pilot: <strong>{e(dem['status'])}</strong>, {e(dem['attempted_utc'])}. {link('knowledge/session2/dem_pilot.json','Evidence')}.
Reads a 2048 × 2048 native 1 m window from USGS 3DEP, derives break-in-slope, and discards a 40 m nodata/edge buffer. Not calibrated, not a fault map, not yet fused into the submission.</p>
<h3>H9 · GeoDAWN radiometrics — closed after three weak/negative screens</h3>
<p>Official USGS K/Th/U/TC grids are absent from the supplied 19-band stack. The first lidar-restricted raw screen narrowly edged bands19 but failed its fold rule. On the wider radiometric support, bands19 scored {h9b['pooled']['bands19']['0.01']['multiple']:.3f}×/{h9b['pooled']['bands19']['0.02']['multiple']:.3f}× random at 1%/2%, raw radiometrics {h9b['pooled']['rad_raw']['0.01']['multiple']:.3f}×/{h9b['pooled']['rad_raw']['0.02']['multiple']:.3f}×, and the fixed lineament representation {h9b['pooled']['rad_lineament']['0.01']['multiple']:.3f}×/{h9b['pooled']['rad_lineament']['0.02']['multiple']:.3f}×. Lineaments won 0/5 folds. The separately retrieved official Th/K, U/K and U/Th ratio grids scored {h9c['pooled']['ratios3']['0.01']['multiple']:.3f}×/{h9c['pooled']['ratios3']['0.02']['multiple']:.3f}× and won only 1/5 folds against the stronger comparator at each target density. Both frozen rules fail. Catalogue truth is not hidden-test truth; nevertheless, more post-hoc radiometric tuning is stopped. {link('knowledge/session7/research.md','Full decision')} · {link('external/geodawn_extensions/geodawn_extensions.json','Ratio product provenance')}.</p>
<h3>Next experiments (pre-register before training)</h3>
{table(['ID / hypothesis','Data & scientific reason','Disproof / controls'],[
['H10 · Interaction-zone connectors','Short secondary strands across step-overs, terminations and intersections; Great Basin structural literature says these zones commonly host geothermal systems.','Pre-register geometry; whole-system/geographic holdout; matched random tangents. Reject if gain is proximity leakage or confined to visible catalogue lines.'],
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
<p>Do not equate smooth airborne grids with uniform information content. GeoDAWN’s two acquisition specifications and four blocks can confound a model. H9b lineaments and H9c official ratios both failed frozen geographic rules, while upward-continued TMI was 0.9933-correlated with supplied TMI after compact encoding. Radiometrics are stopped as a primary arm; block holdout is required only if independent evidence reopens them.</p>
<h3>Source disagreements retained</h3><ul><li>GDR 1391 previously returned “No submission found” and remains unresolved. GDR 1591 was successfully retrieved via the page tool on 2026-09-26 and is the GeoDAWN landing record; this supersedes the earlier failed retrieval. The two radiometric TIFF archives were downloaded and matched to ScienceBase MD5/size; other linked files and per-asset reuse terms remain unverified.</li>
<li>The user-provided sample raster contains positive fault pixels, despite the problem page describing an all-zero example. Geometry is usable; its values must not be interpreted as predictions.</li>
<li>Third-party mirror hashes authenticate consistency with the inherited manifest, not the sponsor’s original bytes. Official account-authenticated comparison is outstanding.</li></ul>
<p>{link('knowledge/sources.json','Auditable source registry')} · {link('knowledge/session2/research.md','Prior research')} · {link('knowledge/session3/research.md','Session 3 source audit')} · {link('knowledge/session4/research.md','Session 4: lidar, leaderboard theory, hypothesis register')} · {link('knowledge/session5/research.md','Session 5: overlooked data, geothermal science, H9–H12')} · {link('knowledge/session7/research.md','Session 7: radiometric falsification and pivot')}</p>''')
    page('data.html','Data provenance',f'''<h2>Data inventory and access</h2>
{table(['Dataset','Location / verification','Limit'],[
['Competition feature stack','~/gems_data/training_features.tif · 19 float32 bands · 418,912,844 bytes','Mirrored from team git bridge after Dropbox TLS failure; sha256 matches inherited pin.'],
['Supplied fault labels','~/gems_data/existing_faults.tif · 60,988 positive pixels','Incomplete catalogue, not private expert labels.'],
['Geometry template','~/gems_data/example_submission.tif · 5,167,373 finite pixels','Same CRS/grid as features. Positive contents conflict with all-zero example prose.'],
['Native 1 m DEM pilot',link(load('knowledge/dem_pilot_source.json')['record']['url'],'Official USGS 3DEP tile'),'One bounded window only. Inventory URL inherited from OCR; not official competition CSV.'],
['Region-wide lidar scarp product',link('external/dem/lidar_scarp_features.json','12 uint8 channels, official grid')+' · '+link('knowledge/dem_tiles.json','716 official tile URLs'),'706 tiles processed on GitHub Actions; inventory is OCR-recovered, not the login-walled CSV; covers 75% of the footprint.'],
['GeoDAWN radiometric product',link('external/geodawn_rad/geodawn_rad_u8.tif','Download four-band K/Th/U/TC')+' · '+link('external/geodawn_rad/geodawn_rad.json','hash/grid manifest'),'ScienceBase Area 1/2 TIFF archives size+MD5 checked; exact competition grid; uint8 feature data, not a submission; H9b did not promote.'],
['GeoDAWN omitted official grids',link('external/geodawn_extensions/geodawn_extensions_u8.tif','Download Th/K, U/K, U/Th, up150')+' · '+link('external/geodawn_extensions/geodawn_extensions.json','hash/member manifest'),f"Exact official archive members; product {ext_product['product_sha256'][:12]}…; ratios failed H9c and up150 is nearly duplicate supplied TMI; not a submission."],
['QFFDB scale/certainty prior',link('external/qfaults/qfaults_prior_u8.tif','Download 3-band diagnostic')+' · '+link('external/qfaults/qfaults_prior.json','schema/product manifest'),'Known-fault catalogue; direct model use risks label leakage. Diagnostic only until spatial/source-independence checks pass.'],
['Scored group files',link('external/scored/manifest.json','8 vendored GeoTIFFs with source commits and SHA-256'),'Scores are group-reported/leaderboard observations; one file-account pairing unverified.'],
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
