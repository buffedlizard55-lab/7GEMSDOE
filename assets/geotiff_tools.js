/* Minimal, dependency-free GeoTIFF reader / writer / competition checker.
 *
 * Runs unchanged in a modern browser and in Node (tests/js/roundtrip.mjs).
 *
 * Why this exists
 * ---------------
 * The competition needs one specific artifact: a single-band float32 GeoTIFF on
 * the official 100 m grid, finite values in [0, 1] inside the template footprint
 * and NaN outside it. Submitting anything else produces the rejection the group
 * hit in 2026 ("Predicted values must be in range [0, 1]"). This file lets the
 * public site (a) check any .tif against those rules locally and (b) rebuild the
 * published submission raster from a compact payload, in the visitor's browser,
 * with a SHA-256 check over the rebuilt float32 pixels.
 *
 * Scope: uncompressed, DEFLATE (8) and old-style DEFLATE (32946) strips, with
 * predictors 1/2/3, little- or big-endian, one or more strips. It rejects LZW,
 * PackBits, tiles, BigTIFF and multi-sample files with an explicit message rather
 * than guessing. Verified against GDAL/libtiff output in tests/js/roundtrip.mjs
 * and tests/test_browser_tools.py.
 */
(function (root) {
  'use strict';

  var TAGS = {
    ImageWidth: 256, ImageLength: 257, BitsPerSample: 258, Compression: 259,
    Photometric: 262, StripOffsets: 273, SamplesPerPixel: 277, RowsPerStrip: 278,
    StripByteCounts: 279, PlanarConfig: 284, Predictor: 317, SampleFormat: 339,
    ModelPixelScale: 33550, ModelTiepoint: 33922, GeoKeyDirectory: 34735,
    GeoDoubleParams: 34736, GeoAsciiParams: 34737, GDAL_NODATA: 42113
  };
  var TYPE_SIZE = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8};
  var COMPRESSION = {1: 'none', 5: 'LZW', 8: 'DEFLATE', 32946: 'DEFLATE-raw', 32773: 'PackBits'};

  function parseTIFF(buffer) {
    var dv = new DataView(buffer);
    if (buffer.byteLength < 8) throw new Error('not a TIFF: file is shorter than 8 bytes');
    var b0 = dv.getUint8(0), b1 = dv.getUint8(1);
    var littleEndian;
    if (b0 === 0x49 && b1 === 0x49) littleEndian = true;
    else if (b0 === 0x4D && b1 === 0x4D) littleEndian = false;
    else throw new Error('not a TIFF: byte-order mark is neither II nor MM');
    var magic = dv.getUint16(2, littleEndian);
    if (magic === 43) throw new Error('BigTIFF (magic 43) is not supported by this page; re-save as a classic GeoTIFF');
    if (magic !== 42) throw new Error('not a TIFF: magic number is ' + magic + ', expected 42');
    var ifd = dv.getUint32(4, littleEndian);
    if (dv.getUint16(ifd, littleEndian) === 0 && ifd + 2 > buffer.byteLength) throw new Error('IFD offset is past the end of the file');

    function fieldValues(entryOffset, type, count) {
      var size = TYPE_SIZE[type] * count;
      var at = size > 4 ? dv.getUint32(entryOffset + 8, littleEndian) : entryOffset + 8;
      var out = [];
      for (var i = 0; i < count; i++) {
        var o = at + i * TYPE_SIZE[type];
        if (type === 1 || type === 2 || type === 6 || type === 7) out.push(dv.getUint8(o));
        else if (type === 3 || type === 8) out.push(dv.getUint16(o, littleEndian));
        else if (type === 4 || type === 9) out.push(dv.getUint32(o, littleEndian));
        else if (type === 11) out.push(dv.getFloat32(o, littleEndian));
        else if (type === 12) out.push(dv.getFloat64(o, littleEndian));
        else if (type === 5) out.push([dv.getUint32(o, littleEndian), dv.getUint32(o + 4, littleEndian)]);
        else throw new Error('unsupported TIFF field type ' + type);
      }
      return out;
    }

    var n = dv.getUint16(ifd, littleEndian);
    var entries = [], tags = {};
    for (var i = 0; i < n; i++) {
      var off = ifd + 2 + i * 12;
      var tag = dv.getUint16(off, littleEndian);
      var type = dv.getUint16(off + 2, littleEndian);
      var count = dv.getUint32(off + 4, littleEndian);
      var values = fieldValues(off, type, count);
      entries.push({tag: tag, type: type, count: count, values: values, offset: off});
      tags[tag] = values;
    }
    function ascii(values) {
      return String.fromCharCode.apply(null, values.map(function (c) { return c & 0xFF; })).replace(/\0+$/, '');
    }
    var geo = {crsEpsg: null, pixelScale: null, origin: null, nodataText: null};
    if (tags[TAGS.ModelPixelScale]) geo.pixelScale = tags[TAGS.ModelPixelScale].slice(0, 2);
    if (tags[TAGS.ModelTiepoint] && tags[TAGS.ModelTiepoint].length >= 6) {
      geo.origin = [tags[TAGS.ModelTiepoint][3], tags[TAGS.ModelTiepoint][4]];
    }
    if (tags[TAGS.GeoKeyDirectory]) {
      var k = tags[TAGS.GeoKeyDirectory];
      for (var j = 4; j + 3 < k.length; j += 4) {
        if (k[j] === 3072) geo.crsEpsg = k[j + 3];        // ProjectedCSTypeGeoKey
        if (k[j] === 2048) geo.geographicEpsg = k[j + 3]; // GeographicTypeGeoKey
      }
    }
    if (tags[TAGS.GDAL_NODATA]) geo.nodataText = ascii(tags[TAGS.GDAL_NODATA]);
    return {
      littleEndian: littleEndian, entries: entries, tags: tags, geo: geo,
      width: tags[TAGS.ImageWidth] ? tags[TAGS.ImageWidth][0] : null,
      height: tags[TAGS.ImageLength] ? tags[TAGS.ImageLength][0] : null,
      bitsPerSample: tags[TAGS.BitsPerSample] ? tags[TAGS.BitsPerSample][0] : null,
      samples: tags[TAGS.SamplesPerPixel] ? tags[TAGS.SamplesPerPixel][0] : 1,
      sampleFormat: tags[TAGS.SampleFormat] ? tags[TAGS.SampleFormat][0] : 1,
      compression: tags[TAGS.Compression] ? tags[TAGS.Compression][0] : 1,
      predictor: tags[TAGS.Predictor] ? tags[TAGS.Predictor][0] : 1,
      rowsPerStrip: tags[TAGS.RowsPerStrip] ? tags[TAGS.RowsPerStrip][0] : null,
      planar: tags[TAGS.PlanarConfig] ? tags[TAGS.PlanarConfig][0] : 1,
      stripOffsets: tags[TAGS.StripOffsets] || [],
      stripByteCounts: tags[TAGS.StripByteCounts] || []
    };
  }

  function inflate(bytes, raw) {
    if (typeof DecompressionStream === 'undefined') {
      throw new Error('this browser cannot inflate DEFLATE data (DecompressionStream missing); ' +
                      'use the direct download link instead');
    }
    var stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream(raw ? 'deflate-raw' : 'deflate'));
    return new Response(stream).arrayBuffer().then(function (buf) { return new Uint8Array(buf); });
  }

  function deflateBytes(bytes) {
    if (typeof CompressionStream === 'undefined') {
      throw new Error('this browser cannot DEFLATE data (CompressionStream missing)');
    }
    var stream = new Blob([bytes]).stream().pipeThrough(new CompressionStream('deflate'));
    return new Response(stream).arrayBuffer().then(function (buf) { return new Uint8Array(buf); });
  }

  /** Undo a TIFF predictor for one row of float32 data, in place. */
  function undoPredictor(row, predictor, width, samples, littleEndian) {
    if (predictor === 2) {
      var bytesPerSample = 4, stride = width * samples;
      for (var i = samples; i < stride; i++) row[i] = (row[i] + row[i - samples]) & 0xFF;
      return row;
    }
    if (predictor === 3) {
      // Floating-point predictor (GDAL default for float32 + DEFLATE): the row is
      // byte-planed big-endian (plane 0 = most significant byte of every value),
      // the four planes are concatenated and the whole stream is horizontally
      // differenced. Undo: running sum mod 256, then read the i-th byte of each
      // plane as a big-endian float32.
      var acc = new Uint8Array(row.length), sum = 0;
      for (var k = 0; k < row.length; k++) { sum = (sum + row[k]) & 0xFF; acc[k] = sum; }
      var out = new Uint8Array(row.length), view = new DataView(out.buffer);
      for (var c = 0; c < width; c++) {
        var w = (acc[c] << 24) | (acc[width + c] << 16) | (acc[2 * width + c] << 8) | acc[3 * width + c];
        // the bit pattern is plane0 = most significant byte; store it in the
        // file's own byte order so the caller's getFloat32 flag stays correct
        view.setUint32(4 * c, w >>> 0, !!littleEndian);
      }
      row.set(out);
      return row;
    }
    return row;   // predictor 1 (none)
  }

  /** Read one single-band float32 GeoTIFF -> {width, height, values, ...}. */
  function readRaster(buffer) {
    var t = parseTIFF(buffer);
    if (t.samples !== 1) throw new Error('this file has ' + t.samples + ' samples per pixel; the competition needs one band');
    if (t.bitsPerSample !== 32 || t.sampleFormat !== 3) {
      throw new Error('this file is ' + t.bitsPerSample + '-bit format code ' + t.sampleFormat +
                      '; the competition needs 32-bit floats (SampleFormat 3)');
    }
    if (t.compression !== 1 && t.compression !== 8 && t.compression !== 32946) {
      throw new Error('compression code ' + t.compression + ' (' + (COMPRESSION[t.compression] || 'unknown') +
                      ') is not supported by this page; re-save as DEFLATE or uncompressed');
    }
    var width = t.width, height = t.height;
    var values = new Float32Array(width * height);
    var rowBytes = width * 4;
    var chains = [];
    for (var s = 0; s < t.stripOffsets.length; s++) {
      var bytes = new Uint8Array(buffer, t.stripOffsets[s], t.stripByteCounts[s]);
      chains.push(t.compression === 1 ? Promise.resolve(bytes) : inflate(bytes, t.compression === 32946));
    }
    return Promise.all(chains).then(function (parts) {
      var rowsPerStrip = t.rowsPerStrip || height;
      var flat = new Float32Array(width * height);
      parts.forEach(function (raw, index) {
        var firstRow = index * rowsPerStrip;
        var rows = Math.min(rowsPerStrip, height - firstRow);
        for (var r = 0; r < rows; r++) {
          var slice = raw.subarray(r * rowBytes, (r + 1) * rowBytes);
          if (slice.length < rowBytes) break;
          slice = slice.slice();
          undoPredictor(slice, t.predictor, width, 1, t.littleEndian);
          var rowView = new DataView(slice.buffer, slice.byteOffset, slice.byteLength);
          for (var c = 0; c < width; c++) {
            flat[(firstRow + r) * width + c] = rowView.getFloat32(4 * c, t.littleEndian);
          }
        }
      });
      return {width: width, height: height, samples: t.samples, bitsPerSample: t.bitsPerSample,
              sampleFormat: t.sampleFormat, compression: t.compression, predictor: t.predictor,
              geo: t.geo, values: flat, tags: t.tags};
    });
  }

  function toHex(buffer) {
    var b = new Uint8Array(buffer), s = '';
    for (var i = 0; i < b.length; i++) s += b[i].toString(16).padStart(2, '0');
    return s;
  }

  function sha256Hex(bytes) {
    var view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    return crypto.subtle.digest('SHA-256', view).then(toHex);
  }

  /** SHA-256 of the raw little-endian float32 payload (the repository's identity). */
  function pixelPayloadSha256(values) {
    var v = values instanceof Float32Array ? values : Float32Array.from(values);
    var little = new Uint8Array(new Uint32Array([1]).buffer)[0] === 1;
    if (little) return sha256Hex(new Uint8Array(v.buffer, v.byteOffset, v.byteLength));
    var out = new Uint8Array(v.length * 4), dv = new DataView(out.buffer);
    for (var i = 0; i < v.length; i++) dv.setFloat32(4 * i, v[i], true);
    return sha256Hex(out);
  }

  /** Check a raster against the competition rules and a template raster. */
  function validate(raster, reference) {
    var problems = [], warnings = [], info = {};
    if (raster.samples !== 1) problems.push('samples per pixel is ' + raster.samples + '; the competition needs a single-band raster');
    if (raster.bitsPerSample !== 32 || raster.sampleFormat !== 3) {
      problems.push('the file is ' + raster.bitsPerSample + '-bit format code ' + raster.sampleFormat +
                    ' instead of 32-bit float; integer rasters with 0-255 values are the usual cause of the ' +
                    '"Predicted values must be in range [0, 1]" rejection');
    }
    if (reference) {
      if (raster.width !== reference.width || raster.height !== reference.height) {
        problems.push('shape is ' + raster.width + 'x' + raster.height + '; the template is ' +
                      reference.width + 'x' + reference.height);
      }
      var a = raster.geo || {}, b = reference.geo || {};
      if (!a.pixelScale || !b.pixelScale) problems.push('missing ModelPixelScale: no geotransform');
      else if (a.pixelScale[0] !== b.pixelScale[0] || a.pixelScale[1] !== b.pixelScale[1]) {
        problems.push('pixel size is ' + a.pixelScale + '; the template is ' + b.pixelScale);
      }
      if (!a.origin || !b.origin) problems.push('missing ModelTiepoint: origin undefined');
      else if (a.origin[0] !== b.origin[0] || a.origin[1] !== b.origin[1]) {
        problems.push('origin is [' + a.origin + ']; the template is [' + b.origin + ']');
      }
      if (a.crsEpsg === null) warnings.push('no ProjectedCSTypeGeoKey in the file: CRS could not be checked');
      else if (b.crsEpsg !== null && a.crsEpsg !== b.crsEpsg) {
        problems.push('projected CRS is EPSG:' + a.crsEpsg + '; the template is EPSG:' + b.crsEpsg);
      }
    }
    var v = raster.values, n = v.length, nan = 0, inf = 0, below = 0, above = 0;
    var min = Infinity, max = -Infinity, finite = 0;
    for (var i = 0; i < n; i++) {
      var x = v[i];
      if (Number.isNaN(x)) { nan++; continue; }
      if (x === Infinity || x === -Infinity) { inf++; continue; }
      finite++;
      if (x < min) min = x;
      if (x > max) max = x;
      if (x < 0) below++;
      if (x > 1) above++;
    }
    info.finite = finite; info.nan = nan; info.inf = inf; info.min = finite ? min : null; info.max = finite ? max : null;
    if (below) problems.push(below + ' finite pixels are below 0');
    if (above) problems.push(above + ' finite pixels are above 1; the platform rejects values outside [0, 1]');
    if (inf) problems.push(inf + ' pixels are infinite');
    if (reference && reference.footprint) {
      var fp = reference.footprint, insideNotFinite = 0, outsideNotNan = 0;
      for (var j = 0; j < fp.length; j++) {
        var ok = Number.isFinite(v[j]);
        if (fp[j]) { if (!ok) insideNotFinite++; }
        else if (ok) outsideNotNan++;
      }
      info.inside_footprint_not_finite = insideNotFinite;
      info.outside_footprint_finite = outsideNotNan;
      if (insideNotFinite) {
        problems.push(insideNotFinite + ' pixels inside the template footprint are not finite (NaN/Infinity); ' +
                      'the group hit exactly this rejection in 2026: fill them with a finite value in [0, 1]');
      }
      if (outsideNotNan) {
        problems.push(outsideNotNan + ' pixels outside the template footprint are finite; the published ' +
                      'convention is NaN outside so the platform ignores them');
      }
    }
    info.crsEpsg = (raster.geo || {}).crsEpsg;
    info.compression = raster.compression;
    return {ok: problems.length === 0, problems: problems, warnings: warnings, info: info,
            min: info.min, max: info.max, nan: nan};
  }

  function typeSize(type, count) { return (TYPE_SIZE[type] || 1) * count; }

  /** Build a single-band float32 GeoTIFF that copies the template's georeferencing. */
  function buildGeoTIFF(values, width, height, templateBuffer) {
    var template = parseTIFF(templateBuffer);
    var keep = [TAGS.ModelPixelScale, TAGS.ModelTiepoint, TAGS.GeoKeyDirectory,
                TAGS.GeoDoubleParams, TAGS.GeoAsciiParams, TAGS.GDAL_NODATA];
    var copied = [];
    template.entries.forEach(function (e) {
      if (keep.indexOf(e.tag) >= 0) copied.push({tag: e.tag, type: e.type, values: e.values});
    });
    var little = new Uint8Array(new Uint32Array([1]).buffer)[0] === 1;
    var bytes;
    if (little) {
      bytes = new Uint8Array(values.buffer ? values.buffer.slice(values.byteOffset, values.byteOffset + values.byteLength)
                                           : Float32Array.from(values).buffer);
    } else {
      var tmp = new Uint8Array(values.length * 4), dv = new DataView(tmp.buffer);
      for (var i = 0; i < values.length; i++) dv.setFloat32(4 * i, values[i], true);
      bytes = tmp;
    }
    return deflateBytes(bytes).then(function (compressed) {
      var entries = [
        {tag: TAGS.ImageWidth, type: 3, values: [width]},
        {tag: TAGS.ImageLength, type: 3, values: [height]},
        {tag: TAGS.BitsPerSample, type: 3, values: [32]},
        {tag: TAGS.Compression, type: 3, values: [8]},
        {tag: TAGS.Photometric, type: 3, values: [1]},
        {tag: TAGS.StripOffsets, type: 4, values: [0]},
        {tag: TAGS.SamplesPerPixel, type: 3, values: [1]},
        {tag: TAGS.RowsPerStrip, type: 4, values: [height]},
        {tag: TAGS.StripByteCounts, type: 4, values: [compressed.length]},
        {tag: TAGS.PlanarConfig, type: 3, values: [1]},
        {tag: TAGS.Predictor, type: 3, values: [1]},
        {tag: TAGS.SampleFormat, type: 3, values: [3]}
      ].concat(copied);
      entries.sort(function (a, b) { return a.tag - b.tag; });

      var headerSize = 8, pixelOffset = headerSize;
      var ifdOffset = pixelOffset + compressed.length;
      if (ifdOffset % 2) ifdOffset++;
      var ifdSize = 2 + entries.length * 12 + 4;
      var cursor = ifdOffset + ifdSize;
      entries.forEach(function (e) {
        e.size = typeSize(e.type, e.values.length);
        if (e.size > 4) {
          var align = Math.min(8, TYPE_SIZE[e.type] || 1);
          if (cursor % align) cursor += align - (cursor % align);
          e.valueOffset = cursor;
          cursor += e.size;
        }
      });
      var out = new ArrayBuffer(cursor);
      var u8 = new Uint8Array(out), dv2 = new DataView(out);
      u8[0] = 0x49; u8[1] = 0x49;                       // little-endian
      dv2.setUint16(2, 42, true);
      dv2.setUint32(4, ifdOffset, true);
      u8.set(compressed, pixelOffset);
      dv2.setUint16(ifdOffset, entries.length, true);
      dv2.setUint32(ifdOffset + 2 + entries.length * 12, 0, true);
      entries.forEach(function (e, index) {
        var at = ifdOffset + 2 + index * 12;
        dv2.setUint16(at, e.tag, true);
        dv2.setUint16(at + 2, e.type, true);
        dv2.setUint32(at + 4, e.values.length, true);
        var target = e.size > 4 ? e.valueOffset : at + 8;
        if (e.size > 4) dv2.setUint32(at + 8, e.valueOffset, true);
        for (var i = 0; i < e.values.length; i++) {
          var o = target + i * (TYPE_SIZE[e.type] || 1);
          if (e.type === 2) dv2.setUint8(o, e.values[i] & 0xFF);
          else if (e.type === 3) dv2.setUint16(o, e.values[i], true);
          else if (e.type === 4) dv2.setUint32(o, e.values[i], true);
          else if (e.type === 11) dv2.setFloat32(o, e.values[i], true);
          else if (e.type === 12) dv2.setFloat64(o, e.values[i], true);
          else throw new Error('cannot write TIFF field type ' + e.type + ' (tag ' + e.tag + ')');
        }
        if (e.tag === TAGS.StripOffsets) dv2.setUint32(target, pixelOffset, true);
      });
      return out;
    });
  }

  function base64ToBytes(b64) {
    var bin = (typeof atob === 'function' ? atob(b64)
               : Buffer.from(b64, 'base64').toString('binary'));
    var out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  /** Rebuild the published raster from the compact payload (codes -> 0/1/NaN). */
  function decodePayload(b64, width, height) {
    var declared = root.GEMS_SUBMISSION_PAYLOAD && root.GEMS_SUBMISSION_PAYLOAD.manifest
      ? root.GEMS_SUBMISSION_PAYLOAD.manifest.grid : null;
    return inflate(base64ToBytes(b64), false).then(function (codes) {
      var w = width || (declared && declared.width);
      var h = height || (declared && declared.height);
      if (codes.length !== w * h) throw new Error('payload length ' + codes.length + ' does not match ' + w + 'x' + h);
      var values = new Float32Array(w * h);
      for (var i = 0; i < codes.length; i++) {
        values[i] = codes[i] === 2 ? NaN : (codes[i] === 1 ? 1.0 : 0.0);
      }
      return {width: w, height: h, values: values};
    });
  }

  root.GEOTIFF = {
    parseTIFF: parseTIFF, readRaster: readRaster, validate: validate,
    buildGeoTIFF: buildGeoTIFF, decodePayload: decodePayload,
    sha256Hex: sha256Hex, pixelPayloadSha256: pixelPayloadSha256, deflateBytes: deflateBytes
  };
})(typeof window !== 'undefined' ? window : globalThis);
