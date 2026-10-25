package com.vgp.markengine.trial

import android.content.Context
import android.net.Uri
import android.util.Log
import com.vgp.markengine.InvisibleMark
import com.vgp.markengine.ReadOptions
import com.vgp.markengine.toPixelArray
import java.io.File

/**
 * Test hook for adb: `am start -n .../.MainActivity --es batch read` reads every picture in the app's
 * external files folder (`Android/data/<package>/files/batch`) and logs one line each under tag MET.
 * A `<name>.corners` file (8 numbers: x,y of TL TR BR BL, in the picture as decoded at about 2000 px)
 * makes it a screen/print read.
 */
object BatchTest {
    /** Logs, and appends to results.txt next to the pictures (some phones hide app logs). */
    private fun log(context: Context, line: String) {
        Log.i("MET", line)
        runCatching { File(context.filesDir, "batch_results.txt").appendText(line + "\n") }
    }

    fun run(context: Context) {
        val dir = File(context.filesDir, "batch")
        File(context.filesDir, "batch_results.txt").delete()
        val files = dir.listFiles { f -> f.extension.lowercase() in setOf("jpg", "jpeg", "png") }?.sortedBy { it.name } ?: emptyList()
        log(context, "batch start: ${files.size} files in ${dir.path}")
        for (f in files) {
            runCatching {
                val corners = File(f.path + ".corners").takeIf { it.exists() }?.readText()?.trim()?.split(",")?.map { it.trim().toDouble() }
                val t0 = System.nanoTime()
                if (corners != null && corners.size == 8) {
                    val bmp = InvisibleMark.decodeForRead(context, Uri.fromFile(f), 2000)!!
                    val px = bmp.toPixelArray()
                    val q = Array(4) { doubleArrayOf(corners[it * 2], corners[it * 2 + 1]) }
                    val r = InvisibleMark.readPerspective(px, bmp.width, bmp.height, q)
                    val ms = (System.nanoTime() - t0) / 1_000_000
                    log(context, "${f.name} [screen/print ${bmp.width}x${bmp.height}] ${r?.status} z1=%.1f z2=%.1f lat=${r?.layer1?.latitude} lon=${r?.layer1?.longitude} ${ms} ms".format(r?.z1 ?: 0.0, r?.z2 ?: 0.0))
                } else {
                    val r = InvisibleMark.read(context, Uri.fromFile(f), ReadOptions(searchCrops = true))!!
                    log(context, "${f.name} ${r.result.status} z1=%.1f z2=%.1f lat=${r.result.layer1?.latitude} lon=${r.result.layer1?.longitude} turn=${r.turnedDegrees} crop=${r.result.crop != null} ${r.millis} ms".format(r.result.z1, r.result.z2))
                }
            }.onFailure { log(context, "${f.name} FAILED $it") }
        }
        log(context, "batch done")
    }
}
