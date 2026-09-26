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
                assert page.locator('h2').first.inner_text()=='Session 4: test region-wide lidar scarp evidence.'
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
                for name in ['how-to-submit','results','strategy','research','data','metric']:
                    response=page.goto(f'http://127.0.0.1:8765/{name}.html',wait_until='networkidle')
                    assert response.status==200
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), name
                assert not errors, errors
                checks.append(dict(width=width,status='PASS',download_sha256=m['sha256'],
                                   checks=['all pages','no horizontal viewport overflow','copy note','download hash','mismatch blocked','no JS errors']))
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
