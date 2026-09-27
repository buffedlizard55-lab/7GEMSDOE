"""Optional real-browser smoke test (pip install playwright; playwright install chromium).

A local HTTP server is scoped to this test; remote feed is mocked to make assertions
reproducible. Does not claim to test the real competition or release availability.
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'scratch/browser'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    server=subprocess.Popen([sys.executable,'-m','http.server','8765','--bind','0.0.0.0'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        # Bounded test-only startup wait, not a persistent service poll.
        for _ in range(30):
            try:
                urlopen('http://127.0.0.1:8765',timeout=1).close(); break
            except OSError: time.sleep(.1)
        feed=json.loads((ROOT/'knowledge/feed.json').read_text())
        payload=json.loads((ROOT/'downloads/gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.payload.json').read_text())
        payload['output_name']=json.loads((ROOT/'downloads/lidar_meta.json').read_text())['file']
        feed['status']='ok'
        checks=[]
        with sync_playwright() as pw:
            browser=pw.chromium.launch()
            for width in [1440,390]:
                ctx=browser.new_context(viewport=dict(width=width,height=950),accept_downloads=True,
                                        permissions=['clipboard-read','clipboard-write'])
                page=ctx.new_page(); errors=[]
                page.on('pageerror', lambda err: errors.append(str(err)))
                page.route('https://api.github.com/**', lambda route: route.fulfill(json={'body':json.dumps(feed)}))
                page.goto('http://127.0.0.1:8765',wait_until='networkidle')
                # the page now opens with the generate-and-download block (session 8)
                assert page.locator('h2').first.inner_text()=='Generate the exact .tif, here, in one click'
                assert page.locator('#generate-tif').is_visible()
                assert page.locator('#validate-file').is_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                page.screenshot(path=str(OUT/f'home-{width}.png'),full_page=True)
                page.locator('.copy-note').first.click()
                expect(page.locator('.copy-note').first).to_have_text('Copied')
                with page.expect_download() as event:
                    page.locator('[data-verify-download]').first.click()
                download=event.value
                m=json.loads((ROOT/'downloads/lidar_meta.json').read_text())
                assert download.suggested_filename == m['file']
                assert hashlib.sha256(Path(download.path()).read_bytes()).hexdigest()==m['sha256']
                page.locator('[data-verify-download]').first.evaluate("e => e.dataset.sha = '0'.repeat(64)")
                page.locator('[data-verify-download]').first.click()
                page.wait_for_function("document.querySelector('.download-status').textContent.includes('mismatch')")
                # 1. the browser rebuilds the submission raster itself and the bytes verify
                with page.expect_download() as gen_event:
                    page.locator('#generate-tif').click()
                gen=gen_event.value
                gen_bytes=Path(gen.path()).read_bytes()
                assert gen_bytes[:4]==b'II*\x00', gen_bytes[:4]
                assert gen.suggested_filename==payload['output_name']
                page.wait_for_function("document.getElementById('generate-status').textContent.includes('Same pixels as the published artifact')")
                import base64 as _b64
                verified=page.evaluate("""async (b64) => {
                    const bin = atob(b64); const u8 = new Uint8Array(bin.length);
                    for (let i=0;i<bin.length;i++) u8[i]=bin.charCodeAt(i);
                    const raster = await window.GEOTIFF.readRaster(u8.buffer);
                    const tpl = await window.GEOTIFF.readRaster(await (await fetch('downloads/' + %s)).arrayBuffer());
                    const ref = {width: tpl.width, height: tpl.height, geo: tpl.geo,
                                 footprint: Uint8Array.from(tpl.values, v => Number.isFinite(v) ? 1 : 0)};
                    const rep = window.GEOTIFF.validate(raster, ref);
                    const sha = await window.GEOTIFF.pixelPayloadSha256(raster.values);
                    return {ok: rep.ok, problems: rep.problems, sha: sha, n: raster.values.length};
                }""" % repr(payload['output_name']), _b64.b64encode(gen_bytes).decode())
                assert verified['ok'], verified['problems']
                assert verified['sha']==payload['pixel_payload_sha256'], (verified['sha'], payload['pixel_payload_sha256'])
                assert verified['n']==payload['grid']['width']*payload['grid']['height']

                # 2. the in-page checker accepts the good file and rejects a corrupted one
                page.set_input_files('#validate-file', str(ROOT/'downloads'/payload['output_name']))
                page.wait_for_function("document.getElementById('validate-status').textContent.includes('matches the competition template')")
                badfile=OUT/'corrupt-nan-inside.tif'
                import rasterio as _rio
                import numpy as _np
                with _rio.open(ROOT/'downloads'/payload['output_name']) as src:
                    prof=src.profile.copy(); arr=src.read(1)
                arr[10,10]=_np.nan
                prof.update(compress='deflate',predictor=3,nodata=_np.nan)
                with _rio.open(badfile,'w',**prof) as dst:
                    dst.write(arr,1)
                page.set_input_files('#validate-file', str(badfile))
                page.wait_for_function("document.getElementById('validate-status').textContent.includes('problem')")
                report=page.locator('#validate-report').inner_text()
                assert 'FAIL' in report and 'not finite' in report or 'NaN' in report, report

                for name in ['how-to-submit','results','strategy','research','data','metric']:
                    response=page.goto(f'http://127.0.0.1:8765/{name}.html',wait_until='networkidle')
                    assert response.status==200
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), name
                assert not errors, errors
                checks.append(dict(width=width,status='PASS',download_sha256=m['sha256'],
                                   checks=['all pages','no horizontal viewport overflow','copy note','download hash',
                                           'mismatch blocked','browser-built raster verified (pixels + format)',
                                           'pre-upload checker PASS on good file','pre-upload checker FAIL on NaN-inside file',
                                           'no JS errors',
                                           'generated_file_sha256='+hashlib.sha256(gen_bytes).hexdigest()]))
                ctx.close()
            browser.close()
        (OUT/'report.json').write_text(json.dumps(dict(status='PASS',feed='mocked release; real download bytes',checks=checks),indent=2)+'\n')
    finally:
        server.terminate(); server.wait(timeout=10)

if __name__=='__main__':
    try:
        main()
    except Exception:
        import traceback
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT/'report.json').write_text(json.dumps(dict(status='FAIL',traceback=traceback.format_exc()),indent=2))
        raise
