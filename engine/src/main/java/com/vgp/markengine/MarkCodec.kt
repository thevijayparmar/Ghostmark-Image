package com.vgp.markengine

import java.math.BigInteger
import java.security.MessageDigest
import kotlin.math.floor
import kotlin.math.pow
import kotlin.math.roundToLong

/**
 * Bits, check codes, payloads and the repair code of the invisible mark.
 *
 * Format: `watermark/WATERMARK-SPEC.md`. `watermark/wm-engine.js` is the reference; this file
 * must stay bit-for-bit compatible with it (see `MarkCompatTest`).
 */

/** What layer 1 carries. A null field means "was not known when the photo was taken". */
data class MarkRecord(
    val latitude: Double?,
    val longitude: Double?,
    val altitudeMeters: Double?,
    /** UTC seconds since 1970. */
    val timeSeconds: Long?,
    /** Tenths of a second, 0 to 9. */
    val tenth: Int = 0,
    /** True when the location was added by hand to an existing photo rather than captured live. */
    val manual: Boolean = false,
)

/** What layer 1 gave back. [id] is derived from the other fields and is never stored in the pixels. */
data class Layer1Data(
    val id: String,
    val tenth: Int,
    val manual: Boolean,
    val latitude: Double?,
    val longitude: Double?,
    val altitudeMeters: Int?,
    val timeSeconds: Long?,
)

data class Layer2Data(val latitude: Double?, val longitude: Double?)

internal object MarkCodec {
    const val EPOCH = 1767225600L // 2026-01-01T00:00:00Z
    const val N1 = 118
    const val N2 = 60

    fun toBits(value: Long, n: Int): IntArray = IntArray(n) { ((value shr (n - 1 - it)) and 1L).toInt() }

    fun fromBits(b: IntArray, from: Int = 0, to: Int = b.size): Long {
        var v = 0L
        for (i in from until to) v = v * 2 + b[i]
        return v
    }

    /** CRC-16/CCITT-FALSE over the bits, zero padded to a whole byte. */
    fun crc16(bits: IntArray, length: Int = bits.size): Int {
        val padded = IntArray(((length + 7) / 8) * 8)
        for (i in 0 until length) padded[i] = bits[i]
        var crc = 0xFFFF
        var i = 0
        while (i < padded.size) {
            var byte = 0
            for (j in 0 until 8) byte = (byte shl 1) or padded[i + j]
            crc = crc xor (byte shl 8)
            for (k in 0 until 8) {
                crc = if (crc and 0x8000 != 0) ((crc shl 1) xor 0x1021) and 0xFFFF else (crc shl 1) and 0xFFFF
            }
            i += 8
        }
        return crc
    }

    fun makeId(body: IntArray): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(ByteArray(body.size) { body[it].toByte() })
        var n = BigInteger(1, digest.copyOfRange(0, 8))
        val sb = StringBuilder()
        val twentySix = BigInteger.valueOf(26)
        repeat(10) {
            sb.append(('A'.code + n.mod(twentySix).toInt()).toChar())
            n = n.divide(twentySix)
        }
        return sb.toString()
    }

    /** The 10-letter ID a record's mark will carry (derived, never stored in the pixels). */
    fun idFor(r: MarkRecord): String {
        val bits = packL1(r)
        return makeId(bits.copyOfRange(0, bits.size - 16))
    }

    private fun scaled(value: Double, offset: Double, span: Double, bits: Int): Long =
        ((value + offset) / span * (2.0.pow(bits) - 1)).roundHalfUp()

    private fun Double.roundHalfUp(): Long = floor(this + 0.5).toLong()

    fun packL1(r: MarkRecord): IntArray {
        val hasLoc = r.latitude != null && r.longitude != null
        val hasAlt = r.altitudeMeters != null
        val hasT = r.timeSeconds != null
        val la = if (hasLoc) scaled(r.latitude, 90.0, 180.0, 25) else 0L
        val lo = if (hasLoc) scaled(r.longitude, 180.0, 360.0, 26) else 0L
        val al = if (hasAlt) (r.altitudeMeters.roundHalfUp() + 500).coerceIn(0, 16383) else 0L
        val tt = if (hasT) (r.timeSeconds - EPOCH).coerceIn(0, (1L shl 29) - 1) else 0L
        val tenth = r.tenth.coerceIn(0, 9).toLong()
        val parts = listOf(
            intArrayOf(if (hasLoc) 1 else 0, if (hasAlt) 1 else 0, if (hasT) 1 else 0),
            toBits(la, 25), toBits(lo, 26), toBits(al, 14), toBits(tt, 29), toBits(tenth, 4),
            intArrayOf(if (r.manual) 1 else 0),
        )
        val body = parts.fold(IntArray(0)) { acc, p -> acc + p }
        return body + toBits(crc16(body).toLong(), 16)
    }

    fun unpackL1(bits: IntArray): Layer1Data? {
        val body = bits.copyOfRange(0, bits.size - 16)
        if (crc16(body) != fromBits(bits, bits.size - 16, bits.size).toInt()) return null
        var p = 3
        fun take(n: Int): Long { val v = fromBits(body, p, p + n); p += n; return v }
        val la = take(25); val lo = take(26); val al = take(14); val tt = take(29); val tenth = take(4); val man = take(1)
        return Layer1Data(
            id = makeId(body),
            tenth = tenth.toInt(),
            manual = man == 1L,
            latitude = if (body[0] == 1) la / (2.0.pow(25) - 1) * 180 - 90 else null,
            longitude = if (body[0] == 1) lo / (2.0.pow(26) - 1) * 360 - 180 else null,
            altitudeMeters = if (body[1] == 1) (al - 500).toInt() else null,
            timeSeconds = if (body[2] == 1) EPOCH + tt else null,
        )
    }

    fun packL2(r: MarkRecord): IntArray {
        val hasLoc = r.latitude != null && r.longitude != null
        val la = if (hasLoc) scaled(r.latitude, 90.0, 180.0, 21) else 0L
        val lo = if (hasLoc) scaled(r.longitude, 180.0, 360.0, 22) else 0L
        val body = intArrayOf(if (hasLoc) 1 else 0) + toBits(la, 21) + toBits(lo, 22)
        return body + toBits(crc16(body).toLong(), 16)
    }

    fun unpackL2(bits: IntArray): Layer2Data? {
        val body = bits.copyOfRange(0, bits.size - 16)
        if (crc16(body) != fromBits(bits, bits.size - 16, bits.size).toInt()) return null
        val la = fromBits(body, 1, 22); val lo = fromBits(body, 22, 44)
        return Layer2Data(
            latitude = if (body[0] == 1) la / (2.0.pow(21) - 1) * 180 - 90 else null,
            longitude = if (body[0] == 1) lo / (2.0.pow(22) - 1) * 360 - 180 else null,
        )
    }

    // ---- convolutional code, K=7, rate 1/2, generators 133 and 171 octal ----
    private const val G0 = 0x5B
    private const val G1 = 0x79
    private val out0 = IntArray(128)
    private val out1 = IntArray(128)

    init {
        for (s in 0 until 64) for (u in 0 until 2) {
            val reg = (u shl 6) or s
            out0[reg] = Integer.bitCount(reg and G0) and 1
            out1[reg] = Integer.bitCount(reg and G1) and 1
        }
    }

    fun convEncode(bits: IntArray): IntArray {
        val seq = bits + IntArray(6)
        val out = IntArray(seq.size * 2)
        var st = 0
        for (i in seq.indices) {
            val reg = (seq[i] shl 6) or st
            out[2 * i] = out0[reg]; out[2 * i + 1] = out1[reg]
            st = reg shr 1
        }
        return out
    }

    /** [soft]: positive favours 1. Returns the information bits, tail removed. */
    fun viterbi(soft: DoubleArray): IntArray {
        val m = soft.size / 2
        var pm = DoubleArray(64) { -1e300 }; pm[0] = 0.0
        var nm = DoubleArray(64)
        val back = ByteArray(m * 64)
        for (t in 0 until m) {
            val s0 = soft[2 * t]; val s1 = soft[2 * t + 1]
            for (ns in 0 until 64) {
                val uu = ns shr 5; val p0 = (ns shl 1) and 63; val p1 = p0 or 1
                val r0 = (uu shl 6) or p0; val r1 = (uu shl 6) or p1
                val c0 = pm[p0] + (if (out0[r0] == 1) s0 else -s0) + (if (out1[r0] == 1) s1 else -s1)
                val c1 = pm[p1] + (if (out0[r1] == 1) s0 else -s0) + (if (out1[r1] == 1) s1 else -s1)
                if (c1 > c0) { nm[ns] = c1; back[t * 64 + ns] = 1 } else { nm[ns] = c0; back[t * 64 + ns] = 0 }
            }
            val tmp = pm; pm = nm; nm = tmp
        }
        var st = 0
        val bits = IntArray(m)
        for (t in m - 1 downTo 0) {
            bits[t] = st shr 5
            st = ((st shl 1) and 63) or back[t * 64 + st].toInt()
        }
        return bits.copyOfRange(0, m - 6)
    }
}
