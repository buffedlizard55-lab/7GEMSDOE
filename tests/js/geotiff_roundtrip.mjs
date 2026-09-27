/* Node harness for assets/geotiff_tools.js.
 *
 * Usage: node tests/js/geotiff_roundtrip.mjs <canonical.tif> <payload.js> <out.tif> <report.json>
 *
 * It (1) reads the canonical artifact, (2) rebuilds the raster in the browser code
 * path from the compact payload, (3) writes a new GeoTIFF, (4) verifies the pixel
 * payload SHA-256 and the validator verdict on both the canonical file and a
 * deliberately corrupted copy. Python/rasterio re-checks the written file in
 * tests/test_browser_tools.py; this harness cannot see GDAL.
 */
import fs from 'node:fs';
import vm from 'node:vm';

const [canonicalPath, payloadPath, outPath, reportPath] = process.argv.slice(2);
const toolsSrc = fs.readFileSync('assets/geotiff_tools.js', 'utf8');
const sandbox = {console, TextDecoder, TextEncoder, Blob, Response, DecompressionStream,
                 CompressionStream, crypto, Buffer, atob, btoa, Uint8Array, Float32Array,
                 DataView, ArrayBuffer, Number, Math, Error};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(toolsSrc, sandbox, {filename: 'geotiff_tools.js'});
const G = sandbox.GEOTIFF;

const payloadSrc = fs.readFileSync(payloadPath, 'utf8');
const payloadSandbox = {window: {}};
vm.createContext(payloadSandbox);
vm.runInContext(payloadSrc, payloadSandbox, {filename: 'submission_payload.js'});
const payload = payloadSandbox.window.GEMS_SUBMISSION_PAYLOAD;

const report = {steps: []};
function step(name, detail) { report.steps.push({name, ...detail}); }

const canonicalBuf = fs.readFileSync(canonicalPath);
const ab = canonicalBuf.buffer.slice(canonicalBuf.byteOffset, canonicalBuf.byteOffset + canonicalBuf.byteLength);

const canonical = await G.readRaster(ab);
step('read_canonical', {width: canonical.width, height: canonical.height, geo: canonical.geo,
                        sampleFormat: canonical.sampleFormat, bits: canonical.bitsPerSample,
                        compression: canonical.compression});

const reference = {
  width: canonical.width, height: canonical.height, geo: canonical.geo,
  footprint: Uint8Array.from(canonical.values, (v) => (Number.isFinite(v) ? 1 : 0)),
};

// 1. validator must PASS the canonical artifact
const okReport = G.validate(canonical, reference);
step('validate_canonical', {ok: okReport.ok, problems: okReport.problems, warnings: okReport.warnings,
                            min: okReport.min, max: okReport.max, nan: okReport.nan});
if (!okReport.ok) { fs.writeFileSync(reportPath, JSON.stringify(report, null, 1)); throw new Error('canonical file failed validation'); }

// 2. validator must FAIL a file whose finite values leave [0, 1]
const corrupted = {width: canonical.width, height: canonical.height, samples: 1, bitsPerSample: 32,
                   sampleFormat: 3, values: Float32Array.from(canonical.values, (v) => (Number.isFinite(v) ? v * 300 : v)),
                   geo: canonical.geo};
const badReport = G.validate(corrupted, reference);
step('validate_uint8_like', {ok: badReport.ok, problems: badReport.problems.slice(0, 2), max: badReport.max});
if (badReport.ok) { fs.writeFileSync(reportPath, JSON.stringify(report, null, 1)); throw new Error('validator accepted out-of-range values'); }

// 3. rebuild the raster from the compact payload and check the pixel hash
const rebuilt = G.decodePayload(payload.base64);
const pixelSha = await G.pixelPayloadSha256(rebuilt.values);
step('payload_rebuild', {width: rebuilt.width, height: rebuilt.height, pixel_sha256: pixelSha,
                         expected: payload.manifest.pixel_payload_sha256,
                         counts: payload.manifest.counts});
if (pixelSha !== payload.manifest.pixel_payload_sha256) {
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 1));
  throw new Error(`pixel payload hash mismatch: ${pixelSha} != ${payload.manifest.pixel_payload_sha256}`);
}

// 4. build a GeoTIFF in the browser code path and validate that too
const built = await G.buildGeoTIFF(rebuilt.values, rebuilt.width, rebuilt.height, ab);
fs.writeFileSync(outPath, Buffer.from(built));
step('build_geotiff', {bytes: built.byteLength});

const rereadAb = built.slice(0);
const reread = await G.readRaster(rereadAb);
const rereadReport = G.validate(reread, reference);
step('validate_built', {ok: rereadReport.ok, problems: rereadReport.problems,
                        warnings: rereadReport.warnings.slice(0, 2), geo: reread.geo,
                        compression: reread.compression, sampleFormat: reread.sampleFormat});
let same = true;
for (let i = 0; i < reread.values.length; i++) {
  const a = reread.values[i], b = canonical.values[i];
  if (Number.isNaN(a) && Number.isNaN(b)) continue;
  if (a !== b) { same = false; break; }
}
step('pixels_identical_to_canonical', {same});
fs.writeFileSync(reportPath, JSON.stringify(report, null, 1));
if (!rereadReport.ok) throw new Error('built file failed validation: ' + rereadReport.problems.join('; '));
if (!same) throw new Error('rebuilt pixels differ from the canonical artifact');
console.log(JSON.stringify(report, null, 1));
