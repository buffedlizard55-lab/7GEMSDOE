import sys
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from validate_submission import validate


def write(path, data, **overrides):
    meta = dict(driver='GTiff', height=data.shape[-2], width=data.shape[-1],
                count=1, dtype='float32', crs='EPSG:32611',
                transform=from_origin(100, 200, 100, 100), nodata=np.nan)
    meta.update(overrides)
    with rasterio.open(path, 'w', **meta) as f:
        for band in range(1, meta['count'] + 1):
            f.write(data.astype(meta['dtype']), band)


@pytest.fixture
def files(tmp_path):
    t, p = tmp_path / 'template.tif', tmp_path / 'pred.tif'
    a = np.array([[0, 0], [0, np.nan]], dtype='float32')
    write(t, a)
    write(p, a)
    return t, p, a


def test_valid(files):
    t, p, _ = files
    assert validate(str(p), str(t)) == []


@pytest.mark.parametrize('bad', [-1e-8, np.nextafter(np.float32(1), np.float32(2)), np.inf, -np.inf, np.nan])
def test_invalid_inside(files, bad):
    t, p, a = files
    a[0, 0] = bad
    write(p, a)
    assert validate(str(p), str(t))


@pytest.mark.parametrize('bad', [0, np.inf, -np.inf])
def test_outside_requires_nan(files, bad):
    t, p, a = files
    a[1, 1] = bad
    write(p, a)
    assert validate(str(p), str(t))


@pytest.mark.parametrize('overrides', [dict(count=2), dict(dtype='float64'),
    dict(crs='EPSG:4326'), dict(nodata=None), dict(transform=from_origin(0, 0, 1, 1))])
def test_metadata(files, overrides):
    t, p, a = files
    write(p, a, **overrides)
    assert validate(str(p), str(t))


def test_wrong_shape_returns_error(files):
    t, p, _ = files
    write(p, np.zeros((3, 3)))
    assert any('shape' in e for e in validate(str(p), str(t)))


def test_missing_or_corrupt(files):
    t, p, _ = files
    p.write_text('not a raster')
    assert validate(str(p), str(t))
    p.unlink()
    assert validate(str(p), str(t))


def test_masked_inside(files):
    t, p, a = files
    with rasterio.open(p, 'r+') as f:
        f.write_mask(np.zeros(a.shape, dtype='uint8'))
    assert validate(str(p), str(t))
