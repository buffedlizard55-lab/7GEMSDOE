/* Browser-side GeoTIFF tools for the GEMS submission workflow.
 *
 * The site must be able to (a) generate the exact .tif that gets uploaded and
 * (b) check any file before it is uploaded, because the submission form rejects
 * whole files with the single message "Predicted values must be in range [0, 1]".
 * Both are done offline in the page: no server, no upload of the user's file.
 *
 * Exposed as `window.GEOTIFF` (and `globalThis.GEOTIFF` in Node for the tests in
 * tests/js/). Pure data processing: no DOM access.
 *
 * Reference for the tag numbers: TIFF 6.0 specification and the GeoTIFF 1.1
 * specification (ModelPixelScaleTag 33550, ModelTiepointTag 33922,
 * GeoKeyDirectoryTag 34735, GDAL_NODATA 42113).
 */
(function (root) {
  'use strict';

  var TYPE_SIZE = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8, 16: 8, 17: 8, 18: 8};
  var TYPE_NAME = {1: 'BYTE', 2: 'ASCII', 3: 'SHORT', 4: 'LONG', 5: 'RATIONAL', 6: 'SBYTE', 7: 'UNDEFINED',
                   8: 'SSHORT', 9: 'SLONG', 10: 'SRATIONAL', 11: 'FLOAT', 12: 'DOUBLE', 16: 'LONG8',
                   17: 'SLONG8', 18: 'IFD8'};
  var TAG = {
    ImageWidth: 256, ImageLength: 257, BitsPerSample: 258, Compression: 259,
    PhotometricInterpretation: 262, StripOffsets: 273, SamplesPerPixel: 277,
    RowsPerStrip: 278, StripByteCounts: 279, PlanarConfiguration: 284, Predictor: 317,
    TileWidth: 322, TileLength: 323, TileOffsets: 324, TileByteCounts: 325,
    SampleFormat: 339, ModelPixelScale: 33550, ModelTiepoint: 33922,
    GeoKeyDirectory: 34735, GeoDoubleParams: 34736, GeoAsciiParams: 34737, GDAL_NODATA: 42113
  };
  var GEOKEY = {ProjectedCSTypeGeoKey: 3072, GeographicTypeGeoKey: 2048, GTModelTypeGeoKey: 1024};

  function typeSize(type, count) {
    var s = TYPE_SIZE[type];
    if (!s) throw new Error('unsupported TIFF field type ' + type);
    return s * count;
  }

  function readValues(dv, le, type, count, offset) {
    var i, out = [];
    switch (type) {
      case 1: case 7: for (i = 0; i < count; i++) out.push(dv.getUint8(offset + i)); break;
      case 2: { var bytes = []; for (i = 0; i < count; i++) bytes.push(dv.getUint8(offset + i));
                out.push(new TextDecoder('latin1').decode(new Uint8Array(bytes))); break; }
      case 3: for (i = 0; i < count; i++) out.push(dv.getUint16(offset + 2 * i, le)); break;
      case 4: for (i = 0; i < count; i++) out.push(dv.getUint32(offset + 4 * i, le)); break;
      case 5: for (i = 0; i < count; i++) out.push(dv.getUint32(offset + 8 * i, le) / dv.getUint32(offset + 8 * i + 4, le)); break;
      case 6: for (i = 0; i < count; i++) out.push(dv.getInt8(offset + i)); break;
      case 8: for (i = 0; i < count; i++) out.push(dv.getInt16(offset + 2 * i, le)); break;
      case 9: for (i = 0; i < count; i++) out.push(dv.getInt32(offset + 4 * i, le)); break;
      case 10: for (i = 0; i < count; i++) out.push(dv.getInt32(offset + 8 * i, le) / dv.getInt32(offset + 8 * i + 4, le)); break;
      case 11: for (i = 0; i < count; i++) out.push(dv.getFloat32(offset + 4 * i, le)); break;
      case 12: for (i = 0; i < count; i++) out.push(dv.getFloat64(offset + 8 * i, le)); break;
      case 16: for (i = 0; i < count; i++) out.push(Number(dv.getBigUint64(offset + 8 * i, le))); break;
      case 17: for (i = 0; i < count; i++) out.push(Number(dv.getBigInt64(offset + 8 * i, le))); break;
      case 18: for (i = 0; i < count; i++) out.push(Number(dv.getBigUint64(offset + 8 * i, le))); break;
      default: throw new Error('unsupported TIFF field type ' + type);
    }
    return out;
  }

  function parseTIFF(buffer) {
    var dv = new DataView(buffer);
    if (dv.byteLength < 8) throw new Error('file is too small to be a TIFF');
    var b0 = dv.getUint8(0), b1 = dv.getUint8(1), le;
    if (b0 === 0x49 && b1 === 0x49) le = true;
    else if (b0 === 0x4D && b1 === 0x4D) le = false;
    else throw new Error('not a TIFF: the first two bytes are not II or MM (the file may be a ZIP, JSON or a renamed image)');
    var magic = dv.getUint16(2, le);
    if (magic !== 42) {
      throw new Error('classic TIFF expected (magic ' + magic + '); BigTIFF (magic 43) is not supported by this reader');
    }
    var ifd = dv.getUint32(4, le);
    if (ifd + 2 > dv.byteLength) throw new Error('TIFF directory offset is outside the file');
    var n = dv.getUint16(ifd, le), tags = {}, entries = [];
    for (var i = 0; i < n; i++) {
      var off = ifd + 2 + i * 12;
      var tag = dv.getUint16(off, le), type = dv.getUint16(off + 2, le), count = dv.getUint32(off + 4, le);
      var size = typeSize(type, count);
      var dataOffset = size <= 4 ? off + 8 : dv.getUint32(off + 8, le);
      if (dataOffset + size > dv.byteLength) throw new Error('TIFF field ' + tag + ' points outside the file');
      var values = readValues(dv, le, type, count, dataOffset);
      entries.push({tag: tag, type: type, count: count, values: values, dataOffset: dataOffset});
      tags[tag] = values;
    }
    return {littleEndian: le, entries: entries, tags: tags, ifdOffset: ifd, byteLength: dv.byteLength};
  }

  function first(tags, tag) { var v = tags[tag]; return Array.isArray(v) ? v[0] : v; }

  function geoInfo(tiff) {
    var t = tiff.tags, info = {crsEpsg: null, pixelScale: null, origin: null, nodataText: null};
    if (t[TAG.ModelPixelScale]) info.pixelScale = t[TAG.ModelPixelScale].slice(0, 2);
    if (t[TAG.ModelTiepoint] && info.pixelScale) {
      var tp = t[TAG.ModelTiepoint];
      // tiepoint = (raster i, j, k, model x, y, z); origin is the model position of raster (0,0)
      info.origin = [tp[3] - tp[0] * info.pixelScale[0], tp[4] + tp[1] * info.pixelScale[1]];
    }
    if (t[TAG.GeoKeyDirectory]) {
      var g = t[TAG.GeoKeyDirectory];
      for (var i = 4; i + 3 < g.length; i += 4) {
        if (g[i] === GEOKEY.ProjectedCSTypeGeoKey && g[i + 1] === 0) info.crsEpsg = g[i + 3];
      }
    }
    if (t[TAG.GDAL_NODATA]) info.nodataText = String(t[TAG.GDAL_NODATA][0]).replace(/\u0000$/, '');
    return info;
  }

  function decompressBytes(bytes, compression) {
    if (compression === 1) return Promise.resolve(bytes);
    var fmt;
    if (compression === 8 || compression === 32946) fmt = 'deflate';  // Adobe Deflate / zlib-wrapped
    else if (compression === 5) throw new Error('LZW-compressed TIFF strips are not supported by this page; re-export with GDAL default (DEFLATE) or no compression');
    else throw new Error('unsupported TIFF compression ' + compression);
    if (typeof DecompressionStream !== 'function') throw new Error('this browser cannot decompress DEFLATE strips (needs DecompressionStream)');
    var stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream(fmt));
    return new Response(stream).arrayBuffer().then(function (ab) { return new Uint8Array(ab); });
  }

  /**
   * Undo a TIFF predictor, in place.
   *
   * Predictor 3 (the floating-point predictor GDAL writes by default for float32
   * + DEFLATE) is not a simple difference: each row is byte-planed big-endian
   * (plane j holds byte j of every value), the four planes are concatenated and
   * then horizontally differenced as one byte stream.  Verified byte-for-byte
   * against libtiff output in tests/js/geotiff_roundtrip.mjs.
   */
  function undoPredictorRow(row, predictor, width, samples, littleEndian) {
    var i;
    if (predictor === 1 || predictor === undefined || predictor === 0) return row;
    if (predictor === 2) {
      var stride = width * samples;
      for (i = samples; i < stride; i++) row[i] = (row[i] + row[i - samples]) & 0xFF;
      return row;
    }
    if (predictor === 3) {
      if (samples !== 1) throw new Error('floating-point predictor with multiple samples per pixel is not supported by this page');
      if (width * 4 !== row.length) throw new Error('row length does not match width for float32 data');
      var acc = new Uint8Array(row.length);
      var sum = 0;
      for (i = 0; i < row.length; i++) { sum = (sum + row[i]) & 0xFF; acc[i] = sum; }
      // acc = [plane0 | plane1 | plane2 | plane3]; value i uses the i-th byte of each plane, big-endian
      for (i = 0; i < width; i++) {
        var b0 = acc[i], b1 = acc[width + i], b2 = acc[2 * width + i], b3 = acc[3 * width + i];
        // big-endian bit pattern -> bytes in file order
        row[4 * i] = littleEndian ? b3 : b0;
        row[4 * i + 1] = littleEndian ? b2 : b1;
        row[4 * i + 2] = littleEndian ? b1 : b2;
        row[4 * i + 3] = littleEndian ? b0 : b3;
      }
      return row;
    }
    if (predictor === 5) throw new Error('PNG predictor (5) is not supported by this page');
    throw new Error('unsupported TIFF predictor ' + predictor);
  }

  function decodeFloats(bytes, littleEndian) {
    var out = new Float32Array(bytes.length / 4);
    var dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    for (var i = 0; i < out.length; i++) out[i] = dv.getFloat32(i * 4, littleEndian);
    return out;
  }

  /** Read a single-band float32 raster plus its georeferencing. */
  function readRaster(buffer) {
    var tiff = parseTIFF(buffer), t = tiff.tags;
    var width = first(t, TAG.ImageWidth), height = first(t, TAG.ImageLength);
    var bits = first(t, TAG.BitsPerSample), sampleFormat = first(t, TAG.SampleFormat) || 1;
    var samples = first(t, TAG.SamplesPerPixel) || 1;
    var compression = first(t, TAG.Compression) || 1;
    var predictor = first(t, TAG.Predictor) || 1;
    var tasks = [];

    if (t[TAG.StripOffsets]) {
      var so = t[TAG.StripOffsets], sc = t[TAG.StripByteCounts];
      var rps = first(t, TAG.RowsPerStrip) || height;
      for (var i = 0; i < so.length; i++) {
        tasks.push({row: i * rps, col: 0, rows: Math.min(rps, height - i * rps), cols: width,
                    offset: so[i], count: sc[i]});
      }
    } else if (t[TAG.TileOffsets]) {
      var to = t[TAG.TileOffsets], tc = t[TAG.TileByteCounts];
      var tw = first(t, TAG.TileWidth), th = first(t, TAG.TileLength);
      var perRow = Math.ceil(width / tw);
      for (var k = 0; k < to.length; k++) {
        var tr = Math.floor(k / perRow), tcIndex = k % perRow;
        tasks.push({row: tr * th, col: tcIndex * tw, rows: Math.min(th, height - tr * th),
                    cols: Math.min(tw, width - tcIndex * tw), offset: to[k], count: tc[k]});
      }
    } else {
      throw new Error('TIFF has neither strip nor tile offsets; it is not a readable raster');
    }

    return Promise.all(tasks.map(function (task) {
      return decompressBytes(new Uint8Array(buffer, task.offset, task.count), compression)
        .then(function (raw) { return {task: task, raw: raw}; });
    })).then(function (parts) {
      var values = new Float32Array(width * height);
      parts.forEach(function (part) {
        var task = part.task;
        var bytes = part.raw;
        var rowBytes = task.cols * 4, outRow = new Uint8Array(rowBytes);
        for (var r = 0; r < task.rows; r++) {
          var start = r * rowBytes, slice = bytes.subarray(start, start + rowBytes);
          if (slice.length < rowBytes) break;
          outRow.set(slice);
          undoPredictorRow(outRow, predictor, task.cols, 1, tiff.littleEndian);
          var floats = new Float32Array(outRow.buffer.slice(0));
          for (var c = 0; c < task.cols; c++) {
            values[(task.row + r) * width + task.col + c] = floats[c];
          }
        }
      });
      return {width: width, height: height, samples: samples, bitsPerSample: bits,
              sampleFormat: sampleFormat, compression: compression, predictor: predictor,
              values: values, geo: geoInfo(tiff), tiff: tiff};
    });
  }

  function hex(bytes) {
    var out = '';
    for (var i = 0; i < bytes.length; i++) out += (bytes[i] + 0x100).toString(16).slice(1);
    return out;
  }

  function sha256Hex(bytes) {
    if (typeof crypto === 'undefined' || !crypto.subtle) {
      return Promise.reject(new Error('SHA-256 needs a secure context (https:// or localhost)'));
    }
    return crypto.subtle.digest('SHA-256', bytes).then(function (d) { return hex(new Uint8Array(d)); });
  }

  /** SHA-256 of the raw little-endian float32 pixel array (compressor-independent). */
  function pixelPayloadSha256(values) {
    return sha256Hex(new Uint8Array(values.buffer, values.byteOffset, values.byteLength));
  }

  /**
   * Validate a candidate submission file against the competition template.
   * `reference` is a parsed raster of the authoritative template (or an object
   * with {width, height, geo, footprint} where footprint is a Uint8Array).
   */
  function validate(raster, reference, opts) {
    opts = opts || {};
    var problems = [], warnings = [], info = {};
    var tol = opts.tolerance || 1e-6;
    function near(a, b) { return Math.abs(a - b) <= tol * Math.max(1, Math.abs(a), Math.abs(b)); }

    if (raster.samples !== 1) problems.push('samples per pixel is ' + raster.samples + '; the competition needs a single-band raster (single raster layer)');
    if (raster.bitsPerSample !== 32) problems.push('bits per sample is ' + raster.bitsPerSample + '; the competition needs 32-bit floats');
    if (raster.sampleFormat !== 3) problems.push('sample format is ' + raster.sampleFormat + ' (1 = unsigned integer, 2 = signed integer, 3 = float); ' +
      'uint8/uint16 data (values 0-255) is the most common cause of the "Predicted values must be in range [0, 1]" rejection');
    if (reference) {
      if (raster.width !== reference.width || raster.height !== reference.height) {
        problems.push('shape is ' + raster.width + ' x ' + raster.height + '; the template is ' + reference.width + ' x ' + reference.height);
      }
    }
    var geo = raster.geo;
    info.crs_epsg = geo.crsEpsg;
    info.pixel_scale = geo.pixelScale;
    info.origin = geo.origin;
    if (reference && reference.geo) {
      if (!geo.pixelScale) problems.push('no ModelPixelScaleTag (33550): the file has no geotransform');
      else if (!(near(geo.pixelScale[0], reference.geo.pixelScale[0]) && near(geo.pixelScale[1], reference.geo.pixelScale[1]))) {
        problems.push('pixel size is ' + geo.pixelScale.join(' x ') + '; the template is ' + reference.geo.pixelScale.join(' x '));
      }
      if (!geo.origin) problems.push('no ModelTiepointTag (33922): the file origin is undefined');
      else if (!(near(geo.origin[0], reference.geo.origin[0]) && near(geo.origin[1], reference.geo.origin[1]))) {
        problems.push('origin is [' + geo.origin.join(', ') + ']; the template origin is [' + reference.geo.origin.join(', ') + ']');
      }
      if (reference.geo.crsEpsg !== null && geo.crsEpsg !== null && geo.crsEpsg !== reference.geo.crsEpsg) {
        problems.push('projected CRS code is EPSG:' + geo.crsEpsg + '; the template is EPSG:' + reference.geo.crsEpsg);
      } else if (geo.crsEpsg === null) {
        warnings.push('no GeoKeyDirectoryTag (34735) with ProjectedCSTypeGeoKey: CRS cannot be checked from the file');
      }
    }

    var v = raster.values, n = v.length, finite = 0, nan = 0, posInf = 0, negInf = 0, below = 0, above = 0;
    var min = Infinity, max = -Infinity, maxNeg = 0, minPos = Infinity;
    for (var i = 0; i < n; i++) {
      var x = v[i];
      if (Number.isNaN(x)) { nan++; continue; }
      if (x === Infinity) { posInf++; continue; }
      if (x === -Infinity) { negInf++; continue; }
      finite++;
      if (x < min) min = x;
      if (x > max) max = x;
      if (x < 0) { below++; if (x < maxNeg) maxNeg = x; }
      if (x > 1) { above++; if (x < minPos) minPos = x; }
    }
    info.finite = finite; info.nan = nan; info.posInf = posInf; info.negInf = negInf;
    info.min = finite ? min : null; info.max = finite ? max : null;

    if (below) problems.push(below + ' finite pixels are below 0 (most negative ' + maxNeg + ')');
    if (above) problems.push(above + ' finite pixels are above 1 (most positive ' + minPos + '); the form rejects files outside [0, 1]');
    if (posInf) problems.push(posInf + ' pixels are +Infinity');
    if (negInf) problems.push(negInf + ' pixels are -Infinity');

    if (reference && reference.footprint) {
      var fp = reference.footprint, insideNotFinite = 0, outsideFinite = 0, outsideNonZero = 0;
      for (var j = 0; j < fp.length; j++) {
        var isFinite = !Number.isNaN(v[j]) && v[j] !== Infinity && v[j] !== -Infinity;
        if (fp[j]) { if (!isFinite) insideNotFinite++; }
        else if (isFinite) {
          outsideFinite++;
          if (v[j] !== 0) outsideNonZero++;
        }
      }
      info.inside_not_finite = insideNotFinite;
      info.outside_finite = outsideFinite;
      info.outside_finite_nonzero = outsideNonZero;
      if (insideNotFinite) {
        problems.push(insideNotFinite + ' pixels are NaN/Inf inside the template footprint; the submission form reads these as out of range ' +
                      '(this is the documented root cause of the group\'s rejection)');
      }
      if (outsideFinite) {
        warnings.push(outsideFinite + ' finite pixels lie outside the template footprint' + (outsideNonZero ? ' (' + outsideNonZero + ' non-zero)' : ' (all zero)') +
                      '; GDAL-driven validators can mask these away, but NaN outside is the safest layout');
      }
    }
    info.problems = problems; info.warnings = warnings;
    info.ok = problems.length === 0;
    return info;
  }

  function encodeLE(values) {
    var out = new Uint8Array(values.length * 4);
    var dv = new DataView(out.buffer);
    for (var i = 0; i < values.length; i++) dv.setFloat32(i * 4, values[i], true);
    return out;
  }

  function deflate(bytes, fmt) {
    if (typeof CompressionStream !== 'function') throw new Error('this browser cannot compress DEFLATE (needs CompressionStream)');
    var stream = new Blob([bytes]).stream().pipeThrough(new CompressionStream(fmt || 'deflate'));
    return new Response(stream).arrayBuffer().then(function (ab) { return new Uint8Array(ab); });
  }

  /**
   * Build a single-band float32 GeoTIFF, copying the georeferencing tags of a
   * template file. Returns a Promise<ArrayBuffer>.
   */
  function buildGeoTIFF(values, width, height, templateBuffer) {
    var template = parseTIFF(templateBuffer), t = template.tags;
    var entries = [];
    function add(tag, type, valuesArray) { entries.push({tag: tag, type: type, values: valuesArray}); }

    var copyable = {};
    template.entries.forEach(function (en) {
      if ([TAG.ModelPixelScale, TAG.ModelTiepoint, TAG.GeoKeyDirectory, TAG.GeoDoubleParams,
           TAG.GeoAsciiParams, TAG.GDAL_NODATA].indexOf(en.tag) >= 0) {
        copyable[en.tag] = {type: en.type, values: en.values};
      }
    });

    add(TAG.ImageWidth, 3, [width]);
    add(TAG.ImageLength, 3, [height]);
    add(TAG.BitsPerSample, 3, [32]);
    add(TAG.Compression, 3, [8]);                 // Adobe Deflate (zlib stream)
    add(TAG.PhotometricInterpretation, 3, [1]);
    add(TAG.StripOffsets, 4, [0]);                // filled once the layout is known
    add(TAG.SamplesPerPixel, 3, [1]);
    add(TAG.RowsPerStrip, 4, [height]);
    add(TAG.StripByteCounts, 4, [0]);
    add(TAG.PlanarConfiguration, 3, [1]);
    add(TAG.SampleFormat, 3, [3]);                // IEEE float
    Object.keys(copyable).map(Number).sort(function (a, b) { return a - b; }).forEach(function (tag) {
      add(tag, copyable[tag].type, copyable[tag].values);
    });
    entries.sort(function (a, b) { return a.tag - b.tag; });

    return deflate(encodeLE(values), 'deflate').then(function (compressed) {
      var header = 8, pixelOffset = header;
      var n = entries.length;
      var ifdSize = 2 + n * 12 + 4;
      var ifdOffset = pixelOffset + compressed.length;
      var cursor = ifdOffset + ifdSize;
      entries.forEach(function (en) {
        if (en.type === 2) en.byteLength = String(en.values[0]).length + 1;   // ASCII: count includes the NUL
        en.size = en.type === 2 ? en.byteLength : typeSize(en.type, en.values.length);
        if (en.size > 4) {
          var align = Math.min(8, TYPE_SIZE[en.type]);
          if (cursor % align) cursor += align - (cursor % align);
          en.offset = cursor;
          cursor += en.size;
        }
      });
      var out = new ArrayBuffer(cursor);
      var dv = new DataView(out), u8 = new Uint8Array(out);
      dv.setUint8(0, 0x49); dv.setUint8(1, 0x49);
      dv.setUint16(2, 42, true); dv.setUint32(4, ifdOffset, true);
      u8.set(compressed, pixelOffset);
      dv.setUint16(ifdOffset, n, true);
      dv.setUint32(ifdOffset + 2 + n * 12, 0, true);
      entries.forEach(function (en, i) {
        var off = ifdOffset + 2 + i * 12;
        dv.setUint16(off, en.tag, true);
        dv.setUint16(off + 2, en.type, true);
        dv.setUint32(off + 4, en.type === 2 ? en.byteLength : en.values.length, true);
        var writeAt = en.size > 4 ? en.offset : off + 8;
        if (en.size > 4) dv.setUint32(off + 8, en.offset, true);   // pointer to the out-of-line value
        if (en.type === 1) {
          en.values.forEach(function (val, k) { dv.setUint8(writeAt + k, val); });
        } else if (en.type === 2) {
          var s = String(en.values[0]);
          for (var c = 0; c < s.length; c++) dv.setUint8(writeAt + c, s.charCodeAt(c) & 0xFF);
          dv.setUint8(writeAt + s.length, 0);
        } else {
          en.values.forEach(function (val, k) {
            var o = writeAt + k * TYPE_SIZE[en.type];
            if (en.type === 3) dv.setUint16(o, val, true);
            else if (en.type === 4) dv.setUint32(o, val, true);
            else if (en.type === 12) dv.setFloat64(o, val, true);
            else throw new Error('cannot write TIFF field type ' + en.type + ' (tag ' + en.tag + ')');
          });
        }
      });
      // the two layout-dependent values
      entries.forEach(function (en, i) {
        if (en.tag !== TAG.StripOffsets && en.tag !== TAG.StripByteCounts) return;
        var o = ifdOffset + 2 + i * 12 + 8;
        dv.setUint32(o, en.tag === TAG.StripOffsets ? pixelOffset : compressed.length, true);
      });
      return out;
    });
  }

  function decodeBase64(b64) {
    var bin = (typeof atob === 'function' ? atob(b64) : Buffer.from(b64, 'base64').toString('binary'));
    var out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  function varint(bytes, state) {
    var result = 0, shift = 0, b;
    do {
      if (state.i >= bytes.length) throw new Error('payload ended mid-varint');
      b = bytes[state.i++];
      result += (b & 0x7F) * Math.pow(2, shift);
      shift += 7;
    } while (b & 0x80);
    return result;
  }

  /** Decode the G7PL1 payload into a Float32Array (0.0 / 1.0 / NaN). */
  function decodePayload(base64) {
    var bytes = decodeBase64(base64);
    var magic = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3], bytes[4]);
    if (magic !== 'G7PL1') throw new Error('unexpected payload magic ' + magic);
    var dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    var rows = dv.getUint32(5, true), cols = dv.getUint32(9, true);
    var values = new Float32Array(rows * cols);
    var state = {i: 13};
    for (var r = 0; r < rows; r++) {
      var runs = dv.getUint32(state.i, true); state.i += 4;
      var x = 0;
      for (var k = 0; k < runs; k++) {
        var len = varint(bytes, state);
        var code = bytes[state.i++];
        var value = code === 0 ? 0 : code === 1 ? 1 : NaN;
        for (var j = 0; j < len; j++) values[r * cols + x + j] = value;
        x += len;
      }
      if (x !== cols) throw new Error('row ' + r + ' decoded to ' + x + ' pixels, expected ' + cols);
    }
    return {width: cols, height: rows, values: values};
  }

  root.GEOTIFF = {
    TAG: TAG,
    TYPE_NAME: TYPE_NAME,
    parseTIFF: parseTIFF,
    geoInfo: geoInfo,
    readRaster: readRaster,
    validate: validate,
    buildGeoTIFF: buildGeoTIFF,
    sha256Hex: sha256Hex,
    pixelPayloadSha256: pixelPayloadSha256,
    decodePayload: decodePayload,
    decodeBase64: decodeBase64
  };
})(typeof window !== 'undefined' ? window : globalThis);
