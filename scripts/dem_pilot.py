"""H4 bounded native-1m scarp-feature pilot; never a full-grid submission.

Uses a 2048x2048 central window of an official USGS 3DEP tile. Reports uncalibrated
break-in-slope statistics, not fault detections. Erodes nodata/window edges by
40m before derivative statistics so missing-data edges cannot masquerade as scarps.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window
from scipy.ndimage import binary_erosion, gaussian_filter, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]


def scarp_features(elevation, valid, resolution=1.):
    if not valid.any():
        raise ValueError('DEM window has no valid elevations')
    filled = np.where(valid, elevation, np.median(elevation[valid])).astype('float32')
    smooth = gaussian_filter(filled, 3 / resolution)
    gy, gx = np.gradient(smooth, resolution)
    slope = np.hypot(gx, gy)
    sy, sx = np.gradient(slope, resolution)
    edge = np.hypot(sx, sy)
    safe = binary_erosion(valid, iterations=int(np.ceil(40 / resolution)), border_value=0)
    if not safe.any():
        raise ValueError('no safe pixels after nodata buffer')
    edge[~safe] = np.nan
    return edge, safe


def main():
    config = json.loads((ROOT / 'knowledge/dem_pilot_source.json').read_text())
    url = config['record']['url']
    report = dict(attempted_utc=datetime.now(timezone.utc).isoformat(), url=url,
                  caveat='Small engineering pilot only; slope breaks also occur at roads, '
                         'drainage, lithologic contacts and landslides. No fault labels or discovery validation.')
    try:
        if not url.startswith('https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/'):
            raise ValueError('source must be the USGS 3DEP 1m bucket')
        with rasterio.Env(GDAL_HTTP_TIMEOUT='60', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                          CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif'):
            with rasterio.open(url) as src:
                if not src.crs or not src.crs.is_projected or not np.allclose(src.res, (1,1)):
                    raise ValueError('expected projected 1m DEM')
                size = min(2048, src.width, src.height)
                # Partial-coverage tiles can have an all-nodata center. Locate an
                # interior valid patch in a cheap overview, then read NATIVE pixels.
                overview = src.read(1, out_shape=(512,512), masked=True)
                ov_valid = ~np.ma.getmaskarray(overview) & np.isfinite(overview.data)
                if not ov_valid.any():
                    raise ValueError('tile overview has no valid elevations')
                padded = np.pad(ov_valid, 1)
                interior = distance_transform_edt(padded)[1:-1,1:-1]
                oy, ox = np.unravel_index(np.argmax(interior), interior.shape)
                cy, cx = (oy+.5)*src.height/512, (ox+.5)*src.width/512
                window = Window(int(np.clip(cx-size/2,0,src.width-size)),
                                int(np.clip(cy-size/2,0,src.height-size)),size,size)
                report['window_selection'] = 'max distance from overview nodata/edge; native pixels read afterwards' 
                data = src.read(1, window=window, masked=True)
                valid = ~np.ma.getmaskarray(data) & np.isfinite(data.data)
                edge, safe = scarp_features(data.data, valid)
                report.update(status='pilot_complete', crs=str(src.crs), resolution=list(src.res),
                              window=[int(v) for v in (window.col_off,window.row_off,window.width,window.height)],
                              transform=list(src.window_transform(window))[:6],
                              valid_px=int(valid.sum()), safe_px=int(safe.sum()),
                              pixel_sha256=hashlib.sha256(data.filled(np.nan).tobytes()).hexdigest(),
                              edge_quantiles=dict(zip(['p50','p90','p99'],
                                                      map(float,np.nanpercentile(edge,[50,90,99])))))
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        report.update(status='blocked', error=str(exc)[:800])
    dest = ROOT / 'knowledge/session2/dem_pilot.json'
    dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
