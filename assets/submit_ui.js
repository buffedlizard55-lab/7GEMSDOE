/* Submission UI for index.html and how-to-submit.html.
 *
 * Two jobs, both entirely local to the visitor's browser:
 *   1. #generate-tif  -> rebuild the published submission raster from the compact
 *      payload, verify the rebuilt float32 pixels against the manifest SHA-256,
 *      and save the GeoTIFF under its unique competition filename.
 *   2. #validate-file -> run the competition's format rules on a file the visitor
 *      is about to upload (single band, float32, exact grid, [0, 1] inside the
 *      footprint, NaN outside) and print every problem found.
 *
 * Nothing is uploaded: both paths use Blob/ArrayBuffer APIs only.
 */
(function () {
  'use strict';
  var G = window.GEOTIFF;

  function el(id) { return document.getElementById(id); }
  function say(node, text, cls) {
    if (!node) return;
    node.textContent = text;
    node.className = 'download-status' + (cls ? ' ' + cls : '');
  }
  function bytes(n) { return n.toLocaleString(); }

  function templateBuffer() {
    if (!window.__gemsTemplate) {
      var man = (window.GEMS_SUBMISSION_PAYLOAD || {}).manifest || {};
      var path = man.template_path || 'downloads/gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.tif';
      window.__gemsTemplate = fetch(path).then(function (r) {
        if (!r.ok) throw new Error('could not fetch the reference template (HTTP ' + r.status + ')');
        return r.arrayBuffer();
      });
    }
    return window.__gemsTemplate;
  }
  function templateRaster() {
    if (!window.__gemsTemplateRaster) {
      window.__gemsTemplateRaster = templateBuffer().then(G.readRaster);
    }
    return window.__gemsTemplateRaster;
  }
  function referenceFrom(tpl) {
    return {
      width: tpl.width, height: tpl.height, geo: tpl.geo,
      footprint: Uint8Array.from(tpl.values, function (v) { return Number.isFinite(v) ? 1 : 0; })
    };
  }
  function save(blob, name) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(url); a.remove(); }, 5000);
  }

  function initGenerator() {
    var button = el('generate-tif');
    if (!button) return;
    var status = el('generate-status'), shaOut = el('generate-sha');
    button.addEventListener('click', function () {
      var payload = window.GEMS_SUBMISSION_PAYLOAD;
      if (!payload || !payload.base64) {
        say(status, 'The embedded payload did not load — use the direct download button instead.', 'bad');
        return;
      }
      button.disabled = true;
      var started = Date.now();
      say(status, 'Rebuilding the raster from the embedded payload…');
      G.decodePayload(payload.base64, payload.manifest.grid.width, payload.manifest.grid.height)
        .then(function (rebuilt) {
          say(status, 'Verifying the rebuilt pixels against the published SHA-256…');
          return G.pixelPayloadSha256(rebuilt.values).then(function (pixelSha) {
            if (pixelSha !== payload.manifest.pixel_payload_sha256) {
              throw new Error('pixel hash mismatch (' + pixelSha.slice(0, 12) + ' vs ' +
                              payload.manifest.pixel_payload_sha256.slice(0, 12) +
                              '): refusing to hand out a file that is not the published raster');
            }
            return templateBuffer().then(function (tpl) {
              return G.buildGeoTIFF(rebuilt.values, rebuilt.width, rebuilt.height, tpl);
            }).then(function (buf) {
              return G.sha256Hex(new Uint8Array(buf)).then(function (fileSha) {
                var name = payload.manifest.output_name || 'gems7-submission.tif';
                save(new Blob([buf], {type: 'image/tiff'}), name);
                say(status, 'Saved ' + name + ' (' + (buf.byteLength / 1024).toFixed(0) +
                            ' KB) in ' + ((Date.now() - started) / 1000).toFixed(1) +
                            ' s — same pixels as the published artifact. Upload it and paste the Note.', 'good');
                if (shaOut) {
                  shaOut.textContent = 'file SHA-256 ' + fileSha +
                    ' · pixel payload SHA-256 ' + pixelSha + ' · ' + bytes(rebuilt.width * rebuilt.height) + ' pixels';
                }
              });
            });
          });
        })
        .catch(function (err) {
          say(status, 'Could not generate the file: ' + err.message + ' — use the direct download instead.', 'bad');
        })
        .then(function () { button.disabled = false; });
    });
  }

  function initValidator() {
    var input = el('validate-file');
    if (!input) return;
    var status = el('validate-status'), report = el('validate-report');
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      if (!file) return;
      if (report) report.innerHTML = '';
      say(status, 'Reading ' + file.name + ' (' + (file.size / 1024).toFixed(0) + ' KB)…');
      file.arrayBuffer().then(function (buf) {
        return Promise.all([G.readRaster(buf), templateRaster()]).then(function (both) {
          var raster = both[0], reference = referenceFrom(both[1]);
          var res = G.validate(raster, reference);
          var info = res.info || {};
          var html = [];
          html.push('<h3>' + (res.ok ? 'PASS — this file should be accepted by the platform'
                                     : 'FAIL — do not upload this file') + '</h3>');
          if (res.problems.length) {
            html.push('<p><strong>Problems</strong></p><ul>' +
                      res.problems.map(function (p) { return '<li>' + p + '</li>'; }).join('') + '</ul>');
          }
          if (res.warnings.length) {
            html.push('<p><strong>Warnings</strong></p><ul>' +
                      res.warnings.map(function (w) { return '<li>' + w + '</li>'; }).join('') + '</ul>');
          }
          html.push('<p>Shape ' + raster.width + ' × ' + raster.height +
                    ' · single band float32 · compression ' + raster.compression +
                    ' · CRS ' + (info.crsEpsg ? 'EPSG:' + info.crsEpsg : 'unknown') +
                    ' · finite values [' + (info.min === null ? '—' : info.min) + ', ' +
                    (info.max === null ? '—' : info.max) + '] on ' + bytes(info.finite || 0) + ' pixels' +
                    ' · NaN ' + bytes(info.nan || 0) +
                    (info.inside_footprint_not_finite !== undefined
                      ? ' · inside footprint not finite: ' + info.inside_footprint_not_finite : '') +
                    (info.outside_footprint_finite !== undefined
                      ? ' · outside footprint finite: ' + info.outside_footprint_finite : '') + '</p>');
          if (report) report.innerHTML = html.join('');
          say(status, res.ok ? 'Checks complete: this file matches the competition template.'
                             : 'Checks complete: ' + res.problems.length + ' problem(s) found.', res.ok ? 'good' : 'bad');
        });
      }).catch(function (err) {
        say(status, 'Could not read that file: ' + err.message, 'bad');
        if (report) {
          report.innerHTML = '<h3>FAIL — the file could not be read as a submission raster</h3><p>' +
                             err.message + '</p>';
        }
      });
    });
  }

  function init() { initGenerator(); initValidator(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
