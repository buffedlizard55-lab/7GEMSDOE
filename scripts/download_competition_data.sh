#!/usr/bin/env bash
# Download the official GEMS Prize competition rasters into $GEMS_DATA_DIR
# (default: ~/gems_data). Every file is sha256-verified against the pins in
# knowledge/inherited_evidence/data_bridge_manifest.json (measured from the
# official downloads on 2026-09-17, scripts/make_data_bridge.py).
#
# Sources, in order of preference:
#   1. User-supplied Dropbox mirrors (not independently authenticated):
#        example_submission.tif  https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=1
#        existing_faults.tif     https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=1
#        gems-geodawn-numerical-features.tif
#                                https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=1
#      (login-free mirrors of the files on the DrivenData data tab:
#       https://www.drivendata.org/competitions/306/competition-doe-gems/data/ )
#   2. Fallback: the hash-pinned git data bridge in the sibling public repo
#      buffedlizard55-lab/GEMSDOE (data/bridge/), which reassembles the same
#      bytes via scripts/assemble_data_bridge.py.
#
# The full DrivenData data tab itself requires login (training_features.tif,
# labels.tif, sample_submission.tif, 1m_DEM_links.csv) - NOT auto-downloadable
# without credentials. The mirrors above match inherited team sha256 pins (not independent official authentication)
# for the three rasters; labels.tif == existing_faults.tif and
# sample_submission.tif == example_submission.tif per the manifest's
# canonical-name mapping. 1m_DEM_links.csv is not mirrored yet (see
# knowledge/02_data_sources.md - DEM links were OCR-recovered to
# data/dem_links.json in the sibling repo).

set -euo pipefail

DEST="${GEMS_DATA_DIR:-$HOME/gems_data}"
mkdir -p "$DEST"
DEST="$(cd "$DEST" && pwd)" # relative overrides must remain valid after cd
cd "$DEST"

declare -A SHA=(
  [example_submission.tif]=2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc
  [existing_faults.tif]=7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093
  [training_features.tif]=4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5
)

declare -A URL=(
  [example_submission.tif]="https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=1"
  [existing_faults.tif]="https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=1"
  [training_features.tif]="https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=1"
)

verify() { # $1=file  $2=expected sha
  local got
  got=$(sha256sum "$1" | cut -d' ' -f1)
  if [[ "$got" == "$2" ]]; then
    echo "PASS  $1  $got"
  else
    echo "FAIL  $1  got $got want $2"
    return 1
  fi
}

for f in example_submission.tif existing_faults.tif training_features.tif; do
  if [[ -f "$f" ]] && verify "$f" "${SHA[$f]}"; then
    continue
  fi
  echo "== downloading $f (dropbox mirror)"
  if curl -fL --connect-timeout 15 --max-time 90 --retry 1 -A "Mozilla/5.0" -o "$f" "${URL[$f]}"; then
    verify "$f" "${SHA[$f]}" || { echo "dropbox bytes failed hash; removing"; rm -f "$f"; }
  fi
  if [[ ! -f "$f" ]] || ! verify "$f" "${SHA[$f]}" >/dev/null 2>&1; then
    echo "== fallback: sibling-repo data bridge for $f"
    rm -f "$f" # a failed curl may leave partial bytes; never preserve them
    BRIDGE_TMP="$(mktemp -d)"
    trap 'rm -rf "$BRIDGE_TMP"' EXIT
    BRIDGE="$BRIDGE_TMP/GEMSDOE"
    git clone --depth 1 --filter=blob:none --sparse \
      https://github.com/buffedlizard55-lab/GEMSDOE "$BRIDGE"
    ( cd "$BRIDGE" && git sparse-checkout set --skip-checks data/bridge data/evidence scripts )
    # writes canonical names into $BRIDGE/data (hash-verified by the script)
    ( cd "$BRIDGE" && python3 scripts/assemble_data_bridge.py \
        --bridge data/bridge --out data )
    cp "$BRIDGE/data/training_features.tif" "$DEST/training_features.tif" 2>/dev/null || true
    cp "$BRIDGE/data/labels.tif" "$DEST/existing_faults.tif" 2>/dev/null || true
    cp "$BRIDGE/data/sample_submission.tif" "$DEST/example_submission.tif" 2>/dev/null || true
    verify "$f" "${SHA[$f]}"
    rm -rf "$BRIDGE_TMP"
  fi
done

echo
echo "All mirrored rasters present and matched to inherited hash pins in $DEST:"
ls -la "$DEST"/*.tif
