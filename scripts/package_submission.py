"""Validate and publish an immutable, hash-named GeoTIFF + manifest + single-file ZIP.

No clipping here: invalid predictions fail. Existing control is never overwritten.
"""
import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import rasterio
from paths import TEMPLATE_TIF, DOCS_DOWNLOADS
from validate_submission import validate


def package(candidate, template, slug, note, out_dir=DOCS_DOWNLOADS, evidence=None):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,60}', slug):
        raise ValueError('slug: 1–61 lower-case letters, numbers or hyphens')
    if not note.strip() or len(note) > 240:
        raise ValueError('note must be 1–240 characters')
    errors = validate(str(candidate), str(template))
    if errors:
        raise ValueError('; '.join(errors))
    data = Path(candidate).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    name = f'gems7-{slug}-{sha[:12]}'
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tif = out / f'{name}.tif'
    if tif.exists() and hashlib.sha256(tif.read_bytes()).hexdigest() != sha:
        raise ValueError('immutable name collision')
    with rasterio.open(candidate) as src:
        arr = src.read(1)
        vals = arr[np.isfinite(arr)]
        grid = dict(width=src.width, height=src.height, crs=str(src.crs),
                    transform=list(src.transform)[:6], dtype=src.dtypes[0])
    report = dict(name=name, file=tif.name, zip=f'{name}.zip', sha256=sha,
                  bytes=len(data), generated_utc=datetime.now(timezone.utc).isoformat(),
                  template_sha256=hashlib.sha256(Path(template).read_bytes()).hexdigest(),
                  suggested_submission_note=f'{note} | {sha[:12]}', format_gate='PASS',
                  grid=grid, stats=dict(min=float(vals.min()), max=float(vals.max()),
                                       finite_px=int(vals.size), mass=float(vals.sum(dtype=np.float64))),
                  competition_score=None, evidence=evidence,
                  caveat='Local format pass only; no server acceptance or leaderboard gain verified.')
    manifest = out / f'{name}.json'
    zipped = out / f'{name}.zip'
    if manifest.exists():
        previous = json.loads(manifest.read_text())
        comparable = {k: v for k, v in previous.items() if k != 'generated_utc'}
        expected = {k: v for k, v in report.items() if k != 'generated_utc'}
        if comparable != expected or not tif.exists() or not zipped.exists():
            raise ValueError('immutable publication metadata mismatch or incomplete bundle')
        report = previous
    if zipped.exists():
        try:
            with zipfile.ZipFile(zipped) as z:
                if z.namelist() != [tif.name] or z.read(tif.name) != data:
                    raise ValueError('immutable ZIP content mismatch')
        except zipfile.BadZipFile as exc:
            raise ValueError('invalid immutable ZIP') from exc
    # Validate the existing bundle before writing anything; never restamp a release.
    if not tif.exists():
        tif.write_bytes(data)
    if not zipped.exists():
        info = zipfile.ZipInfo(tif.name, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        with zipfile.ZipFile(zipped, 'w') as z:
            z.writestr(info, data)
    if not manifest.exists():
        manifest.write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--template', type=Path, default=TEMPLATE_TIF)
    parser.add_argument('--slug', required=True)
    parser.add_argument('--note', required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.candidate, args.template, args.slug, args.note), indent=2))

if __name__ == '__main__':
    main()
