package com.vgp.markengine.trial

import android.Manifest
import android.annotation.SuppressLint
import android.content.ContentValues
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Looper
import android.provider.MediaStore
import android.provider.OpenableColumns
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.exifinterface.media.ExifInterface
import com.vgp.markengine.InvisibleMark
import com.vgp.markengine.MarkReadResult
import com.vgp.markengine.MarkRecord
import com.vgp.markengine.MarkStatus
import com.vgp.markengine.ReadOptions
import com.vgp.markengine.toPixelArray
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.File
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (intent.getStringExtra("batch") != null) Thread { BatchTest.run(applicationContext) }.start()
        setContent {
            MaterialTheme(colorScheme = darkColorScheme()) {
                Surface(Modifier.fillMaxSize()) { TrialApp() }
            }
        }
    }
}

@Composable
private fun TrialApp() {
    var tab by remember { mutableStateOf(0) }
    Column(Modifier.fillMaxSize().statusBarsPadding()) {
        Text(
            "Mark Engine Trial · engine ${InvisibleMark.ENGINE_VERSION} · format ${InvisibleMark.FORMAT}",
            style = MaterialTheme.typography.labelMedium, modifier = Modifier.padding(start = 16.dp, top = 8.dp, bottom = 4.dp),
        )
        TabRow(selectedTabIndex = tab) {
            listOf("Capture", "Read", "Screen / print").forEachIndexed { i, t ->
                Tab(selected = tab == i, onClick = { tab = i }, text = { Text(t) })
            }
        }
        when (tab) {
            0 -> CaptureTab()
            1 -> ReadTab()
            else -> ScreenTab()
        }
    }
}

// ====================================================================== capture

private const val SAVE_ALBUM = "MarkEngineTrial"
private const val MAX_EDGE = 4096
private const val JPEG_QUALITY = 95

@Composable
private fun CaptureTab() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var granted by remember { mutableStateOf(hasPermission(context, Manifest.permission.CAMERA)) }
    var hasLocation by remember { mutableStateOf(hasPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)) }
    val askPerms = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        granted = hasPermission(context, Manifest.permission.CAMERA)
        hasLocation = hasPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
    }
    if (!granted) {
        Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
            Text("The camera (and, if you allow it, location for the mark) is needed.")
            Spacer(Modifier.height(12.dp))
            Button(onClick = { askPerms.launch(arrayOf(Manifest.permission.CAMERA, Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)) }) { Text("Allow") }
        }
        return
    }

    var fix by remember { mutableStateOf<Location?>(null) }
    if (hasLocation) LocationWatcher(context) { fix = it }

    var markOn by remember { mutableStateOf(true) }
    var selfTest by remember { mutableStateOf(true) }
    var busy by remember { mutableStateOf(false) }
    var report by remember { mutableStateOf<List<String>>(emptyList()) }
    val imageCapture = remember { ImageCapture.Builder().setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY).build() }

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
        CameraPreview(imageCapture, Modifier.fillMaxWidth().height(380.dp))
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                fix?.let { "Location: %.5f, %.5f  ±%.0f m".format(it.latitude, it.longitude, it.accuracy) }
                    ?: if (hasLocation) "Location: waiting for a fix (the mark will carry the time only)" else "Location: not allowed (the mark will carry the time only)",
                style = MaterialTheme.typography.bodySmall,
            )
            SwitchRow("Invisible mark", markOn) { markOn = it }
            SwitchRow("Self-test (squeeze like a chat app, strengthen if needed)", selfTest) { selfTest = it }
            Button(
                enabled = !busy, modifier = Modifier.fillMaxWidth(),
                onClick = {
                    val pressedAt = System.currentTimeMillis()
                    val snap = fix
                    val file = File(context.cacheDir, "shot_$pressedAt.jpg")
                    busy = true; report = listOf("Capturing…")
                    imageCapture.takePicture(
                        ImageCapture.OutputFileOptions.Builder(file).build(),
                        ContextCompat.getMainExecutor(context),
                        object : ImageCapture.OnImageSavedCallback {
                            override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                                scope.launch {
                                    report = listOf("Processing…")
                                    report = withContext(Dispatchers.Default) {
                                        runCatching { processShot(context, file, pressedAt, snap, markOn, selfTest) }
                                            .getOrElse { listOf("FAILED: ${it.javaClass.simpleName} ${it.message}") }
                                    }
                                    file.delete(); busy = false
                                }
                            }
                            override fun onError(e: ImageCaptureException) { report = listOf("Capture failed: ${e.message}"); busy = false }
                        },
                    )
                },
            ) { Text(if (busy) "Working…" else "Take photo") }
            if (report.isNotEmpty()) ReportCard(report)
        }
    }
}

/** Decodes the shot upright (long edge at most [MAX_EDGE]), marks it, saves it to Pictures/MarkEngineTrial and reads the saved file back. */
private fun processShot(context: Context, file: File, pressedAt: Long, fix: Location?, markOn: Boolean, selfTest: Boolean): List<String> {
    val lines = mutableListOf<String>()
    val t0 = System.nanoTime()
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(file.path, bounds)
    var sample = 1
    while (maxOf(bounds.outWidth, bounds.outHeight) / sample > MAX_EDGE) sample *= 2
    val decoded = BitmapFactory.decodeFile(file.path, BitmapFactory.Options().apply { inPreferredConfig = Bitmap.Config.ARGB_8888; inSampleSize = sample })
        ?: return listOf("Could not decode the shot")
    val orientation = ExifInterface(file.path).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
    val degrees = when (orientation) { 6 -> 90f; 3 -> 180f; 8 -> 270f; else -> 0f }
    var bmp = if (degrees == 0f) decoded else Bitmap.createBitmap(decoded, 0, 0, decoded.width, decoded.height, Matrix().apply { postRotate(degrees) }, true)
    if (bmp !== decoded) decoded.recycle()
    if (!bmp.isMutable) bmp = bmp.copy(Bitmap.Config.ARGB_8888, true)
    val decodeMs = (System.nanoTime() - t0) / 1_000_000
    lines += "Picture ${bmp.width} x ${bmp.height}, decoded in $decodeMs ms"

    var marked = false
    if (markOn) {
        val record = MarkRecord(
            latitude = fix?.latitude, longitude = fix?.longitude,
            altitudeMeters = fix?.takeIf { it.hasAltitude() }?.altitude,
            timeSeconds = Math.floorDiv(pressedAt, 1000L),
            tenth = (Math.floorMod(pressedAt, 1000L) / 100).toInt(),
            manual = false,
        )
        val w = InvisibleMark.mark(bmp, record, selfTest)
        if (w == null) lines += "MARK FAILED (photo saved unmarked)"
        else {
            marked = true
            lines += "Mark written: strength ${w.strength}, self-test ${w.selfTestMillis} ms, embed ${w.embedMillis} ms"
        }
    } else lines += "Mark switched off (control photo)"

    val bytes = ByteArrayOutputStream().use { bmp.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, it); it.toByteArray() }
    bmp.recycle()
    val out = File(context.cacheDir, "out_$pressedAt.jpg").apply { writeBytes(bytes) }
    ExifInterface(out.path).apply {
        setAttribute(ExifInterface.TAG_ORIENTATION, "1")
        val utc = SimpleDateFormat("yyyy:MM:dd HH:mm:ss", Locale.US).apply { timeZone = TimeZone.getTimeZone("UTC") }
        setAttribute(ExifInterface.TAG_DATETIME_ORIGINAL, utc.format(pressedAt))
        setAttribute(ExifInterface.TAG_OFFSET_TIME_ORIGINAL, "+00:00")
        if (fix != null) {
            setLatLong(fix.latitude, fix.longitude)
            if (fix.hasAltitude()) setAltitude(fix.altitude)
        }
        saveAttributes()
    }
    val name = "MET_${SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(pressedAt)}${if (marked) "_marked" else "_plain"}.jpg"
    val uri = saveToGallery(context, out, name)
    lines += if (uri != null) "Saved: Pictures/$SAVE_ALBUM/$name" else "SAVE FAILED"

    // Read the saved file back, the way the Read tab would.
    val back = InvisibleMark.read(context, Uri.fromFile(out))
    if (back != null) lines += "Read back (${back.millis} ms): " + describe(back.result.status) + "  z1=%.1f z2=%.1f".format(back.result.z1, back.result.z2)
    out.delete()
    lines += "Total ${(System.nanoTime() - t0) / 1_000_000} ms"
    return lines
}

private fun saveToGallery(context: Context, file: File, name: String): Uri? {
    val values = ContentValues().apply {
        put(MediaStore.Images.Media.DISPLAY_NAME, name)
        put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
        if (Build.VERSION.SDK_INT >= 29) put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/$SAVE_ALBUM")
    }
    val uri = context.contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values) ?: return null
    context.contentResolver.openOutputStream(uri)?.use { o -> file.inputStream().use { it.copyTo(o) } } ?: return null
    return uri
}

@Composable
private fun CameraPreview(imageCapture: ImageCapture, modifier: Modifier) {
    val context = LocalContext.current
    val owner = LocalLifecycleOwner.current
    AndroidView(
        modifier = modifier,
        factory = { ctx ->
            PreviewView(ctx).also { view ->
                val future = ProcessCameraProvider.getInstance(ctx)
                future.addListener({
                    val provider = future.get()
                    val preview = Preview.Builder().build().also { it.setSurfaceProvider(view.surfaceProvider) }
                    provider.unbindAll()
                    provider.bindToLifecycle(owner, CameraSelector.DEFAULT_BACK_CAMERA, preview, imageCapture)
                }, ContextCompat.getMainExecutor(context))
            }
        },
    )
}

@SuppressLint("MissingPermission")
@Composable
private fun LocationWatcher(context: Context, onFix: (Location) -> Unit) {
    DisposableEffect(Unit) {
        val lm = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val listener = LocationListener { onFix(it) }
        runCatching {
            lm.getProviders(true).mapNotNull { lm.getLastKnownLocation(it) }.maxByOrNull { it.time }?.let(onFix)
            for (p in listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)) {
                if (lm.isProviderEnabled(p)) lm.requestLocationUpdates(p, 2000L, 0f, listener, Looper.getMainLooper())
            }
        }
        onDispose { runCatching { lm.removeUpdates(listener) } }
    }
}

// ====================================================================== read

@Composable
private fun ReadTab() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var uri by remember { mutableStateOf<Uri?>(null) }
    var name by remember { mutableStateOf("") }
    var searchCrops by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var report by remember { mutableStateOf<List<String>>(emptyList()) }
    fun readNow(u: Uri) {
        busy = true; report = listOf("Reading…")
        scope.launch {
            report = withContext(Dispatchers.Default) {
                runCatching {
                    val r = InvisibleMark.read(context, u, ReadOptions(searchCrops = searchCrops))
                    if (r == null) listOf("This file is not a picture")
                    else listOf(describe(r.result.status) + "  (${r.millis} ms" +
                        (if (r.turnedDegrees != 0) ", picture was turned ${r.turnedDegrees}°" else "") +
                        (if (r.usedCropSearch && r.result.crop != null) ", crop found" else "") + ")") + markLines(r.result)
                }.getOrElse { listOf("FAILED: ${it.javaClass.simpleName} ${it.message}") }
            }
            busy = false
        }
    }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { u ->
        if (u != null) { uri = u; name = displayName(context, u); report = emptyList() }
    }
    var pending by remember { mutableStateOf<Uri?>(null) }
    val shoot = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { ok ->
        val u = pending; pending = null
        if (u == null) return@rememberLauncherForActivityResult
        if (ok) { uri = u; name = "Camera photo"; readNow(u) } else context.contentResolver.delete(u, null, null)
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Take a photo with the camera (of a screen, a print, anything) and it is read straight away, or pick an existing photo. Camera photos are also saved in Pictures/$SAVE_ALBUM.", style = MaterialTheme.typography.bodySmall)
        SwitchRow("Also look for a cropped photo (slower)", searchCrops) { searchCrops = it }
        Button(
            onClick = { newScanUri(context)?.let { pending = it; shoot.launch(it) } },
            modifier = Modifier.fillMaxWidth(), enabled = !busy,
        ) { Text("Take a photo and read it") }
        OutlinedButton(onClick = { pick.launch(arrayOf("image/*")) }, modifier = Modifier.fillMaxWidth(), enabled = !busy) { Text(if (uri == null) "Choose a photo" else "Choose another photo") }
        if (uri != null) {
            Text(name, style = MaterialTheme.typography.labelLarge)
            Button(onClick = { readNow(uri!!) }, modifier = Modifier.fillMaxWidth(), enabled = !busy) { Text("Read the mark again") }
            OutlinedButton(
                onClick = {
                    busy = true; report = listOf("Stress test running…")
                    scope.launch {
                        report = withContext(Dispatchers.Default) { runCatching { stressTest(context, uri!!) }.getOrElse { listOf("FAILED: ${it.javaClass.simpleName} ${it.message}") } }
                        busy = false
                    }
                },
                modifier = Modifier.fillMaxWidth(), enabled = !busy,
            ) { Text("Stress test (simulate chat apps)") }
        }
        if (report.isNotEmpty()) ReportCard(report)
    }
}

/** A new empty gallery entry for the camera app to write a picture into. */
private fun newScanUri(context: Context): Uri? {
    val values = ContentValues().apply {
        put(MediaStore.Images.Media.DISPLAY_NAME, "MET_scan_${SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(System.currentTimeMillis())}.jpg")
        put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
        if (Build.VERSION.SDK_INT >= 29) put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/$SAVE_ALBUM")
    }
    return context.contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
}

/** Squeezes the chosen picture the way sharing apps do and reads each copy. */
private fun stressTest(context: Context, uri: Uri): List<String> {
    val bmp = InvisibleMark.decodeForRead(context, uri, 2400) ?: return listOf("This file is not a picture")
    val out = mutableListOf("Source ${bmp.width} x ${bmp.height}")
    val plain = InvisibleMark.read(bmp, ReadOptions(tryTurns = false))
    out += "As is: ${describe(plain.result.status)}  z1=%.1f z2=%.1f  (${plain.millis} ms)".format(plain.result.z1, plain.result.z2)
    for ((edge, q) in listOf(1600 to 70, 1280 to 60, 1080 to 50, 800 to 40)) {
        val s = InvisibleMark.squeeze(bmp, edge, q)
        if (s == null) { out += "$edge px, JPEG $q: could not build the copy"; continue }
        val r = InvisibleMark.read(s, ReadOptions(tryTurns = false))
        out += "$edge px, JPEG $q: ${describe(r.result.status)}  z1=%.1f z2=%.1f".format(r.result.z1, r.result.z2)
        s.recycle()
    }
    bmp.recycle()
    return out
}

// ====================================================================== screen / print

@Composable
private fun ScreenTab() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var bitmap by remember { mutableStateOf<Bitmap?>(null) }
    var pixels by remember { mutableStateOf<IntArray?>(null) }
    var corners by remember { mutableStateOf<List<Offset>>(emptyList()) }
    var progress by remember { mutableStateOf<Float?>(null) }
    var report by remember { mutableStateOf<List<String>>(emptyList()) }
    var job by remember { mutableStateOf<Job?>(null) }
    fun load(u: Uri) {
        scope.launch {
            report = emptyList()
            val loaded = withContext(Dispatchers.IO) { loadUpright(context, u, 2000) }
            if (loaded == null) { report = listOf("Could not open that photo"); return@launch }
            bitmap = loaded
            pixels = withContext(Dispatchers.Default) { loaded.toPixelArray() }
            val w = loaded.width.toFloat(); val h = loaded.height.toFloat()
            corners = listOf(Offset(w * .08f, h * .08f), Offset(w * .92f, h * .08f), Offset(w * .92f, h * .92f), Offset(w * .08f, h * .92f))
        }
    }
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { u -> if (u != null) load(u) }
    var pending by remember { mutableStateOf<Uri?>(null) }
    val shoot = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { ok ->
        val u = pending; pending = null
        if (u == null) return@rememberLauncherForActivityResult
        if (ok) load(u) else context.contentResolver.delete(u, null, null)
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            "Take a photo of a monitor or a printed copy, then drag the four corners onto the corners of the picture (drag from a corner, or touch anywhere to bring the nearest corner there; a magnifier shows the spot). Roughly is fine, the reader snaps to the picture's edges. Takes about half a minute.",
            style = MaterialTheme.typography.bodySmall,
        )
        Button(onClick = { newScanUri(context)?.let { pending = it; shoot.launch(it) } }, modifier = Modifier.fillMaxWidth(), enabled = progress == null) { Text("Take a photo of the screen or print") }
        OutlinedButton(onClick = { pick.launch(arrayOf("image/*")) }, modifier = Modifier.fillMaxWidth(), enabled = progress == null) { Text(if (bitmap == null) "Choose a photo" else "Choose another photo") }
        val bmp = bitmap
        if (bmp != null && corners.size == 4) {
            CornerEditor(bmp, corners, progress == null) { corners = it }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(
                    onClick = {
                        val px = pixels ?: return@OutlinedButton
                        scope.launch {
                            val found = withContext(Dispatchers.Default) { InvisibleMark.autoCorners(px, bmp.width, bmp.height) }
                            if (found != null) { corners = found.map { Offset(it[0].toFloat(), it[1].toFloat()) }; report = listOf("Corners found. Check them.") }
                            else report = listOf("Could not find the edges. Drag the corners by hand.")
                        }
                    },
                    modifier = Modifier.weight(1f), enabled = progress == null,
                ) { Text("Find corners") }
                Button(
                    onClick = {
                        if (progress != null) { job?.cancel(); return@Button }
                        val px = pixels ?: return@Button
                        val q = Array(4) { doubleArrayOf(corners[it].x.toDouble(), corners[it].y.toDouble()) }
                        progress = 0f; report = emptyList()
                        val t0 = System.nanoTime()
                        job = scope.launch {
                            val r = withContext(Dispatchers.Default) {
                                runCatching {
                                    InvisibleMark.readPerspective(px, bmp.width, bmp.height, q, onProgress = { p -> progress = p.toFloat() }, cancelled = { !isActive })
                                }.getOrNull()
                            }
                            progress = null
                            val ms = (System.nanoTime() - t0) / 1_000_000
                            report = if (r == null) listOf("Stopped or failed") else listOf(describe(r.status) + "  ($ms ms)") + markLines(r) +
                                (if (r.status == MarkStatus.OK) emptyList() else listOf(
                                    "Tips: fill the frame with the picture but keep it fully inside; hold the phone square to the screen; step back and zoom in a little (coloured wavy stripes = moire from the screen's pixels); lower the screen brightness; keep the picture on screen at 100% or smaller.",
                                ))
                        }
                    },
                    modifier = Modifier.weight(1f),
                ) { Text(if (progress == null) "Read the mark" else "Stop") }
            }
            progress?.let { LinearProgressIndicator(progress = { it }, modifier = Modifier.fillMaxWidth()) }
        }
        if (report.isNotEmpty()) ReportCard(report)
    }
}

@Composable
private fun CornerEditor(bmp: Bitmap, corners: List<Offset>, enabled: Boolean, onChange: (List<Offset>) -> Unit) {
    val density = LocalDensity.current
    val image = remember(bmp) { bmp.asImageBitmap() }
    val cornersNow by rememberUpdatedState(corners)
    val onChangeNow by rememberUpdatedState(onChange)
    BoxWithConstraints(Modifier.fillMaxWidth()) {
        val boxW = with(density) { maxWidth.toPx() }
        val scale = boxW / bmp.width
        val boxHdp = with(density) { (bmp.height * scale).toDp() }
        val hit = with(density) { 56.dp.toPx() }
        var active by remember { mutableStateOf(-1) }
        Box(Modifier.fillMaxWidth().height(boxHdp)) {
            Image(image, contentDescription = null, contentScale = ContentScale.FillWidth, modifier = Modifier.fillMaxSize())
            Canvas(
                Modifier.fillMaxSize().pointerInput(enabled, bmp) {
                    if (!enabled) return@pointerInput
                    // Own gesture loop: consuming the touch from the first moment keeps the scrolling page from stealing the drag.
                    awaitEachGesture {
                        val down = awaitFirstDown(requireUnconsumed = false)
                        down.consume()
                        val start = cornersNow
                        val d = start.map { (it * scale - down.position).getDistance() }
                        val idx = d.indexOf(d.min())
                        active = idx
                        // Near a corner: keep the finger's offset from it. Far away: the corner jumps to the finger.
                        val grab = if (d[idx] < hit) start[idx] * scale - down.position else Offset.Zero
                        fun moveTo(p: Offset) {
                            val n = (p + grab) / scale
                            val moved = cornersNow.toMutableList()
                            moved[idx] = Offset(n.x.coerceIn(0f, bmp.width - 1f), n.y.coerceIn(0f, bmp.height - 1f))
                            onChangeNow(moved)
                        }
                        moveTo(down.position)
                        do {
                            val ev = awaitPointerEvent()
                            val c = ev.changes.firstOrNull { it.id == down.id } ?: break
                            if (c.pressed) { c.consume(); moveTo(c.position) }
                        } while (c.pressed)
                        active = -1
                    }
                },
            ) {
                val pts = corners.map { it * scale }
                for (i in 0 until 4) drawLine(Color(0xFF22D3EE), pts[i], pts[(i + 1) % 4], strokeWidth = 3f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(18f, 10f)))
                pts.forEachIndexed { i, p ->
                    drawCircle(if (i == active) Color(0xFFFACC15) else Color(0xFF22D3EE), radius = 22f, center = p, style = Stroke(width = 5f))
                    drawCircle(Color.White.copy(alpha = 0.7f), radius = 4f, center = p)
                }
                // Magnifier: the picture around the corner being moved, shown on the opposite side so the finger does not cover it.
                if (active >= 0) {
                    val c = corners[active]
                    val half = 40; val loupe = 300
                    val sx = (c.x.toInt() - half).coerceIn(0, bmp.width - 2 * half)
                    val sy = (c.y.toInt() - half).coerceIn(0, bmp.height - 2 * half)
                    val lx = if (c.x * scale < size.width / 2) size.width - loupe - 12f else 12f
                    drawImage(image, srcOffset = IntOffset(sx, sy), srcSize = IntSize(2 * half, 2 * half), dstOffset = IntOffset(lx.toInt(), 12), dstSize = IntSize(loupe, loupe))
                    drawRect(Color.White, topLeft = Offset(lx, 12f), size = androidx.compose.ui.geometry.Size(loupe.toFloat(), loupe.toFloat()), style = Stroke(3f))
                    val mx = lx + (c.x - sx) / (2 * half) * loupe; val my = 12f + (c.y - sy) / (2 * half) * loupe
                    drawLine(Color(0xFFFACC15), Offset(mx - 18, my), Offset(mx + 18, my), strokeWidth = 2f)
                    drawLine(Color(0xFFFACC15), Offset(mx, my - 18), Offset(mx, my + 18), strokeWidth = 2f)
                }
            }
        }
    }
}

/** Decodes [uri] to roughly [edge] px on the long edge and applies the EXIF turn, so what the user sees is what the reader gets. */
private fun loadUpright(context: Context, uri: Uri, edge: Int): Bitmap? {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    context.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
    if (bounds.outWidth <= 0) return null
    var s = 1
    while (maxOf(bounds.outWidth, bounds.outHeight) / (s * 2) >= edge) s *= 2
    val decoded = context.contentResolver.openInputStream(uri)?.use {
        BitmapFactory.decodeStream(it, null, BitmapFactory.Options().apply { inPreferredConfig = Bitmap.Config.ARGB_8888; inSampleSize = s })
    } ?: return null
    val orientation = runCatching {
        context.contentResolver.openInputStream(uri)?.use { ExifInterface(it).getAttributeInt(ExifInterface.TAG_ORIENTATION, 1) }
    }.getOrNull() ?: 1
    val degrees = when (orientation) { 6 -> 90f; 3 -> 180f; 8 -> 270f; else -> 0f }
    return if (degrees == 0f) decoded else Bitmap.createBitmap(decoded, 0, 0, decoded.width, decoded.height, Matrix().apply { postRotate(degrees) }, true).also { if (it !== decoded) decoded.recycle() }
}

// ====================================================================== shared bits

@Composable
private fun SwitchRow(label: String, value: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
        Spacer(Modifier.width(8.dp))
        Switch(checked = value, onCheckedChange = onChange)
    }
}

@Composable
private fun ReportCard(lines: List<String>) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            lines.forEachIndexed { i, l ->
                Text(l, fontFamily = if (i == 0) FontFamily.Default else FontFamily.Monospace, fontSize = if (i == 0) 15.sp else 12.sp)
            }
        }
    }
}

private fun hasPermission(context: Context, p: String) = ContextCompat.checkSelfPermission(context, p) == PackageManager.PERMISSION_GRANTED

private fun displayName(context: Context, uri: Uri): String = runCatching {
    context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { if (it.moveToFirst()) it.getString(0) else null }
}.getOrNull() ?: (uri.lastPathSegment ?: "photo")

private fun describe(s: MarkStatus) = when (s) {
    MarkStatus.OK -> "MARK READ: full record"
    MarkStatus.PART -> "MARK READ: location only (layer 2)"
    MarkStatus.DAMAGED -> "Mark is there but too damaged to read"
    MarkStatus.NONE -> "No mark found"
}

private fun markLines(r: MarkReadResult): List<String> {
    val out = mutableListOf<String>()
    val utc = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).apply { timeZone = TimeZone.getTimeZone("UTC") }
    r.layer1?.let {
        out += "Latitude   ${it.latitude?.let { v -> "%.6f".format(v) } ?: "none"}"
        out += "Longitude  ${it.longitude?.let { v -> "%.6f".format(v) } ?: "none"}"
        out += "Altitude   ${it.altitudeMeters?.let { v -> "$v m" } ?: "none"}"
        out += "Time (UTC) ${it.timeSeconds?.let { s -> utc.format(s * 1000) + ".${it.tenth}" } ?: "none"}"
        out += "Location   ${if (it.manual) "MANUAL (hand placed)" else "live capture"}"
        out += "Mark id    ${it.id}"
    }
    r.layer2?.let { out += "Layer 2    %s, %s".format(it.latitude?.let { v -> "%.4f".format(v) } ?: "none", it.longitude?.let { v -> "%.4f".format(v) } ?: "none") }
    r.layerDisagreementMeters?.let { out += "Layers differ by %.0f m%s".format(it, if (it > 30) "  <- SUSPICIOUS" else "") }
    out += "Strength   z1=%.1f z2=%.1f".format(r.z1, r.z2)
    r.crop?.let { out += "Crop       about %d%% of the original frame".format((it.widthFraction * it.heightFraction * 100).toInt()) }
    r.perspective?.let { out += "Perspective aligned, z=%.1f".format(it.alignZ) }
    return out
}
