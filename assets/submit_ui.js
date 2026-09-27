/* Submission UI: browser-side generation and pre-upload validation.
 *
 * Loaded only on pages that carry the controls (index.html, how-to-submit.html).
 * Everything runs locally: the user's file is never uploaded anywhere. The
 * reference template is fetched once from this site and cached in memory.
 */
(function () {
  'use strict';
  var G = window.GEOTIFF;
  var templatePromise = null;

  function el(id) { return document.getElementById(id); }
  function say(node, text, cls) {
    if (!node) return;
    node.textContent = text;
    node.className = 'download-status' + (cls ? ' ' + cls : '');
  }
  function templateBuffer() {
    if (!templatePromise) {
      var meta = (window.GEMS_SUBMISSION_PAYLOAD || {}).manifest || {};
      var path = meta.template_path || 'downloads/gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.tif';
      templatePromise = fetch(path).then(function (r) {
        if (!r.ok) throw new Error('could not fetch the reference template (' + r.status + ')');
        return r.arrayBuffer();
      });
    }
    return templatePromise;
  }
  function getTemplateRaster() {
    if (!window.__templateRaster) window.__templateRaster = templateBuffer().then(G.readRaster);
    return window.__templateRaster;
  }

  function download(blob, name) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = name;
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(url); a.remove(); }, 4000);
  }

  function initGenerator() {
    var button = el('generate-tif');
    if (!button) return;
    var status = el('generate-status');
    var shaOut = el('generate-sha');
    button.addEventListener('click', function () {
      var payload = window.GEMS_SUBMISSION_PAYLOAD;
      if (!payload) { say(status, 'The embedded payload did not load; use the direct download instead.', 'bad'); return; }
      button.disabled = true;
      say(status, 'Rebuilding the raster from the embedded payload…');
      var t0 = Date.now();
      var rebuilt = G.decodePayload(payload.base64);
      G.pixelPayloadSha256(rebuilt.values).then(function (pixelSha) {
        var expected = payload.manifest.pixel_payload_sha256;
        if (pixelSha !== expected) {
          throw new Error('pixel hash mismatch: the page payload does not match the published artifact (' +
                          pixelSha.slice(0, 12) + ' vs ' + expected.slice(0, 12) + ')');
        }
        say(status, 'Pixels verified against the published SHA-256. Writing the GeoTIFF…');
        return templateBuffer().then(function (tpl) {
          return G.buildGeoTIFF(rebuilt.values, rebuilt.width, rebuilt.height, tpl);
        }).then(function (buf) {
          return G.sha256Hex(new Uint8Array(buf)).then(function (fileSha) {
            var name = (payload.manifest.output_name || 'gems7-submission-browser.tif');
            download(new Blob([buf], {type: 'image/tiff'}), name);
            var mb = (buf.byteLength / 1e6).toFixed(2);
            say(status, 'Built ' + name + ' (' + mb + ' MB) in ' + ((Date.now() - t0) / 1000).toFixed(1) +
                        ' s. Same pixels as the published artifact; upload this file.', 'good');
            if (shaOut) {
              shaOut.textContent = 'file SHA-256 ' + fileSha + ' · pixel payload SHA-256 ' + pixelSha;
            }
          });
        });
      }).catch(function (err) {
        say(status, 'Could not generate the file: ' + err.message, 'bad');
      }).then(function () { button.disabled = false; });
    });
  }

  function initValidator() {
    var input = el('validate-file');
    if (!input) return;
    var status = el('validate-status');
    var report = el('validate-report');
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      if (!file) return;
      if (report) report.innerHTML = '';
      say(status, 'Reading ' + file.name + ' (' + (file.size / 1e6).toFixed(2) + ' MB)…');
      file.arrayBuffer().then(function (buf) {
        return Promise.all([G.readRaster(buf), getTemplateRaster()]).then(function (both) {
          var raster = both[0], tpl = both[1];
          var reference = {
            width: tpl.width, height: tpl.height, geo: tpl.geo,
            footprint: Uint8Array.from(tpl.values, function (v) { return Number.isFinite(v) ? 1 : 0; })
          };
          var res = G.validate(raster, reference);
          var lines = [];
          lines.push('<h3>' + (res.ok ? 'PASS — this file should be accepted' : 'FAIL — do not upload this file') + '</h3>');
          if (res.problems.length) {
            lines.push('<p><strong>Problems</strong></p><ul>' + res.problems.map(function (p) {
              return '<li>' + p + '</li>'; }).join('') + '</ul>');
          }
          if (res.warnings.length) {
            lines.push('<p><strong>Warnings</strong></p><ul>' + res.warnings.map(function (w) {
              return '<li>' + w + '</li>'; }).join('') + '</ul>');
          }
          lines.push('<p>Shape ' + raster.width + ' × ' + raster.height + ' · ' + raster.bitsPerSample +
                     '-bit format code ' + raster.sampleFormat + ' · compression ' + raster.compression +
                     ' · CRS EPSG:' + (res.crs_epsg === null ? '?' : res.crs_epsg) +
                     ' · values min ' + res.min + ', max ' + res.max +
                     ' · NaN ' + res.nan.toLocaleString() + ' pixels' +
                     (res.inside_not_finite !== undefined ? ' · non-finite inside footprint ' + res.inside_not_finite : '') + '</p>');
          if (report) report.innerHTML = lines.join('');
          say(status, res.ok ? 'Checks complete: the file matches the competition template.'
                             : 'Checks complete: ' + res.problems.length + ' problem(s) found.', res.ok ? 'good' : 'bad');
        });
      }).catch(function (err) {
        say(status, 'Could not read that file: ' + err.message, 'bad');
        if (report) report.innerHTML = '<h3>FAIL — this file was rejected by the reader</h3><p>' + err.message + '</p>';
      });
    });
  }

  function init() { initGenerator(); initValidator(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
