package com.vgp.markengine

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import java.io.ByteArrayOutputStream
import java.io.File

/** Row access to an Android bitmap (must be ARGB_8888; mutable to write). */
internal class BitmapPixels(private val bitmap: Bitmap) : PixelBuffer {
    override val width get() = bitmap.width
    override val height get() = bitmap.height
    override fun readRow(y: Int, out: IntArray) = bitmap.getPixels(out, 0, bitmap.width, 0, y, bitmap.width, 1)
    override fun writeRow(y: Int, row: IntArray) = bitmap.setPixels(row, 0, bitmap.width, 0, y, bitmap.width, 1)
}

/** All pixels of a bitmap in one array (ARGB), as [InvisibleMark.readPerspective] and [InvisibleMark.snapCorners] want them. */
fun Bitmap.toPixelArray(): IntArray {
    val px = IntArray(width * height)
    getPixels(px, 0, width, 0, 0, width, height)
    return px
}

/** What [InvisibleMark.read] should try, beyond reading the picture as it comes. */
data class ReadOptions(
    /** Also try the other three quarter turns when the upright read fails (cheap). */
    val tryTurns: Boolean = true,
    /** Also look for a plain crop of the original frame (a second or two more). */
    val searchCrops: Boolean = false,
)

/** [result] plus how it was found. */
data class ReadReport(
    val result: MarkReadResult,
    /** 0, 90, 180 or 270: the turn that was needed to read it. */
    val turnedDegrees: Int,
    val usedCropSearch: Boolean,
    val millis: Long,
)

/** What [InvisibleMark.mark] did. */
data class WriteReport(
    /** Strength finally used (1.0 normal, up to 1.9 when the self-test said a chat app would damage a weaker mark). */
    val strength: Double,
    val selfTestMillis: Long,
    val embedMillis: Long,
    /** Things the engine had to change in the record, e.g. a time it cannot store. Empty when all is as given. */
    val notes: List<String> = emptyList(),
)

/** A marked picture as JPEG bytes (see [InvisibleMark.markToJpeg]). */
class MarkedJpeg(val bytes: ByteArray, val report: WriteReport)

/**
 * THE public face of the engine, and the only thing an app needs to call. There is no UI, no permission, no file
 * dialog, no camera in here: the app owns all of that and hands pictures in and takes results out.
 *
 * Everything is blocking and CPU heavy: call from a background thread (a coroutine on Dispatchers.Default is fine).
 * Full contract and integration steps: ENGINE.md next to this module.
 */
object InvisibleMark {
    /** Bumped when the engine's behaviour changes. [FORMAT] is bumped when marks written by older versions cannot be read. */
    const val ENGINE_VERSION = "1.1.0"
    const val FORMAT = 1

    /** Pictures with a shorter long edge than this are not worth marking or reading. */
    const val MIN_EDGE = 64

    /** First moment a mark's clock can hold (2026-01-01 00:00:00 UTC) and the last (about 17 years later), in unix seconds. */
    const val TIME_MIN = 1767225600L
    const val TIME_MAX = TIME_MIN + (1L shl 29) - 1

    // ------------------------------------------------------------------ writing

    /**
     * Writes the mark into [bitmap] in place. [bitmap] must be mutable ARGB_8888.
     *
     * With [selfTest] a scaled-down copy is squeezed like a chat app does (1600 px, JPEG 70) and read back, and the
     * mark is written stronger if it would not survive (about half a second more on a 12 MP photo).
     *
     * Returns null when the mark could not be written; the bitmap is then untouched or partly marked, so keep the
     * original or mark a copy. A failure here must never cost the photo itself.
     * A time outside [TIME_MIN]..[TIME_MAX] cannot be stored: it is left out and [WriteReport.notes] says so.
     */
    fun mark(bitmap: Bitmap, record: MarkRecord, selfTest: Boolean = true): WriteReport? = try {
        require(bitmap.isMutable && bitmap.config == Bitmap.Config.ARGB_8888) { "bitmap must be mutable ARGB_8888" }
        require(maxOf(bitmap.width, bitmap.height) >= MIN_EDGE) { "bitmap too small" }
        val notes = mutableListOf<String>()
        val rec = sanitize(record, notes)
        val t0 = System.nanoTime()
        var strength = StrengthPlan.STEPS.first()
        if (selfTest) strength = StrengthPlan.pick { s -> survivesChatApp(bitmap, rec, s) }
        val t1 = System.nanoTime()
        MarkEngine.embed(BitmapPixels(bitmap), rec, strength)
        val t2 = System.nanoTime()
        WriteReport(strength, (t1 - t0) / 1_000_000, (t2 - t1) / 1_000_000, notes)
    } catch (t: Throwable) {
        null
    }

    /** A marked copy of [source] (which stays untouched), or null when it cannot be made. The caller recycles the copy. */
    fun markedCopy(source: Bitmap, record: MarkRecord, selfTest: Boolean = true): Bitmap? = try {
        source.copy(Bitmap.Config.ARGB_8888, true)?.also {
            if (mark(it, record, selfTest) == null) { it.recycle(); return null }
        }
    } catch (oom: OutOfMemoryError) {
        null
    }

    /**
     * Marks a copy of [source] and encodes it as JPEG ([quality] 90 or more is advised). [source] is untouched.
     * The JPEG carries no EXIF: write your own (see [MarkExif]) with your EXIF library afterwards.
     */
    fun markToJpeg(source: Bitmap, record: MarkRecord, quality: Int = 95, selfTest: Boolean = true): MarkedJpeg? {
        val copy = try { source.copy(Bitmap.Config.ARGB_8888, true) } catch (oom: OutOfMemoryError) { null } ?: return null
        return try {
            val report = mark(copy, record, selfTest) ?: return null
            MarkedJpeg(ByteArrayOutputStream().use { copy.compress(Bitmap.CompressFormat.JPEG, quality, it); it.toByteArray() }, report)
        } finally { copy.recycle() }
    }

    /**
     * The 10-letter ID a record's mark carries (derived from the record, never stored in the pixels). Two photos marked
     * with the same record share an ID; handy as a key in a log or a database.
     */
    fun markId(record: MarkRecord): String = MarkCodec.idFor(record)

    // ------------------------------------------------------------------ reading a picture

    /**
     * Reads a picture. Safe on unmarked pictures: the status is [MarkStatus.NONE], never a wrong record (CRC protected).
     * Give it a picture whose long edge is at least about 1600 px when you have it (see [decodeForRead]).
     */
    fun read(bitmap: Bitmap, options: ReadOptions = ReadOptions()): ReadReport {
        val t0 = System.nanoTime()
        var best = MarkEngine.read(BitmapPixels(bitmap))
        var turned = 0
        var crops = false
        if (best.status != MarkStatus.OK && options.searchCrops) {
            crops = true
            MarkEngine.readCropped(BitmapPixels(bitmap))?.let { if (rank(it) > rank(best)) best = it }
        }
        if (best.status != MarkStatus.OK && options.tryTurns) {
            for (deg in intArrayOf(90, 270, 180)) {
                val t = rotate(bitmap, deg) ?: continue
                val r = try { MarkEngine.read(BitmapPixels(t)) } finally { if (t !== bitmap) t.recycle() }
                if (rank(r) > rank(best)) { best = r; turned = deg }
                if (best.status == MarkStatus.OK) break
            }
        }
        return ReadReport(best, turned, crops, (System.nanoTime() - t0) / 1_000_000)
    }

    /** Reads a picture from a content or file [uri] (gallery, file picker, share target). Null when it is not a picture. */
    fun read(context: Context, uri: Uri, options: ReadOptions = ReadOptions()): ReadReport? {
        val bmp = decodeForRead(context, uri) ?: return null
        return try { read(bmp, options) } finally { bmp.recycle() }
    }

    /** Reads a picture file. Null when it is not a picture. */
    fun read(file: File, options: ReadOptions = ReadOptions()): ReadReport? {
        val bmp = decodeForRead(file.path) ?: return null
        return try { read(bmp, options) } finally { bmp.recycle() }
    }

    /** Reads a picture held in memory (JPEG, PNG, WebP bytes). Null when it is not a picture. */
    fun read(bytes: ByteArray, options: ReadOptions = ReadOptions()): ReadReport? {
        val bmp = decodeForRead(bytes) ?: return null
        return try { read(bmp, options) } finally { bmp.recycle() }
    }

    // ------------------------------------------------------------------ reading a photo of a screen or a print

    /**
     * Moves four hand-tapped corners onto the picture's outline (the dark surround against the picture), which is far
     * more exact than a finger. Corners are TL, TR, BR, BL in the coordinates of [pixels]. Null when no clean outline is
     * found; then use the tapped corners as they are ([readPerspective] also does this itself).
     */
    fun snapCorners(pixels: IntArray, width: Int, height: Int, corners: Array<DoubleArray>): Array<DoubleArray>? =
        MarkEngine.snapCorners(pixels, width, height, corners)

    /**
     * Reads a photo of a screen or a print. [corners] are the four corners of the PICTURE inside [pixels]
     * (top-left, top-right, bottom-right, bottom-left); a few percent off is fine, the engine snaps them to the outline
     * and then lines the hidden pattern up by itself. [pixels] come from [toPixelArray] of a bitmap whose long edge is
     * about 2000 px (see [decodeForRead] with minEdge = 2000), turned upright.
     *
     * Takes 10 to 60 s on a phone (all cores are used): run it on a background thread, show [onProgress] (0..1) and
     * poll [cancelled] to let the user stop it. Null when cancelled or when no fit was possible.
     */
    fun readPerspective(
        pixels: IntArray, width: Int, height: Int, corners: Array<DoubleArray>,
        onProgress: ((Double) -> Unit)? = null, cancelled: () -> Boolean = { false },
    ): MarkReadResult? = MarkEngine.readPerspective(pixels, width, height, corners, onProgress, cancelled)

    /** A first guess for the corners of a bright picture on a dark surround. Only a starting point for the user to correct. */
    fun autoCorners(pixels: IntArray, width: Int, height: Int): Array<DoubleArray>? = MarkEngine.autoCorners(pixels, width, height)

    // ------------------------------------------------------------------ helpers for the app

    /**
     * Decodes [uri] with its long edge as close to [minEdge] as possible without going under it (halving only),
     * ARGB_8888, immutable. The EXIF turn is NOT applied ([read] tries the turns itself; for [readPerspective] and for
     * showing the picture to the user, turn it upright yourself). Null when it is not a picture.
     */
    fun decodeForRead(context: Context, uri: Uri, minEdge: Int = 1600): Bitmap? {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        context.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
        if (bounds.outWidth <= 0) return null
        val opts = BitmapFactory.Options().apply { inPreferredConfig = Bitmap.Config.ARGB_8888; inSampleSize = sampleFor(bounds, minEdge) }
        return context.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, opts) }
    }

    fun decodeForRead(path: String, minEdge: Int = 1600): Bitmap? {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(path, bounds)
        if (bounds.outWidth <= 0) return null
        return BitmapFactory.decodeFile(path, BitmapFactory.Options().apply { inPreferredConfig = Bitmap.Config.ARGB_8888; inSampleSize = sampleFor(bounds, minEdge) })
    }

    fun decodeForRead(bytes: ByteArray, minEdge: Int = 1600): Bitmap? {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
        if (bounds.outWidth <= 0) return null
        return BitmapFactory.decodeByteArray(bytes, 0, bytes.size, BitmapFactory.Options().apply { inPreferredConfig = Bitmap.Config.ARGB_8888; inSampleSize = sampleFor(bounds, minEdge) })
    }

    /** For testing: squeezes [bitmap] the way a chat app would (scale to [longEdge], JPEG [quality]) and returns the result. */
    fun squeeze(bitmap: Bitmap, longEdge: Int, quality: Int): Bitmap? = try {
        val scale = minOf(1.0, longEdge.toDouble() / maxOf(bitmap.width, bitmap.height))
        val w = (bitmap.width * scale).toInt().coerceAtLeast(MIN_EDGE)
        val h = (bitmap.height * scale).toInt().coerceAtLeast(MIN_EDGE)
        val scaled = Bitmap.createScaledBitmap(bitmap, w, h, true)
        val bytes = ByteArrayOutputStream().use { scaled.compress(Bitmap.CompressFormat.JPEG, quality, it); it.toByteArray() }
        if (scaled !== bitmap) scaled.recycle()
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, BitmapFactory.Options().apply { inPreferredConfig = Bitmap.Config.ARGB_8888 })
    } catch (t: Throwable) { null }

    // ------------------------------------------------------------------ inside

    private fun sampleFor(bounds: BitmapFactory.Options, minEdge: Int): Int {
        var s = 1
        val longEdge = maxOf(bounds.outWidth, bounds.outHeight)
        while (longEdge / (s * 2) >= minEdge) s *= 2
        return s
    }

    private fun sanitize(r: MarkRecord, notes: MutableList<String>): MarkRecord {
        var rec = r
        val t = rec.timeSeconds
        if (t != null && (t < TIME_MIN || t > TIME_MAX)) {
            notes += "time $t is outside what a mark can hold (2026-01-01 .. about 2043) and was left out"
            rec = rec.copy(timeSeconds = null, tenth = 0)
        }
        val lat = rec.latitude; val lon = rec.longitude
        if ((lat != null && (lat < -90 || lat > 90)) || (lon != null && (lon < -180 || lon > 180))) {
            notes += "location is not a valid latitude/longitude and was left out"
            rec = rec.copy(latitude = null, longitude = null)
        }
        return rec
    }

    private fun survivesChatApp(bitmap: Bitmap, record: MarkRecord, strength: Double): Boolean = try {
        val scale = minOf(1.0, 1600.0 / maxOf(bitmap.width, bitmap.height))
        val w = (bitmap.width * scale).toInt().coerceAtLeast(MIN_EDGE)
        val h = (bitmap.height * scale).toInt().coerceAtLeast(MIN_EDGE)
        val scaled = Bitmap.createScaledBitmap(bitmap, w, h, true)
        val work = scaled.copy(Bitmap.Config.ARGB_8888, true)
        if (scaled !== bitmap) scaled.recycle()
        try {
            MarkEngine.embed(BitmapPixels(work), record, strength)
            val bytes = ByteArrayOutputStream().use { work.compress(Bitmap.CompressFormat.JPEG, 70, it); it.toByteArray() }
            val back = BitmapFactory.decodeByteArray(bytes, 0, bytes.size, BitmapFactory.Options().apply { inPreferredConfig = Bitmap.Config.ARGB_8888 })
            try { back != null && MarkEngine.read(BitmapPixels(back)).status == MarkStatus.OK } finally { back?.recycle() }
        } finally { work.recycle() }
    } catch (t: Throwable) {
        true // a failed test must not make the mark stronger than necessary
    }

    private fun rank(r: MarkReadResult) = when (r.status) {
        MarkStatus.OK -> 3; MarkStatus.PART -> 2; MarkStatus.DAMAGED -> 1; MarkStatus.NONE -> 0
    }

    private fun rotate(src: Bitmap, degrees: Int): Bitmap? = runCatching {
        Bitmap.createBitmap(src, 0, 0, src.width, src.height, Matrix().apply { postRotate(degrees.toFloat()) }, true)
    }.getOrNull()
}

/** Which strengths to try, weakest first. Pure, so it can be unit tested without a bitmap. */
internal object StrengthPlan {
    val STEPS = doubleArrayOf(1.0, 1.4, 1.9)
    val MAX = STEPS.last()

    /** The first strength for which [survives] is true; the strongest one when none is. */
    fun pick(survives: (Double) -> Boolean): Double {
        for (s in STEPS) if (survives(s)) return s
        return MAX
    }
}
