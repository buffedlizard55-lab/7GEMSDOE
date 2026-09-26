import sys
from pathlib import Path
import requests
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from refresh_sources import parse_leaderboard, refresh


def test_parse():
    html='<table><tr><td>#1</td><td></td><td><a href="/users/test/">test</a> 1h ago</td><td>0.3049</td></tr></table>'
    assert parse_leaderboard(html) == [dict(rank=1, participant='test', score=.3049)]


@pytest.mark.parametrize('html', ['<h1>Login</h1>', '<table></table>', '<td>0.3</td>'])
def test_not_a_leaderboard(html):
    with pytest.raises(ValueError): parse_leaderboard(html)


def test_network_failure_keeps_last_verified_date_and_rows():
    old=dict(verified_utc='2026-01-01', rows=[dict(rank=1,score=.3)])
    def fail(*args, **kwargs): raise requests.Timeout('offline')
    result=refresh(old,fail)
    assert result['verified_utc']==old['verified_utc']
    assert result['rows']==old['rows']
    assert result['status']=='refresh_failed'
    assert result['attempted_utc']


def test_public_htmx_fragment():
    class Response:
        def __init__(self,text,url): self.text=text; self.content=text.encode(); self.url=url
        def raise_for_status(self): pass
    calls=[]
    def get(url,**kwargs):
        calls.append(url)
        if len(calls)==1:
            return Response('<div hx-get="/competitions/306/competition-doe-gems/leaderboard/table/">Loading</div>',url)
        return Response('<table><tr><td>#1</td><td></td><td><a href="/users/test/">test</a></td><td>0.3</td></tr></table>',url)
    result=refresh({},get)
    assert result['status']=='ok'
    assert len(calls)==2
    assert result['rows'][0]['score']==.3


def test_external_htmx_rejected():
    class Response:
        text='<div hx-get="https://evil.example/competition-doe-gems/leaderboard/">Loading</div>'
        content=text.encode(); url='https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/'
        def raise_for_status(self): pass
    calls=[]
    def get(url,**kw): calls.append(url); return Response()
    assert refresh({},get)['status']=='refresh_failed'
    assert len(calls)==1


def test_follow_all_explicit_pages():
    class Response:
        def __init__(self,text,url): self.text=text; self.content=text.encode(); self.url=url
        def raise_for_status(self): pass
    calls=[]
    def row(rank,score):
        return f'<table><tr><td>#{rank}</td><td></td><td>x</td><td>{score}</td></tr></table>'
    def get(url,**kwargs):
        calls.append(url)
        text=row(1,'0.3')+'<a href="?page=2">Next</a>' if len(calls)==1 else row(2,'0.2')
        return Response(text,url)
    result=refresh({},get)
    assert result['status']=='ok'
    assert len(result['pages'])==2
    assert [r['rank'] for r in result['rows']]==[1,2]
