package com.vgp.markengine

import java.io.File
import javax.imageio.ImageIO
import org.junit.Assume.assumeTrue
import org.junit.Test

/**
 * Developer harness, skipped unless env MET_REAL points at a folder holding `<name>.jpg` + `<name>.jpg.corners`
 * (8 numbers TL,TR,BR,BL in the picture after halving to about 2000 px). Prints the read for each.
 */
class RealScreenTest {
    @Test
    fun realScreenPhotos() {
        val dir = System.getenv("MET_REAL")
        assumeTrue(dir != null)
        for (f in File(dir!!).listFiles { x -> x.name.endsWith(".jpg") }!!.sortedBy { it.name }) {
            val cf = File(f.path + ".corners"); if (!cf.exists()) continue
            var img = ImageIO.read(f)
            while (System.getenv("MET_FULL") == null && maxOf(img.width, img.height) / 2 >= 2000) {
                val h = java.awt.image.BufferedImage(img.width / 2, img.height / 2, java.awt.image.BufferedImage.TYPE_INT_RGB)
                val g = h.createGraphics(); g.setRenderingHint(java.awt.RenderingHints.KEY_INTERPOLATION, java.awt.RenderingHints.VALUE_INTERPOLATION_BILINEAR)
                g.drawImage(img.getScaledInstance(h.width, h.height, java.awt.Image.SCALE_AREA_AVERAGING), 0, 0, null); g.dispose(); img = h
            }
            val w = img.width; val hh = img.height
            val px = IntArray(w * hh); img.getRGB(0, 0, w, hh, px, 0, w)
            val c = cf.readText().trim().split(",").map { it.trim().toDouble() }
            val q = Array(4) { doubleArrayOf(c[it * 2], c[it * 2 + 1]) }
            val sn = MarkEngine.snapCorners(px, w, hh, q)
            println("REAL snap ${f.name} tapped=" + q.joinToString { "(%.0f,%.0f)".format(it[0], it[1]) } + " snapped=" + (sn?.joinToString { "(%.0f,%.0f)".format(it[0], it[1]) } ?: "null"))
            val t0 = System.nanoTime()
            val r = MarkEngine.readPerspective(px, w, hh, q, snap = System.getenv("MET_NOSNAP") == null, refine = System.getenv("MET_NOREFINE") == null, aspectHint = System.getenv("MET_ASPECT")?.toDouble())
            val ms = (System.nanoTime() - t0) / 1_000_000
            println("REAL ${f.name} ${w}x$hh ${r?.status} z1=%.1f z2=%.1f align=%.1f lat=${r?.layer1?.latitude} $ms ms".format(r?.z1 ?: 0.0, r?.z2 ?: 0.0, r?.perspective?.alignZ ?: 0.0))
        }
    }
}
