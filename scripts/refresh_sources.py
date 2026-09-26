"""Refresh official-source excerpts + leaderboard. Failures never become evidence.

Network checks verify excerpt presence, not scientific truth. Changed/missing
text is flagged for review. The last successful leaderboard is retained with
its original timestamp; attempt status and staleness remain visible.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/'


def parse_leaderboard(html):
    soup = BeautifulSoup(html, 'html.parser')
    rows = []
    for tr in soup.select('table tr'):
        cells = tr.find_all('td')
        if len(cells) < 4:
            continue
        rank = re.fullmatch(r'#?\s*(\d+)', cells[0].get_text(' ', strip=True))
        if not rank:
            continue
        score_text = cells[3].get_text(' ', strip=True)
        if not re.fullmatch(r'\d+\.\d+', score_text):
            raise ValueError('score column changed')
        score = float(score_text)
        if not 0 <= score <= 1:
            raise ValueError('score outside [0,1]')
        participant = cells[2].get_text(' ', strip=True)
        link = cells[2].select_one('a[href*="/users/"]')
        name = link.get_text(strip=True) if link else re.split(r'\s+\d+[wdhm]', participant)[0]
        rows.append(dict(rank=int(rank[1]), participant=name, score=score))
    if not rows or rows[0]['rank'] != 1 or len({r['rank'] for r in rows}) != len(rows):
        raise ValueError('no valid unique ranked table; login/error/layout change possible')
    if any(a['score'] < b['score'] for a, b in zip(rows, rows[1:])):
        raise ValueError('leaderboard no longer descending')
    return rows


def refresh(previous, getter=requests.get):
    now = datetime.now(timezone.utc).isoformat()
    result = dict(previous, attempted_utc=now)
    response = None
    try:
        response = getter(URL, timeout=(10, 40))
        response.raise_for_status()
        rows = parse_leaderboard(response.text)
        result.update(status='ok', verified_utc=now, rows=rows,
                      source=URL, response_sha256=hashlib.sha256(response.content).hexdigest(),
                      method='automated HTML table parse', error=None)
    except (requests.RequestException, ValueError) as exc:
        result.update(status='refresh_failed', error=str(exc)[:500])
        if response is not None:
            soup = BeautifulSoup(response.text, 'html.parser')
            result['parse_diagnostics'] = [dict(cells=[td.get_text(' ', strip=True) for td in tr.find_all(['td','th'])], html=str(tr)[:3000]) for tr in soup.select('table tr')[:3]]
    return result


def main():
    dest = ROOT / 'knowledge/feed.json'
    old = json.loads(dest.read_text()) if dest.exists() else {}
    feed = refresh(old)
    results = []
    for source in json.loads((ROOT / 'knowledge/sources.json').read_text()):
        record = dict(id=source['id'], url=source['url'], checked_utc=feed['attempted_utc'])
        try:
            res = requests.get(source['url'], timeout=(10, 40))
            res.raise_for_status()
            text = ' '.join(BeautifulSoup(res.text, 'html.parser').get_text(' ', strip=True).split())
            ok = source['excerpt'] in text
            record.update(status='excerpt_found' if ok else 'REVIEW_excerpt_missing',
                          sha256=hashlib.sha256(res.content).hexdigest())
            # Keep excerpts rather than republish entire papers.
        except requests.RequestException as exc:
            record.update(status='unreachable', error=str(exc)[:300])
        results.append(record)
    feed['source_checks'] = results
    temp = dest.with_suffix('.tmp')
    temp.write_text(json.dumps(feed, indent=2) + '\n')
    temp.replace(dest)
    print(json.dumps(feed, indent=2))

if __name__ == '__main__':
    main()
