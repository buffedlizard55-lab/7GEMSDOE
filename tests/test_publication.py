import hashlib
import json
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlsplit, unquote
from bs4 import BeautifulSoup
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from validate_submission import validate
from package_submission import package


@pytest.mark.parametrize('meta_file',['control_meta.json','structural_meta.json'])
def test_publication_bytes_zip_and_format(meta_file):
    m=json.loads((ROOT/'downloads'/meta_file).read_text())
    f=ROOT/'downloads'/m['file']
    assert hashlib.sha256(f.read_bytes()).hexdigest()==m['sha256']
    assert f.stat().st_size==m['bytes']
    # Pinned original control serves as an in-repo geometry/footprint fixture.
    assert validate(str(f),str(ROOT/'downloads/submission.tif'))==[]
    with zipfile.ZipFile(ROOT/'downloads'/m['zip']) as z:
        assert z.namelist()==[m['file']]
        assert z.read(m['file'])==f.read_bytes()
    assert m['competition_score'] is None
    assert m['sha256'][:12] in m['suggested_submission_note']


def test_local_page_links_exist():
    for path in list(ROOT.glob('*.html'))+[ROOT/'docs/index.html']:
        soup=BeautifulSoup(path.read_text(),'html.parser')
        for tag in soup.find_all(['a','script','link']):
            raw=tag.get('href') or tag.get('src') or ''
            url=urlsplit(raw)
            if not raw or url.scheme or url.netloc or raw.startswith('#'): continue
            dest=(path.parent/unquote(url.path)).resolve()
            assert dest.exists(), (path.name,raw)


def test_invalid_publication_does_not_write(tmp_path):
    out=tmp_path/'published'
    with pytest.raises(ValueError):
        package(tmp_path/'missing.tif',ROOT/'downloads/submission.tif','test','note',out)
    assert not out.exists()


def test_packaging_is_idempotent_and_rejects_mutation(tmp_path):
    candidate=ROOT/'downloads/submission.tif'
    first=package(candidate,candidate,'repeat','fixed note',tmp_path)
    before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    assert package(candidate,candidate,'repeat','fixed note',tmp_path)==first
    assert before=={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError,match='metadata mismatch'):
        package(candidate,candidate,'repeat','changed note',tmp_path)
    (tmp_path/first['zip']).write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='immutable ZIP'):
        package(candidate,candidate,'repeat','fixed note',tmp_path)
