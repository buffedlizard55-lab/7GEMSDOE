/* End-to-end check of assets/geotiff_tools.js against the published artifact.
 *
 *   node tests/js/roundtrip.mjs <template.tif> <payload.js> <out.tif> <report.json>
 *
 * It reads the published submission raster (GDAL-written, DEFLATE + floating-point
 * predictor 3), rebuilds the same pixels from the compact site payload, writes a
 * new GeoTIFF with the browser writer, re-reads it, validates it against the
 * template, and records every verdict in the report. tests/test_browser_tools.py
 * then re-checks the written file with rasterio/GDAL (which this harness cannot see).
 */
import fs from 'node:fs';
import vm from 'node:vm';

const [templatePath, payloadPath, outPath, reportPath] = process.argv.slice(2);
const report = {steps: [], ok: false};
function step(name, data) { report.steps.push(Object.assign({name}, data)); return data; }
function fail(message, data) {
  step('FAILED', Object.assign({message}, data || {}));
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 1));
  throw new Error(message);
}

const toolsSrc = fs.readFileSync('assets/geotiff_tools.js', 'utf8');
const sandbox = {
  console, TextDecoder, TextEncoder, Blob, Response, DecompressionStream, CompressionStream,
  crypto: globalThis.crypto, atob, btoa, Uint8Array, Float32Array, Uint32Array, DataView,
  ArrayBuffer, Number, Math, Error, Promise, JSON, String, Object, Array, Buffer, setTimeout
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(toolsSrc, sandbox, {filename: 'geotiff_tools.js'});
const G = sandbox.GEOTIFF;
if (!G) fail('assets/geotiff_tools.js did not define GEOTIFF');

// the payload script runs in the SAME context as the tools, exactly as the page loads them
sandbox.window = sandbox;
vm.runInContext(fs.readFileSync(payloadPath, 'utf8'), sandbox, {filename: 'submission_payload.js'});
const payload = sandbox.GEMS_SUBMISSION_PAYLOAD;
if (!payload) fail('payload file did not define window.GEMS_SUBMISSION_PAYLOAD');
const man = payload.manifest;

// --- 1. the template (published artifact) reads and passes the competition rules
const templateBuf = fs.readFileSync(templatePath);
const ab = templateBuf.buffer.slice(templateBuf.byteOffset, templateBuf.byteOffset + templateBuf.byteLength);
const template = await G.readRaster(ab);
step('read_template', {width: template.width, height: template.height, bits: template.bitsPerSample,
                       sampleFormat: template.sampleFormat, compression: template.compression,
                       predictor: template.predictor, geo: template.geo,
                       nan: template.values.filter((v) => Number.isNaN(v)).length});
const reference = {
  width: template.width, height: template.height, geo: template.geo,
  footprint: Uint8Array.from(template.values, (v) => (Number.isFinite(v) ? 1 : 0))
};
function counts(values) {
  let one = 0, zero = 0, nan = 0, other = 0;
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (Number.isNaN(v)) nan++;
    else if (v === 1) one++;
    else if (v === 0) zero++;
    else other++;
  }
  return {one, zero, nan, other};
}
const templateCounts = counts(template.values);
if (templateCounts.other !== 0) {
  fail('the published template contains values that are neither 0, 1 nor NaN', templateCounts);
}
if (man.counts.one !== templateCounts.one || man.counts.zero !== templateCounts.zero ||
    man.counts.nan !== templateCounts.nan) {
  fail('the raw TIFF decode does not reproduce the manifest class counts',
       {decoded: templateCounts, manifest: man.counts});
}
step('template_class_counts', templateCounts);
const templateReport = G.validate(template, reference);
if (!templateReport.ok) fail('the published template fails the rules it defines', templateReport.problems);
step('validate_template', {ok: templateReport.ok, min: templateReport.min, max: templateReport.max,
                           nan: templateReport.nan});

// --- 2. the payload rebuilds the same pixels, hash-verified
const rebuilt = await G.decodePayload(payload.base64);
if (rebuilt.width !== template.width || rebuilt.height !== template.height) {
  fail('payload grid does not match the template', {payload: [rebuilt.width, rebuilt.height],
                                                    template: [template.width, template.height]});
}
const pixelSha = await G.pixelPayloadSha256(rebuilt.values);
if (pixelSha !== man.pixel_payload_sha256) {
  fail('rebuilt pixel payload hash does not match the manifest',
       {got: pixelSha, want: man.pixel_payload_sha256});
}
let mismatches = 0, firstMismatch = null;
for (let i = 0; i < rebuilt.values.length; i++) {
  const a = rebuilt.values[i], b = template.values[i];
  if (Number.isNaN(a) && Number.isNaN(b)) continue;
  if (a !== b) { mismatches++; if (!firstMismatch) firstMismatch = [i, a, b]; }
}
if (mismatches) fail('payload pixels differ from the published artifact',
                     {mismatches, firstMismatch});
step('rebuild_from_payload', {pixel_sha256: pixelSha, expected: man.pixel_payload_sha256,
                              ones: rebuilt.values.filter((v) => v === 1).length,
                              zeros: rebuilt.values.filter((v) => v === 0).length,
                              nan: rebuilt.values.filter((v) => Number.isNaN(v)).length});

// --- 3. the browser writer produces a file that re-reads and validates
const built = await G.buildGeoTIFF(rebuilt.values, rebuilt.width, rebuilt.height, ab);
fs.writeFileSync(outPath, Buffer.from(built));
const reread = await G.readRaster(built.slice(0));
const rereadReport = G.validate(reread, reference);
if (!rereadReport.ok) fail('the browser-written file fails the competition rules', rereadReport.problems);
let same = 0;
for (let i = 0; i < reread.values.length; i++) {
  const a = reread.values[i], b = template.values[i];
  if (Number.isNaN(a) && Number.isNaN(b)) continue;
  if (a === b) same++;
}
step('build_and_reread', {bytes: built.byteLength, width: reread.width, height: reread.height,
                          compression: reread.compression, predictor: reread.predictor,
                          geo: reread.geo, ok: rereadReport.ok, equal_values: same,
                          crsEpsg: reread.geo.crsEpsg, file_sha256: await G.sha256Hex(new Uint8Array(built))});

// --- 4. negative controls: the checker must reject the classic failure modes
const badRange = {width: template.width, height: template.height, samples: 1, bitsPerSample: 32,
                  sampleFormat: 3, compression: 8, geo: template.geo,
                  values: Uint8Array.from([1, 2, 3])};
const badShape = G.validate(Object.assign({}, template, {width: 10}), reference);
if (badShape.ok) fail('a wrong-shaped raster passed the shape check');
const nanInside = Float32Array.from(template.values);
for (let i = 0; i < nanInside.length; i++) {
  if (reference.footprint[i] === 1) { nanInside[i] = NaN; break; }
}
const nanReport = G.validate(Object.assign({}, template, {values: nanInside}), reference);
if (nanReport.ok) fail('NaN inside the footprint passed the checker');
const above = Float32Array.from(template.values);
for (let i = 0; i < above.length; i++) { if (reference.footprint[i] === 1) { above[i] = 7; break; } }
const aboveReport = G.validate(Object.assign({}, template, {values: above}), reference);
if (aboveReport.ok) fail('a value above 1 passed the checker');
step('negative_controls', {samples_filtered: badRange.values.length, wrong_shape_rejected: !badShape.ok,
                           nan_inside_rejected: !nanReport.ok, above_one_rejected: !aboveReport.ok,
                           nan_message: nanReport.problems[0]});

report.ok = true;
fs.writeFileSync(reportPath, JSON.stringify(report, null, 1));
console.log(JSON.stringify(report, null, 1));
