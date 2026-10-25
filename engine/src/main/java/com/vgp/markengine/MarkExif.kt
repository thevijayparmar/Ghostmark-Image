package com.vgp.markengine

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * Pure helpers between EXIF text and the mark's numbers (no Android classes, no EXIF library): the app reads and
 * writes its own EXIF with whatever library it uses and uses these to convert. Typical uses:
 *  - an existing photo is to be marked: [captureTime] and [recordFor] turn its EXIF values into a MarkRecord;
 *  - a mark was read from a photo whose EXIF was stripped: [exifDateTimeUtc], [exifGpsDate], [exifGpsTime] give the EXIF text to write back.
 */
object MarkExif {
    private fun fmt(pattern: String, zone: TimeZone) =
        SimpleDateFormat(pattern, Locale.US).apply { timeZone = zone; isLenient = false }

    private val utc = TimeZone.getTimeZone("UTC")

    /** "+05:30" to milliseconds, or null. */
    fun parseOffsetMillis(offset: String?): Int? {
        val m = Regex("""^([+-])(\d{2}):(\d{2})$""").matchEntire(offset?.trim() ?: return null) ?: return null
        val minutes = m.groupValues[2].toInt() * 60 + m.groupValues[3].toInt()
        return (if (m.groupValues[1] == "-") -minutes else minutes) * 60_000
    }

    /**
     * Capture time in UTC milliseconds from whatever a photo's EXIF offers, best source first:
     * local time with its UTC offset, then the GPS date and time (always UTC), then local time
     * read in [fallbackZone] (an assumption, reported by [TimeBasis.ASSUMED_ZONE]).
     */
    fun captureTime(
        dateTimeOriginal: String?,
        offsetTime: String?,
        subSec: String?,
        gpsDate: String?,
        gpsTimeRationals: String?,
        fallbackZone: TimeZone,
    ): Pair<Long, TimeBasis>? {
        val subMillis = subSec?.trim()?.takeIf { it.isNotEmpty() && it.all(Char::isDigit) }
            ?.let { (("0." + it).toDouble() * 1000).toLong() } ?: 0L
        val local = dateTimeOriginal?.trim()?.takeIf { it.isNotEmpty() }
        parseOffsetMillis(offsetTime)?.let { off ->
            if (local != null) {
                val zone = java.util.SimpleTimeZone(off, "offset")
                runCatching { fmt("yyyy:MM:dd HH:mm:ss", zone).parse(local)!!.time + subMillis }
                    .getOrNull()?.let { return it to TimeBasis.EXIF_OFFSET }
            }
        }
        if (gpsDate != null && gpsTimeRationals != null) {
            val hms = gpsTimeRationals.split(",").mapNotNull { part ->
                val nd = part.trim().split("/")
                if (nd.size == 2 && nd[1].toDoubleOrNull() != null && nd[1].toDouble() != 0.0) nd[0].toDouble() / nd[1].toDouble() else null
            }
            if (hms.size == 3) {
                runCatching {
                    val base = fmt("yyyy:MM:dd", utc).parse(gpsDate.trim())!!.time
                    base + ((hms[0] * 3600 + hms[1] * 60 + hms[2]) * 1000).toLong() + subMillis
                }.getOrNull()?.let { return it to TimeBasis.GPS_UTC }
            }
        }
        if (local != null) {
            runCatching { fmt("yyyy:MM:dd HH:mm:ss", fallbackZone).parse(local)!!.time + subMillis }
                .getOrNull()?.let { return it to TimeBasis.ASSUMED_ZONE }
        }
        return null
    }

    enum class TimeBasis { EXIF_OFFSET, GPS_UTC, ASSUMED_ZONE }

    /** The record to write for an existing photo's EXIF values. */
    fun recordFor(lat: Double?, lon: Double?, alt: Double?, utcMillis: Long?, manual: Boolean) = MarkRecord(
        latitude = lat, longitude = lon, altitudeMeters = alt,
        timeSeconds = utcMillis?.let { Math.floorDiv(it, 1000L) },
        tenth = utcMillis?.let { (Math.floorMod(it, 1000L) / 100).toInt() } ?: 0,
        manual = manual,
    )

    // ---- the other direction: text for the restored EXIF ----
    fun exifDateTimeUtc(timeSeconds: Long): String = fmt("yyyy:MM:dd HH:mm:ss", utc).format(Date(timeSeconds * 1000))
    fun exifGpsDate(timeSeconds: Long): String = fmt("yyyy:MM:dd", utc).format(Date(timeSeconds * 1000))

    /** GPSTimeStamp as the three rationals ExifInterface expects. */
    fun exifGpsTime(timeSeconds: Long): String {
        val hms = fmt("HH:mm:ss", utc).format(Date(timeSeconds * 1000)).split(":")
        return hms.joinToString(",") { "${it.toInt()}/1" }
    }

    fun distanceMeters(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val dLat = (lat1 - lat2) * 111320.0
        val dLon = (lon1 - lon2) * 111320.0 * Math.cos(Math.toRadians((lat1 + lat2) / 2))
        return Math.sqrt(dLat * dLat + dLon * dLon)
    }
}
