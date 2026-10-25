# Mark Engine: invisible photo marking and reading (integration guide)

Engine version **1.1.0**, mark format **1**. This file is written for people and for AI coding assistants. If you are an AI asked to "integrate the mark engine into this app", read sections 1 to 6 and 12 first, then follow the checklist in section 12.

---

## 1. What this is (and is not)

The Mark Engine is a **backend library, with no user interface of its own**. An app keeps its own screens, camera, gallery and look. The engine only gives the app four abilities:

1. **Mark** a photo: hide a small record (location, altitude, UTC time to 0.1 s, "location was hand placed" flag) inside the picture's pixels, invisibly.
2. **Read** that record back from a photo: straight from a camera capture, from a file or gallery pick, or from a photo that was shared, resized, re-compressed, cropped.
3. **Read from a photo of a screen or a print** (someone photographed a monitor or a paper copy with another phone).
4. Small helpers (decode a picture at the right size, snap hand-tapped corners to a picture's outline, turn a read record into EXIF text).

It is **not** a camera, not a gallery, not a screen, not a permission asker, not a file saver. It never touches the network, never asks for any Android permission, never writes a file by itself. The app hands it pictures and gets results back.

Why the record lives in the pixels: EXIF (GPS, time) is lost the moment a chat app, a screenshot, a converter or a cropper touches the file. The hidden mark is part of the picture itself, so it usually survives.

Properties (measured on real phone photos, see section 9): lightweight (about 60 KB of Kotlin source, 97 KB AAR, no dependencies, no native code, no network); marking a 12 MP photo takes about 1.8 s including the optional self-test; reading takes about 0.15 s.

## 2. Get it into an app

Two ways, same code:

**A. Source module (recommended: the AI or developer can see and update it).** Copy the folder `engine/` (this folder) into the app project next to `app/`.
`settings.gradle.kts`: `include(":engine")`
`app/build.gradle.kts`: `dependencies { implementation(project(":engine")) }`
Requirements: Android `minSdk 26`, Kotlin, JVM 17. The engine has **no other dependency**.

**B. Prebuilt AAR.** `../dist/markengine-<version>.aar` (build it with `gradlew :engine:assembleRelease`). Put it in `app/libs/` and `implementation(files("libs/markengine-1.1.0.aar"))`.

Nothing to add to the manifest. No permissions. ProGuard/R8: the library ships `consumer-rules.pro` that keeps the public classes.

## 3. The public API (everything an app should touch)

Package `com.vgp.markengine`. Only these are public: `InvisibleMark`, `MarkRecord`, `MarkReadResult` (+ `Layer1Data`, `Layer2Data`, `MarkStatus`, `CropInfo`, `PerspectiveInfo`), `ReadOptions`, `ReadReport`, `WriteReport`, `MarkedJpeg`, `MarkExif`, `Bitmap.toPixelArray()`. The rest is internal on purpose, so the engine can change inside without breaking apps.

**Threading:** every call is blocking and CPU heavy. Call from a background thread (`withContext(Dispatchers.Default)`), never from the main thread.

### 3.1 The record that is hidden

```kotlin
data class MarkRecord(
    val latitude: Double?,        // degrees, null = not known
    val longitude: Double?,
    val altitudeMeters: Double?,  // null = not known
    val timeSeconds: Long?,       // UTC unix seconds, 2026-01-01 .. about 2043 only, null = not known
    val tenth: Int = 0,           // tenths of a second 0..9
    val manual: Boolean = false,  // true when a person placed the location by hand on an existing photo
)
```
A field that is `null` is stored as "not present" and comes back as `null` (the reader never invents a value). A time outside the clock's range (before 2026-01-01) cannot be stored: the engine leaves it out and says so in `WriteReport.notes`.
Precision after a round trip: location about 1 m, altitude 1 m, time 0.1 s.

### 3.2 Writing

| Call | Does |
|---|---|
| `InvisibleMark.mark(bitmap, record, selfTest = true): WriteReport?` | Marks a **mutable ARGB_8888** bitmap in place. `null` = failed, keep the original. |
| `InvisibleMark.markedCopy(bitmap, record, selfTest): Bitmap?` | Same, on a copy; the source stays untouched; caller recycles the copy. |
| `InvisibleMark.markToJpeg(bitmap, record, quality = 95, selfTest): MarkedJpeg?` | Marks a copy and returns JPEG bytes (no EXIF in them). |

`InvisibleMark.markId(record): String` gives the 10-letter ID the mark will carry (derived from the record; handy as a key in a log).

`selfTest = true` (recommended): the engine squeezes a scaled copy like WhatsApp would (1600 px, JPEG 70), reads it back, and writes the mark stronger (up to strength 1.9) if it would not survive. `WriteReport` has `strength`, `selfTestMillis`, `embedMillis`, `notes`.

### 3.3 Reading a picture

| Call | Does |
|---|---|
| `InvisibleMark.read(bitmap, ReadOptions()): ReadReport` | Reads a decoded picture. |
| `InvisibleMark.read(context, uri, options): ReadReport?` | Opens a gallery / file-picker / share `Uri` and reads it. `null` = not a picture. |
| `InvisibleMark.read(file, options)` / `read(bytes, options)` | Same for a `File` or for bytes in memory. |
| `InvisibleMark.decodeForRead(...)` | Decodes at the right size (long edge at least 1600 px, halving only). Used internally by the Uri/File/bytes versions. |

`ReadOptions(tryTurns = true, searchCrops = false)`: `tryTurns` also tries the three other quarter turns (cheap, needed when an app or the camera stored the picture rotated); `searchCrops = true` also looks for a plain crop of the original frame (1 to 5 s more; offer it as an "also look for cropped photos" switch).

`ReadReport` = `result: MarkReadResult`, `turnedDegrees`, `usedCropSearch`, `millis`.

```kotlin
class MarkReadResult(
    val status: MarkStatus,       // OK, PART, DAMAGED, NONE
    val layer1: Layer1Data?,      // full record, when status == OK
    val layer2: Layer2Data?,      // location only (about 10 m), when layer 2 read
    val z1: Double, val z2: Double, // detection strength, see 3.5
    val crop: CropInfo?, val perspective: PerspectiveInfo?,
    val layerDisagreementMeters: Double?, // computed property
)
class Layer1Data(val id: String, val latitude: Double?, val longitude: Double?, val altitudeMeters: Int?,
                 val timeSeconds: Long?, val tenth: Int, val manual: Boolean)
class Layer2Data(val latitude: Double?, val longitude: Double?)
```

### 3.4 Reading a photo of a screen or a print

The user photographs a monitor or a paper copy with any camera. The app lets the user mark the four corners of the picture, then calls the engine. The engine needs the **corners of the picture inside the photo** (not of the monitor), top-left, top-right, bottom-right, bottom-left.

```kotlin
val bmp = InvisibleMark.decodeForRead(context, uri, minEdge = 2000)!!   // then turn it upright with EXIF yourself
val pixels = bmp.toPixelArray()
// optional first guess for the corner handles (bright picture on dark surround):
val guess = InvisibleMark.autoCorners(pixels, bmp.width, bmp.height)
// the user drags four handles; corners = arrayOf(doubleArrayOf(x, y), ...) in bmp pixel coordinates
val result = InvisibleMark.readPerspective(pixels, bmp.width, bmp.height, corners,
    onProgress = { p -> /* 0..1 */ }, cancelled = { !isActive })
```
- A few percent off is fine: the engine snaps the corners onto the picture's outline (`InvisibleMark.snapCorners`, also used inside) and then lines the hidden pattern up by itself.
- Takes **10 to 60 s on a phone** (uses all cores). Always show progress and let the user stop (`cancelled`).
- The app should give the user a **magnifier while dragging a corner** and let a touch anywhere bring the nearest corner there. `trial/.../MainActivity.kt` (`CornerEditor`) is a complete working example including a scrolling-page fix (consume the touch from the first moment).
- This is the least reliable path (see limits, 9.3). Show tips when it does not read.

### 3.5 Reading the status

| `status` | Meaning | What the app should say / do |
|---|---|---|
| `OK` | Layer 1 read: full record in `layer1` | Show/use location, altitude, time. `layer1.manual` = hand placed. |
| `PART` | Only layer 2 read: location about 10 m, no time/altitude | Say "partly recovered, location only". |
| `DAMAGED` | A mark is certainly there but cannot be read | Say so; suggest a bigger/less compressed copy or (for screens) better corners. |
| `NONE` | No mark found | Say "no mark". This is never a wrong record. |

`z1`, `z2` are detection strengths: above 3.5 a mark is present; real reads are typically 12 to 35 for layer 1. A read with `z1` below about 10 is a weak read: it is still correct (the record is CRC protected) but the photo was near the limit.
**Tamper hint:** if both layers read and `layerDisagreementMeters` is over 30, the two locations disagree: warn that the picture may have been tampered with.

### 3.6 Helpers: EXIF text (`MarkExif`)

The engine has no EXIF library on purpose. The app reads/writes EXIF with its own (e.g. `androidx.exifinterface`) and uses `MarkExif` only to convert:
- Marking an **existing photo**: `MarkExif.captureTime(dateTimeOriginal, offsetTime, subSec, gpsDate, gpsTimeRationals, fallbackZone)` returns UTC millis and how trustworthy it is (`TimeBasis`), then `MarkExif.recordFor(lat, lon, alt, utcMillis, manual)` builds the `MarkRecord`.
- **Restoring EXIF** from a read mark (the photo came back stripped): `MarkExif.exifDateTimeUtc(seconds)`, `exifGpsDate`, `exifGpsTime` give the strings to write; write GPS lat/lon/alt from `layer1`. Do not overwrite existing GPS that differs by more than about 50 m (`MarkExif.distanceMeters`).

## 4. The four flows an app usually wants

**A. Camera capture (live photo).** After the app has drawn its overlay (if any) on the final bitmap and **before** JPEG encoding:
```kotlin
val record = MarkRecord(lat, lon, alt, timeSeconds = Math.floorDiv(shutterMillis, 1000L),
                        tenth = (Math.floorMod(shutterMillis, 1000L) / 100).toInt())
val report = withContext(Dispatchers.Default) { InvisibleMark.mark(finalBitmap, record) }
// report == null -> save the photo unmarked, never fail the capture
// then compress to JPEG quality >= 90 and write EXIF as usual
```
Take the location and time at the **moment of the shutter press**, not when the JPEG arrives. Keep the camera ready for the next shot: run this in a background worker.

**B. Mark an existing photo** (gallery import): decode (long edge at most about 4096 to keep memory sane), build the record from EXIF with `MarkExif`, set `manual = true` if the location was placed by hand, `markedCopy` / `markToJpeg`, save as a **new** file, never overwrite the source.

**C. Read a photo** (file manager, gallery, share target): `InvisibleMark.read(context, uri, ReadOptions(searchCrops = userSwitch))`, show the status and fields.

**D. Read a photo of a screen or print:** section 3.4.

## 5. Rules that keep it accurate

- Mark the **final pixels**: after overlays, text and stamps; before JPEG encoding. Anything drawn or filtered over large areas afterwards weakens the mark.
- Save marked photos as JPEG quality 90 or more (or PNG/WebP lossless). Re-encoding below JPEG 70 or under about 800 px on the long edge can destroy it (800 px at JPEG 40 still read in the phone test).
- The picture must be at least 64 px long edge to be marked; for a reliable read give 800 px or more, and feed `read` about 1600 px when you have it.
- Mark a picture once (not tested on double marking; avoid it). To re-stamp, start from the clean original.
- Smooth, flat pictures (clear sky, white wall) carry the mark weakly by design (it is kept invisible). Self-test compensates.
- Black-and-white copies lose the colour layer: expect `PART` (location only).
- The mark does **not** prove authenticity by itself; a determined person who has the engine can write a mark with any values. It makes honest metadata survive; the tamper hint only flags disagreement between layers.

## 6. Memory and speed (Samsung-class phone, measured)

12 MP (4096 px long edge) marking: self-test 0.56 s + embed 0.65 s. Reading 12 MP: about 0.15 s. Crop search 2.5 to 4.6 s. Screen/print: 24 s (clean case) to about 55 s. A 12 MP ARGB bitmap is about 48 MB: decode with a limit (long edge 4096) and recycle bitmaps promptly.

## 7. How it works (short)

Two layers share the picture. **Layer 1** (colour): about 10,000 tiles whose chroma is nudged up or down by 1 to 2 grey levels in a pseudo-random pattern, carrying 118 bits (location 1 m, altitude, time, flags, CRC-16) protected by a rate-1/2 convolutional code. **Layer 2** (brightness): about 50,000 finer tiles carrying location only (60 bits) as a backup. 20% of tiles are "pilot" tiles with a known pattern: the reader correlates the picture against them to detect and align, then decodes with a Viterbi decoder and checks the CRC. Strength adapts to how textured each tile is, so flat areas get almost nothing. Cropped, rotated and perspective-skewed photos are handled by first finding where the original frame sits (or where the corners are) and mapping the tiles. Exact bit layout: `FORMAT-SPEC.md` in this folder. The JavaScript reference implementation (`reference/wm-engine.js` in this repository) wins over the text if they disagree; the Kotlin engine here must stay compatible with it.

## 8. Updating the engine later

Change only this module. Then:
1. Bump `InvisibleMark.ENGINE_VERSION`. Bump `FORMAT` **only** if marks written by older versions can no longer be read; then the reader must keep the old decoder too, because photos marked long ago still exist.
2. Keep every public signature in section 3 working (add, do not remove). Then apps need no code change.
3. Run `gradlew :engine:testDebugUnitTest` (29 tests; includes fixtures written by the JavaScript reference engine, attacked by resize/JPEG/crop/screen simulation).
4. Rebuild the AAR (`gradlew :engine:assembleRelease`, copy to `dist/`), run the trial app on a phone (Capture, Read, stress test, Screen/print).
5. Tell the AI/developer of each app: "the engine in `engine/` was updated to version X: replace the folder, rebuild, no other change needed unless the notes say so."

Dev harness: `RealScreenTest` (env `MET_REAL=<folder of photo + .corners files>`) reads real photographs of screens on the PC in seconds; run with `--no-build-cache` and `cleanTestDebugUnitTest` because Gradle's cache ignores env vars.

## 9. What it does and does not survive (measured)

**9.1 Reads fully (layer 1, phone photos):** original JPEG; WhatsApp-style 1600 px JPEG 70 (z1 about 31 on a 12 MP photo); 1280 px q60; 1080 px q50; 800 px q40 (z1 about 15); EXIF stripped; format converted; rotated turns of 90/180/270 degrees; plain crops down to about 10 to 35% of the frame (with `searchCrops`); a 25% area painted over.
**9.2 Partly:** black-and-white copies (location only, layer 2); heavily degraded copies (location only).
**9.3 Photos of screens and prints:** read fully when the picture is photographed square-on, fills the frame, and its corners are given well: tested from a real monitor with a phone (12.7 z1 clean case, 9.7 z1 on a photo with strong moire stripes) and a steeply angled print. Fails when moire from the screen's pixel grid dominates (picture shown at 100% zoom on a high-resolution monitor, very close shot) or when the corners are far off. Tips for users: step back and zoom a little, lower screen brightness, show the picture smaller than the screen, hold the phone parallel to the screen.
**9.4 Not supported:** photos edited so heavily the pattern is gone (strong blur, heavy denoise, big AI retouching); a photo turned by a non-right angle or tilted and then cropped (crop search assumes an upright plain crop); marking pictures under 64 px; times before 2026-01-01 or after about 2043; marks cannot be removed or edited, only overwritten by marking the clean original again.

## 10. Frequently asked

*Is anything visible?* The change is a few grey levels at most, smoothed, adapted to texture; it is not visible at normal viewing. (Judge it yourself on your photos; the self-test only checks survival, not looks.)
*Does it need internet, accounts, a license?* No.
*Does it need permissions?* None of its own. The app needs camera/location permission for its own capture.
*Can two apps read each other's marks?* Yes, if both use the same FORMAT. That is the point of one shared engine.
*Why is `MarkEngine` internal?* So the inside can be rewritten freely; apps use `InvisibleMark` only.
*A read gave `OK` but the location is far from the EXIF GPS?* Believe the mark (it is in the pixels); show both and flag the difference.

## 11. File map

```
engine/
  ENGINE.md                  this file
  FORMAT-SPEC.md             exact bit-level format of the mark (copy of the spec)
  build.gradle.kts           Android library, no dependencies
  consumer-rules.pro         keeps the public classes for apps that shrink code
  src/main/java/com/vgp/markengine/
    InvisibleMark.kt         THE public API (+ ReadOptions, ReadReport, WriteReport, MarkedJpeg, toPixelArray)
    MarkExif.kt              EXIF text helpers (pure Kotlin)
    MarkEngine.kt            embed, read, crop search, perspective, snapping (internal)
    MarkCodec.kt             bits, CRC, payload, repair code (internal)
  src/test/                  29 JVM tests and fixtures (photos marked by the JS reference engine)
../trial/                    sample app: Capture, Read (+ camera, stress test), Screen/print with corner editor
../samples/                  marked demo photos for testing readers
../reference/                JavaScript reference implementation (writes/reads the same format)
../dist/markengine-<version>.aar` (build it with `gradlew :engine:assembleRelease`). Put it in `app/libs/` and `implementation(files("libs/markengine-1.1.0.aar"))`.

Nothing to add to the manifest. No permissions. ProGuard/R8: the library ships `consumer-rules.pro` that keeps the public classes.

## 3. The public API (everything an app should touch)

Package `com.vgp.markengine`. Only these are public: `InvisibleMark`, `MarkRecord`, `MarkReadResult` (+ `Layer1Data`, `Layer2Data`, `MarkStatus`, `CropInfo`, `PerspectiveInfo`), `ReadOptions`, `ReadReport`, `WriteReport`, `MarkedJpeg`, `MarkExif`, `Bitmap.toPixelArray()`. The rest is internal on purpose, so the engine can change inside without breaking apps.

**Threading:** every call is blocking and CPU heavy. Call from a background thread (`withContext(Dispatchers.Default)`), never from the main thread.

### 3.1 The record that is hidden

```kotlin
data class MarkRecord(
    val latitude: Double?,        // degrees, null = not known
    val longitude: Double?,
    val altitudeMeters: Double?,  // null = not known
    val timeSeconds: Long?,       // UTC unix seconds, 2026-01-01 .. about 2043 only, null = not known
    val tenth: Int = 0,           // tenths of a second 0..9
    val manual: Boolean = false,  // true when a person placed the location by hand on an existing photo
)
```
A field that is `null` is stored as "not present" and comes back as `null` (the reader never invents a value). A time outside the clock's range (before 2026-01-01) cannot be stored: the engine leaves it out and says so in `WriteReport.notes`.
Precision after a round trip: location about 1 m, altitude 1 m, time 0.1 s.

### 3.2 Writing

| Call | Does |
|---|---|
| `InvisibleMark.mark(bitmap, record, selfTest = true): WriteReport?` | Marks a **mutable ARGB_8888** bitmap in place. `null` = failed, keep the original. |
| `InvisibleMark.markedCopy(bitmap, record, selfTest): Bitmap?` | Same, on a copy; the source stays untouched; caller recycles the copy. |
| `InvisibleMark.markToJpeg(bitmap, record, quality = 95, selfTest): MarkedJpeg?` | Marks a copy and returns JPEG bytes (no EXIF in them). |

`InvisibleMark.markId(record): String` gives the 10-letter ID the mark will carry (derived from the record; handy as a key in a log).

`selfTest = true` (recommended): the engine squeezes a scaled copy like WhatsApp would (1600 px, JPEG 70), reads it back, and writes the mark stronger (up to strength 1.9) if it would not survive. `WriteReport` has `strength`, `selfTestMillis`, `embedMillis`, `notes`.

### 3.3 Reading a picture

| Call | Does |
|---|---|
| `InvisibleMark.read(bitmap, ReadOptions()): ReadReport` | Reads a decoded picture. |
| `InvisibleMark.read(context, uri, options): ReadReport?` | Opens a gallery / file-picker / share `Uri` and reads it. `null` = not a picture. |
| `InvisibleMark.read(file, options)` / `read(bytes, options)` | Same for a `File` or for bytes in memory. |
| `InvisibleMark.decodeForRead(...)` | Decodes at the right size (long edge at least 1600 px, halving only). Used internally by the Uri/File/bytes versions. |

`ReadOptions(tryTurns = true, searchCrops = false)`: `tryTurns` also tries the three other quarter turns (cheap, needed when an app or the camera stored the picture rotated); `searchCrops = true` also looks for a plain crop of the original frame (1 to 5 s more; offer it as an "also look for cropped photos" switch).

`ReadReport` = `result: MarkReadResult`, `turnedDegrees`, `usedCropSearch`, `millis`.

```kotlin
class MarkReadResult(
    val status: MarkStatus,       // OK, PART, DAMAGED, NONE
    val layer1: Layer1Data?,      // full record, when status == OK
    val layer2: Layer2Data?,      // location only (about 10 m), when layer 2 read
    val z1: Double, val z2: Double, // detection strength, see 3.5
    val crop: CropInfo?, val perspective: PerspectiveInfo?,
    val layerDisagreementMeters: Double?, // computed property
)
class Layer1Data(val id: String, val latitude: Double?, val longitude: Double?, val altitudeMeters: Int?,
                 val timeSeconds: Long?, val tenth: Int, val manual: Boolean)
class Layer2Data(val latitude: Double?, val longitude: Double?)
```

### 3.4 Reading a photo of a screen or a print

The user photographs a monitor or a paper copy with any camera. The app lets the user mark the four corners of the picture, then calls the engine. The engine needs the **corners of the picture inside the photo** (not of the monitor), top-left, top-right, bottom-right, bottom-left.

```kotlin
val bmp = InvisibleMark.decodeForRead(context, uri, minEdge = 2000)!!   // then turn it upright with EXIF yourself
val pixels = bmp.toPixelArray()
// optional first guess for the corner handles (bright picture on dark surround):
val guess = InvisibleMark.autoCorners(pixels, bmp.width, bmp.height)
// the user drags four handles; corners = arrayOf(doubleArrayOf(x, y), ...) in bmp pixel coordinates
val result = InvisibleMark.readPerspective(pixels, bmp.width, bmp.height, corners,
    onProgress = { p -> /* 0..1 */ }, cancelled = { !isActive })
```
- A few percent off is fine: the engine snaps the corners onto the picture's outline (`InvisibleMark.snapCorners`, also used inside) and then lines the hidden pattern up by itself.
- Takes **10 to 60 s on a phone** (uses all cores). Always show progress and let the user stop (`cancelled`).
- The app should give the user a **magnifier while dragging a corner** and let a touch anywhere bring the nearest corner there. `trial/.../MainActivity.kt` (`CornerEditor`) is a complete working example including a scrolling-page fix (consume the touch from the first moment).
- This is the least reliable path (see limits, 9.3). Show tips when it does not read.

### 3.5 Reading the status

| `status` | Meaning | What the app should say / do |
|---|---|---|
| `OK` | Layer 1 read: full record in `layer1` | Show/use location, altitude, time. `layer1.manual` = hand placed. |
| `PART` | Only layer 2 read: location about 10 m, no time/altitude | Say "partly recovered, location only". |
| `DAMAGED` | A mark is certainly there but cannot be read | Say so; suggest a bigger/less compressed copy or (for screens) better corners. |
| `NONE` | No mark found | Say "no mark". This is never a wrong record. |

`z1`, `z2` are detection strengths: above 3.5 a mark is present; real reads are typically 12 to 35 for layer 1. A read with `z1` below about 10 is a weak read: it is still correct (the record is CRC protected) but the photo was near the limit.
**Tamper hint:** if both layers read and `layerDisagreementMeters` is over 30, the two locations disagree: warn that the picture may have been tampered with.

### 3.6 Helpers: EXIF text (`MarkExif`)

The engine has no EXIF library on purpose. The app reads/writes EXIF with its own (e.g. `androidx.exifinterface`) and uses `MarkExif` only to convert:
- Marking an **existing photo**: `MarkExif.captureTime(dateTimeOriginal, offsetTime, subSec, gpsDate, gpsTimeRationals, fallbackZone)` returns UTC millis and how trustworthy it is (`TimeBasis`), then `MarkExif.recordFor(lat, lon, alt, utcMillis, manual)` builds the `MarkRecord`.
- **Restoring EXIF** from a read mark (the photo came back stripped): `MarkExif.exifDateTimeUtc(seconds)`, `exifGpsDate`, `exifGpsTime` give the strings to write; write GPS lat/lon/alt from `layer1`. Do not overwrite existing GPS that differs by more than about 50 m (`MarkExif.distanceMeters`).

## 4. The four flows an app usually wants

**A. Camera capture (live photo).** After the app has drawn its overlay (if any) on the final bitmap and **before** JPEG encoding:
```kotlin
val record = MarkRecord(lat, lon, alt, timeSeconds = Math.floorDiv(shutterMillis, 1000L),
                        tenth = (Math.floorMod(shutterMillis, 1000L) / 100).toInt())
val report = withContext(Dispatchers.Default) { InvisibleMark.mark(finalBitmap, record) }
// report == null -> save the photo unmarked, never fail the capture
// then compress to JPEG quality >= 90 and write EXIF as usual
```
Take the location and time at the **moment of the shutter press**, not when the JPEG arrives. Keep the camera ready for the next shot: run this in a background worker.

**B. Mark an existing photo** (gallery import): decode (long edge at most about 4096 to keep memory sane), build the record from EXIF with `MarkExif`, set `manual = true` if the location was placed by hand, `markedCopy` / `markToJpeg`, save as a **new** file, never overwrite the source.

**C. Read a photo** (file manager, gallery, share target): `InvisibleMark.read(context, uri, ReadOptions(searchCrops = userSwitch))`, show the status and fields.

**D. Read a photo of a screen or print:** section 3.4.

## 5. Rules that keep it accurate

- Mark the **final pixels**: after overlays, text and stamps; before JPEG encoding. Anything drawn or filtered over large areas afterwards weakens the mark.
- Save marked photos as JPEG quality 90 or more (or PNG/WebP lossless). Re-encoding below JPEG 70 or under about 800 px on the long edge can destroy it (800 px at JPEG 40 still read in the phone test).
- The picture must be at least 64 px long edge to be marked; for a reliable read give 800 px or more, and feed `read` about 1600 px when you have it.
- Mark a picture once (not tested on double marking; avoid it). To re-stamp, start from the clean original.
- Smooth, flat pictures (clear sky, white wall) carry the mark weakly by design (it is kept invisible). Self-test compensates.
- Black-and-white copies lose the colour layer: expect `PART` (location only).
- The mark does **not** prove authenticity by itself; a determined person who has the engine can write a mark with any values. It makes honest metadata survive; the tamper hint only flags disagreement between layers.

## 6. Memory and speed (Samsung-class phone, measured)

12 MP (4096 px long edge) marking: self-test 0.56 s + embed 0.65 s. Reading 12 MP: about 0.15 s. Crop search 2.5 to 4.6 s. Screen/print: 24 s (clean case) to about 55 s. A 12 MP ARGB bitmap is about 48 MB: decode with a limit (long edge 4096) and recycle bitmaps promptly.

## 7. How it works (short)

Two layers share the picture. **Layer 1** (colour): about 10,000 tiles whose chroma is nudged up or down by 1 to 2 grey levels in a pseudo-random pattern, carrying 118 bits (location 1 m, altitude, time, flags, CRC-16) protected by a rate-1/2 convolutional code. **Layer 2** (brightness): about 50,000 finer tiles carrying location only (60 bits) as a backup. 20% of tiles are "pilot" tiles with a known pattern: the reader correlates the picture against them to detect and align, then decodes with a Viterbi decoder and checks the CRC. Strength adapts to how textured each tile is, so flat areas get almost nothing. Cropped, rotated and perspective-skewed photos are handled by first finding where the original frame sits (or where the corners are) and mapping the tiles. Exact bit layout: `FORMAT-SPEC.md` in this folder. The JavaScript reference implementation (`reference/wm-engine.js` in this repository) wins over the text if they disagree; the Kotlin engine here must stay compatible with it.

## 8. Updating the engine later

Change only this module. Then:
1. Bump `InvisibleMark.ENGINE_VERSION`. Bump `FORMAT` **only** if marks written by older versions can no longer be read; then the reader must keep the old decoder too, because photos marked long ago still exist.
2. Keep every public signature in section 3 working (add, do not remove). Then apps need no code change.
3. Run `gradlew :engine:testDebugUnitTest` (29 tests; includes fixtures written by the JavaScript reference engine, attacked by resize/JPEG/crop/screen simulation).
4. Rebuild the AAR (`gradlew :engine:assembleRelease`, copy to `dist/`), run the trial app on a phone (Capture, Read, stress test, Screen/print).
5. Tell the AI/developer of each app: "the engine in `engine/` was updated to version X: replace the folder, rebuild, no other change needed unless the notes say so."

Dev harness: `RealScreenTest` (env `MET_REAL=<folder of photo + .corners files>`) reads real photographs of screens on the PC in seconds; run with `--no-build-cache` and `cleanTestDebugUnitTest` because Gradle's cache ignores env vars.

## 9. What it does and does not survive (measured)

**9.1 Reads fully (layer 1, phone photos):** original JPEG; WhatsApp-style 1600 px JPEG 70 (z1 about 31 on a 12 MP photo); 1280 px q60; 1080 px q50; 800 px q40 (z1 about 15); EXIF stripped; format converted; rotated turns of 90/180/270 degrees; plain crops down to about 10 to 35% of the frame (with `searchCrops`); a 25% area painted over.
**9.2 Partly:** black-and-white copies (location only, layer 2); heavily degraded copies (location only).
**9.3 Photos of screens and prints:** read fully when the picture is photographed square-on, fills the frame, and its corners are given well: tested from a real monitor with a phone (12.7 z1 clean case, 9.7 z1 on a photo with strong moire stripes) and a steeply angled print. Fails when moire from the screen's pixel grid dominates (picture shown at 100% zoom on a high-resolution monitor, very close shot) or when the corners are far off. Tips for users: step back and zoom a little, lower screen brightness, show the picture smaller than the screen, hold the phone parallel to the screen.
**9.4 Not supported:** photos edited so heavily the pattern is gone (strong blur, heavy denoise, big AI retouching); a photo turned by a non-right angle or tilted and then cropped (crop search assumes an upright plain crop); marking pictures under 64 px; times before 2026-01-01 or after about 2043; marks cannot be removed or edited, only overwritten by marking the clean original again.

## 10. Frequently asked

*Is anything visible?* The change is a few grey levels at most, smoothed, adapted to texture; it is not visible at normal viewing. (Judge it yourself on your photos; the self-test only checks survival, not looks.)
*Does it need internet, accounts, a license?* No.
*Does it need permissions?* None of its own. The app needs camera/location permission for its own capture.
*Can two apps read each other's marks?* Yes, if both use the same FORMAT. That is the point of one shared engine.
*Why is `MarkEngine` internal?* So the inside can be rewritten freely; apps use `InvisibleMark` only.
*A read gave `OK` but the location is far from the EXIF GPS?* Believe the mark (it is in the pixels); show both and flag the difference.

## 11. File map

```
engine/
  ENGINE.md                  this file
  FORMAT-SPEC.md             exact bit-level format of the mark (copy of the spec)
  build.gradle.kts           Android library, no dependencies
  consumer-rules.pro         keeps the public classes for apps that shrink code
  src/main/java/com/vgp/markengine/
    InvisibleMark.kt         THE public API (+ ReadOptions, ReadReport, WriteReport, MarkedJpeg, toPixelArray)
    MarkExif.kt              EXIF text helpers (pure Kotlin)
    MarkEngine.kt            embed, read, crop search, perspective, snapping (internal)
    MarkCodec.kt             bits, CRC, payload, repair code (internal)
  src/test/                  29 JVM tests and fixtures (photos marked by the JS reference engine)
../trial/                    sample app: Capture, Read (+ camera, stress test), Screen/print with corner editor
../test-photos/              ready-made marked photos for testing readers, SET2 set with expected values
../tools/mark_set2.py        marks photos with the JS reference engine for testing
../dist/                     built AAR
```

## 12. Integration checklist (for an AI assistant doing the work)

1. Do not build UI inside the engine and do not copy engine internals into the app; add the module (section 2) and call `InvisibleMark` only.
2. Find the app's capture path. After the final bitmap (overlay included) exists and before JPEG encode, call `mark(...)` on a background thread with a record taken at shutter time (flow A). If it returns null, continue unmarked. Make the mark switch a setting if the app has settings (default on).
3. Find where the app already writes EXIF; leave it as is. The mark is in addition to EXIF.
4. Add a "read mark" action to the app's own UI that takes a `Uri` (gallery/file picker) and calls `read(context, uri, ReadOptions(searchCrops = switch))`; show the fields per section 3.5. Add the screen/print reader (3.4) only if the app wants it, using the trial app's corner editor as a model.
5. If the app imports existing photos, build the record with `MarkExif` (flow B), set `manual` when the user placed the location, save as a new file.
6. Build, run on a phone: take a photo, share it through WhatsApp, read the received copy: expect `OK`. Read an unmarked photo: expect `NONE`.
7. Report to the owner what was changed in the app and the engine version used (`InvisibleMark.ENGINE_VERSION`).
