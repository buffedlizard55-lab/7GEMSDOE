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
