package com.vgp.markengine

import java.util.TimeZone
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class MarkExifTest {
    private val ist = TimeZone.getTimeZone("Asia/Kolkata")

    @Test
    fun offsetStringsParse() {
        assertEquals(19_800_000, MarkExif.parseOffsetMillis("+05:30"))
        assertEquals(-18_000_000, MarkExif.parseOffsetMillis("-05:00"))
        assertNull(MarkExif.parseOffsetMillis("IST"))
        assertNull(MarkExif.parseOffsetMillis(null))
    }

    @Test
    fun localTimeWithOffsetIsTheBestSource() {
        // 2026-10-07 16:58:42 +05:30 = 11:28:42 UTC
        val (ms, basis) = MarkExif.captureTime("2026:10:07 16:58:42", "+05:30", "4", null, null, ist)!!
        assertEquals(MarkExif.TimeBasis.EXIF_OFFSET, basis)
        assertEquals(1791372522_400L, ms)
    }

    @Test
    fun gpsDateAndTimeAreUsedWhenThereIsNoOffset() {
        val (ms, basis) = MarkExif.captureTime(null, null, null, "2026:10:07", "11/1,28/1,42/1", ist)!!
        assertEquals(MarkExif.TimeBasis.GPS_UTC, basis)
        assertEquals(1791372522_000L, ms)
    }

    @Test
    fun plainLocalTimeIsAnAssumptionAndSaysSo() {
        val (ms, basis) = MarkExif.captureTime("2026:10:07 16:58:42", null, null, null, null, ist)!!
        assertEquals(MarkExif.TimeBasis.ASSUMED_ZONE, basis)
        assertEquals(1791372522_000L, ms)
    }

    @Test
    fun noTimeAtAllGivesNull() {
        assertNull(MarkExif.captureTime(null, null, null, null, null, ist))
        assertNull(MarkExif.captureTime("garbage", "+05:30", null, null, null, ist))
    }

    @Test
    fun recordSplitsSecondsAndTenths() {
        val r = MarkExif.recordFor(1.0, 2.0, 3.0, 1791372522_700L, true)
        assertEquals(1791372522L, r.timeSeconds)
        assertEquals(7, r.tenth)
        assertEquals(true, r.manual)
        val none = MarkExif.recordFor(null, null, null, null, true)
        assertNull(none.timeSeconds); assertEquals(0, none.tenth)
    }

    @Test
    fun restoredExifTextIsInUtcAndRationalForm() {
        val t = 1791372522L
        assertEquals("2026:10:07 11:28:42", MarkExif.exifDateTimeUtc(t))
        assertEquals("2026:10:07", MarkExif.exifGpsDate(t))
        assertEquals("11/1,28/1,42/1", MarkExif.exifGpsTime(t))
    }

    @Test
    fun distanceIsSensible() {
        val d = MarkExif.distanceMeters(40.0, -83.0, 40.001, -83.0)
        assertEquals(111.3, d, 1.0)
        assertNotNull(d)
    }

    @Test
    fun aFullRecordSurvivesTheRoundTripThroughTheMarkPayload() {
        val rec = MarkExif.recordFor(40.18324, -83.08501, 253.4, 1791372522_700L, false)
        val back = MarkCodec.unpackL1(MarkCodec.packL1(rec))!!
        assertEquals(40.18324, back.latitude!!, 2e-5)
        assertEquals(253, back.altitudeMeters)
        assertEquals(1791372522L, back.timeSeconds)
        assertEquals(7, back.tenth)
    }
}
