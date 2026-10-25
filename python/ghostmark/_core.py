"""Ghostmark core: mark format 1, a numpy port of the reference engine (reference/wm-engine.js).

Pure functions on RGB uint8 arrays of shape (H, W, 3). The only dependency is numpy.
The mark written here is bit-compatible with the Kotlin and JavaScript engines: tile grids, the PRNG,
the interleaving, the convolutional code and the CRCs are the same, so any engine reads any engine's marks.
"""
import hashlib
import math

import numpy as np

EPOCH = 1767225600  # 2026-01-01T00:00:00Z
T_STD = 14.0
DETECT_Z = 3.5
N1 = 118  # layer 1 payload bits: 3 flags + 25 + 26 + 14 + 29 + 4 + 1 + crc16
N2 = 60   # layer 2 payload bits: 1 flag + 21 + 22 + crc16


class _Layer:
    def __init__(self, name, ncells, seed, amax, floor, kind, kern, pilot_frac=0.20):
        self.name, self.ncells, self.seed, self.amax, self.floor = name, ncells, seed, amax, floor
        self.kind, self.kern, self.pilot_frac = kind, kern, pilot_frac


L1 = _Layer('colour', 10000, 11, 2.0, 0.25, 'cbcr', 5)
L2 = _Layer('brightness', 50000, 77, 4.5, 0.0, 'luma', 3)


# ------------------------------------------------------------------ bits and CRC
def to_bits(v, n):
    return [(int(v) >> (n - 1 - i)) & 1 for i in range(n)]


def from_bits(b):
    v = 0
    for x in b:
        v = v * 2 + int(x)
    return v


def crc16(bits):
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) over the bits, zero-padded to a whole byte."""
    padded = list(bits)
    while len(padded) % 8:
        padded.append(0)
    crc = 0xFFFF
    for i in range(0, len(padded), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | padded[i + j]
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def make_id(body_bits):
    """10-letter ID: first 8 bytes of SHA-256 over the payload bits (one byte per bit), base 26, A = 0."""
    n = int.from_bytes(hashlib.sha256(bytes(body_bits)).digest()[:8], 'big')
    s = ''
    for _ in range(10):
        s += chr(65 + n % 26)
        n //= 26
    return s


def _js_round(x):
    return math.floor(x + 0.5)


# ------------------------------------------------------------------ payloads
def pack_l1(d):
    has_loc = d.get('lat') is not None and d.get('lon') is not None
    has_alt = d.get('alt') is not None
    has_t = d.get('t') is not None
    la = _js_round((d['lat'] + 90) / 180 * (2 ** 25 - 1)) if has_loc else 0
    lo = _js_round((d['lon'] + 180) / 360 * (2 ** 26 - 1)) if has_loc else 0
    al = min(max(_js_round(d['alt']) + 500, 0), 16383) if has_alt else 0
    tt = min(max(math.floor(d['t']) - EPOCH, 0), 2 ** 29 - 1) if has_t else 0
    tenth = min(max(int(d.get('tenth') or 0), 0), 9)
    bits = [int(has_loc), int(has_alt), int(has_t)] + to_bits(la, 25) + to_bits(lo, 26) + to_bits(al, 14) \
        + to_bits(tt, 29) + to_bits(tenth, 4) + [1 if d.get('manual') else 0]
    return bits + to_bits(crc16(bits), 16)


def unpack_l1(bits):
    body, tail = bits[:-16], bits[-16:]
    if crc16(body) != from_bits(tail):
        return None
    p = 3

    def take(n):
        nonlocal p
        v = from_bits(body[p:p + n])
        p += n
        return v
    la, lo, al, tt, tenth, man = take(25), take(26), take(14), take(29), take(4), take(1)
    return dict(id=make_id(body), tenth=tenth, manual=man,
                lat=la / (2 ** 25 - 1) * 180 - 90 if body[0] else None,
                lon=lo / (2 ** 26 - 1) * 360 - 180 if body[0] else None,
                alt=al - 500 if body[1] else None,
                t=EPOCH + tt if body[2] else None)


def pack_l2(d):
    has_loc = d.get('lat') is not None and d.get('lon') is not None
    la = _js_round((d['lat'] + 90) / 180 * (2 ** 21 - 1)) if has_loc else 0
    lo = _js_round((d['lon'] + 180) / 360 * (2 ** 22 - 1)) if has_loc else 0
    bits = [int(has_loc)] + to_bits(la, 21) + to_bits(lo, 22)
    return bits + to_bits(crc16(bits), 16)


def unpack_l2(bits):
    body, tail = bits[:-16], bits[-16:]
    if crc16(body) != from_bits(tail):
        return None
    la, lo = from_bits(body[1:22]), from_bits(body[22:44])
    return dict(lat=la / (2 ** 21 - 1) * 180 - 90 if body[0] else None,
                lon=lo / (2 ** 22 - 1) * 360 - 180 if body[0] else None)


# ------------------------------------------------------------------ convolutional code K=7, rate 1/2, soft Viterbi
_G0, _G1 = 0x5B, 0x79  # 0o133, 0o171
_OUT0 = np.zeros(128, np.int8)
_OUT1 = np.zeros(128, np.int8)
for _reg in range(128):
    _OUT0[_reg] = bin(_reg & _G0).count('1') & 1
    _OUT1[_reg] = bin(_reg & _G1).count('1') & 1
_NS = np.arange(64)
_P0 = (_NS << 1) & 63
_P1 = _P0 | 1
_R0 = ((_NS >> 5) << 6) | _P0
_R1 = ((_NS >> 5) << 6) | _P1
_S00, _S01 = np.where(_OUT0[_R0] == 1, 1.0, -1.0), np.where(_OUT1[_R0] == 1, 1.0, -1.0)
_S10, _S11 = np.where(_OUT0[_R1] == 1, 1.0, -1.0), np.where(_OUT1[_R1] == 1, 1.0, -1.0)


def conv_encode(bits):
    st, out = 0, []
    for b in list(bits) + [0] * 6:
        reg = (b << 6) | st
        out += [int(_OUT0[reg]), int(_OUT1[reg])]
        st = reg >> 1
    return out


def viterbi(soft):
    """soft: positive favours bit 1. Returns the information bits (tail removed)."""
    soft = np.asarray(soft, np.float64)
    m = len(soft) // 2
    pm = np.full(64, -1e300)
    pm[0] = 0.0
    back = np.zeros((m, 64), np.uint8)
    for t in range(m):
        s0, s1 = soft[2 * t], soft[2 * t + 1]
        c0 = pm[_P0] + _S00 * s0 + _S01 * s1
        c1 = pm[_P1] + _S10 * s0 + _S11 * s1
        take1 = c1 > c0
        back[t] = take1
        pm = np.where(take1, c1, c0)
    st, bits = 0, [0] * m
    for t in range(m - 1, -1, -1):
        bits[t] = st >> 5
        st = ((st << 1) & 63) | int(back[t, st])
    return bits[:m - 6]


# ------------------------------------------------------------------ portable PRNG, grid, plan
def mulberry32(seed):
    a = seed & 0xFFFFFFFF

    def rng():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return rng


def grid_for(W, H, ncells):
    nx = max(8, math.floor(math.sqrt(ncells * W / H) + 0.5))
    ny = max(8, math.floor(ncells / nx + 0.5))
    return nx, ny


def grid_from_aspect(aspect, ncells):
    nx = max(8, math.floor(math.sqrt(ncells * aspect) + 0.5))
    return nx, max(8, math.floor(ncells / nx + 0.5))


class _Plan:
    pass


_plan_cache = {}


def plan(layer, nx, ny, ncoded):
    key = (layer.name, nx, ny, ncoded)
    if key in _plan_cache:
        return _plan_cache[key]
    N = nx * ny
    rng = mulberry32((layer.seed * 1000003 + nx * 1009 + ny) & 0xFFFFFFFF)
    pn = np.array([-1.0 if rng() < 0.5 else 1.0 for _ in range(N)])
    perm = list(range(N))
    for i in range(N - 1, 0, -1):
        j = math.floor(rng() * (i + 1))
        perm[i], perm[j] = perm[j], perm[i]
    perm = np.array(perm, np.int64)
    P = _js_round(layer.pilot_frac * N)
    pl = _Plan()
    pl.nx, pl.ny, pl.pn, pl.pilot = nx, ny, pn, perm[:P]
    pl.cells = perm[P:]                                   # data cells; cell q feeds coded bit q % ncoded
    pl.gid = np.arange(N - P) % ncoded
    pl.ncoded = ncoded
    _plan_cache.clear()
    _plan_cache[key] = pl
    return pl


# ------------------------------------------------------------------ tile statistics
def _tile_map(n, size):
    return np.minimum(np.arange(size) * n // size, n - 1)


def _luma_chroma(px):
    R, G, B = px[..., 0], px[..., 1], px[..., 2]
    Y = 0.299 * R + 0.587 * G + 0.114 * B
    return Y, ((R - Y) * 0.713 + (B - Y) * 0.564) * 0.5 + 128


def _finish_stats(nx, ny, sc, sy, syy, cnt, valid_min=None):
    n = nx * ny
    cn = np.where(cnt > 0, cnt, 1.0)
    my, myy = sy / cn, syy / cn
    tex = np.clip(np.sqrt(np.maximum(myy - my * my, 0)) / T_STD, 0, 1)
    return dict(nx=nx, ny=ny, c=(sc / cn).reshape(ny, nx), y=my.reshape(ny, nx), tex=tex.reshape(ny, nx))


def accumulate(rgb, grids, stride=1):
    """Per grid (nx, ny): tile means of chroma, luma and texture, from every `stride`-th pixel."""
    H, W = rgb.shape[:2]
    sub = rgb[::stride, ::stride].astype(np.float64)
    Y, C = _luma_chroma(sub)
    ys, xs = np.arange(0, H, stride), np.arange(0, W, stride)
    out = []
    for nx, ny in grids:
        t = (_tile_map(ny, H)[ys][:, None] * nx + _tile_map(nx, W)[xs][None, :]).ravel()
        n = nx * ny
        bc = lambda w: np.bincount(t, weights=w.ravel(), minlength=n)
        out.append(_finish_stats(nx, ny, bc(C), bc(Y), bc(Y * Y), np.bincount(t, minlength=n).astype(np.float64)))
    return out


def high_pass(r, k):
    """r minus the mean of the other k*k-1 neighbours (mirrored borders)."""
    h = k >> 1
    ny, nx = r.shape
    p = np.pad(r, h, mode='symmetric')
    s = np.zeros_like(r)
    for dy in range(k):
        for dx in range(k):
            s += p[dy:dy + ny, dx:dx + nx]
    return r - (s - r) / (k * k - 1)


# ------------------------------------------------------------------ embedding
def _bilin_map(size, n):
    u = (np.arange(size) + 0.5) * n / size - 0.5
    fl = np.floor(u)
    return np.clip(fl, 0, n - 1).astype(int), np.clip(fl + 1, 0, n - 1).astype(int), u - fl


def _tile_values(layer, st, coded, strength):
    nx, ny = st['nx'], st['ny']
    pl = plan(layer, nx, ny, len(coded))
    val = np.zeros(nx * ny)
    val[pl.pilot] = pl.pn[pl.pilot]
    sgn = np.where(np.asarray(coded) == 1, 1.0, -1.0)
    val[pl.cells] = pl.pn[pl.cells] * sgn[pl.gid]
    return (val * layer.amax * strength * np.maximum(st['tex'].ravel(), layer.floor)).reshape(ny, nx)


def _upsample(grid, W, H, rows):
    """Bilinear field for picture rows rows[0]..rows[1]."""
    ny, nx = grid.shape
    yi0, yi1, fy = _bilin_map(H, ny)
    xi0, xi1, fx = _bilin_map(W, nx)
    a, b = slice(*rows), None
    ga, gb = grid[yi0[a]], grid[yi1[a]]
    top = ga[:, xi0] + (ga[:, xi1] - ga[:, xi0]) * fx
    bot = gb[:, xi0] + (gb[:, xi1] - gb[:, xi0]) * fx
    return top + (bot - top) * fy[a][:, None]


def embed(rgb, payload, strength1=1.0, strength2=1.0):
    """Returns a marked copy of `rgb` (uint8, H x W x 3). payload: lat, lon, alt, t (unix s), tenth, manual."""
    H, W = rgb.shape[:2]
    c1, c2 = conv_encode(pack_l1(payload)), conv_encode(pack_l2(payload))
    g1, g2 = grid_for(W, H, L1.ncells), grid_for(W, H, L2.ncells)
    stride = max(1, int(math.sqrt(W * H / 3e6)))
    st = accumulate(rgb, [g1, g2], stride)
    grid1 = _tile_values(L1, st[0], c1, strength1 or 1.0)
    grid2 = _tile_values(L2, st[1], c2, strength2 or 1.0)
    out = np.empty_like(rgb)
    for y0 in range(0, H, 256):
        y1 = min(H, y0 + 256)
        p1 = _upsample(grid1, W, H, (y0, y1))[..., None]
        p2 = _upsample(grid2, W, H, (y0, y1))[..., None]
        px = rgb[y0:y1].astype(np.float64)
        add = p2 + p1 * np.array([1.403, -1.058, 1.773])
        out[y0:y1] = np.clip(np.floor(px + add + 0.5), 0, 255).astype(np.uint8)
    return out


# ------------------------------------------------------------------ reading
def score_cells(pl, w, hp, valid=None, pilot_only=False):
    w, hp = w.ravel(), hp.ravel()
    wp = w[pl.pilot] if valid is None else np.where(valid.ravel()[pl.pilot], w[pl.pilot], 0.0)
    num = float(np.sum(wp * pl.pn[pl.pilot] * hp[pl.pilot]))
    den = float(np.sum((wp * hp[pl.pilot]) ** 2))
    z = num / math.sqrt(den + 1e-9)
    if pilot_only:
        return z, None
    c = pl.cells
    wq = w[c] if valid is None else np.where(valid.ravel()[c], w[c], 0.0)
    s = np.bincount(pl.gid, weights=wq * pl.pn[c] * hp[c], minlength=pl.ncoded)
    cov = np.bincount(pl.gid, weights=wq * wq, minlength=pl.ncoded)
    return z, np.where(cov > 0, s / np.sqrt(np.where(cov > 0, cov, 1.0)), 0.0)


def _decode_layer(layer, st, n_bits, unpack):
    ncoded = 2 * (n_bits + 6)
    pl = plan(layer, st['nx'], st['ny'], ncoded)
    hp = high_pass(st['y'] if layer.kind == 'luma' else st['c'], layer.kern)
    w = np.maximum(st['tex'], layer.floor if layer.floor > 0 else 0.02)
    z, soft = score_cells(pl, w, hp)
    return dict(data=unpack(viterbi(soft)), z=z)


def _result(r1, r2):
    status = 'ok' if r1['data'] else ('part' if r2['data'] else ('damaged' if max(r1['z'], r2['z']) > DETECT_Z else 'none'))
    return dict(status=status, l1=r1['data'], l2=r2['data'], z1=r1['z'], z2=r2['z'])


def _try_siblings(rgb, stride, layer, n_bits, unpack, current, shifts):
    H, W = rgb.shape[:2]
    base, best = grid_for(W, H, layer.ncells), current
    for s in shifts:
        nx = base[0] + s
        ny = max(8, math.floor(layer.ncells / nx + 0.5))
        if nx < 8:
            continue
        r = _decode_layer(layer, accumulate(rgb, [(nx, ny)], stride)[0], n_bits, unpack)
        if r['data']:
            return r
        if r['z'] > best['z']:
            best = r
    return best


def read(rgb, stride=None):
    """Reads an RGB picture. status: 'ok' (layer 1), 'part' (only layer 2), 'damaged', 'none'."""
    H, W = rgb.shape[:2]
    stride = stride or max(1, int(math.sqrt(W * H / 3e6)))
    b1, b2 = grid_for(W, H, L1.ncells), grid_for(W, H, L2.ncells)
    st = accumulate(rgb, [b1, b2], stride)
    r1, r2 = _decode_layer(L1, st[0], N1, unpack_l1), _decode_layer(L2, st[1], N2, unpack_l2)
    if not r1['data']:
        r1 = _try_siblings(rgb, stride, L1, N1, unpack_l1, r1, [1, -1])
    if not r2['data']:
        r2 = _try_siblings(rgb, stride, L2, N2, unpack_l2, r2, [1, -1, 2, -2])
    return _result(r1, r2)


# ------------------------------------------------------------------ cropped pictures
CROP_ASPECTS = [4 / 3, 3 / 4, 16 / 9, 9 / 16, 1.0]


def _xcorr_valid(S, A):
    """out[iy, ix] = sum over (j, i) of S[iy + j, ix + i] * A[j, i], for every offset where A fits inside S."""
    ny, nx = S.shape
    nj, ni = A.shape
    sh = (ny + nj, nx + ni)
    c = np.fft.irfft2(np.fft.rfft2(S, sh) * np.conj(np.fft.rfft2(A, sh)), sh)
    return c[:ny - nj + 1, :nx - ni + 1]


def _chroma_plane(rgb, stride):
    H, W = rgb.shape[:2]
    h, w = H // stride, W // stride
    _, C = _luma_chroma(rgb[:h * stride:stride, :w * stride:stride].astype(np.float64))
    return C


def _integral(p):
    I = np.zeros((p.shape[0] + 1, p.shape[1] + 1))
    I[1:, 1:] = p.cumsum(0).cumsum(1)
    return I


def _box_means(I, w, h, xe, ye):
    """Means over the pixel boxes xe[i]..xe[i+1] x ye[j]..ye[j+1] (rounded like the reference engine)."""
    r = lambda v: np.floor(v + 0.5).astype(int)
    a, b = np.maximum(0, r(xe[:-1])), np.minimum(w, r(xe[1:]))
    c, d = np.maximum(0, r(ye[:-1])), np.minimum(h, r(ye[1:]))
    s = I[np.ix_(d, b)] - I[np.ix_(c, b)] - I[np.ix_(d, a)] + I[np.ix_(c, a)]
    area = (b - a)[None, :] * (d - c)[:, None]
    return np.where(area > 0, s / np.maximum(area, 1), 0.0)


def _crop_candidate(I, w, h, nx, ny, pil, fw, fh, px, py, rng):
    sx, sy = w / (fw * nx), h / (fh * ny)
    ni = min(nx, math.floor(w / sx - px - 1e-9))
    nj = min(ny, math.floor(h / sy - py - 1e-9))
    if ni < 12 or nj < 12:
        return None
    T = _box_means(I, w, h, (np.arange(ni + 1) + px) * sx, (np.arange(nj + 1) + py) * sy)
    hp = high_pass(T, 5)
    S, M = pil
    num = _xcorr_valid(S, hp)
    den = _xcorr_valid(M, hp * hp)
    cnt = np.rint(_xcorr_valid(M, np.ones_like(hp)))
    ixLo, ixHi, iyLo, iyHi = rng
    xa, xb, ya, yb = max(0, ixLo), min(nx - ni, ixHi), max(0, iyLo), min(ny - nj, iyHi)
    if xb < xa or yb < ya:
        return None
    z = num / np.sqrt(den + 1e-9)
    z = np.where(cnt >= 300, z, -np.inf)[ya:yb + 1, xa:xb + 1]
    if not np.isfinite(z).any():
        return None
    k = int(np.argmax(z))
    iy, ix = divmod(k, z.shape[1])
    return dict(z=float(z.flat[k]), ix=xa + ix, iy=ya + iy, px=px, py=py, fw=fw, fh=fh, sx=sx, sy=sy)


def _search_crop(I, w, h, aspect_o):
    nx, ny = grid_for(aspect_o * 1000, 1000, L1.ncells)
    pl = plan(L1, nx, ny, 2 * (N1 + 6))
    S = np.zeros(nx * ny)
    S[pl.pilot] = pl.pn[pl.pilot]
    M = np.zeros(nx * ny)
    M[pl.pilot] = 1.0
    pil = (S.reshape(ny, nx), M.reshape(ny, nx))
    ac, best = w / h, None
    full = (0, nx, 0, ny)
    for fw in np.arange(0.56, 1.0001, 0.02):
        fh = fw * aspect_o / ac
        if fh > 1.003 or fh < 0.5:
            continue
        for a in (0, 1 / 3, 2 / 3):
            for b in (0, 1 / 3, 2 / 3):
                r = _crop_candidate(I, w, h, nx, ny, pil, fw, fh, a, b, full)
                if r and (best is None or r['z'] > best['z']):
                    best = r
    if best is None:
        return None
    c0 = best
    for df in np.arange(-0.016, 0.0161, 0.004):
        f2 = c0['fw'] + df
        h2 = f2 * aspect_o / ac
        if f2 > 1.0001 or h2 > 1.003 or h2 < 0.5:
            continue
        for dx in np.arange(-1 / 3, 0.3334, 1 / 6):
            for dy in np.arange(-1 / 3, 0.3334, 1 / 6):
                qx, qy = c0['px'] + dx, c0['py'] + dy
                qx -= math.floor(qx)
                qy -= math.floor(qy)
                r2 = _crop_candidate(I, w, h, nx, ny, pil, f2, h2, qx, qy, (c0['ix'] - 2, c0['ix'] + 2, c0['iy'] - 2, c0['iy'] + 2))
                if r2 and r2['z'] > best['z']:
                    best = r2
    best.update(nx=nx, ny=ny, aspect=aspect_o)
    return best


def _masked_stats(nx, ny, sc, sy, syy, cnt, expected):
    n = nx * ny
    valid = (cnt >= 0.6 * expected) & (cnt >= 4)
    cn = np.where(cnt > 0, cnt, 1.0)
    my, myy = sy / cn, syy / cn
    tex = np.clip(np.sqrt(np.maximum(myy - my * my, 0)) / T_STD, 0, 1)
    z = np.zeros(n)
    return dict(nx=nx, ny=ny, valid=valid.reshape(ny, nx),
                c=np.where(valid, sc / cn, z).reshape(ny, nx), y=np.where(valid, my, z).reshape(ny, nx),
                tex=np.where(valid, tex, z).reshape(ny, nx))


def _accumulate_mapped(rgb, grids, m, stride):
    H, W = rgb.shape[:2]
    ys, xs = np.arange(0, H, stride), np.arange(0, W, stride)
    Y, C = _luma_chroma(rgb[::stride, ::stride].astype(np.float64))
    out = []
    for nx, ny in grids:
        cm = np.floor((m['ax'] + (xs + 0.5) * m['bx']) * nx).astype(int)
        rm = np.floor((m['ay'] + (ys + 0.5) * m['by']) * ny).astype(int)
        cm[(cm < 0) | (cm >= nx)] = -1
        rm[(rm < 0) | (rm >= ny)] = -1
        ok = (rm[:, None] >= 0) & (cm[None, :] >= 0)
        t = (rm[:, None] * nx + cm[None, :])[ok]
        n = nx * ny
        bc = lambda v: np.bincount(t, weights=v[ok], minlength=n)
        expected = (1 / (m['bx'] * nx)) * (1 / (m['by'] * ny)) / (stride * stride)
        out.append(_masked_stats(nx, ny, bc(C), bc(Y), bc(Y * Y), np.bincount(t, minlength=n).astype(np.float64), expected))
    return out


def _masked_score(layer, st, n_bits, pilot_only=False):
    ncoded = 2 * (n_bits + 6)
    nx, ny = st['nx'], st['ny']
    pl = plan(layer, nx, ny, ncoded)
    valid = st['valid']
    if valid.sum() < nx * ny * 0.3:
        return None, 0.0
    r = (st['y'] if layer.kind == 'luma' else st['c']).copy()
    r[~valid] = r[valid].mean()
    hp = high_pass(r, layer.kern)
    half = layer.kern >> 1
    pv = np.pad(valid, half, constant_values=True)
    ok = np.ones_like(valid)
    for dy in range(layer.kern):
        for dx in range(layer.kern):
            ok &= pv[dy:dy + ny, dx:dx + nx]
    w = np.maximum(st['tex'], layer.floor if layer.floor > 0 else 0.02)
    z, soft = score_cells(pl, w, hp, ok, pilot_only)
    return soft, z


def _decode_masked(layer, st, n_bits, unpack):
    soft, z = _masked_score(layer, st, n_bits)
    if soft is None:
        return dict(data=None, z=0.0)
    return dict(data=unpack(viterbi(soft)), z=z)


def read_cropped(rgb):
    """Reads a plain crop of a marked picture (no turn, no tilt). Returns read()'s dict plus `crop`, or None."""
    H, W = rgb.shape[:2]
    stride = max(1, int(math.sqrt(W * H / 2.5e6)))
    p = _chroma_plane(rgb, stride)
    I = _integral(p)
    best = None
    for asp in CROP_ASPECTS:
        c = _search_crop(I, p.shape[1], p.shape[0], asp)
        if not c or c['z'] < 8:  # noise peaks at about 5; a real mark gives 15 to 23
            continue
        X0, Y0 = c['ix'] - c['px'], c['iy'] - c['py']
        m = dict(ax=X0 / c['nx'], bx=1 / (c['sx'] * c['nx']) / stride, ay=Y0 / c['ny'], by=1 / (c['sy'] * c['ny']) / stride)
        g2 = grid_for(c['aspect'] * 1000, 1000, L2.ncells)
        st = _accumulate_mapped(rgb, [(c['nx'], c['ny']), g2], m, stride)
        cur = _result(_decode_masked(L1, st[0], N1, unpack_l1), _decode_masked(L2, st[1], N2, unpack_l2))
        cur['crop'] = dict(aspect=c['aspect'], widthFraction=c['fw'], heightFraction=c['fh'], left=m['ax'], top=m['ay'], searchZ=c['z'])
        rk = {'ok': 3, 'part': 2, 'damaged': 1, 'none': 0}[cur['status']] * 1000 + max(cur['z1'], cur['z2'])
        if best is None or rk > best[0]:
            best = (rk, cur)
        if cur['status'] == 'ok':
            break
    return best[1] if best else None


# ------------------------------------------------------------------ photos of a screen or a print
def solve_homography(src, dst):
    A, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    try:
        h = np.linalg.solve(np.array(A, float), np.array(b, float))
    except np.linalg.LinAlgError:
        return None
    return np.append(h, 1.0)


def _warp_stats(rgb, Hm, RW, RH, grids, stride):
    H, W = rgb.shape[:2]
    rx, ry = np.arange(0, RW, stride), np.arange(0, RH, stride)
    xc, yc = (rx + 0.5)[None, :], (ry + 0.5)[:, None]
    d = Hm[6] * xc + Hm[7] * yc + 1
    sx = (Hm[0] * xc + Hm[1] * yc + Hm[2]) / d - 0.5
    sy = (Hm[3] * xc + Hm[4] * yc + Hm[5]) / d - 0.5
    ok = (sx >= 0) & (sy >= 0) & (sx < W - 1) & (sy < H - 1)
    x0, y0 = sx[ok].astype(int), sy[ok].astype(int)
    fx, fy = sx[ok] - x0, sy[ok] - y0
    px = (rgb[y0, x0] * ((1 - fx) * (1 - fy))[:, None] + rgb[y0, x0 + 1] * (fx * (1 - fy))[:, None]
          + rgb[y0 + 1, x0] * ((1 - fx) * fy)[:, None] + rgb[y0 + 1, x0 + 1] * (fx * fy)[:, None])
    Y, C = _luma_chroma(px)
    out = []
    for nx, ny in grids:
        t = (_tile_map(ny, RH)[ry][:, None] * nx + _tile_map(nx, RW)[rx][None, :])[ok]
        n = nx * ny
        bc = lambda v: np.bincount(t, weights=v, minlength=n)
        expected = (RW / nx) * (RH / ny) / (stride * stride)
        out.append(_masked_stats(nx, ny, bc(C), bc(Y), bc(Y * Y), np.bincount(t, minlength=n).astype(np.float64), expected))
    return out


def _rect_corners(RW, RH):
    return [[0, 0], [RW, 0], [RW, RH], [0, RH]]


def pick_aspect(q):
    ln = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
    r = ((ln(q[0], q[1]) + ln(q[3], q[2])) / 2) / ((ln(q[0], q[3]) + ln(q[1], q[2])) / 2)
    return min(CROP_ASPECTS, key=lambda a: abs(math.log(a / r)))


def _persp_z(rgb, q, aspect, RW, RH, stride, both):
    Hm = solve_homography(_rect_corners(RW, RH), q)
    if Hm is None:
        return -1e9
    grids = [grid_from_aspect(aspect, L1.ncells)] + ([grid_from_aspect(aspect, L2.ncells)] if both else [])
    st = _warp_stats(rgb, Hm, RW, RH, grids, stride)
    z = _masked_score(L1, st[0], N1, True)[1]
    if both:
        z += max(_masked_score(L2, st[1], N2, True)[1], 0)
    return z


def _rect_size(aspect, long_side):
    return (long_side, round(long_side / aspect)) if aspect >= 1 else (round(long_side * aspect), long_side)


def refine_corners(rgb, q0, aspect, on_progress=None):
    """Slides each corner until the hidden pilot tiles line up. Returns (corners, z)."""
    RW, RH = _rect_size(aspect, 800)
    scale = RW / math.hypot(q0[1][0] - q0[0][0], q0[1][1] - q0[0][1])
    step = 1 / max(scale, 1e-6)
    state = dict(done=0, total=121 + 392 + 324 + 196 + 200)

    def score(qq, both, rw, rh):
        state['done'] += 1
        if on_progress and state['done'] % 25 == 0:
            on_progress(min(0.99, state['done'] / state['total']))
        return _persp_z(rgb, qq, aspect, rw, rh, 2, both)
    q = [list(map(float, p)) for p in q0]
    best, bq = score(q, False, RW, RH), q
    for dx in range(-30, 31, 6):
        for dy in range(-30, 31, 6):
            qq = [[p[0] + dx * step, p[1] + dy * step] for p in q]
            s = score(qq, False, RW, RH)
            if s > best:
                best, bq = s, qq
    q = bq
    for span, inc, rounds in [(18, 6, 2), (8, 2, 1), (3, 1, 1)]:
        for _ in range(rounds):
            for i in range(4):
                cand, cb = q, best
                for dx in range(-span, span + 1, inc):
                    for dy in range(-span, span + 1, inc):
                        q2 = [p[:] for p in q]
                        q2[i][0] += dx * step
                        q2[i][1] += dy * step
                        s2 = score(q2, False, RW, RH)
                        if s2 > cb:
                            cb, cand = s2, q2
                q, best = cand, cb
    RW2, RH2 = _rect_size(aspect, 1200)
    step2 = step * RW / RW2
    b2 = score(q, False, RW2, RH2)
    for span, inc in [(3, 1.5), (1.5, 0.75)]:
        for i in range(4):
            cand, cb = q, b2
            for dx in np.arange(-span, span + 1e-9, inc):
                for dy in np.arange(-span, span + 1e-9, inc):
                    q3 = [p[:] for p in q]
                    q3[i][0] += dx * step2
                    q3[i][1] += dy * step2
                    s3 = score(q3, False, RW2, RH2)
                    if s3 > cb:
                        cb, cand = s3, q3
            q, b2 = cand, cb
    if on_progress:
        on_progress(1.0)
    return q, b2


def read_perspective(rgb, corners, aspect=None, on_progress=None):
    """Reads a photo of a screen or a print. corners: four (x, y) points, TL, TR, BR, BL, in picture pixels."""
    aspect = aspect or pick_aspect(corners)
    q, z = refine_corners(rgb, corners, aspect, on_progress)
    RW, RH = _rect_size(aspect, 1600)
    Hm = solve_homography(_rect_corners(RW, RH), q)
    if Hm is None:
        return None
    g1, g2 = grid_from_aspect(aspect, L1.ncells), grid_from_aspect(aspect, L2.ncells)
    st = _warp_stats(rgb, Hm, RW, RH, [g1, g2], 1)
    r = _result(_decode_masked(L1, st[0], N1, unpack_l1), _decode_masked(L2, st[1], N2, unpack_l2))
    r['perspective'] = dict(aspect=aspect, corners=q, alignZ=z)
    return r


def auto_corners(rgb):
    """A first guess at the four corners of a bright picture on a dark surround. Only a starting point."""
    H, W = rgb.shape[:2]
    sw, sh = 160, max(8, round(160 * H / W))
    px = np.minimum(W - 1, np.floor((np.arange(sw) + 0.5) * W / sw + 0.5).astype(int))
    py = np.minimum(H - 1, np.floor((np.arange(sh) + 0.5) * H / sh + 0.5).astype(int))
    sm = rgb[np.ix_(py, px)].astype(np.float64)
    g = 0.299 * sm[..., 0] + 0.587 * sm[..., 1] + 0.114 * sm[..., 2]
    hist = np.bincount(np.minimum(255, g.astype(int)).ravel(), minlength=256).astype(np.float64)
    total, sum_all = g.size, float((np.arange(256) * hist).sum())
    wB = sumB = 0.0
    best_var, thr = -1.0, 128
    for t in range(256):
        wB += hist[t]
        if not wB:
            continue
        wF = total - wB
        if not wF:
            break
        sumB += t * hist[t]
        v = wB * wF * (sumB / wB - (sum_all - sumB) / wF) ** 2
        if v > best_var:
            best_var, thr = v, t
    mask = g > thr
    comp = -np.ones((sh, sw), int)
    best, best_size, cid = -1, 0, 0
    for k in range(sh * sw):
        y0, x0 = divmod(k, sw)
        if not mask[y0, x0] or comp[y0, x0] >= 0:
            continue
        stack, size = [(y0, x0)], 0
        comp[y0, x0] = cid
        while stack:
            cy, cx = stack.pop()
            size += 1
            for ny_, nx_ in ((cy, cx + 1), (cy, cx - 1), (cy + 1, cx), (cy - 1, cx)):
                if 0 <= ny_ < sh and 0 <= nx_ < sw and mask[ny_, nx_] and comp[ny_, nx_] < 0:
                    comp[ny_, nx_] = cid
                    stack.append((ny_, nx_))
        if size > best_size:
            best_size, best = size, cid
        cid += 1
    if best < 0 or best_size < 0.12 * sw * sh:
        return None
    ys, xs = np.nonzero(comp == best)
    s, d = xs + ys, xs - ys
    pick = lambda i: (int(xs[i]), int(ys[i]))
    tl, br, tr, bl = pick(np.argmin(s)), pick(np.argmax(s)), pick(np.argmax(d)), pick(np.argmin(d))
    f = lambda p, dx, dy: [(p[0] + dx) * W / sw, (p[1] + dy) * H / sh]
    return [f(tl, 0, 0), f(tr, 1, 0), f(br, 1, 1), f(bl, 0, 1)]


def layer_disagreement_meters(res):
    """Cross-check between the two layers (metres), or None when either has no location."""
    a, b = res.get('l1'), res.get('l2')
    if not a or not b or a.get('lat') is None or b.get('lat') is None:
        return None
    dlat = (a['lat'] - b['lat']) * 111320
    dlon = (a['lon'] - b['lon']) * 111320 * math.cos(math.radians(a['lat']))
    return math.hypot(dlat, dlon)
