package com.vgp.markengine

import java.awt.image.BufferedImage
import java.io.ByteArrayOutputStream
import java.io.File
import javax.imageio.IIOImage
import javax.imageio.ImageIO
import javax.imageio.ImageWriteParam
import javax.imageio.stream.MemoryCacheImageOutputStream
import kotlin.math.abs
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

private class ImagePixels(val img: BufferedImage) : PixelBuffer {
    override val width get() = img.width
    override val height get() = img.height
    override fun readRow(y: Int, out: IntArray) { img.getRGB(0, y, img.width, 1, out, 0, img.width) }
    override fun writeRow(y: Int, row: IntArray) { img.setRGB(0, y, img.width, 1, row, 0, img.width) }
}

/** The Kotlin engine must read what the JavaScript reference engine wrote, and agree on every constant. */
class MarkCompatTest {

    private fun fixture(name: String): BufferedImage {
        val f = File("src/test/resources/mark/$name")
        assertTrue("missing fixture ${f.absolutePath}", f.exists())
        return ImageIO.read(f)
    }

    private fun read(name: String) = MarkEngine.read(ImagePixels(fixture(name)))

    @Test
    fun checkCodeAndIdMatchTheReference() {
        // Vectors produced by wm-engine.js (and by the Python prototype).
        val bits = "123456789".toByteArray().flatMap { b -> (7 downTo 0).map { (b.toInt() shr it) and 1 } }.toIntArray()
        assertEquals(0x29B1, MarkCodec.crc16(bits))
        val rec = MarkRecord(40.09, -83.017, 236.0, 1789567247L, 7, false)
        val packed = MarkCodec.packL1(rec)
        assertEquals(118, packed.size)
        val back = MarkCodec.unpackL1(packed)!!
        assertEquals("NHMAQFNJSH", back.id)
        assertEquals(236, back.altitudeMeters)
        assertEquals(1789567247L, back.timeSeconds)
        assertEquals(7, back.tenth)
        assertEquals(false, back.manual)
        val nothing = MarkCodec.unpackL1(MarkCodec.packL1(MarkRecord(null, null, null, null, 3, true)))!!
        assertEquals("KXKYJZMDSB", nothing.id)
        assertNull(nothing.latitude); assertNull(nothing.altitudeMeters); assertNull(nothing.timeSeconds)
        assertEquals(true, nothing.manual)
    }

    @Test
    fun repairCodeMatchesTheReference() {
        val coded = MarkCodec.convEncode(MarkCodec.packL1(MarkRecord(40.09, -83.017, 236.0, 1789567247L, 7, false)))
        assertEquals("1110011001010000001110001000001000011111", coded.take(40).joinToString(""))
        assertEquals(248, coded.size)
        // survives noise
        val rnd = java.util.Random(5)
        val soft = DoubleArray(coded.size) { (if (coded[it] == 1) 1.0 else -1.0) + rnd.nextGaussian() * 0.7 }
        val bits = MarkCodec.viterbi(soft)
        assertEquals(236, MarkCodec.unpackL1(bits)!!.altitudeMeters)
    }

    @Test
    fun readsAWhatsAppSizedPhotoWrittenByTheReferenceEngine() {
        val r = read("photo1_wa1600.jpg")
        assertEquals(MarkStatus.OK, r.status)
        val d = r.layer1!!
        assertEquals(40.18323928, d.latitude!!, 2e-5)
        assertEquals(-83.08500622, d.longitude!!, 2e-5)
        assertEquals(253, d.altitudeMeters)
        assertEquals(1791392322L, d.timeSeconds)
        assertEquals(7, d.tenth)
        assertEquals(false, d.manual)
        assertEquals(10, d.id.length)
        assertNotNull(r.layer2)
        assertEquals(40.18323928, r.layer2!!.latitude!!, 1.2e-4)
        assertTrue("layers must agree", (r.layerDisagreementMeters ?: 999.0) < 30.0)
    }

    @Test
    fun readsThePortraitPhotoToo() {
        val r = read("photo3_wa1600.jpg")
        assertEquals(MarkStatus.OK, r.status)
        assertEquals(253, r.layer1!!.altitudeMeters)
    }

    @Test
    fun readsAnEightHundredPixelCopy() {
        assertEquals(MarkStatus.OK, read("photo1_800.jpg").status)
    }

    @Test
    fun blackAndWhiteKeepsOnlyTheBrightnessLayer() {
        val r = read("photo1_bw.jpg")
        assertEquals(MarkStatus.PART, r.status)
        assertNull(r.layer1)
        assertEquals(40.18323928, r.layer2!!.latitude!!, 1.2e-4)
    }

    @Test
    fun anUnmarkedPhotoIsReportedAsNoMarkNeverAWrongRecord() {
        val r = read("photo1_unmarked.jpg")
        assertEquals(MarkStatus.NONE, r.status)
        assertNull(r.layer1); assertNull(r.layer2)
    }

    @Test
    fun missingFieldsAreReportedAsNotPresentAndManualIsKept() {
        val r = read("photo4_noloc_wa1600.jpg")
        assertEquals(MarkStatus.OK, r.status)
        val d = r.layer1!!
        assertNull(d.latitude); assertNull(d.longitude); assertNull(d.altitudeMeters)
        assertEquals(1791392322L, d.timeSeconds)
        assertEquals(3, d.tenth)
        assertEquals(true, d.manual)
        assertNull(r.layer2!!.latitude)
    }

    // ---- crops: the reader must find the original frame by itself ----

    @Test
    fun aCroppedPhotoIsNotReadByThePlainReaderButTheCropSearchFindsIt() {
        val img = fixture("photo3_crop25_wa1600.jpg")
        assertEquals(MarkStatus.NONE, MarkEngine.read(ImagePixels(img)).status)
        val r = MarkEngine.readCropped(ImagePixels(img))!!
        assertEquals(MarkStatus.OK, r.status)
        assertEquals(253, r.layer1!!.altitudeMeters)
        assertEquals(40.18323928, r.layer1!!.latitude!!, 2e-5)
        assertEquals(1791392322L, r.layer1!!.timeSeconds)
        assertEquals(0.75, r.crop!!.aspect, 1e-9)
        assertEquals(0.864, r.crop!!.widthFraction, 0.01)
        assertEquals(0.067, r.crop!!.left, 0.01)
        assertNotNull(r.layer2)
    }

    @Test
    fun aLeftQuarterCutOffLandscapePhotoIsFound() {
        val r = MarkEngine.readCropped(ImagePixels(fixture("photo4_left25_wa1600.jpg")))!!
        assertEquals(MarkStatus.OK, r.status)
        assertEquals(253, r.layer1!!.altitudeMeters)
        assertEquals(0.25, r.crop!!.left, 0.01)
    }

    @Test
    fun theCropSearchNeverInventsAMarkOnAnUnmarkedPhoto() {
        val r = MarkEngine.readCropped(ImagePixels(fixture("photo1_unmarked.jpg")))
        assertTrue("got ${r?.status}", r == null || r.status == MarkStatus.NONE)
        assertNull(r?.layer1)
    }

    @Test
    fun strengthPlanTriesWeakestFirstAndFallsBackToTheStrongest() {
        assertEquals(1.0, StrengthPlan.pick { true }, 0.0)
        assertEquals(1.4, StrengthPlan.pick { it >= 1.4 }, 0.0)
        assertEquals(1.9, StrengthPlan.pick { false }, 0.0)
    }

    @Test
    fun aStrongerMarkChangesMoreAndStillReads() {
        fun change(strength: Double): Double {
            val img = synthetic(1200, 900)
            val before = BufferedImage(1200, 900, BufferedImage.TYPE_INT_RGB).also { it.graphics.drawImage(img, 0, 0, null) }
            MarkEngine.embed(ImagePixels(img), MarkRecord(1.0, 2.0, 3.0, 1790000000L, 0, false), strength)
            var sum = 0L
            for (y in 0 until 900) for (x in 0 until 1200) {
                val a = before.getRGB(x, y); val b = img.getRGB(x, y)
                for (sh in intArrayOf(16, 8, 0)) sum += abs(((a shr sh) and 255) - ((b shr sh) and 255))
            }
            val r = MarkEngine.read(ImagePixels(img))
            assertEquals(MarkStatus.OK, r.status)
            return sum / (1200.0 * 900 * 3)
        }
        assertTrue(change(1.9) > change(1.0) * 1.5)
    }

    // ---- photos of a screen or a print, read from four tapped corners ----

    private fun tapped(name: String): Array<DoubleArray> {
        val text = File("src/test/resources/mark/$name").readText()
        val part = text.substringAfter("\"tapped\":").substringBefore("\"true\"")
        val nums = Regex("""-?\d+(?:\.\d+)?(?:e-?\d+)?""").findAll(part).map { it.value.toDouble() }.toList()
        assertEquals(8, nums.size)
        return Array(4) { doubleArrayOf(nums[it * 2], nums[it * 2 + 1]) }
    }

    private fun pixels(img: BufferedImage): IntArray = img.getRGB(0, 0, img.width, img.height, null, 0, img.width)

    @Test
    fun aPhotoOfAMonitorIsReadFromFourApproximateCorners() {
        val img = fixture("photo3_screen_monitor_mild.jpg")
        val r = MarkEngine.readPerspective(pixels(img), img.width, img.height, tapped("photo3_screen_monitor_mild.json"))!!
        assertEquals(MarkStatus.OK, r.status)
        assertEquals(253, r.layer1!!.altitudeMeters)
        assertEquals(40.18323928, r.layer1!!.latitude!!, 2e-5)
        assertEquals(0.75, r.perspective!!.aspect, 1e-9)
    }

    @Test
    fun aPhotoOfAPrintAtASteepAngleIsRead() {
        val img = fixture("photo3_screen_print_steep.jpg")
        val r = MarkEngine.readPerspective(pixels(img), img.width, img.height, tapped("photo3_screen_print_steep.json"))!!
        assertEquals(MarkStatus.OK, r.status)
        assertEquals(1791392322L, r.layer1!!.timeSeconds)
    }

    @Test
    fun cornersOnAnUnmarkedPictureNeverGiveARecord() {
        val img = fixture("photo1_unmarked.jpg")
        val w = img.width.toDouble(); val h = img.height.toDouble()
        val q = arrayOf(doubleArrayOf(w * .05, h * .05), doubleArrayOf(w * .95, h * .05), doubleArrayOf(w * .95, h * .95), doubleArrayOf(w * .05, h * .95))
        val r = MarkEngine.readPerspective(pixels(img), img.width, img.height, q)
        assertTrue(r == null || r.status == MarkStatus.NONE || r.status == MarkStatus.DAMAGED)
        assertNull(r?.layer1)
    }

    @Test
    fun theHomographySolverMapsCornersToCorners() {
        val from = arrayOf(doubleArrayOf(0.0, 0.0), doubleArrayOf(100.0, 0.0), doubleArrayOf(100.0, 80.0), doubleArrayOf(0.0, 80.0))
        val to = arrayOf(doubleArrayOf(10.0, 5.0), doubleArrayOf(190.0, 20.0), doubleArrayOf(170.0, 150.0), doubleArrayOf(5.0, 120.0))
        val h = MarkEngine.solveHomography(from, to)!!
        for (i in 0 until 4) {
            val d = h[6] * from[i][0] + h[7] * from[i][1] + 1.0
            assertEquals(to[i][0], (h[0] * from[i][0] + h[1] * from[i][1] + h[2]) / d, 1e-6)
            assertEquals(to[i][1], (h[3] * from[i][0] + h[4] * from[i][1] + h[5]) / d, 1e-6)
        }
    }

    // ---- Kotlin writes, Kotlin reads ----

    private fun synthetic(w: Int, h: Int): BufferedImage {
        val img = BufferedImage(w, h, BufferedImage.TYPE_INT_RGB)
        val rnd = java.util.Random(42)
        for (y in 0 until h) for (x in 0 until w) {
            val base = 90 + 80 * Math.sin(x / 90.0) * Math.cos(y / 70.0)
            val tex = if ((x / 40 + y / 40) % 3 == 0) rnd.nextGaussian() * 14 else rnd.nextGaussian() * 3
            val r = (base + tex + 20).toInt().coerceIn(0, 255)
            val g = (base + tex).toInt().coerceIn(0, 255)
            val b = (base * 0.8 + tex + 40).toInt().coerceIn(0, 255)
            img.setRGB(x, y, (r shl 16) or (g shl 8) or b)
        }
        return img
    }

    private fun jpegRoundTrip(img: BufferedImage, longSide: Int, quality: Float): BufferedImage {
        val s = longSide.toDouble() / maxOf(img.width, img.height)
        val w = (img.width * s).toInt(); val h = (img.height * s).toInt()
        val small = BufferedImage(w, h, BufferedImage.TYPE_INT_RGB)
        val g = small.createGraphics()
        g.setRenderingHint(java.awt.RenderingHints.KEY_INTERPOLATION, java.awt.RenderingHints.VALUE_INTERPOLATION_BILINEAR)
        g.drawImage(img, 0, 0, w, h, null); g.dispose()
        val out = ByteArrayOutputStream()
        val writer = ImageIO.getImageWritersByFormatName("jpeg").next()
        val param = writer.defaultWriteParam.apply { compressionMode = ImageWriteParam.MODE_EXPLICIT; compressionQuality = quality }
        writer.output = MemoryCacheImageOutputStream(out)
        writer.write(null, IIOImage(small, null, null), param); writer.dispose()
        return ImageIO.read(out.toByteArray().inputStream())
    }

    @Test
    fun kotlinRoundTripThroughAChatStyleShrink() {
        val img = synthetic(2000, 1500)
        MarkEngine.embed(ImagePixels(img), MarkRecord(12.97163, 77.59456, 920.0, 1790000000L, 4, false))
        val received = jpegRoundTrip(img, 1200, 0.7f)
        val r = MarkEngine.read(ImagePixels(received))
        assertEquals(MarkStatus.OK, r.status)
        val d = r.layer1!!
        assertEquals(12.97163, d.latitude!!, 2e-5)
        assertEquals(77.59456, d.longitude!!, 2e-5)
        assertEquals(920, d.altitudeMeters)
        assertEquals(1790000000L, d.timeSeconds)
        assertEquals(4, d.tenth)
    }

    @Test
    fun theMarkChangesPixelsOnlyALittle() {
        val img = synthetic(1200, 900)
        val before = BufferedImage(1200, 900, BufferedImage.TYPE_INT_RGB).also { it.graphics.drawImage(img, 0, 0, null) }
        MarkEngine.embed(ImagePixels(img), MarkRecord(1.0, 2.0, 3.0, 1790000000L, 0, true))
        var maxd = 0; var sum = 0L
        for (y in 0 until 900) for (x in 0 until 1200) {
            val a = before.getRGB(x, y); val b = img.getRGB(x, y)
            for (sh in intArrayOf(16, 8, 0)) { val d = abs(((a shr sh) and 255) - ((b shr sh) and 255)); maxd = maxOf(maxd, d); sum += d }
        }
        assertTrue("max change $maxd", maxd <= 16)
        assertTrue("mean change ${sum / (1200.0 * 900 * 3)}", sum / (1200.0 * 900 * 3) < 4.0)
    }

    /** Leaves a Kotlin-written, chat-shrunk picture behind so the JavaScript engine can be pointed at it. */
    @Test
    fun writeKotlinMarkedFixtureForTheJavaScriptEngine() {
        val img = synthetic(2000, 1500)
        MarkEngine.embed(ImagePixels(img), MarkRecord(12.97163, 77.59456, 920.0, 1790000000L, 4, false))
        val received = jpegRoundTrip(img, 1200, 0.7f)
        val dir = File("build/tmp"); dir.mkdirs()
        ImageIO.write(received, "png", File(dir, "kotlin_marked_1200.png"))
    }
}
