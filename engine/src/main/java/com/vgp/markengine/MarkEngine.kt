package com.vgp.markengine

import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Row access to a picture, so the engine never needs a second full-size copy of it.
 * Pixels are ARGB ints (the layout of [android.graphics.Bitmap.getPixels]).
 */
internal interface PixelBuffer {
    val width: Int
    val height: Int
    fun readRow(y: Int, out: IntArray)
    fun writeRow(y: Int, row: IntArray)
}

enum class MarkStatus { OK, PART, DAMAGED, NONE }

/** Where the original frame sat inside a cropped picture: fractions of the original frame. */
/** Where a photo of a screen or print was lined up: the refined corners in picture pixels. */
data class PerspectiveInfo(val aspect: Double, val corners: List<DoubleArray>, val alignZ: Double)

data class CropInfo(
    val aspect: Double, val widthFraction: Double, val heightFraction: Double,
    val left: Double, val top: Double, val searchZ: Double,
)

/**
 * Outcome of reading a picture.
 * [OK]: layer 1 gave the full record. [PART]: only layer 2 survived (location only).
 * [DAMAGED]: a mark is certainly there but cannot be read. [NONE]: no mark found.
 */
data class MarkReadResult(
    val status: MarkStatus,
    val layer1: Layer1Data?,
    val layer2: Layer2Data?,
    val z1: Double,
    val z2: Double,
    /** Set when the picture had to be matched to a cropped frame; says where the original frame sat. */
    val crop: CropInfo? = null,
    val perspective: PerspectiveInfo? = null,
) {
    /** Metres between the two layers' locations, or null when either has none. Over 30 m is suspicious. */
    val layerDisagreementMeters: Double?
        get() {
            val a = layer1; val b = layer2
            if (a?.latitude == null || a.longitude == null || b?.latitude == null || b.longitude == null) return null
            val dLat = (a.latitude - b.latitude) * 111320.0
            val dLon = (a.longitude - b.longitude) * 111320.0 * Math.cos(Math.toRadians(a.latitude))
            return sqrt(dLat * dLat + dLon * dLon)
        }
}

private class LayerDef(
    val name: String, val ncells: Int, val seed: Int, val pilotFrac: Double,
    val amax: Double, val floor: Double, val chroma: Boolean, val kern: Int,
)

private class TilePlan(val nx: Int, val ny: Int, val pn: DoubleArray, val pilot: IntArray, val groups: Array<IntArray>)

private class TileStats(val nx: Int, val ny: Int, val chroma: DoubleArray, val luma: DoubleArray, val tex: DoubleArray)

/** Writes and reads the two-layer invisible mark. Format: `watermark/WATERMARK-SPEC.md`. */
internal object MarkEngine {
    private const val T_STD = 14.0
    const val DETECT_Z = 3.5

    private val L1 = LayerDef("colour", 10000, 11, 0.20, 2.0, 0.25, true, 5)
    private val L2 = LayerDef("brightness", 50000, 77, 0.20, 4.5, 0.0, false, 3)

    // ------------------------------------------------------------------ PRNG, grid, plan
    private class Mulberry32(seed: Int) {
        private var a = seed
        fun next(): Double {
            a += 0x6D2B79F5
            var t = a
            t = (t xor (t ushr 15)) * (t or 1)
            t = t xor (t + (t xor (t ushr 7)) * (t or 61))
            return ((t xor (t ushr 14)).toLong() and 0xFFFFFFFFL).toDouble() / 4294967296.0
        }
    }

    private fun gridFor(w: Int, h: Int, ncells: Int): IntArray {
        val nx = max(8, floor(sqrt(ncells.toDouble() * w / h) + 0.5).toInt())
        val ny = max(8, floor(ncells.toDouble() / nx + 0.5).toInt())
        return intArrayOf(nx, ny)
    }

    private val planCache = HashMap<String, TilePlan>()

    @Synchronized
    private fun plan(layer: LayerDef, nx: Int, ny: Int, ncoded: Int): TilePlan {
        val key = "${layer.name}:$nx:$ny:$ncoded"
        planCache[key]?.let { return it }
        val n = nx * ny
        val rng = Mulberry32(layer.seed * 1000003 + nx * 1009 + ny)
        val pn = DoubleArray(n) { if (rng.next() < 0.5) -1.0 else 1.0 }
        val perm = IntArray(n) { it }
        for (i in n - 1 downTo 1) {
            val j = floor(rng.next() * (i + 1)).toInt()
            val tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp
        }
        val p = floor(layer.pilotFrac * n + 0.5).toInt()
        val pilot = perm.copyOfRange(0, p)
        val dataN = n - p
        val groups = Array(ncoded) { k ->
            val cnt = if (k < dataN) (dataN - k + ncoded - 1) / ncoded else 0
            IntArray(cnt) { q -> perm[p + k + q * ncoded] }
        }
        val res = TilePlan(nx, ny, pn, pilot, groups)
        planCache.clear()
        planCache[key] = res
        return res
    }

    // ------------------------------------------------------------------ tile statistics
    private fun tileMap(n: Int, size: Int): IntArray = IntArray(size) { min(n - 1, (it.toLong() * n / size).toInt()) }

    private fun accumulate(buf: PixelBuffer, grids: List<IntArray>, stride: Int): List<TileStats> {
        val w = buf.width; val h = buf.height
        val ng = grids.size
        val cm = Array(ng) { tileMap(grids[it][0], w) }
        val rm = Array(ng) { tileMap(grids[it][1], h) }
        val sc = Array(ng) { DoubleArray(grids[it][0] * grids[it][1]) }
        val sy = Array(ng) { DoubleArray(grids[it][0] * grids[it][1]) }
        val syy = Array(ng) { DoubleArray(grids[it][0] * grids[it][1]) }
        val cnt = Array(ng) { DoubleArray(grids[it][0] * grids[it][1]) }
        val row = IntArray(w)
        var y = 0
        while (y < h) {
            buf.readRow(y, row)
            var x = 0
            while (x < w) {
                val px = row[x]
                val r = ((px shr 16) and 0xFF).toDouble()
                val g = ((px shr 8) and 0xFF).toDouble()
                val b = (px and 0xFF).toDouble()
                val yy = 0.299 * r + 0.587 * g + 0.114 * b
                val c = ((r - yy) * 0.713 + (b - yy) * 0.564) * 0.5 + 128.0
                for (gi in 0 until ng) {
                    val t = rm[gi][y] * grids[gi][0] + cm[gi][x]
                    sc[gi][t] += c; sy[gi][t] += yy; syy[gi][t] += yy * yy; cnt[gi][t] += 1.0
                }
                x += stride
            }
            y += stride
        }
        return List(ng) { gi ->
            val n = grids[gi][0] * grids[gi][1]
            val c = DoubleArray(n); val ly = DoubleArray(n); val tex = DoubleArray(n)
            for (t in 0 until n) {
                val cn = if (cnt[gi][t] == 0.0) 1.0 else cnt[gi][t]
                val my = sy[gi][t] / cn; val myy = syy[gi][t] / cn
                ly[t] = my
                c[t] = sc[gi][t] / cn
                tex[t] = (sqrt(max(myy - my * my, 0.0)) / T_STD).coerceIn(0.0, 1.0)
            }
            TileStats(grids[gi][0], grids[gi][1], c, ly, tex)
        }
    }

    private fun reflect(i: Int, n: Int) = if (i < 0) -i - 1 else if (i >= n) 2 * n - i - 1 else i

    private fun highPass(r: DoubleArray, nx: Int, ny: Int, k: Int): DoubleArray {
        val half = k shr 1; val n2 = k * k
        val out = DoubleArray(nx * ny)
        for (y in 0 until ny) for (x in 0 until nx) {
            var s = 0.0
            for (dy in -half..half) {
                val yy = reflect(y + dy, ny) * nx
                for (dx in -half..half) s += r[yy + reflect(x + dx, nx)]
            }
            val v = r[y * nx + x]
            out[y * nx + x] = v - (s - v) / (n2 - 1)
        }
        return out
    }

    // ------------------------------------------------------------------ writing
    /**
     * Adds both layers to the picture, in place, one row at a time.
     * Write this LAST, after any overlay has been drawn.
     */
    fun embed(buf: PixelBuffer, record: MarkRecord, strength: Double = 1.0) {
        val w = buf.width; val h = buf.height
        val c1 = MarkCodec.convEncode(MarkCodec.packL1(record))
        val c2 = MarkCodec.convEncode(MarkCodec.packL2(record))
        val g1 = gridFor(w, h, L1.ncells); val g2 = gridFor(w, h, L2.ncells)
        val stride = max(1, floor(sqrt(w.toDouble() * h / 3e6)).toInt())
        val st = accumulate(buf, listOf(g1, g2), stride)
        val grid1 = tileValues(L1, st[0], c1, strength)
        val grid2 = tileValues(L2, st[1], c2, strength)
        val nx1 = st[0].nx; val nx2 = st[1].nx
        val bx1 = BilinMap(w, nx1); val by1 = BilinMap(h, st[0].ny)
        val bx2 = BilinMap(w, nx2); val by2 = BilinMap(h, st[1].ny)
        val row = IntArray(w)
        for (y in 0 until h) {
            buf.readRow(y, row)
            val fy1 = by1.f[y]; val fy2 = by2.f[y]
            val r1a = by1.i0[y] * nx1; val r1b = by1.i1[y] * nx1
            val r2a = by2.i0[y] * nx2; val r2b = by2.i1[y] * nx2
            for (x in 0 until w) {
                val fx1 = bx1.f[x]; val xa = bx1.i0[x]; val xb = bx1.i1[x]
                val top1 = grid1[r1a + xa] + (grid1[r1a + xb] - grid1[r1a + xa]) * fx1
                val bot1 = grid1[r1b + xa] + (grid1[r1b + xb] - grid1[r1b + xa]) * fx1
                val p1 = top1 + (bot1 - top1) * fy1
                val fx2 = bx2.f[x]; val xc = bx2.i0[x]; val xd = bx2.i1[x]
                val top2 = grid2[r2a + xc] + (grid2[r2a + xd] - grid2[r2a + xc]) * fx2
                val bot2 = grid2[r2b + xc] + (grid2[r2b + xd] - grid2[r2b + xc]) * fx2
                val p2 = top2 + (bot2 - top2) * fy2
                val px = row[x]
                val r = ((px shr 16) and 0xFF) + p2 + 1.403 * p1
                val g = ((px shr 8) and 0xFF) + p2 - 1.058 * p1
                val b = (px and 0xFF) + p2 + 1.773 * p1
                row[x] = (px and 0xFF000000.toInt()) or (clamp8(r) shl 16) or (clamp8(g) shl 8) or clamp8(b)
            }
            buf.writeRow(y, row)
        }
    }

    private fun clamp8(v: Double): Int = if (v < 0) 0 else if (v > 255) 255 else (v + 0.5).toInt()

    private class BilinMap(size: Int, n: Int) {
        val i0 = IntArray(size); val i1 = IntArray(size); val f = DoubleArray(size)
        init {
            for (p in 0 until size) {
                val u = (p + 0.5) * n / size - 0.5
                val fl = floor(u)
                f[p] = u - fl
                i0[p] = fl.toInt().coerceIn(0, n - 1)
                i1[p] = (fl.toInt() + 1).coerceIn(0, n - 1)
            }
        }
    }

    private fun tileValues(layer: LayerDef, st: TileStats, coded: IntArray, strength: Double): DoubleArray {
        val pl = plan(layer, st.nx, st.ny, coded.size)
        val n = st.nx * st.ny
        val v = DoubleArray(n)
        for (c in pl.pilot) v[c] = pl.pn[c]
        for (k in pl.groups.indices) {
            val sgn = if (coded[k] == 1) 1.0 else -1.0
            for (c in pl.groups[k]) v[c] = pl.pn[c] * sgn
        }
        return DoubleArray(n) { v[it] * layer.amax * strength * max(st.tex[it], layer.floor) }
    }

    // ------------------------------------------------------------------ reading
    private class LayerScore(val z: Double, val soft: DoubleArray)

    private fun scoreCells(pl: TilePlan, w: DoubleArray, hp: DoubleArray, valid: BooleanArray?, pilotOnly: Boolean = false): LayerScore {
        var num = 0.0; var den = 0.0
        for (c in pl.pilot) {
            val wc = if (valid != null && !valid[c]) 0.0 else w[c]
            num += wc * pl.pn[c] * hp[c]
            den += (wc * hp[c]) * (wc * hp[c])
        }
        if (pilotOnly) return LayerScore(num / sqrt(den + 1e-9), DoubleArray(0))
        val soft = DoubleArray(pl.groups.size)
        for (k in pl.groups.indices) {
            var s = 0.0; var cov = 0.0
            for (c in pl.groups[k]) {
                val wq = if (valid != null && !valid[c]) 0.0 else w[c]
                s += wq * pl.pn[c] * hp[c]
                cov += wq * wq
            }
            soft[k] = if (cov > 0) s / sqrt(cov) else 0.0
        }
        return LayerScore(num / sqrt(den + 1e-9), soft)
    }

    private class LayerRead<T>(val data: T?, val z: Double)

    private fun <T> decodeLayer(layer: LayerDef, st: TileStats, nBits: Int, unpack: (IntArray) -> T?): LayerRead<T> {
        val ncoded = 2 * (nBits + 6)
        val pl = plan(layer, st.nx, st.ny, ncoded)
        val r = if (layer.chroma) st.chroma else st.luma
        val hp = highPass(r, st.nx, st.ny, layer.kern)
        val fl = if (layer.floor > 0) layer.floor else 0.02
        val w = DoubleArray(st.nx * st.ny) { max(st.tex[it], fl) }
        val sc = scoreCells(pl, w, hp, null)
        return LayerRead(unpack(MarkCodec.viterbi(sc.soft)), sc.z)
    }

    private fun <T> trySiblings(
        buf: PixelBuffer, stride: Int, layer: LayerDef, nBits: Int, unpack: (IntArray) -> T?,
        current: LayerRead<T>, shifts: IntArray,
    ): LayerRead<T> {
        val base = gridFor(buf.width, buf.height, layer.ncells)
        var best = current
        for (s in shifts) {
            val nx = base[0] + s
            if (nx < 8) continue
            val ny = max(8, floor(layer.ncells.toDouble() / nx + 0.5).toInt())
            val st = accumulate(buf, listOf(intArrayOf(nx, ny)), stride)[0]
            val r = decodeLayer(layer, st, nBits, unpack)
            if (r.data != null) return r
            if (r.z > best.z) best = r
        }
        return best
    }

    /** Reads a picture. Safe on unmarked pictures: the result is [MarkStatus.NONE], never a wrong record. */
    fun read(buf: PixelBuffer): MarkReadResult {
        val w = buf.width; val h = buf.height
        if (w < 64 || h < 64) return MarkReadResult(MarkStatus.NONE, null, null, 0.0, 0.0)
        val stride = max(1, floor(sqrt(w.toDouble() * h / 3e6)).toInt())
        val b1 = gridFor(w, h, L1.ncells); val b2 = gridFor(w, h, L2.ncells)
        val st = accumulate(buf, listOf(b1, b2), stride)
        var r1 = decodeLayer(L1, st[0], MarkCodec.N1, MarkCodec::unpackL1)
        var r2 = decodeLayer(L2, st[1], MarkCodec.N2, MarkCodec::unpackL2)
        // A resized copy can round its size so that the tile grid differs by one tile.
        if (r1.data == null) r1 = trySiblings(buf, stride, L1, MarkCodec.N1, MarkCodec::unpackL1, r1, intArrayOf(1, -1))
        if (r2.data == null) r2 = trySiblings(buf, stride, L2, MarkCodec.N2, MarkCodec::unpackL2, r2, intArrayOf(1, -1, 2, -2))
        val status = when {
            r1.data != null -> MarkStatus.OK
            r2.data != null -> MarkStatus.PART
            r1.z > DETECT_Z || r2.z > DETECT_Z -> MarkStatus.DAMAGED
            else -> MarkStatus.NONE
        }
        return MarkReadResult(status, r1.data, r2.data, r1.z, r2.z)
    }

    // ------------------------------------------------------------------ cropped pictures
    /*
     * A crop shifts the tile grid. The reader finds where the original frame sat inside the picture
     * by correlating the picture's colour detail with the known pilot pattern, then reads the tiles
     * that are fully inside the crop and treats the rest as missing (the repair code absorbs it).
     * Assumes a plain crop (no turn, no tilt) of a frame with one of the app's usual shapes.
     */
    private val CROP_ASPECTS = doubleArrayOf(4.0 / 3, 3.0 / 4, 16.0 / 9, 9.0 / 16, 1.0)
    private const val CROP_MIN_Z = 8.0 // noise peaks at about 5; a real mark gives 15 to 23

    private class Plane(val p: DoubleArray, val w: Int, val h: Int)

    private class CropHit(
        val z: Double, val ix: Int, val iy: Int, val px: Double, val py: Double,
        val fw: Double, val fh: Double, val sx: Double, val sy: Double,
    ) {
        var nx = 0; var ny = 0; var aspect = 0.0
    }

    private class MaskedStats(val nx: Int, val ny: Int, val chroma: DoubleArray, val luma: DoubleArray, val tex: DoubleArray, val valid: BooleanArray)

    private fun chromaPlane(buf: PixelBuffer, stride: Int): Plane {
        val w = buf.width / stride; val h = buf.height / stride
        val out = DoubleArray(w * h)
        val row = IntArray(buf.width)
        for (y in 0 until h) {
            buf.readRow(y * stride, row)
            for (x in 0 until w) {
                val px = row[x * stride]
                val r = ((px shr 16) and 0xFF).toDouble(); val b = (px and 0xFF).toDouble()
                val yy = 0.299 * r + 0.587 * ((px shr 8) and 0xFF) + 0.114 * b
                out[y * w + x] = ((r - yy) * 0.713 + (b - yy) * 0.564) * 0.5 + 128.0
            }
        }
        return Plane(out, w, h)
    }

    private fun integral(pl: Plane): DoubleArray {
        val w = pl.w; val h = pl.h
        val ii = DoubleArray((w + 1) * (h + 1))
        for (y in 1..h) {
            var row = 0.0
            for (x in 1..w) {
                row += pl.p[(y - 1) * w + (x - 1)]
                ii[y * (w + 1) + x] = ii[(y - 1) * (w + 1) + x] + row
            }
        }
        return ii
    }

    private fun boxMean(ii: DoubleArray, w: Int, h: Int, x0: Double, y0: Double, x1: Double, y1: Double): Double {
        val a = max(0L, Math.round(x0)).toInt(); val b = min(w.toLong(), Math.round(x1)).toInt()
        val c = max(0L, Math.round(y0)).toInt(); val d = min(h.toLong(), Math.round(y1)).toInt()
        if (b <= a || d <= c) return 0.0
        val w1 = w + 1
        return (ii[d * w1 + b] - ii[c * w1 + b] - ii[d * w1 + a] + ii[c * w1 + a]) / ((b - a).toDouble() * (d - c))
    }

    private fun cropCandidate(
        ii: DoubleArray, w: Int, h: Int, nx: Int, ny: Int, pX: IntArray, pY: IntArray, pS: DoubleArray,
        fw: Double, fh: Double, px: Double, py: Double, ixLo: Int, ixHi: Int, iyLo: Int, iyHi: Int,
    ): CropHit? {
        val sx = w / (fw * nx); val sy = h / (fh * ny)
        val ni = min(nx, floor(w / sx - px - 1e-9).toInt()); val nj = min(ny, floor(h / sy - py - 1e-9).toInt())
        if (ni < 12 || nj < 12) return null
        val t = DoubleArray(ni * nj)
        for (j in 0 until nj) for (i in 0 until ni) {
            t[j * ni + i] = boxMean(ii, w, h, (i + px) * sx, (j + py) * sy, (i + 1 + px) * sx, (j + 1 + py) * sy)
        }
        val hp = highPass(t, ni, nj, 5)
        var best: CropHit? = null
        val xa = max(0, ixLo); val xb = min(nx - ni, ixHi); val ya = max(0, iyLo); val yb = min(ny - nj, iyHi)
        for (iy in ya..yb) for (ix in xa..xb) {
            var num = 0.0; var den = 0.0; var cnt = 0
            for (k in pX.indices) {
                val i2 = pX[k] - ix; val j2 = pY[k] - iy
                if (i2 < 0 || i2 >= ni || j2 < 0 || j2 >= nj) continue
                val v = hp[j2 * ni + i2]
                num += pS[k] * v; den += v * v; cnt++
            }
            if (cnt < 300) continue
            val z = num / sqrt(den + 1e-9)
            if (best == null || z > best.z) best = CropHit(z, ix, iy, px, py, fw, fh, sx, sy)
        }
        return best
    }

    private fun searchCrop(ii: DoubleArray, w: Int, h: Int, aspectO: Double): CropHit? {
        val gx = max(8, floor(sqrt(L1.ncells * aspectO) + 0.5).toInt())
        val gy = max(8, floor(L1.ncells.toDouble() / gx + 0.5).toInt())
        val nx = gx; val ny = gy
        val pl = plan(L1, nx, ny, 2 * (MarkCodec.N1 + 6))
        val pc = pl.pilot.size
        val pX = IntArray(pc) { pl.pilot[it] % nx }
        val pY = IntArray(pc) { pl.pilot[it] / nx }
        val pS = DoubleArray(pc) { pl.pn[pl.pilot[it]] }
        val ac = w.toDouble() / h
        var best: CropHit? = null
        val ph = doubleArrayOf(0.0, 1.0 / 3, 2.0 / 3)
        var fw = 0.56
        while (fw <= 1.0001) {
            val fh = fw * aspectO / ac
            if (fh <= 1.003 && fh >= 0.5) {
                for (a in 0 until 3) for (b in 0 until 3) {
                    val r = cropCandidate(ii, w, h, nx, ny, pX, pY, pS, fw, fh, ph[a], ph[b], 0, nx, 0, ny)
                    if (r != null && (best == null || r.z > best.z)) best = r
                }
            }
            fw += 0.02
        }
        val c0 = best ?: return null
        var df = -0.016
        while (df <= 0.0161) {
            val f2 = c0.fw + df; val h2 = f2 * aspectO / ac
            if (f2 <= 1.0001 && h2 <= 1.003 && h2 >= 0.5) {
                var dx = -1.0 / 3
                while (dx <= 0.3334) {
                    var dy = -1.0 / 3
                    while (dy <= 0.3334) {
                        var qx = c0.px + dx; var qy = c0.py + dy
                        qx -= floor(qx); qy -= floor(qy)
                        val r2 = cropCandidate(ii, w, h, nx, ny, pX, pY, pS, f2, h2, qx, qy, c0.ix - 2, c0.ix + 2, c0.iy - 2, c0.iy + 2)
                        if (r2 != null && r2.z > (best?.z ?: -1e9)) best = r2
                        dy += 1.0 / 6
                    }
                    dx += 1.0 / 6
                }
            }
            df += 0.004
        }
        return best?.also { it.nx = nx; it.ny = ny; it.aspect = aspectO }
    }

    /** Tile means for a picture covering only part of the original frame: original fraction = a + pixel * b. */
    private fun accumulateMapped(
        buf: PixelBuffer, grids: List<IntArray>, ax: Double, bx: Double, ay: Double, by: Double, stride: Int,
    ): List<MaskedStats> {
        val w = buf.width; val h = buf.height; val ng = grids.size
        val cm = Array(ng) { gi -> IntArray(w) { x -> val t = floor((ax + (x + 0.5) * bx) * grids[gi][0]).toInt(); if (t < 0 || t >= grids[gi][0]) -1 else t } }
        val rm = Array(ng) { gi -> IntArray(h) { y -> val t = floor((ay + (y + 0.5) * by) * grids[gi][1]).toInt(); if (t < 0 || t >= grids[gi][1]) -1 else t } }
        val sc = Array(ng) { DoubleArray(grids[it][0] * grids[it][1]) }
        val sy = Array(ng) { DoubleArray(grids[it][0] * grids[it][1]) }
        val syy = Array(ng) { DoubleArray(grids[it][0] * grids[it][1]) }
        val cnt = Array(ng) { DoubleArray(grids[it][0] * grids[it][1]) }
        val row = IntArray(w)
        var y = 0
        while (y < h) {
            var needed = false
            for (gi in 0 until ng) if (rm[gi][y] >= 0) needed = true
            if (needed) {
                buf.readRow(y, row)
                var x = 0
                while (x < w) {
                    val px = row[x]
                    val r = ((px shr 16) and 0xFF).toDouble(); val b = (px and 0xFF).toDouble()
                    val yy = 0.299 * r + 0.587 * ((px shr 8) and 0xFF) + 0.114 * b
                    val c = ((r - yy) * 0.713 + (b - yy) * 0.564) * 0.5 + 128.0
                    for (gi in 0 until ng) {
                        val cx = cm[gi][x]; val cy = rm[gi][y]
                        if (cx < 0 || cy < 0) continue
                        val t = cy * grids[gi][0] + cx
                        sc[gi][t] += c; sy[gi][t] += yy; syy[gi][t] += yy * yy; cnt[gi][t] += 1.0
                    }
                    x += stride
                }
            }
            y += stride
        }
        return List(ng) { gi ->
            val nx = grids[gi][0]; val ny = grids[gi][1]; val n = nx * ny
            val expected = (1 / (bx * nx)) * (1 / (by * ny)) / (stride.toDouble() * stride)
            val c = DoubleArray(n); val ly = DoubleArray(n); val tex = DoubleArray(n); val valid = BooleanArray(n)
            for (t in 0 until n) {
                if (cnt[gi][t] < 0.6 * expected || cnt[gi][t] < 4) continue
                valid[t] = true
                val my = sy[gi][t] / cnt[gi][t]; val myy = syy[gi][t] / cnt[gi][t]
                ly[t] = my; c[t] = sc[gi][t] / cnt[gi][t]
                tex[t] = (sqrt(max(myy - my * my, 0.0)) / T_STD).coerceIn(0.0, 1.0)
            }
            MaskedStats(nx, ny, c, ly, tex, valid)
        }
    }

    private class MaskedScore(val sc: LayerScore?, val z: Double)

    /** Pilot score (and soft bits unless [pilotOnly]) for tile stats with a validity mask. */
    private fun maskedScore(layer: LayerDef, st: MaskedStats, nBits: Int, pilotOnly: Boolean = false): MaskedScore {
        val ncoded = 2 * (nBits + 6); val nx = st.nx; val ny = st.ny; val n = nx * ny
        val pl = plan(layer, nx, ny, ncoded)
        val r = (if (layer.chroma) st.chroma else st.luma).copyOf()
        var sum = 0.0; var cnt = 0
        for (t in 0 until n) if (st.valid[t]) { sum += r[t]; cnt++ }
        if (cnt < n * 0.3) return MaskedScore(null, 0.0)
        val mean = sum / cnt
        for (t in 0 until n) if (!st.valid[t]) r[t] = mean
        val hp = highPass(r, nx, ny, layer.kern); val half = layer.kern shr 1
        val ok = BooleanArray(n); val fl = if (layer.floor > 0) layer.floor else 0.02
        val w = DoubleArray(n)
        for (y in 0 until ny) for (x in 0 until nx) {
            var good = true
            loop@ for (dy in -half..half) for (dx in -half..half) {
                val yy = y + dy; val xx = x + dx
                if (yy < 0 || yy >= ny || xx < 0 || xx >= nx) continue
                if (!st.valid[yy * nx + xx]) { good = false; break@loop }
            }
            ok[y * nx + x] = good; w[y * nx + x] = max(st.tex[y * nx + x], fl)
        }
        val sc = scoreCells(pl, w, hp, ok, pilotOnly)
        return MaskedScore(sc, sc.z)
    }

    private fun <T> decodeLayerMasked(layer: LayerDef, st: MaskedStats, nBits: Int, unpack: (IntArray) -> T?): LayerRead<T> {
        val m = maskedScore(layer, st, nBits)
        val sc = m.sc ?: return LayerRead(null, 0.0)
        return LayerRead(unpack(MarkCodec.viterbi(sc.soft)), m.z)
    }

    /**
     * Reads a cropped picture (about 2 s on a PC). Null when no frame position fits.
     * Use after [read] came back without a full record.
     */
    fun readCropped(buf: PixelBuffer): MarkReadResult? {
        if (buf.width < 200 || buf.height < 200) return null
        val stride = max(1, floor(sqrt(buf.width.toDouble() * buf.height / 2.5e6)).toInt())
        val pl = chromaPlane(buf, stride)
        val ii = integral(pl)
        var best: MarkReadResult? = null
        var bestRank = -1.0
        for (aspect in CROP_ASPECTS) {
            val c = searchCrop(ii, pl.w, pl.h, aspect) ?: continue
            if (c.z < CROP_MIN_Z) continue
            val x0 = c.ix - c.px; val y0 = c.iy - c.py
            val ax = x0 / c.nx; val bx = 1 / (c.sx * c.nx) / stride
            val ay = y0 / c.ny; val by = 1 / (c.sy * c.ny) / stride
            val nx2 = max(8, floor(sqrt(L2.ncells * aspect) + 0.5).toInt())
            val ny2 = max(8, floor(L2.ncells.toDouble() / nx2 + 0.5).toInt())
            val st = accumulateMapped(buf, listOf(intArrayOf(c.nx, c.ny), intArrayOf(nx2, ny2)), ax, bx, ay, by, stride)
            val r1 = decodeLayerMasked(L1, st[0], MarkCodec.N1, MarkCodec::unpackL1)
            val r2 = decodeLayerMasked(L2, st[1], MarkCodec.N2, MarkCodec::unpackL2)
            val status = when {
                r1.data != null -> MarkStatus.OK
                r2.data != null -> MarkStatus.PART
                r1.z > DETECT_Z || r2.z > DETECT_Z -> MarkStatus.DAMAGED
                else -> MarkStatus.NONE
            }
            val cur = MarkReadResult(status, r1.data, r2.data, r1.z, r2.z, CropInfo(aspect, c.fw, c.fh, ax, ay, c.z))
            val rank = status.ordinal.let { 3 - it } * 1000.0 + max(cur.z1, cur.z2)
            if (rank > bestRank) { best = cur; bestRank = rank }
            if (status == MarkStatus.OK) break
        }
        return best
    }

    // ------------------------------------------------------------------ photos of a screen or a print
    /*
     * The user gives four approximate corners of the photo inside the picture (taps, or autoCorners).
     * No visible marker is needed: the corners are nudged until the hidden pilot tiles line up.
     * The frame shape is the nearest of the app's usual shapes to the quadrilateral that was given.
     */
    private fun gridFromAspect(aspect: Double, ncells: Int): IntArray {
        val nx = max(8, floor(sqrt(ncells * aspect) + 0.5).toInt())
        return intArrayOf(nx, max(8, floor(ncells.toDouble() / nx + 0.5).toInt()))
    }

    /** 3x3 homography (row major) taking the four points [from] to the four points [to]; null when degenerate. */
    internal fun solveHomography(from: Array<DoubleArray>, to: Array<DoubleArray>): DoubleArray? {
        val a = Array(8) { DoubleArray(8) }; val b = DoubleArray(8)
        for (i in 0 until 4) {
            val x = from[i][0]; val y = from[i][1]; val u = to[i][0]; val v = to[i][1]
            a[2 * i] = doubleArrayOf(x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y); b[2 * i] = u
            a[2 * i + 1] = doubleArrayOf(0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y); b[2 * i + 1] = v
        }
        for (i in 0 until 8) {
            var p = i
            for (j in i + 1 until 8) if (Math.abs(a[j][i]) > Math.abs(a[p][i])) p = j
            val t = a[i]; a[i] = a[p]; a[p] = t
            val tb = b[i]; b[i] = b[p]; b[p] = tb
            if (Math.abs(a[i][i]) < 1e-12) return null
            for (j in i + 1 until 8) {
                val f = a[j][i] / a[i][i]
                for (k in i until 8) a[j][k] -= f * a[i][k]
                b[j] -= f * b[i]
            }
        }
        val h = DoubleArray(8)
        for (i in 7 downTo 0) {
            var s = b[i]
            for (j in i + 1 until 8) s -= a[i][j] * h[j]
            h[i] = s / a[i][i]
        }
        return doubleArrayOf(h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], 1.0)
    }

    /** Tile means of the picture seen through [hm] (rectangle pixel to picture pixel). [px] is the whole picture, ARGB. */
    private fun warpStats(px: IntArray, w: Int, h: Int, hm: DoubleArray, rw: Int, rh: Int, grids: List<IntArray>, stride: Int): List<MaskedStats> {
        val ng = grids.size
        val cm = Array(ng) { tileMap(grids[it][0], rw) }; val rm = Array(ng) { tileMap(grids[it][1], rh) }
        val sc = Array(ng) { DoubleArray(grids[it][0] * grids[it][1]) }
        val sy = Array(ng) { DoubleArray(grids[it][0] * grids[it][1]) }
        val syy = Array(ng) { DoubleArray(grids[it][0] * grids[it][1]) }
        val cnt = Array(ng) { DoubleArray(grids[it][0] * grids[it][1]) }
        val h0 = hm[0]; val h1 = hm[1]; val h2 = hm[2]; val h3 = hm[3]; val h4 = hm[4]; val h5 = hm[5]; val h6 = hm[6]; val h7 = hm[7]
        var ry = 0
        while (ry < rh) {
            val yc = ry + 0.5
            var rx = 0
            while (rx < rw) {
                val xc = rx + 0.5; val d = h6 * xc + h7 * yc + 1.0
                val sx = (h0 * xc + h1 * yc + h2) / d - 0.5; val sY = (h3 * xc + h4 * yc + h5) / d - 0.5
                if (sx >= 0 && sY >= 0 && sx < w - 1 && sY < h - 1) {
                    val x0 = sx.toInt(); val y0 = sY.toInt(); val fx = sx - x0; val fy = sY - y0
                    val i = y0 * w + x0; val j = i + w
                    val w00 = (1 - fx) * (1 - fy); val w10 = fx * (1 - fy); val w01 = (1 - fx) * fy; val w11 = fx * fy
                    val p00 = px[i]; val p10 = px[i + 1]; val p01 = px[j]; val p11 = px[j + 1]
                    val r = ((p00 shr 16) and 255) * w00 + ((p10 shr 16) and 255) * w10 + ((p01 shr 16) and 255) * w01 + ((p11 shr 16) and 255) * w11
                    val g = ((p00 shr 8) and 255) * w00 + ((p10 shr 8) and 255) * w10 + ((p01 shr 8) and 255) * w01 + ((p11 shr 8) and 255) * w11
                    val b = (p00 and 255) * w00 + (p10 and 255) * w10 + (p01 and 255) * w01 + (p11 and 255) * w11
                    val yy = 0.299 * r + 0.587 * g + 0.114 * b
                    val c = ((r - yy) * 0.713 + (b - yy) * 0.564) * 0.5 + 128.0
                    for (gi in 0 until ng) {
                        val t = rm[gi][ry] * grids[gi][0] + cm[gi][rx]
                        sc[gi][t] += c; sy[gi][t] += yy; syy[gi][t] += yy * yy; cnt[gi][t] += 1.0
                    }
                }
                rx += stride
            }
            ry += stride
        }
        return List(ng) { gi ->
            val nx = grids[gi][0]; val ny = grids[gi][1]; val n = nx * ny
            val expected = (rw.toDouble() / nx) * (rh.toDouble() / ny) / (stride.toDouble() * stride)
            val c = DoubleArray(n); val ly = DoubleArray(n); val tex = DoubleArray(n); val valid = BooleanArray(n)
            for (t in 0 until n) {
                if (cnt[gi][t] < 0.6 * expected || cnt[gi][t] < 4) continue
                valid[t] = true
                val my = sy[gi][t] / cnt[gi][t]; val myy = syy[gi][t] / cnt[gi][t]
                ly[t] = my; c[t] = sc[gi][t] / cnt[gi][t]
                tex[t] = (sqrt(max(myy - my * my, 0.0)) / T_STD).coerceIn(0.0, 1.0)
            }
            MaskedStats(nx, ny, c, ly, tex, valid)
        }
    }

    private fun rectCorners(rw: Int, rh: Int) = arrayOf(doubleArrayOf(0.0, 0.0), doubleArrayOf(rw.toDouble(), 0.0), doubleArrayOf(rw.toDouble(), rh.toDouble()), doubleArrayOf(0.0, rh.toDouble()))

    private fun dist(a: DoubleArray, b: DoubleArray) = Math.hypot(a[0] - b[0], a[1] - b[1])

    /** The frame shape nearest to the quadrilateral (corners TL, TR, BR, BL). */
    fun pickAspect(q: Array<DoubleArray>): Double {
        val wq = (dist(q[0], q[1]) + dist(q[3], q[2])) / 2; val hq = (dist(q[0], q[3]) + dist(q[1], q[2])) / 2
        val r = wq / hq
        return CROP_ASPECTS.minByOrNull { Math.abs(Math.log(it / r)) } ?: 1.0
    }

    private fun perspZ(px: IntArray, w: Int, h: Int, q: Array<DoubleArray>, aspect: Double, rw: Int, rh: Int, stride: Int, both: Boolean): Double {
        val hm = solveHomography(rectCorners(rw, rh), q) ?: return -1e9
        val grids = mutableListOf(gridFromAspect(aspect, L1.ncells))
        if (both) grids.add(gridFromAspect(aspect, L2.ncells))
        val st = warpStats(px, w, h, hm, rw, rh, grids, stride)
        var z = maskedScore(L1, st[0], MarkCodec.N1, true).z
        if (both) z += max(maskedScore(L2, st[1], MarkCodec.N2, true).z, 0.0)
        return z
    }

    /** Where a refined quadrilateral ended up, and how well the hidden pattern lines up there. */
    class Aligned(val corners: Array<DoubleArray>, val z: Double, val aspect: Double)

    /**
     * Slides each corner until the hidden pilot tiles line up (about 1,300 trial pictures).
     * [onProgress] gets 0..1; [cancelled] is polled so a screen can stop the search.
     */
    fun refineCorners(
        px: IntArray, w: Int, h: Int, q0: Array<DoubleArray>, aspect: Double,
        onProgress: ((Double) -> Unit)? = null, cancelled: () -> Boolean = { false },
        /** (range, step) in tile-sized units of a 800 px rectangle for the whole-picture slide; null skips it. */
        translate: Pair<Int, Int>? = 30 to 3,
        stages: List<Triple<Int, Int, Int>> = listOf(Triple(40, 4, 1), Triple(18, 3, 2), Triple(8, 2, 1), Triple(3, 1, 1)),
        lastPass: Boolean = true,
    ): Aligned {
        val long1 = 800
        val rw = if (aspect >= 1) long1 else Math.round(long1 * aspect).toInt()
        val rh = if (aspect >= 1) Math.round(long1 / aspect).toInt() else long1
        val scale = rw / dist(q0[0], q0[1])
        val total = (translate?.let { val n = 2 * it.first / it.second + 1; n * n } ?: 0) +
            stages.sumOf { (r, s, rounds) -> val n = 2 * r / s + 1; n * n * 4 * rounds } + (if (lastPass) 200 else 0)
        val counter = java.util.concurrent.atomic.AtomicInteger()
        // Trial pictures are independent, so they are scored on all cores at once.
        fun evalAll(cands: List<Array<DoubleArray>>, rW: Int, rH: Int): DoubleArray {
            val out = DoubleArray(cands.size)
            java.util.stream.IntStream.range(0, cands.size).parallel().forEach { out[it] = perspZ(px, w, h, cands[it], aspect, rW, rH, 2, false) }
            val d = counter.addAndGet(cands.size)
            onProgress?.invoke(min(0.99, d.toDouble() / total))
            return out
        }
        fun copy(q: Array<DoubleArray>) = Array(4) { q[it].copyOf() }
        val step = 1.0 / max(scale, 1e-6)
        var q = copy(q0)
        var best = evalAll(listOf(q), rw, rh)[0]
        if (translate != null) {
            val cands = ArrayList<Array<DoubleArray>>()
            var dx = -translate.first
            while (dx <= translate.first) {
                var dy = -translate.first
                while (dy <= translate.first) {
                    cands.add(Array(4) { doubleArrayOf(q[it][0] + dx * step, q[it][1] + dy * step) })
                    dy += translate.second
                }
                dx += translate.second
            }
            val s = evalAll(cands, rw, rh)
            var bi = -1; for (i in s.indices) if (s[i] > best && (bi < 0 || s[i] > s[bi])) bi = i
            if (bi >= 0) { best = s[bi]; q = cands[bi] }
            if (cancelled()) return Aligned(q, best, aspect)
        }
        fun slide(i: Int, range: Double, stp: Double, st: Double, rW: Int, rH: Int, cur: Double): Pair<Double, Array<DoubleArray>> {
            val cands = ArrayList<Array<DoubleArray>>()
            var ddx = -range
            while (ddx <= range + 1e-9) {
                var ddy = -range
                while (ddy <= range + 1e-9) {
                    val q2 = copy(q); q2[i][0] += ddx * st; q2[i][1] += ddy * st
                    cands.add(q2)
                    ddy += stp
                }
                ddx += stp
            }
            val s = evalAll(cands, rW, rH)
            var bi = -1; for (k in s.indices) if (s[k] > cur && (bi < 0 || s[k] > s[bi])) bi = k
            return if (bi >= 0) s[bi] to cands[bi] else cur to q
        }
        for ((range, stp, rounds) in stages) {
            for (round in 0 until rounds) for (i in 0 until 4) {
                val r = slide(i, range.toDouble(), stp.toDouble(), step, rw, rh, best)
                best = r.first; q = r.second
                if (cancelled()) return Aligned(q, best, aspect)
            }
        }
        if (!lastPass) { onProgress?.invoke(1.0); return Aligned(q, best, aspect) }
        // Last pass: layer 1 only; the fine brightness layer is read afterwards at full resolution.
        val long2 = 1200
        val rw2 = if (aspect >= 1) long2 else Math.round(long2 * aspect).toInt()
        val rh2 = if (aspect >= 1) Math.round(long2 / aspect).toInt() else long2
        val step2 = step * rw / rw2
        var b2 = evalAll(listOf(q), rw2, rh2)[0]
        for ((range, stp) in listOf(3.0 to 1.5, 1.5 to 0.75)) {
            for (i in 0 until 4) {
                val r = slide(i, range, stp, step2, rw2, rh2, b2)
                b2 = r.first; q = r.second
                if (cancelled()) return Aligned(q, b2, aspect)
            }
        }
        onProgress?.invoke(1.0)
        return Aligned(q, b2, aspect)
    }

    // ------------------------------------------------------------------ snapping tapped corners to the picture's edges
    /*
     * A hand-tapped corner is a few percent off; the hidden pattern only lines up when the corners are within a
     * fraction of one tile (about 0.4% of the width). The outline of the picture (dark surround against the picture)
     * is a far stronger signal than the pattern, so each tapped edge is first replaced by the straight line that the
     * strongest edge nearby follows, and the corners are the crossings of those lines.
     */
    private class EdgeLine(val px: Double, val py: Double, val dx: Double, val dy: Double, val support: Int)

    private fun lum(px: IntArray, w: Int, h: Int, x: Double, y: Double): Double {
        val xi = x.toInt().coerceIn(0, w - 1); val yi = y.toInt().coerceIn(0, h - 1)
        val p = px[yi * w + xi]
        return 0.299 * ((p shr 16) and 255) + 0.587 * ((p shr 8) and 255) + 0.114 * (p and 255)
    }

    private fun fitEdge(px: IntArray, w: Int, h: Int, a: DoubleArray, b: DoubleArray): EdgeLine? {
        val len = dist(a, b); if (len < 50) return null
        val ux = (b[0] - a[0]) / len; val uy = (b[1] - a[1]) / len
        val nx = -uy; val ny = ux
        val r = (0.07 * len).coerceIn(20.0, 250.0).toInt()
        val n = 48; val half = 6
        val sPos = ArrayList<Double>(); val tPos = ArrayList<Double>(); val wgt = ArrayList<Double>()
        for (i in 0 until n) {
            val s = len * (0.08 + 0.84 * i / (n - 1))
            val bx = a[0] + ux * s; val by = a[1] + uy * s
            // profile across the edge, averaged along it
            val prof = DoubleArray(2 * r + 1)
            for (t in -r..r) {
                var acc = 0.0
                for (k in -half..half step 3) acc += lum(px, w, h, bx + nx * t + ux * k, by + ny * t + uy * k)
                prof[t + r] = acc / (2 * half / 3 + 1)
            }
            val d = DoubleArray(2 * r + 1)
            for (t in 3 until 2 * r - 2) d[t] = Math.abs(prof[t + 3] - prof[t - 3])
            // the two strongest separate maxima
            var taken = 0
            val used = BooleanArray(2 * r + 1)
            while (taken < 2) {
                var bi = -1; var bv = 8.0
                for (t in 3 until 2 * r - 2) if (!used[t] && d[t] > bv && d[t] >= d[t - 1] && d[t] >= d[t + 1]) { bv = d[t]; bi = t }
                if (bi < 0) break
                for (t in max(0, bi - 8)..min(2 * r, bi + 8)) used[t] = true
                sPos.add(s); tPos.add((bi - r).toDouble()); wgt.add(bv); taken++
            }
        }
        val m = sPos.size; if (m < 12) return null
        // RANSAC over pairs: line t = c0 + c1 * s
        var bestScore = 0.0; var bc0 = 0.0; var bc1 = 0.0
        for (i in 0 until m) for (j in i + 1 until m) {
            val ds = sPos[j] - sPos[i]; if (Math.abs(ds) < len * 0.25) continue
            val c1 = (tPos[j] - tPos[i]) / ds; val c0 = tPos[i] - c1 * sPos[i]
            if (Math.abs(c1) > 0.15) continue
            var sc = 0.0
            for (k in 0 until m) if (Math.abs(tPos[k] - (c0 + c1 * sPos[k])) <= 2.5) sc += wgt[k]
            if (sc > bestScore) { bestScore = sc; bc0 = c0; bc1 = c1 }
        }
        if (bestScore <= 0) return null
        // least squares on the inliers
        var sw = 0.0; var ss = 0.0; var st = 0.0; var sss = 0.0; var sst = 0.0; var cnt = 0
        for (k in 0 until m) if (Math.abs(tPos[k] - (bc0 + bc1 * sPos[k])) <= 2.5) {
            val wk = wgt[k]; sw += wk; ss += wk * sPos[k]; st += wk * tPos[k]; sss += wk * sPos[k] * sPos[k]; sst += wk * sPos[k] * tPos[k]; cnt++
        }
        if (cnt < 12) return null
        val den = sw * sss - ss * ss
        if (Math.abs(den) > 1e-9) { bc1 = (sw * sst - ss * st) / den; bc0 = (st - bc1 * ss) / sw }
        // line through (a + n*c0) with direction u + n*c1
        val dx0 = ux + nx * bc1; val dy0 = uy + ny * bc1; val dl = Math.hypot(dx0, dy0)
        return EdgeLine(a[0] + nx * bc0, a[1] + ny * bc0, dx0 / dl, dy0 / dl, cnt)
    }

    private fun cross(l1: EdgeLine, l2: EdgeLine): DoubleArray? {
        val det = l1.dx * l2.dy - l1.dy * l2.dx
        if (Math.abs(det) < 0.2) return null
        val t = ((l2.px - l1.px) * l2.dy - (l2.py - l1.py) * l2.dx) / det
        return doubleArrayOf(l1.px + l1.dx * t, l1.py + l1.dy * t)
    }

    /**
     * Corners (TL, TR, BR, BL) moved onto the picture's outline. An edge that cannot be found keeps its tapped position.
     * Returns null when nothing could be improved.
     */
    fun snapCorners(px: IntArray, w: Int, h: Int, q: Array<DoubleArray>): Array<DoubleArray>? {
        val top = fitEdge(px, w, h, q[0], q[1]); val right = fitEdge(px, w, h, q[1], q[2])
        val bottom = fitEdge(px, w, h, q[2], q[3]); val left = fitEdge(px, w, h, q[3], q[0])
        if (top == null || right == null || bottom == null || left == null) return null
        val tl = cross(left, top); val tr = cross(top, right); val br = cross(right, bottom); val bl = cross(bottom, left)
        if (tl == null || tr == null || br == null || bl == null) return null
        val out = arrayOf(tl, tr, br, bl)
        // refuse a result that moved a corner absurdly far (a wrong edge was latched onto)
        val tol = 0.12 * max(dist(q[0], q[1]), dist(q[1], q[2]))
        for (i in 0 until 4) if (dist(out[i], q[i]) > tol) return null
        return out
    }

    /**
     * Lines the corners up while trying the neighbouring frame shapes: the original photo is rarely exactly 4:3 (or 16:9 ...)
     * and a one-tile difference in the grid keeps the hidden pattern from lining up. A light search per shape, then the fine
     * search on the best shape only.
     */
    private fun alignAcrossShapes(
        px: IntArray, w: Int, h: Int, start: Array<DoubleArray>, aspect: Double, close: Boolean,
        onProgress: ((Double) -> Unit)?, cancelled: () -> Boolean,
    ): Aligned {
        val shapes = ArrayList<Double>(); val seen = HashSet<Int>()
        for (k in intArrayOf(0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6)) {
            val asp = aspect * (1 + 0.003 * k)
            val g = gridFromAspect(asp, L1.ncells)
            if (seen.add(g[0] * 10000 + g[1])) shapes.add(asp)
        }
        // Corners given by hand: slide them wide on the nominal shape first, then sweep the shapes with the light search.
        val lead = if (close) 0.0 else 0.4
        var begin = start
        if (!close) {
            val wide = refineCorners(px, w, h, start, aspect, { p -> onProgress?.invoke(p * lead) }, cancelled, 30 to 3, listOf(Triple(40, 4, 1), Triple(18, 3, 2)), lastPass = false)
            if (cancelled()) return wide
            begin = wide.corners
        }
        val coarseStages = listOf(Triple(16, 4, 1), Triple(6, 2, 1))
        val translate = 12 to 3
        var best: Aligned? = null
        for ((i, asp) in shapes.withIndex()) {
            val r = refineCorners(px, w, h, begin, asp, { p -> onProgress?.invoke(lead + (i + p) / shapes.size * (0.6 - lead)) }, cancelled, translate, coarseStages, lastPass = false)
            if (best == null || r.z > best.z) best = r
            if (cancelled()) return best
        }
        val b = best!!
        return refineCorners(px, w, h, b.corners, b.aspect, { p -> onProgress?.invoke(0.6 + p * 0.4) }, cancelled, null, listOf(Triple(8, 2, 1), Triple(3, 1, 1)), lastPass = true)
    }

    /** Reads a photo of a screen or a print. [corners] are TL, TR, BR, BL in picture pixels (about 1% off is fine). */
    fun readPerspective(
        px: IntArray, w: Int, h: Int, corners: Array<DoubleArray>,
        onProgress: ((Double) -> Unit)? = null, cancelled: () -> Boolean = { false }, snap: Boolean = true, refine: Boolean = true, aspectHint: Double? = null,
    ): MarkReadResult? {
        val aspect = aspectHint ?: pickAspect(corners)
        val snapped = if (snap) snapCorners(px, w, h, corners) else null
        val ref = if (!refine) Aligned(snapped ?: corners, 0.0, aspect) else {
            // Edges found: a light search around them. If the pattern does not line up (a wrong edge was latched onto,
            // or no outline), fall back to the wide search around the corners as given.
            var r: Aligned? = null
            if (snapped != null) {
                r = alignAcrossShapes(px, w, h, snapped, aspect, true, { p -> onProgress?.invoke(p * 0.45) }, cancelled)
                if (cancelled() || r.z >= ALIGN_OK_Z) return finishPerspective(px, w, h, r, aspect)
            }
            val wide = alignAcrossShapes(px, w, h, corners, aspect, false, { p -> onProgress?.invoke((if (snapped != null) 0.45 else 0.0) + p * (if (snapped != null) 0.55 else 1.0)) }, cancelled)
            if (r == null || wide.z > r.z) wide else r
        }
        if (cancelled()) return null
        return finishPerspective(px, w, h, ref, aspect)
    }

    private const val ALIGN_OK_Z = 8.0

    private fun finishPerspective(px: IntArray, w: Int, h: Int, ref: Aligned, aspect: Double): MarkReadResult? {
        val long2 = 1600
        val rw = if (aspect >= 1) long2 else Math.round(long2 * aspect).toInt()
        val rh = if (aspect >= 1) Math.round(long2 / aspect).toInt() else long2
        val hm = solveHomography(rectCorners(rw, rh), ref.corners) ?: return null
        // The original photo's exact shape is not exactly 4:3 (or 16:9 ...): its tile grid can be one tile different.
        // Try the neighbouring shapes and keep the best read.
        var best: MarkReadResult? = null
        var bestRank = -1.0
        val seen = HashSet<Long>()
        for (k in -6..6) {
            val asp = aspect * (1 + 0.003 * k)
            val g1 = gridFromAspect(asp, L1.ncells); val g2 = gridFromAspect(asp, L2.ncells)
            if (!seen.add(((g1[0].toLong() * 1000 + g1[1]) * 1000 + g2[0]) * 1000 + g2[1])) continue
            val st = warpStats(px, w, h, hm, rw, rh, listOf(g1, g2), 1)
            val r1 = decodeLayerMasked(L1, st[0], MarkCodec.N1, MarkCodec::unpackL1)
            val r2 = decodeLayerMasked(L2, st[1], MarkCodec.N2, MarkCodec::unpackL2)
            val status = when {
                r1.data != null -> MarkStatus.OK
                r2.data != null -> MarkStatus.PART
                r1.z > DETECT_Z || r2.z > DETECT_Z -> MarkStatus.DAMAGED
                else -> MarkStatus.NONE
            }
            val cur = MarkReadResult(status, r1.data, r2.data, r1.z, r2.z, null, PerspectiveInfo(aspect, ref.corners.map { it.copyOf() }, ref.z))
            val rank = (3 - status.ordinal) * 1000.0 + max(cur.z1, cur.z2)
            if (rank > bestRank) { best = cur; bestRank = rank }
            if (status == MarkStatus.OK) break
        }
        return best
    }

    /**
     * A first guess at the four corners of a bright picture on a dark surround (a monitor in a dim room).
     * Fragile on dark pictures: only a starting point for the user to drag.
     */
    fun autoCorners(px: IntArray, w: Int, h: Int): Array<DoubleArray>? {
        val sw = 160; val sh = max(8, Math.round(160.0 * h / w).toInt())
        val g = DoubleArray(sw * sh)
        for (y in 0 until sh) for (x in 0 until sw) {
            val xx = min(w - 1, Math.round((x + 0.5) * w / sw).toInt()); val yy = min(h - 1, Math.round((y + 0.5) * h / sh).toInt())
            val p = px[yy * w + xx]
            g[y * sw + x] = 0.299 * ((p shr 16) and 255) + 0.587 * ((p shr 8) and 255) + 0.114 * (p and 255)
        }
        val hist = DoubleArray(256)
        for (v in g) hist[min(255, v.toInt())]++
        val total = g.size.toDouble(); var sumAll = 0.0
        for (t in 0 until 256) sumAll += t * hist[t]
        var wB = 0.0; var sumB = 0.0; var bestVar = -1.0; var thr = 128
        for (t in 0 until 256) {
            wB += hist[t]; if (wB == 0.0) continue
            val wF = total - wB; if (wF == 0.0) break
            sumB += t * hist[t]
            val mB = sumB / wB; val mF = (sumAll - sumB) / wF; val v = wB * wF * (mB - mF) * (mB - mF)
            if (v > bestVar) { bestVar = v; thr = t }
        }
        val mask = BooleanArray(sw * sh) { g[it] > thr }
        val comp = IntArray(sw * sh) { -1 }
        var best = -1; var bestSize = 0; var id = 0
        val stack = ArrayDeque<Int>()
        for (k in mask.indices) {
            if (!mask[k] || comp[k] >= 0) continue
            var size = 0; comp[k] = id; stack.addLast(k)
            while (stack.isNotEmpty()) {
                val c = stack.removeLast(); size++
                val cx = c % sw; val cy = c / sw
                for ((ddx, ddy) in listOf(1 to 0, -1 to 0, 0 to 1, 0 to -1)) {
                    val nx = cx + ddx; val ny = cy + ddy
                    if (nx < 0 || ny < 0 || nx >= sw || ny >= sh) continue
                    val n = ny * sw + nx
                    if (mask[n] && comp[n] < 0) { comp[n] = id; stack.addLast(n) }
                }
            }
            if (size > bestSize) { bestSize = size; best = id }
            id++
        }
        if (best < 0 || bestSize < 0.12 * sw * sh) return null
        var tl: IntArray? = null; var tr: IntArray? = null; var br: IntArray? = null; var bl: IntArray? = null
        for (y in 0 until sh) for (x in 0 until sw) {
            if (comp[y * sw + x] != best) continue
            val s = x + y; val d = x - y
            if (tl == null || s < tl[0] + tl[1]) tl = intArrayOf(x, y)
            if (br == null || s > br[0] + br[1]) br = intArrayOf(x, y)
            if (tr == null || d > tr[0] - tr[1]) tr = intArrayOf(x, y)
            if (bl == null || d < bl[0] - bl[1]) bl = intArrayOf(x, y)
        }
        fun f(p: IntArray, dx: Int, dy: Int) = doubleArrayOf((p[0] + dx) * w.toDouble() / sw, (p[1] + dy) * h.toDouble() / sh)
        return arrayOf(f(tl!!, 0, 0), f(tr!!, 1, 0), f(br!!, 1, 1), f(bl!!, 0, 1))
    }
}
