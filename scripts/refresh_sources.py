"""Refresh official-source excerpts + leaderboard. Failures never become evidence.

Network checks verify excerpt presence, not scientific truth. Changed/missing
text is flagged for review. The last successful leaderboard is retained with
its original timestamp; attempt status and staleness remain visible.
"""
from __future__ import annotations
import hashlib
import json
import re
from urllib.parse import urljoin, urlsplit, parse_qs
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
    if not rows or len({r['rank'] for r in rows}) != len(rows):
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
        try:
            rows = parse_leaderboard(response.text)
        except ValueError:
            # DrivenData loads the public table as an HTMX fragment. Follow only
            # an explicit same-origin leaderboard endpoint, never guessed URLs.
            soup = BeautifulSoup(response.text, 'html.parser')
            fragments = []
            for element in soup.select('[hx-get], [data-hx-get]'):
                endpoint = urljoin(URL, element.get('hx-get') or element.get('data-hx-get'))
                parsed = urlsplit(endpoint)
                if parsed.scheme == 'https' and parsed.netloc == urlsplit(URL).netloc and '/competition-doe-gems/' in parsed.path and 'leaderboard' in parsed.path:
                    fragments.append(endpoint)
            if not fragments:
                raise ValueError('no table or recognized public leaderboard fragment')
            response = getter(fragments[0], timeout=(10,40), headers={'HX-Request':'true'})
            response.raise_for_status()
            rows = parse_leaderboard(response.text)
            result['table_source'] = response.url
        pages = [dict(url=response.url, sha256=hashlib.sha256(response.content).hexdigest())]
        # Follow explicit pagination (the previous repository mistook the first
        # 50-row page for the entire competition). Never guess a page endpoint.
        current_page = int(parse_qs(urlsplit(response.url).query).get('page',['1'])[0])
        for _ in range(49):
            soup = BeautifulSoup(response.text, 'html.parser')
            candidates = {}
            for tag in soup.select('[hx-get], [data-hx-get], a[href]'):
                raw = tag.get('hx-get') or tag.get('data-hx-get') or tag.get('href')
                endpoint = urljoin(response.url, raw)
                parsed = urlsplit(endpoint)
                number = parse_qs(parsed.query).get('page',[''])[0]
                if (parsed.scheme == 'https' and parsed.netloc == urlsplit(URL).netloc
                    and '/competition-doe-gems/leaderboard' in parsed.path and number.isdigit()
                    and int(number) > current_page):
                    candidates[int(number)] = endpoint
            if not candidates:
                break
            current_page = min(candidates)
            response = getter(candidates[current_page], timeout=(10,40), headers={'HX-Request':'true'})
            response.raise_for_status()
            rows.extend(parse_leaderboard(response.text))
            pages.append(dict(url=response.url, sha256=hashlib.sha256(response.content).hexdigest()))
        else:
            raise ValueError('pagination exceeded safety cap; refusing partial success')
        if [r['rank'] for r in rows] != list(range(1,len(rows)+1)):
            raise ValueError('pagination rank gap/duplicate; leaderboard may have changed mid-fetch')
        if any(a['score'] < b['score'] for a,b in zip(rows,rows[1:])):
            raise ValueError('scores changed during pagination; retry later')
        result['pages'] = pages
        result.update(status='ok', verified_utc=now, rows=rows,
                      source=URL, response_sha256=hashlib.sha256(response.content).hexdigest(),
                      method='automated official HTML/HTMX table parse', error=None)
        result.pop('page_diagnostics',None)
        result.pop('parse_diagnostics',None)
    except (requests.RequestException, ValueError) as exc:
        result.update(status='refresh_failed', error=str(exc)[:500])
        if response is not None:
            soup = BeautifulSoup(response.text, 'html.parser')
            pos=response.text.find('DARD')
            result['page_diagnostics'] = dict(url=response.url, length=len(response.content), title=str(soup.title), participant_context=response.text[max(0,pos-3000):pos+1500] if pos>=0 else soup.get_text(' ',strip=True)[:5000], fragments=[e.get('hx-get') or e.get('data-hx-get') for e in soup.select('[hx-get], [data-hx-get]')])
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
    temp.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + '\n')
    temp.replace(dest)
    print(json.dumps(feed, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
