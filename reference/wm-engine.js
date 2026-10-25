/*
 * Field Camera invisible mark: reference engine (JavaScript).
 * Spec: WATERMARK-SPEC.md. The Kotlin engine (app/.../core/watermark) must read and write
 * the same marks. Pure functions, no DOM, no Node-only APIs: runs in a browser, a worker or Node.
 *
 * Image buffers are RGBA, row-major, 4 bytes per pixel (canvas ImageData layout).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.WM = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // ------------------------------------------------------------------ constants
  var EPOCH = 1767225600; // 2026-01-01T00:00:00Z
  var T_STD = 14.0;
  var L1 = { name: 'colour', ncells: 10000, seed: 11, pilotFrac: 0.20, amax: 2.0, floor: 0.25, kind: 'cbcr', kern: 5 };
  var L2 = { name: 'brightness', ncells: 50000, seed: 77, pilotFrac: 0.20, amax: 4.5, floor: 0.0, kind: 'luma', kern: 3 };
  var N1 = 118; // layer 1 payload bits (3 flags + 25 + 26 + 14 + 29 + 4 + 1 + crc16)
  var N2 = 60;  // layer 2 payload bits (1 flag + 21 + 22 + crc16)
  var DETECT_Z = 3.5;

  // ------------------------------------------------------------------ bits, crc
  function toBits(v, n) {
    var out = new Array(n);
    for (var i = 0; i < n; i++) out[i] = Math.floor(v / Math.pow(2, n - 1 - i)) % 2;
    return out;
  }
  function fromBits(b) {
    var v = 0;
    for (var i = 0; i < b.length; i++) v = v * 2 + b[i];
    return v;
  }
  /** CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) over the bits, padded with zeros to a whole byte. */
  function crc16(bits) {
    var padded = bits.slice();
    while (padded.length % 8) padded.push(0);
    var crc = 0xFFFF;
    for (var i = 0; i < padded.length; i += 8) {
      var byte = 0;
      for (var j = 0; j < 8; j++) byte = (byte << 1) | padded[i + j];
      crc ^= byte << 8;
      for (var k = 0; k < 8; k++) crc = (crc & 0x8000) ? ((crc << 1) ^ 0x1021) & 0xFFFF : (crc << 1) & 0xFFFF;
    }
    return crc;
  }

  // ------------------------------------------------------------------ sha256 (sync, for the derived ID)
  var K256 = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2];
  function sha256(bytes) {
    var h = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
    var l = bytes.length, bitLen = l * 8;
    var padLen = ((l + 9 + 63) >> 6) << 6;
    var m = new Uint8Array(padLen);
    m.set(bytes);
    m[l] = 0x80;
    var dv = new DataView(m.buffer);
    dv.setUint32(padLen - 8, Math.floor(bitLen / 4294967296));
    dv.setUint32(padLen - 4, bitLen >>> 0);
    var w = new Uint32Array(64);
    for (var off = 0; off < padLen; off += 64) {
      for (var i = 0; i < 16; i++) w[i] = dv.getUint32(off + i * 4);
      for (i = 16; i < 64; i++) {
        var a = w[i - 15], b = w[i - 2];
        var s0 = ((a >>> 7) | (a << 25)) ^ ((a >>> 18) | (a << 14)) ^ (a >>> 3);
        var s1 = ((b >>> 17) | (b << 15)) ^ ((b >>> 19) | (b << 13)) ^ (b >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
      }
      var A = h[0], B = h[1], C = h[2], D = h[3], E = h[4], F = h[5], G = h[6], H = h[7];
      for (i = 0; i < 64; i++) {
        var S1 = ((E >>> 6) | (E << 26)) ^ ((E >>> 11) | (E << 21)) ^ ((E >>> 25) | (E << 7));
        var ch = (E & F) ^ (~E & G);
        var t1 = (H + S1 + ch + K256[i] + w[i]) >>> 0;
        var S0 = ((A >>> 2) | (A << 30)) ^ ((A >>> 13) | (A << 19)) ^ ((A >>> 22) | (A << 10));
        var maj = (A & B) ^ (A & C) ^ (B & C);
        var t2 = (S0 + maj) >>> 0;
        H = G; G = F; F = E; E = (D + t1) >>> 0; D = C; C = B; B = A; A = (t1 + t2) >>> 0;
      }
      h[0] = (h[0] + A) >>> 0; h[1] = (h[1] + B) >>> 0; h[2] = (h[2] + C) >>> 0; h[3] = (h[3] + D) >>> 0;
      h[4] = (h[4] + E) >>> 0; h[5] = (h[5] + F) >>> 0; h[6] = (h[6] + G) >>> 0; h[7] = (h[7] + H) >>> 0;
    }
    var out = new Uint8Array(32), odv = new DataView(out.buffer);
    for (i = 0; i < 8; i++) odv.setUint32(i * 4, h[i]);
    return out;
  }

  /** 10-letter ID: first 8 bytes of SHA-256 over the payload bits (one byte per bit), base 26, A = 0. */
  function makeId(bodyBits) {
    var d = sha256(Uint8Array.from(bodyBits));
    var n = 0n;
    for (var i = 0; i < 8; i++) n = (n << 8n) | BigInt(d[i]);
    var s = '';
    for (i = 0; i < 10; i++) { s += String.fromCharCode(65 + Number(n % 26n)); n /= 26n; }
    return s;
  }

  // ------------------------------------------------------------------ payloads
  /** d = {lat, lon, alt, t (unix seconds), tenth (0-9), manual (0/1)}; missing fields = null/undefined. */
  function packL1(d) {
    var hasLoc = d.lat != null && d.lon != null, hasAlt = d.alt != null, hasT = d.t != null;
    var la = hasLoc ? Math.round((d.lat + 90) / 180 * (Math.pow(2, 25) - 1)) : 0;
    var lo = hasLoc ? Math.round((d.lon + 180) / 360 * (Math.pow(2, 26) - 1)) : 0;
    var al = hasAlt ? Math.min(Math.max(Math.round(d.alt) + 500, 0), 16383) : 0;
    var tt = hasT ? Math.min(Math.max(Math.floor(d.t) - EPOCH, 0), Math.pow(2, 29) - 1) : 0;
    var tenth = Math.min(Math.max(d.tenth | 0, 0), 9);
    var bits = [hasLoc ? 1 : 0, hasAlt ? 1 : 0, hasT ? 1 : 0]
      .concat(toBits(la, 25), toBits(lo, 26), toBits(al, 14), toBits(tt, 29), toBits(tenth, 4), [d.manual ? 1 : 0]);
    return bits.concat(toBits(crc16(bits), 16));
  }
  function unpackL1(bits) {
    var body = bits.slice(0, bits.length - 16);
    if (crc16(body) !== fromBits(bits.slice(bits.length - 16))) return null;
    var p = 3;
    function take(n) { var v = fromBits(body.slice(p, p + n)); p += n; return v; }
    var la = take(25), lo = take(26), al = take(14), tt = take(29), tenth = take(4), man = take(1);
    return {
      id: makeId(body), tenth: tenth, manual: man,
      lat: body[0] ? la / (Math.pow(2, 25) - 1) * 180 - 90 : null,
      lon: body[0] ? lo / (Math.pow(2, 26) - 1) * 360 - 180 : null,
      alt: body[1] ? al - 500 : null,
      t: body[2] ? EPOCH + tt : null
    };
  }
  function packL2(d) {
    var hasLoc = d.lat != null && d.lon != null;
    var la = hasLoc ? Math.round((d.lat + 90) / 180 * (Math.pow(2, 21) - 1)) : 0;
    var lo = hasLoc ? Math.round((d.lon + 180) / 360 * (Math.pow(2, 22) - 1)) : 0;
    var bits = [hasLoc ? 1 : 0].concat(toBits(la, 21), toBits(lo, 22));
    return bits.concat(toBits(crc16(bits), 16));
  }
  function unpackL2(bits) {
    var body = bits.slice(0, bits.length - 16);
    if (crc16(body) !== fromBits(bits.slice(bits.length - 16))) return null;
    var la = fromBits(body.slice(1, 22)), lo = fromBits(body.slice(22, 44));
    return {
      lat: body[0] ? la / (Math.pow(2, 21) - 1) * 180 - 90 : null,
      lon: body[0] ? lo / (Math.pow(2, 22) - 1) * 360 - 180 : null
    };
  }

  // ------------------------------------------------------------------ convolutional code K=7, rate 1/2, soft Viterbi
  var G0 = 0x5B, G1 = 0x79; // 0o133, 0o171
  function parity(x) { x ^= x >> 4; x ^= x >> 2; x ^= x >> 1; return x & 1; }
  var OUT0 = new Uint8Array(128), OUT1 = new Uint8Array(128); // index (u << 6) | state
  for (var s = 0; s < 64; s++) for (var u = 0; u < 2; u++) {
    var reg = (u << 6) | s;
    OUT0[reg] = parity(reg & G0); OUT1[reg] = parity(reg & G1);
  }
  function convEncode(bits) {
    var st = 0, out = [];
    var seq = bits.concat([0, 0, 0, 0, 0, 0]);
    for (var i = 0; i < seq.length; i++) {
      var reg = (seq[i] << 6) | st;
      out.push(OUT0[reg], OUT1[reg]);
      st = reg >> 1;
    }
    return out;
  }
  /** soft: positive favours bit 1. Returns the information bits (tail removed). */
  function viterbi(soft) {
    var m = soft.length >> 1;
    var NEG = -1e300;
    var pm = new Float64Array(64).fill(NEG); pm[0] = 0;
    var back = new Uint8Array(m * 64);
    var nm = new Float64Array(64);
    for (var t = 0; t < m; t++) {
      var s0 = soft[2 * t], s1 = soft[2 * t + 1];
      for (var ns = 0; ns < 64; ns++) {
        var uu = ns >> 5, p0 = (ns << 1) & 63, p1 = p0 | 1;
        var r0 = (uu << 6) | p0, r1 = (uu << 6) | p1;
        var c0 = pm[p0] + (OUT0[r0] ? s0 : -s0) + (OUT1[r0] ? s1 : -s1);
        var c1 = pm[p1] + (OUT0[r1] ? s0 : -s0) + (OUT1[r1] ? s1 : -s1);
        if (c1 > c0) { nm[ns] = c1; back[t * 64 + ns] = 1; } else { nm[ns] = c0; back[t * 64 + ns] = 0; }
      }
      pm.set(nm);
    }
    var st = 0, bits = new Array(m);
    for (t = m - 1; t >= 0; t--) { bits[t] = st >> 5; st = ((st << 1) & 63) | back[t * 64 + st]; }
    return bits.slice(0, m - 6);
  }

  // ------------------------------------------------------------------ portable PRNG, grid, plan
  function mulberry32(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) | 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function gridFor(W, H, ncells) {
    var nx = Math.max(8, Math.floor(Math.sqrt(ncells * W / H) + 0.5));
    var ny = Math.max(8, Math.floor(ncells / nx + 0.5));
    return [nx, ny];
  }
  var planCache = {};
  function plan(layer, nx, ny, ncoded) {
    var key = layer.name + ':' + nx + 'x' + ny + ':' + ncoded;
    if (planCache[key]) return planCache[key];
    var N = nx * ny;
    var rng = mulberry32(((layer.seed * 1000003 + nx * 1009 + ny) >>> 0));
    var pn = new Float64Array(N);
    for (var i = 0; i < N; i++) pn[i] = rng() < 0.5 ? -1 : 1;
    var perm = new Int32Array(N);
    for (i = 0; i < N; i++) perm[i] = i;
    for (i = N - 1; i >= 1; i--) {
      var j = Math.floor(rng() * (i + 1));
      var tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
    }
    var P = Math.floor(layer.pilotFrac * N + 0.5);
    var pilot = perm.slice(0, P);
    var dataN = N - P;
    var groups = [];
    for (var k = 0; k < ncoded; k++) {
      var g = [];
      for (var q = k; q < dataN; q += ncoded) g.push(perm[P + q]);
      groups.push(Int32Array.from(g));
    }
    var res = { nx: nx, ny: ny, pn: pn, pilot: pilot, groups: groups };
    planCache = {}; // keep at most a few grids alive
    planCache[key] = res;
    return res;
  }

  // ------------------------------------------------------------------ tile statistics (one pass over the pixels)
  function tileMaps(n, size) {
    var m = new Int32Array(size);
    for (var i = 0; i < size; i++) { var t = Math.floor(i * n / size); m[i] = t >= n ? n - 1 : t; }
    return m;
  }
  /** grids = [{nx, ny, chroma:boolean}]; returns per grid {c: mean channel (chroma or luma), y, yy tile means}. */
  function accumulate(rgba, W, H, grids, stride) {
    stride = stride || 1;
    var G = grids.map(function (g) {
      var n = g.nx * g.ny;
      return {
        nx: g.nx, ny: g.ny, cm: tileMaps(g.nx, W), rm: tileMaps(g.ny, H),
        sc: new Float64Array(n), sy: new Float64Array(n), syy: new Float64Array(n), cnt: new Float64Array(n)
      };
    });
    for (var y = 0; y < H; y += stride) {
      var rows = G.map(function (g) { return g.rm[y] * g.nx; });
      var rowBase = y * W * 4;
      for (var x = 0; x < W; x += stride) {
        var i = rowBase + x * 4;
        var R = rgba[i], Gc = rgba[i + 1], B = rgba[i + 2];
        var Y = 0.299 * R + 0.587 * Gc + 0.114 * B;
        var C = ((R - Y) * 0.713 + (B - Y) * 0.564) * 0.5 + 128;
        for (var gi = 0; gi < G.length; gi++) {
          var g = G[gi], t = rows[gi] + g.cm[x];
          g.sc[t] += C; g.sy[t] += Y; g.syy[t] += Y * Y; g.cnt[t] += 1;
        }
      }
    }
    return G.map(function (g, gi) {
      var n = g.nx * g.ny, c = new Float64Array(n), y = new Float64Array(n), tex = new Float64Array(n);
      for (var t = 0; t < n; t++) {
        var cn = g.cnt[t] || 1;
        var my = g.sy[t] / cn, myy = g.syy[t] / cn;
        y[t] = my;
        c[t] = g.sc[t] / cn;
        var sd = Math.sqrt(Math.max(myy - my * my, 0));
        tex[t] = Math.min(Math.max(sd / T_STD, 0), 1);
      }
      return { nx: g.nx, ny: g.ny, c: c, y: y, tex: tex };
    });
  }

  function reflect(i, n) { return i < 0 ? -i - 1 : (i >= n ? 2 * n - i - 1 : i); }
  /** r - mean of the other k*k-1 neighbours (reflect borders). */
  function highPass(r, nx, ny, k) {
    var h = k >> 1, out = new Float64Array(nx * ny), n2 = k * k;
    for (var y = 0; y < ny; y++) for (var x = 0; x < nx; x++) {
      var s = 0;
      for (var dy = -h; dy <= h; dy++) {
        var yy = reflect(y + dy, ny) * nx;
        for (var dx = -h; dx <= h; dx++) s += r[yy + reflect(x + dx, nx)];
      }
      var v = r[y * nx + x];
      out[y * nx + x] = v - (s - v) / (n2 - 1);
    }
    return out;
  }

  // ------------------------------------------------------------------ embedding
  /**
   * Adds both layers to the RGBA buffer in place.
   * payload: {lat, lon, alt, t, tenth, manual}. Missing location/alt/time are recorded as "not known".
   */
  function embed(rgba, W, H, payload, opts) {
    opts = opts || {};
    var c1 = convEncode(packL1(payload));
    var c2 = convEncode(packL2(payload));
    var g1 = gridFor(W, H, L1.ncells), g2 = gridFor(W, H, L2.ncells);
    var stride = Math.max(1, Math.floor(Math.sqrt(W * H / 3e6)));
    var st = accumulate(rgba, W, H, [{ nx: g1[0], ny: g1[1] }, { nx: g2[0], ny: g2[1] }], stride);
    var grid1 = tileValues(L1, st[0], c1, (opts.strength1 || 1));
    var grid2 = tileValues(L2, st[1], c2, (opts.strength2 || 1));
    var bx1 = bilinMap(W, st[0].nx), by1 = bilinMap(H, st[0].ny);
    var bx2 = bilinMap(W, st[1].nx), by2 = bilinMap(H, st[1].ny);
    var nx1 = st[0].nx, nx2 = st[1].nx;
    for (var y = 0; y < H; y++) {
      var ya = by1.i0[y], yb = by1.i1[y], fy1 = by1.f[y];
      var yc = by2.i0[y], yd = by2.i1[y], fy2 = by2.f[y];
      var row1a = ya * nx1, row1b = yb * nx1, row2a = yc * nx2, row2b = yd * nx2;
      for (var x = 0; x < W; x++) {
        var fx1 = bx1.f[x], xa = bx1.i0[x], xb = bx1.i1[x];
        var top1 = grid1[row1a + xa] + (grid1[row1a + xb] - grid1[row1a + xa]) * fx1;
        var bot1 = grid1[row1b + xa] + (grid1[row1b + xb] - grid1[row1b + xa]) * fx1;
        var p1 = top1 + (bot1 - top1) * fy1;
        var fx2 = bx2.f[x], xc = bx2.i0[x], xd = bx2.i1[x];
        var top2 = grid2[row2a + xc] + (grid2[row2a + xd] - grid2[row2a + xc]) * fx2;
        var bot2 = grid2[row2b + xc] + (grid2[row2b + xd] - grid2[row2b + xc]) * fx2;
        var p2 = top2 + (bot2 - top2) * fy2;
        var i = (y * W + x) * 4;
        var r = rgba[i] + p2 + 1.403 * p1, g = rgba[i + 1] + p2 - 1.058 * p1, b = rgba[i + 2] + p2 + 1.773 * p1;
        rgba[i] = r < 0 ? 0 : (r > 255 ? 255 : r + 0.5);
        rgba[i + 1] = g < 0 ? 0 : (g > 255 ? 255 : g + 0.5);
        rgba[i + 2] = b < 0 ? 0 : (b > 255 ? 255 : b + 0.5);
      }
    }
    return { grid1: g1, grid2: g2 };
  }
  function bilinMap(size, n) {
    var i0 = new Int32Array(size), i1 = new Int32Array(size), f = new Float64Array(size);
    for (var p = 0; p < size; p++) {
      var u = (p + 0.5) * n / size - 0.5, fl = Math.floor(u), fr = u - fl;
      var a = fl < 0 ? 0 : (fl > n - 1 ? n - 1 : fl), b = fl + 1 < 0 ? 0 : (fl + 1 > n - 1 ? n - 1 : fl + 1);
      i0[p] = a; i1[p] = b; f[p] = fr;
    }
    return { i0: i0, i1: i1, f: f };
  }
  function tileValues(layer, st, coded, strength) {
    var nx = st.nx, ny = st.ny, N = nx * ny;
    var pl = plan(layer, nx, ny, coded.length);
    var val = new Float64Array(N);
    for (var i = 0; i < pl.pilot.length; i++) val[pl.pilot[i]] = pl.pn[pl.pilot[i]];
    for (var k = 0; k < pl.groups.length; k++) {
      var g = pl.groups[k], sgn = coded[k] ? 1 : -1;
      for (var q = 0; q < g.length; q++) val[g[q]] = pl.pn[g[q]] * sgn;
    }
    var out = new Float64Array(N);
    for (i = 0; i < N; i++) out[i] = val[i] * layer.amax * strength * Math.max(st.tex[i], layer.floor);
    return out;
  }

  // ------------------------------------------------------------------ reading
  function layerStats(layer, st, ncoded) {
    var nx = st.nx, ny = st.ny;
    var pl = plan(layer, nx, ny, ncoded);
    var r = layer.kind === 'luma' ? st.y : st.c;
    var hp = highPass(r, nx, ny, layer.kern);
    var fl = layer.floor > 0 ? layer.floor : 0.02;
    var N = nx * ny, w = new Float64Array(N);
    for (var i = 0; i < N; i++) w[i] = Math.max(st.tex[i], fl);
    return scoreCells(pl, w, hp, null);
  }
  /** valid (optional): Uint8Array per cell, 1 = usable. */
  function scoreCells(pl, w, hp, valid, pilotOnly) {
    var num = 0, den = 0, i, c;
    for (i = 0; i < pl.pilot.length; i++) {
      c = pl.pilot[i];
      var wc = valid && !valid[c] ? 0 : w[c];
      num += wc * pl.pn[c] * hp[c];
      den += (wc * hp[c]) * (wc * hp[c]);
    }
    var z = num / Math.sqrt(den + 1e-9);
    if (pilotOnly) return { z: z, soft: null };
    var soft = new Float64Array(pl.groups.length);
    for (var k = 0; k < pl.groups.length; k++) {
      var g = pl.groups[k], s = 0, cov = 0;
      for (var q = 0; q < g.length; q++) {
        c = g[q];
        var wq = valid && !valid[c] ? 0 : w[c];
        s += wq * pl.pn[c] * hp[c];
        cov += wq * wq;
      }
      soft[k] = cov > 0 ? (s / cov) * Math.sqrt(cov) : 0;
    }
    return { z: z, soft: soft };
  }
  function decodeLayer(layer, st, nBits, unpack) {
    var ncoded = 2 * (nBits + 6);
    var sc = layerStats(layer, st, ncoded);
    return { data: unpack(viterbi(Array.from(sc.soft))), z: sc.z, soft: sc.soft };
  }

  /**
   * Reads an RGBA picture. status: 'ok' (layer 1), 'part' (only layer 2), 'damaged' (detected, unreadable), 'none'.
   * The 10-letter ID comes from layer 1 only.
   */
  function read(rgba, W, H, opts) {
    opts = opts || {};
    var stride = opts.stride || Math.max(1, Math.floor(Math.sqrt(W * H / 3e6)));
    var b1 = gridFor(W, H, L1.ncells), b2 = gridFor(W, H, L2.ncells);
    var st = accumulate(rgba, W, H, [{ nx: b1[0], ny: b1[1] }, { nx: b2[0], ny: b2[1] }], stride);
    var r1 = decodeLayer(L1, st[0], N1, unpackL1);
    var r2 = decodeLayer(L2, st[1], N2, unpackL2);
    // A resized copy can round its size so that the tile grid differs by one tile from the one used
    // when the mark was written. Try the neighbouring grids for any layer that did not read.
    if (!r1.data) r1 = trySiblings(rgba, W, H, stride, L1, N1, unpackL1, r1, [1, -1]);
    if (!r2.data) r2 = trySiblings(rgba, W, H, stride, L2, N2, unpackL2, r2, [1, -1, 2, -2]);
    return result(r1, r2);
  }
  function trySiblings(rgba, W, H, stride, layer, nBits, unpack, current, shifts) {
    var base = gridFor(W, H, layer.ncells), best = current;
    for (var i = 0; i < shifts.length; i++) {
      var nx = base[0] + shifts[i], ny = Math.max(8, Math.floor(layer.ncells / nx + 0.5));
      if (nx < 8) continue;
      var st = accumulate(rgba, W, H, [{ nx: nx, ny: ny }], stride)[0];
      var r = decodeLayer(layer, st, nBits, unpack);
      if (r.data) return r;
      if (r.z > best.z) best = r;
    }
    return best;
  }
  function result(r1, r2) {
    var status = r1.data ? 'ok' : (r2.data ? 'part' : ((r1.z > DETECT_Z || r2.z > DETECT_Z) ? 'damaged' : 'none'));
    return { status: status, l1: r1.data, l2: r2.data, z1: r1.z, z2: r2.z };
  }

  // ------------------------------------------------------------------ cropped pictures
  /*
   * A crop shifts the tile grid. The reader finds where the original frame sat inside the picture by
   * correlating the picture's colour detail with the known invisible pilot pattern, then reads the
   * tiles that are fully inside the crop and treats the rest as missing (the repair code absorbs it).
   * Assumes a plain crop (no turn, no tilt) of a frame whose shape is one of the app's usual shapes.
   */
  var CROP_ASPECTS = [4 / 3, 3 / 4, 16 / 9, 9 / 16, 1];

  function chromaPlane(rgba, W, H, stride) {
    var w = Math.floor(W / stride), h = Math.floor(H / stride), out = new Float64Array(w * h);
    for (var y = 0; y < h; y++) for (var x = 0; x < w; x++) {
      var i = ((y * stride) * W + x * stride) * 4, R = rgba[i], B = rgba[i + 2];
      var Y = 0.299 * R + 0.587 * rgba[i + 1] + 0.114 * B;
      out[y * w + x] = ((R - Y) * 0.713 + (B - Y) * 0.564) * 0.5 + 128;
    }
    return { p: out, w: w, h: h };
  }
  function integral(pl) {
    var w = pl.w, h = pl.h, I = new Float64Array((w + 1) * (h + 1));
    for (var y = 1; y <= h; y++) {
      var row = 0;
      for (var x = 1; x <= w; x++) { row += pl.p[(y - 1) * w + (x - 1)]; I[y * (w + 1) + x] = I[(y - 1) * (w + 1) + x] + row; }
    }
    return I;
  }
  function boxMean(I, w, h, x0, y0, x1, y1) { // pixel rectangle [x0,x1) x [y0,y1), rounded
    var a = Math.max(0, Math.round(x0)), b = Math.min(w, Math.round(x1)), c = Math.max(0, Math.round(y0)), d = Math.min(h, Math.round(y1));
    if (b <= a || d <= c) return 0;
    var W1 = w + 1;
    return (I[d * W1 + b] - I[c * W1 + b] - I[d * W1 + a] + I[c * W1 + a]) / ((b - a) * (d - c));
  }
  function cropCandidate(I, w, h, nx, ny, pX, pY, pS, fw, fh, px, py, ixLo, ixHi, iyLo, iyHi) {
    var sx = w / (fw * nx), sy = h / (fh * ny);
    var ni = Math.min(nx, Math.floor(w / sx - px - 1e-9)), nj = Math.min(ny, Math.floor(h / sy - py - 1e-9));
    if (ni < 12 || nj < 12) return null;
    var T = new Float64Array(ni * nj);
    for (var j = 0; j < nj; j++) for (var i = 0; i < ni; i++)
      T[j * ni + i] = boxMean(I, w, h, (i + px) * sx, (j + py) * sy, (i + 1 + px) * sx, (j + 1 + py) * sy);
    var hp = highPass(T, ni, nj, 5), best = null;
    var xa = Math.max(0, ixLo), xb = Math.min(nx - ni, ixHi), ya = Math.max(0, iyLo), yb = Math.min(ny - nj, iyHi);
    for (var iy = ya; iy <= yb; iy++) for (var ix = xa; ix <= xb; ix++) {
      var num = 0, den = 0, cnt = 0;
      for (var k = 0; k < pX.length; k++) {
        var ii = pX[k] - ix, jj = pY[k] - iy;
        if (ii < 0 || ii >= ni || jj < 0 || jj >= nj) continue;
        var v = hp[jj * ni + ii]; num += pS[k] * v; den += v * v; cnt++;
      }
      if (cnt < 300) continue;
      var z = num / Math.sqrt(den + 1e-9);
      if (!best || z > best.z) best = { z: z, ix: ix, iy: iy, px: px, py: py, fw: fw, fh: fh, sx: sx, sy: sy };
    }
    return best;
  }
  function searchCrop(I, w, h, aspectO) {
    var g = gridFor(aspectO * 1000, 1000, L1.ncells), nx = g[0], ny = g[1];
    var pl = plan(L1, nx, ny, 2 * (N1 + 6)), P = pl.pilot.length;
    var pX = new Int32Array(P), pY = new Int32Array(P), pS = new Float64Array(P);
    for (var k = 0; k < P; k++) { var c = pl.pilot[k]; pX[k] = c % nx; pY[k] = (c / nx) | 0; pS[k] = pl.pn[c]; }
    var ac = w / h, best = null, ph = [0, 1 / 3, 2 / 3];
    for (var fw = 0.56; fw <= 1.0001; fw += 0.02) {
      var fh = fw * aspectO / ac;
      if (fh > 1.003 || fh < 0.5) continue;
      for (var a = 0; a < 3; a++) for (var b = 0; b < 3; b++) {
        var r = cropCandidate(I, w, h, nx, ny, pX, pY, pS, fw, fh, ph[a], ph[b], 0, nx, 0, ny);
        if (r && (!best || r.z > best.z)) best = r;
      }
    }
    if (!best) return null;
    var c0 = best;
    for (var df = -0.016; df <= 0.0161; df += 0.004) {
      var f2 = c0.fw + df, h2 = f2 * aspectO / ac;
      if (f2 > 1.0001 || h2 > 1.003 || h2 < 0.5) continue;
      for (var dx = -1 / 3; dx <= 0.3334; dx += 1 / 6) for (var dy = -1 / 3; dy <= 0.3334; dy += 1 / 6) {
        var qx = c0.px + dx, qy = c0.py + dy;
        qx -= Math.floor(qx); qy -= Math.floor(qy);
        var r2 = cropCandidate(I, w, h, nx, ny, pX, pY, pS, f2, h2, qx, qy, c0.ix - 2, c0.ix + 2, c0.iy - 2, c0.iy + 2);
        if (r2 && r2.z > best.z) best = r2;
      }
    }
    best.nx = nx; best.ny = ny; best.aspect = aspectO;
    return best;
  }
  /** Tile means for a picture that covers only part of the original frame. map: original fraction = a + pixel*b. */
  function accumulateMapped(rgba, W, H, grids, map, stride) {
    var G = grids.map(function (g) {
      var n = g.nx * g.ny, cm = new Int32Array(W), rm = new Int32Array(H);
      for (var x = 0; x < W; x++) { var t = Math.floor((map.ax + (x + 0.5) * map.bx) * g.nx); cm[x] = t < 0 || t >= g.nx ? -1 : t; }
      for (var y = 0; y < H; y++) { var u = Math.floor((map.ay + (y + 0.5) * map.by) * g.ny); rm[y] = u < 0 || u >= g.ny ? -1 : u; }
      return { nx: g.nx, ny: g.ny, cm: cm, rm: rm, sc: new Float64Array(n), sy: new Float64Array(n), syy: new Float64Array(n), cnt: new Float64Array(n) };
    });
    for (var y2 = 0; y2 < H; y2 += stride) {
      for (var x2 = 0; x2 < W; x2 += stride) {
        var i = (y2 * W + x2) * 4, R = rgba[i], B = rgba[i + 2];
        var Y = 0.299 * R + 0.587 * rgba[i + 1] + 0.114 * B, C = ((R - Y) * 0.713 + (B - Y) * 0.564) * 0.5 + 128;
        for (var gi = 0; gi < G.length; gi++) {
          var g2 = G[gi], cx = g2.cm[x2], cy = g2.rm[y2];
          if (cx < 0 || cy < 0) continue;
          var t2 = cy * g2.nx + cx;
          g2.sc[t2] += C; g2.sy[t2] += Y; g2.syy[t2] += Y * Y; g2.cnt[t2] += 1;
        }
      }
    }
    return G.map(function (g) {
      var n = g.nx * g.ny, t;
      var expected = (1 / (map.bx * g.nx)) * (1 / (map.by * g.ny)) / (stride * stride); // pixels a whole tile should hold
      var c = new Float64Array(n), y = new Float64Array(n), tex = new Float64Array(n), valid = new Uint8Array(n);
      for (t = 0; t < n; t++) {
        if (g.cnt[t] < 0.6 * expected || g.cnt[t] < 4) continue;
        valid[t] = 1;
        var my = g.sy[t] / g.cnt[t], myy = g.syy[t] / g.cnt[t];
        y[t] = my; c[t] = g.sc[t] / g.cnt[t];
        tex[t] = Math.min(Math.max(Math.sqrt(Math.max(myy - my * my, 0)) / T_STD, 0), 1);
      }
      return { nx: g.nx, ny: g.ny, c: c, y: y, tex: tex, valid: valid };
    });
  }
  /** Pilot detection score and soft bits for tile stats that have a validity mask. null when too little is visible. */
  function maskedScore(layer, st, nBits, pilotOnly) {
    var ncoded = 2 * (nBits + 6), nx = st.nx, ny = st.ny, N = nx * ny;
    var pl = plan(layer, nx, ny, ncoded);
    var r = (layer.kind === 'luma' ? st.y : st.c).slice(), sum = 0, cnt = 0, t;
    for (t = 0; t < N; t++) if (st.valid[t]) { sum += r[t]; cnt++; }
    if (cnt < N * 0.3) return { sc: null, z: 0 };
    var mean = sum / cnt;
    for (t = 0; t < N; t++) if (!st.valid[t]) r[t] = mean;
    var hp = highPass(r, nx, ny, layer.kern), half = layer.kern >> 1;
    var ok = new Uint8Array(N), fl = layer.floor > 0 ? layer.floor : 0.02, w = new Float64Array(N);
    for (var y = 0; y < ny; y++) for (var x = 0; x < nx; x++) {
      var good = 1;
      for (var dy = -half; dy <= half && good; dy++) for (var dx = -half; dx <= half; dx++) {
        var yy = y + dy, xx = x + dx;
        if (yy < 0 || yy >= ny || xx < 0 || xx >= nx) continue;
        if (!st.valid[yy * nx + xx]) { good = 0; break; }
      }
      ok[y * nx + x] = good; w[y * nx + x] = Math.max(st.tex[y * nx + x], fl);
    }
    var sc = scoreCells(pl, w, hp, ok, pilotOnly);
    return { sc: sc, z: sc.z };
  }
  function decodeLayerMasked(layer, st, nBits, unpack) {
    var m = maskedScore(layer, st, nBits);
    if (!m.sc) return { data: null, z: 0 };
    return { data: unpack(viterbi(Array.from(m.sc.soft))), z: m.z };
  }
  /** Reads a cropped picture. Returns the same shape as read() plus `crop`, or null when no frame position fits. */
  function readCropped(rgba, W, H) {
    var stride = Math.max(1, Math.floor(Math.sqrt(W * H / 2.5e6)));
    var pl = chromaPlane(rgba, W, H, stride), I = integral(pl), best = null;
    for (var ai = 0; ai < CROP_ASPECTS.length; ai++) {
      var c = searchCrop(I, pl.w, pl.h, CROP_ASPECTS[ai]);
      if (!c || c.z < 8) continue; // noise peaks at about 5; a real mark gives 15 to 23
      // the search ran on the sampled plane: one plane pixel is `stride` picture pixels
      var X0 = c.ix - c.px, Y0 = c.iy - c.py;
      var map = { ax: X0 / c.nx, bx: 1 / (c.sx * c.nx) / stride, ay: Y0 / c.ny, by: 1 / (c.sy * c.ny) / stride };
      var g2 = gridFor(c.aspect * 1000, 1000, L2.ncells);
      var st = accumulateMapped(rgba, W, H, [{ nx: c.nx, ny: c.ny }, { nx: g2[0], ny: g2[1] }], map, stride);
      var r1 = decodeLayerMasked(L1, st[0], N1, unpackL1), r2 = decodeLayerMasked(L2, st[1], N2, unpackL2);
      var cur = result(r1, r2);
      cur.crop = { aspect: c.aspect, widthFraction: c.fw, heightFraction: c.fh, left: map.ax, top: map.ay, searchZ: c.z };
      var rk = { ok: 3, part: 2, damaged: 1, none: 0 }[cur.status] * 1000 + Math.max(cur.z1, cur.z2);
      if (!best || rk > best.rk) { best = cur; best.rk = rk; }
      if (cur.status === 'ok') break;
    }
    return best;
  }

  // ------------------------------------------------------------------ photos of a screen or a print
  /*
   * The user gives four approximate corners of the photo inside the picture (taps, or autoCorners()).
   * No visible marker is needed: the corners are nudged until the invisible pilot tiles line up.
   * Frame shape: the nearest of the app's usual shapes to the quadrilateral that was given.
   */
  function gridFromAspect(aspect, ncells) {
    var nx = Math.max(8, Math.floor(Math.sqrt(ncells * aspect) + 0.5));
    return [nx, Math.max(8, Math.floor(ncells / nx + 0.5))];
  }
  /** 3x3 homography (row major, 9 numbers) taking the 4 points `from` to the 4 points `to`. */
  function solveHomography(from, to) {
    var A = [], b = [], i, j;
    for (i = 0; i < 4; i++) {
      var x = from[i][0], y = from[i][1], u = to[i][0], v = to[i][1];
      A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.push(u);
      A.push([0, 0, 0, x, y, 1, -v * x, -v * y]); b.push(v);
    }
    for (i = 0; i < 8; i++) { // Gaussian elimination with partial pivoting
      var p = i;
      for (j = i + 1; j < 8; j++) if (Math.abs(A[j][i]) > Math.abs(A[p][i])) p = j;
      var t = A[i]; A[i] = A[p]; A[p] = t; var tb = b[i]; b[i] = b[p]; b[p] = tb;
      if (Math.abs(A[i][i]) < 1e-12) return null;
      for (j = i + 1; j < 8; j++) {
        var f = A[j][i] / A[i][i];
        for (var k = i; k < 8; k++) A[j][k] -= f * A[i][k];
        b[j] -= f * b[i];
      }
    }
    var h = new Array(8);
    for (i = 7; i >= 0; i--) {
      var s = b[i];
      for (j = i + 1; j < 8; j++) s -= A[i][j] * h[j];
      h[i] = s / A[i][i];
    }
    return [h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], 1];
  }
  /** Tile means of the picture seen through the homography `Hm` (rectangle pixel -> picture pixel). */
  function warpStats(rgba, W, H, Hm, RW, RH, grids, stride) {
    var G = grids.map(function (g) {
      var n = g.nx * g.ny;
      return { nx: g.nx, ny: g.ny, cm: tileMaps(g.nx, RW), rm: tileMaps(g.ny, RH), sc: new Float64Array(n), sy: new Float64Array(n), syy: new Float64Array(n), cnt: new Float64Array(n) };
    });
    var h0 = Hm[0], h1 = Hm[1], h2 = Hm[2], h3 = Hm[3], h4 = Hm[4], h5 = Hm[5], h6 = Hm[6], h7 = Hm[7];
    for (var ry = 0; ry < RH; ry += stride) {
      var yc = ry + 0.5;
      for (var rx = 0; rx < RW; rx += stride) {
        var xc = rx + 0.5, d = h6 * xc + h7 * yc + 1;
        var sx = (h0 * xc + h1 * yc + h2) / d - 0.5, sy = (h3 * xc + h4 * yc + h5) / d - 0.5;
        if (sx < 0 || sy < 0 || sx >= W - 1 || sy >= H - 1) continue;
        var x0 = sx | 0, y0 = sy | 0, fx = sx - x0, fy = sy - y0, i = (y0 * W + x0) * 4, j = i + W * 4;
        var w00 = (1 - fx) * (1 - fy), w10 = fx * (1 - fy), w01 = (1 - fx) * fy, w11 = fx * fy;
        var R = rgba[i] * w00 + rgba[i + 4] * w10 + rgba[j] * w01 + rgba[j + 4] * w11;
        var Gc = rgba[i + 1] * w00 + rgba[i + 5] * w10 + rgba[j + 1] * w01 + rgba[j + 5] * w11;
        var B = rgba[i + 2] * w00 + rgba[i + 6] * w10 + rgba[j + 2] * w01 + rgba[j + 6] * w11;
        var Y = 0.299 * R + 0.587 * Gc + 0.114 * B, C = ((R - Y) * 0.713 + (B - Y) * 0.564) * 0.5 + 128;
        for (var gi = 0; gi < G.length; gi++) {
          var g = G[gi], t = g.rm[ry] * g.nx + g.cm[rx];
          g.sc[t] += C; g.sy[t] += Y; g.syy[t] += Y * Y; g.cnt[t] += 1;
        }
      }
    }
    return G.map(function (g) {
      var n = g.nx * g.ny, expected = (RW / g.nx) * (RH / g.ny) / (stride * stride);
      var c = new Float64Array(n), y = new Float64Array(n), tex = new Float64Array(n), valid = new Uint8Array(n);
      for (var t = 0; t < n; t++) {
        if (g.cnt[t] < 0.6 * expected || g.cnt[t] < 4) continue;
        valid[t] = 1;
        var my = g.sy[t] / g.cnt[t], myy = g.syy[t] / g.cnt[t];
        y[t] = my; c[t] = g.sc[t] / g.cnt[t];
        tex[t] = Math.min(Math.max(Math.sqrt(Math.max(myy - my * my, 0)) / T_STD, 0), 1);
      }
      return { nx: g.nx, ny: g.ny, c: c, y: y, tex: tex, valid: valid };
    });
  }
  function rectCorners(RW, RH) { return [[0, 0], [RW, 0], [RW, RH], [0, RH]]; }
  function pickAspect(q) {
    function len(a, b) { return Math.hypot(a[0] - b[0], a[1] - b[1]); }
    var wq = (len(q[0], q[1]) + len(q[3], q[2])) / 2, hq = (len(q[0], q[3]) + len(q[1], q[2])) / 2, r = wq / hq, best = null;
    CROP_ASPECTS.forEach(function (a) { var e = Math.abs(Math.log(a / r)); if (!best || e < best.e) best = { a: a, e: e }; });
    return best.a;
  }
  function perspZ(rgba, W, H, q, aspect, RW, RH, stride, both) {
    var Hm = solveHomography(rectCorners(RW, RH), q);
    if (!Hm) return -1e9;
    var g1 = gridFromAspect(aspect, L1.ncells), grids = [{ nx: g1[0], ny: g1[1] }];
    if (both) { var g2 = gridFromAspect(aspect, L2.ncells); grids.push({ nx: g2[0], ny: g2[1] }); }
    var st = warpStats(rgba, W, H, Hm, RW, RH, grids, stride);
    var z = maskedScore(L1, st[0], N1, true).z;
    if (both) z += Math.max(maskedScore(L2, st[1], N2, true).z, 0);
    return z;
  }
  /**
   * Slides each corner until the hidden pilot tiles line up. onProgress(0..1) is optional.
   * Returns {q, z, aspect}. About 1,300 trial pictures; seconds to tens of seconds.
   */
  function refineCorners(rgba, W, H, q0, aspect, onProgress, fast) {
    var long1 = 800, RW = aspect >= 1 ? long1 : Math.round(long1 * aspect), RH = aspect >= 1 ? Math.round(long1 / aspect) : long1;
    var scale = RW / Math.hypot(q0[1][0] - q0[0][0], q0[1][1] - q0[0][1]); // rect pixels per picture pixel, roughly
    var total = 121 + 392 + 324 + 196 + 200, done = 0;
    function tickp() { done++; if (onProgress && done % 25 === 0) onProgress(Math.min(0.99, done / total)); }
    var q = q0.map(function (p) { return p.slice(); });
    function score(qq, stride, both, rw, rh) { tickp(); return perspZ(rgba, W, H, qq, aspect, rw, rh, stride, both); }
    var step = 1 / Math.max(scale, 1e-6); // one rectangle pixel in picture pixels
    var best = score(q, 2, false, RW, RH), bq = q, dx, dy, i;
    for (dx = -30; dx <= 30; dx += 6) for (dy = -30; dy <= 30; dy += 6) {
      var qq = q.map(function (p) { return [p[0] + dx * step, p[1] + dy * step]; });
      var s = score(qq, 2, false, RW, RH);
      if (s > best) { best = s; bq = qq; }
    }
    q = bq;
    var stages = [[18, 6, 2], [8, 2, 1], [3, 1, 1]];
    stages.forEach(function (st) {
      for (var round = 0; round < st[2]; round++) for (i = 0; i < 4; i++) {
        var cand = q, cb = best;
        for (dx = -st[0]; dx <= st[0]; dx += st[1]) for (dy = -st[0]; dy <= st[0]; dy += st[1]) {
          var q2 = q.map(function (p) { return p.slice(); });
          q2[i][0] += dx * step; q2[i][1] += dy * step;
          var s2 = score(q2, 2, false, RW, RH);
          if (s2 > cb) { cb = s2; cand = q2; }
        }
        q = cand; best = cb;
      }
    });
    // last pass at higher resolution with both layers: the fine brightness tiles need sub-tile accuracy
    var long2 = 1200, RW2 = aspect >= 1 ? long2 : Math.round(long2 * aspect), RH2 = aspect >= 1 ? Math.round(long2 / aspect) : long2;
    var step2 = step * RW / RW2;
    var b2 = score(q, 2, false, RW2, RH2);
    [[3, 1.5], [1.5, 0.75]].forEach(function (st) {
      for (i = 0; i < 4; i++) {
        var cand = q, cb = b2;
        for (dx = -st[0]; dx <= st[0]; dx += st[1]) for (dy = -st[0]; dy <= st[0]; dy += st[1]) {
          var q3 = q.map(function (p) { return p.slice(); });
          q3[i][0] += dx * step2; q3[i][1] += dy * step2;
          var s3 = score(q3, 2, false, RW2, RH2);
          if (s3 > cb) { cb = s3; cand = q3; }
        }
        q = cand; b2 = cb;
      }
    });
    if (onProgress) onProgress(1);
    return { q: q, z: b2, aspect: aspect };
  }
  /** Reads a photo of a screen or print. corners: [[x,y] x4] TL, TR, BR, BL in picture pixels. */
  function readPerspective(rgba, W, H, corners, opts) {
    opts = opts || {};
    var aspect = opts.aspect || pickAspect(corners);
    var ref = refineCorners(rgba, W, H, corners, aspect, opts.onProgress, opts.fast);
    var long2 = 1600, RW = aspect >= 1 ? long2 : Math.round(long2 * aspect), RH = aspect >= 1 ? Math.round(long2 / aspect) : long2;
    var Hm = solveHomography(rectCorners(RW, RH), ref.q);
    if (!Hm) return null;
    var g1 = gridFromAspect(aspect, L1.ncells), g2 = gridFromAspect(aspect, L2.ncells);
    var st = warpStats(rgba, W, H, Hm, RW, RH, [{ nx: g1[0], ny: g1[1] }, { nx: g2[0], ny: g2[1] }], 1);
    var r = result(decodeLayerMasked(L1, st[0], N1, unpackL1), decodeLayerMasked(L2, st[1], N2, unpackL2));
    r.perspective = { aspect: aspect, corners: ref.q, alignZ: ref.z };
    return r;
  }
  /**
   * A first guess at the four corners of a bright picture on a dark surround (a monitor in a dim room).
   * Fragile on dark pictures: it is only a starting point for the user to drag.
   */
  function autoCorners(rgba, W, H) {
    var sw = 160, sh = Math.max(8, Math.round(160 * H / W)), g = new Float64Array(sw * sh), x, y;
    for (y = 0; y < sh; y++) for (x = 0; x < sw; x++) {
      var px = Math.min(W - 1, Math.round((x + 0.5) * W / sw)), py = Math.min(H - 1, Math.round((y + 0.5) * H / sh)), i = (py * W + px) * 4;
      g[y * sw + x] = 0.299 * rgba[i] + 0.587 * rgba[i + 1] + 0.114 * rgba[i + 2];
    }
    var hist = new Float64Array(256);
    for (var k = 0; k < g.length; k++) hist[Math.min(255, g[k] | 0)]++;
    var total = g.length, sumAll = 0, t;
    for (t = 0; t < 256; t++) sumAll += t * hist[t];
    var wB = 0, sumB = 0, bestVar = -1, thr = 128; // Otsu
    for (t = 0; t < 256; t++) {
      wB += hist[t]; if (!wB) continue;
      var wF = total - wB; if (!wF) break;
      sumB += t * hist[t];
      var mB = sumB / wB, mF = (sumAll - sumB) / wF, v = wB * wF * (mB - mF) * (mB - mF);
      if (v > bestVar) { bestVar = v; thr = t; }
    }
    var mask = new Uint8Array(sw * sh), comp = new Int32Array(sw * sh).fill(-1), best = -1, bestSize = 0, id = 0;
    for (k = 0; k < mask.length; k++) mask[k] = g[k] > thr ? 1 : 0;
    for (k = 0; k < mask.length; k++) {
      if (!mask[k] || comp[k] >= 0) continue;
      var stack = [k], size = 0; comp[k] = id;
      while (stack.length) {
        var c = stack.pop(); size++;
        var cx = c % sw, cy = (c / sw) | 0;
        [[1, 0], [-1, 0], [0, 1], [0, -1]].forEach(function (d) {
          var nx = cx + d[0], ny = cy + d[1];
          if (nx < 0 || ny < 0 || nx >= sw || ny >= sh) return;
          var n = ny * sw + nx; if (mask[n] && comp[n] < 0) { comp[n] = id; stack.push(n); }
        });
      }
      if (size > bestSize) { bestSize = size; best = id; }
      id++;
    }
    if (best < 0 || bestSize < 0.12 * sw * sh) return null;
    var tl = null, tr = null, br = null, bl = null;
    for (y = 0; y < sh; y++) for (x = 0; x < sw; x++) {
      if (comp[y * sw + x] !== best) continue;
      var s = x + y, d = x - y;
      if (!tl || s < tl.s) tl = { x: x, y: y, s: s };
      if (!br || s > br.s) br = { x: x, y: y, s: s };
      if (!tr || d > tr.d) tr = { x: x, y: y, d: d };
      if (!bl || d < bl.d) bl = { x: x, y: y, d: d };
    }
    var f = function (p, dx, dy) { return [(p.x + dx) * W / sw, (p.y + dy) * H / sh]; };
    return [f(tl, 0, 0), f(tr, 1, 0), f(br, 1, 1), f(bl, 0, 1)];
  }

  /** Cross-check between the two layers (metres), or null when either has no location. */
  function layerDisagreementMeters(res) {
    if (!res.l1 || !res.l2 || res.l1.lat == null || res.l2.lat == null) return null;
    var dLat = (res.l1.lat - res.l2.lat) * 111320;
    var dLon = (res.l1.lon - res.l2.lon) * 111320 * Math.cos(res.l1.lat * Math.PI / 180);
    return Math.sqrt(dLat * dLat + dLon * dLon);
  }

  return {
    EPOCH: EPOCH, L1: L1, L2: L2, N1: N1, N2: N2, DETECT_Z: DETECT_Z,
    crc16: crc16, sha256: sha256, makeId: makeId,
    packL1: packL1, unpackL1: unpackL1, packL2: packL2, unpackL2: unpackL2,
    convEncode: convEncode, viterbi: viterbi, mulberry32: mulberry32, gridFor: gridFor, plan: plan,
    accumulate: accumulate, highPass: highPass, scoreCells: scoreCells, layerStats: layerStats, decodeLayer: decodeLayer,
    result: result, embed: embed, read: read, readCropped: readCropped, readPerspective: readPerspective, autoCorners: autoCorners, solveHomography: solveHomography, layerDisagreementMeters: layerDisagreementMeters
  };
});
