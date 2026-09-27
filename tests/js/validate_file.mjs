/* Run the site's own pre-upload validator on a file pair, from the command line.
 *
 *   node tests/js/validate_file.mjs <reference.tif> <candidate.tif>
 *
 * Prints one JSON line: {ok, problems, warnings, info}. The reference raster is
 * what the page fetches as the competition template (the published submission
 * artifact); the reference footprint is "pixels the template has as finite".
 * Used by tests/test_browser_tools.py to prove that the browser checker accepts
 * the published file and rejects a genuinely invalid one, so a drifting negative
 * control cannot silently disable the browser integration check again.
 */
import fs from 'node:fs';
import vm from 'node:vm';

const [refPath, candidatePath] = process.argv.slice(2);
const sandbox = {
  console, TextDecoder, TextEncoder, Blob, Response, DecompressionStream, CompressionStream,
  crypto: globalThis.crypto, atob, btoa, Uint8Array, Float32Array, Uint32Array, DataView,
  ArrayBuffer, Number, Math, Error, Promise, JSON, String, Object, Array, Buffer, setTimeout
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('assets/geotiff_tools.js', 'utf8'), sandbox, {filename: 'geotiff_tools.js'});
const G = sandbox.GEOTIFF;

function read(path) {
  const b = fs.readFileSync(path);
  return G.readRaster(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength));
}

const ref = await read(refPath);
const reference = {
  width: ref.width, height: ref.height, geo: ref.geo,
  footprint: Uint8Array.from(ref.values, (v) => (Number.isFinite(v) ? 1 : 0))
};
const candidate = await read(candidatePath);
const res = G.validate(candidate, reference);
console.log(JSON.stringify({ok: res.ok, problems: res.problems, warnings: res.warnings, info: res.info}));
