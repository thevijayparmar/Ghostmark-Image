# Mark Engine

**An invisible, self-contained way to make a photo remember where and when it was taken, even after the metadata is gone.**

Mark Engine hides a small record (location to ~1 m, altitude, UTC time to 0.1 s, a live/manual flag) inside the *pixels* of a photograph. EXIF dies the moment a chat app, screenshot, converter or cropper touches the file; the hidden mark usually does not. The engine is an Android library with **no UI, no dependencies, no permissions, no network and no native code** (97 KB AAR). It marks a 12 MP photo in about 1.2 s and reads one back in about 0.15 s on a mid-range phone.

| | |
|---|---|
| Version / format | Engine 1.1.0 · mark format 1 |
| Platform | Android (minSdk 26), Kotlin, plain `android.graphics`; JavaScript reference implementation included |
| Author | Vijay Parmar ([@thevijayparmar](https://github.com/thevijayparmar)) |
| Licence | Attribution licence: free to use in your apps **with credit**, see [LICENSE](LICENSE) |

---

## Abstract

Field photographs are evidence, but their provenance is stored in the most fragile place possible: file metadata. We present a two-layer, texture-adaptive spread-spectrum watermark that stores a 118-bit record in chroma (layer 1) and a 60-bit location backup in luma (layer 2), protected by a CRC-16 and a rate-½ convolutional code, with 20 % known "pilot" tiles that let a reader detect, align, crop-search and perspective-correct an arbitrary copy. On **7 real phone photographs (9 to 18 MP, three phone models)** attacked 11 ways each (77 copies), the full record was recovered in **56 of 56** copies kept at 1080 px or larger (8 edit types × 7 photos), no attacked copy returned a **wrong record**, and **56 unmarked controls produced zero false alarms** (max detection z = 3.1 against a threshold of 3.5). The marks change the image by 0.9 to 2.7 grey levels on average (PSNR 37.6 to 45.5 dB). Honest limits are reported in section 7.

![Write and read pipeline](assets/fig01_pipeline.png)

## 1. Why a pixel mark

| Survives… | EXIF GPS/time | **Mark Engine** |
|---|:-:|:-:|
| Messenger / social re-compression | ✗ | ✓ |
| Screenshot, format conversion | ✗ | ✓ |
| Resize to 800 px, JPEG q40 | ✗ | ✓ (6 of 7 photos; 7 of 7 at q70) |
| Plain crop | ✗ | ✓ (crop search; see section 7) |
| Rotation by 90° steps | ✗ | ✓ (Kotlin reader tries all four turns) |
| Colour → black & white | ✗ | location only (layer 2) |
| Photo of a monitor / print | ✗ | ✓ with 4 tapped corners |

The mark does **not** prove authenticity: anyone holding this engine can write a mark with any values. It makes *honest* metadata survive, and a tamper hint fires when the two layers disagree by more than 30 m.

## 2. Method in one page

Two invisible grids share the picture ([FORMAT-SPEC.md](engine/FORMAT-SPEC.md) has the exact bit layout):

* **Layer 1 (colour).** About 10,000 tiles; each tile's Cb/Cr mean is nudged by ±(≤ 2) grey levels in a pseudo-random pattern. 118 payload bits → CRC-16 → rate-½, K = 7 convolutional code → 248 coded bits, each repeated over ~32 tiles (spread-spectrum voting).
* **Layer 2 (brightness).** About 50,000 finer luma tiles carry only location (60 bits, ~10 m). It is weaker on busy colour edits but is the one that **survives black & white**.
* **Pilot tiles.** 20 % of tiles have a known sign. The reader correlates the picture with them to *detect* a mark (z-score), to *align* it after a crop or a perspective warp, and as a built-in false-alarm test.
* **Texture-adaptive strength.** Amplitude follows local texture (`amp = a_max · max(σ/14, floor)`), so sky and flat walls are barely touched.
* **Self-test at capture.** The engine squeezes a copy like a chat app would (1600 px, q70), reads it, and strengthens the mark (up to ×1.9) if it did not survive.

![Tile grid and payload layout](assets/fig02_anatomy.png)

## 3. Is it visible?

Mean change per pixel is 0.9 to 2.7 grey levels of 255 and no sample moves by more than 9 (a hard cap). Figure 3 shows a 100 % crop of the original, the marked version, and the difference amplified 24×; the change is a smooth, low-frequency colour texture that follows image detail.

![Invisibility analysis](assets/fig03_invisibility.png)

| Photo | Camera | MP | PSNR (dB) | mean &#124;Δ&#124; | pixels with a change ≥ 3 levels |
|:-:|---|:-:|:-:|:-:|:-:|
| 1 | iPhone, stone carving | 12.2 | 37.6 | 2.72 | 76 % |
| 2 | iPhone, dark water | 12.2 | 41.1 | 1.55 | 36 % |
| 3 | iPhone, stone well | 12.2 | 38.0 | 2.49 | 67 % |
| 4 | vivo, construction site | 15.9 | 38.5 | 2.35 | 65 % |
| 5 | vivo, crane site | 15.9 | 39.7 | 1.91 | 49 % |
| 6 | LAVA, sky over road | 9.4 | **45.5** | 0.86 | 11 % |
| 7 | iPhone, jetty and rig | 18.4 | 40.3 | 1.68 | 41 % |

PSNR rises on flat scenes (photo 6, a sky) because the adaptive rule withholds the mark there. That is also why photo 6 is the most fragile in section 4: **invisibility is traded for strength locally, never globally.** The JPEG file grows by 0 to 3 %.

## 4. Robustness: 7 photos × 12 attacks

Every photo was marked at full resolution with the reference engine, stored as JPEG q95, then attacked with OpenCV and read back. A read counts as correct only if latitude/longitude (±2 m), altitude, time, tenth-of-second and flag all match.

![Survival matrix](assets/fig04_survival_matrix.png)

| Attack (applied to the stored q95 file) | Full record (layer 1) | Location only (layer 2 alone) | Median z (layer 1) |
|---|:-:|:-:|:-:|
| None (stored JPEG q95) | 7 / 7 | 5 / 7 | 27 |
| Chat app: 1600 px, q70 | 7 / 7 | 5 / 7 | 25 |
| Screenshot-style PNG, 1080 px | 7 / 7 | 5 / 7 | 27 |
| Brightness/contrast edit, then chat app | 7 / 7 | 5 / 7 | 25 |
| Colour drained to 40 %, then chat app | 7 / 7 | 5 / 7 | 17 |
| Gaussian blur σ = 1.2, then chat app | 7 / 7 | 4 / 7 | 24 |
| 25 % of the frame painted over, then chat app | 7 / 7 | 5 / 7 | 22 |
| Social: 1080 px, q50 | 7 / 7 | 4 / 7 | 16 |
| Thumbnail: 800 px, q40 | 6 / 7 | 4 / 7 | 12 |
| Tiny: 600 px, q50 | 4 / 7 | 2 / 7 | 11 |
| Black & white, then chat app | 0 / 7 | **5 / 7 recovered as `PART`** | – |
| Unmarked control | 0 false alarms | 0 false alarms | – |

Scaling and compression sweeps (Figure 5) show a graceful, monotonic loss of detection strength: reads become unreliable below ~800 px on the long edge or below ~JPEG q10 at 1600 px.

![Resolution and quality sweeps](assets/fig05_resolution_quality.png)

## 5. Reliability: false alarms and the role of texture

A reader that cries "mark!" on clean photos would be worse than none. All 56 reads of unmarked photos (7 photos × 8 degradations) returned `NONE`; the largest z seen was **3.1** (layer 1) and **2.95** (layer 2) against a threshold of **3.5**, while correct reads started at z ≈ 8. Because every record carries a CRC-16 and a convolutional code, a *wrong* record needs a collision on top of detection: none occurred in the 77 attacked reads.

Detection strength tracks how busy the scene is (Pearson r = 0.95 between mean tile texture and z after a chat-app copy). Stone carvings and construction sites (photos 1, 3, 4) read at z = 26 to 35; a plain sky or dark water (photos 6, 2) at z = 14 to 18, still safely readable, but with less headroom against heavy shrinking.

![False alarms and texture](assets/fig06_false_alarms_texture.png)

## 6. Case study: one photo's journey

The carving (photo 1) is marked with a demonstration record (12.97160 N, 77.59457 E, 920 m, 2026-10-25 12:00:00.4 UTC) and then abused. Green panels return the *complete, identical* record; the black & white copy returns the location only (± 10 m); the unmarked original correctly returns nothing. The monitor photo (⑧) is a simulation (perspective, blur, sensor noise, JPEG) read with four hand-tapped corners that are about 1.2 % off.

![Case study](assets/fig07_case_study.png)

Marked demo images (1600 px, EXIF-free) for all seven photos are in [`samples/`](samples/): download one, send it through any messenger, and read it back with the trial app to repeat the experiment yourself.

## 7. Cost, crops, screens, and honest limits

![Cost, crops and screens](assets/fig08_cost_crops_screens.png)

* **Speed (real phone, 12 MP).** Mark: ~0.65 s embed + ~0.56 s self-test. Read: ~0.15 s. Plain-crop search: 2.5 to 4.6 s. Screen/print reader: 24 s (clean case) to ~55 s. The JavaScript reference implementation needs 0.25 to 0.6 s to mark 9 to 18 MP on a PC.
* **Crops** (cropped, then re-compressed): a 10 % trim or a centred 75 % crop was read in full in **7 / 7** photos; a centred 55 % crop in 3 / 7 (one more gave location only); a one-quarter-area corner crop in **0 / 7**. Plain crops only: no rotation by other than 90° steps, no crop of a tilted photo.
* **Photos of a screen or a print** (simulated, 4 corners tapped) were read in full in **14 / 14** cases (z = 11 to 34). On real hardware the picture is less kind: a real monitor photo read correctly (z = 12.7, 24 s on the phone), a second one shown at 100 % zoom on a high-resolution panel was lost to moiré (z = 4.7). Tip for users: step back, lower brightness, show the picture smaller than the screen.
* **Not supported:** strong denoising or AI retouching, heavy blur, pictures below 64 px, times before 2026-01-01 or after ~2043, removing or editing a mark (only overwriting it by marking the clean original again).
* **Security:** the live/manual flag and the record are **not signed**. Treat the mark as durable honest metadata, not as proof.

## 8. Use it

```kotlin
// 1. add the module:  settings.gradle.kts → include(":engine");  app → implementation(project(":engine"))
// 2. after your overlay is drawn, before JPEG encoding (background thread):
val record = MarkRecord(lat, lon, altitudeMeters = alt, timeSeconds = Math.floorDiv(shutterMillis, 1000L),
                        tenth = (Math.floorMod(shutterMillis, 1000L) / 100).toInt())
val report = InvisibleMark.mark(finalBitmap, record)          // null = failed, save unmarked
// 3. anywhere later:
val read = InvisibleMark.read(context, uri, ReadOptions(searchCrops = true))
when (read?.result?.status) {                                 // OK · PART · DAMAGED · NONE
    MarkStatus.OK   -> read.result.layer1                     // lat, lon, alt, time, manual flag
    MarkStatus.PART -> read.result.layer2                     // location only, ~10 m
    else -> { /* tell the user, never invent a value */ }
}
```

Full API, four integration flows, rules and an AI-assistant checklist are in [`engine/ENGINE.md`](engine/ENGINE.md).

## 9. Repository map & reproducing every number

```
engine/        the library (source, ENGINE.md, FORMAT-SPEC.md, 29 JVM tests with cross-language fixtures)
dist/          prebuilt markengine-1.1.0.aar
trial/         small Compose sample app: Capture, Read, Screen/print with corner editor
reference/     JavaScript reference implementation + CLI (wins over the spec if they disagree)
tools/         run_experiments.py → results/results.json, make_figures.py → assets/*.png
samples/       marked demo photos (1600 px)
```

```
gradlew :engine:testDebugUnitTest :engine:assembleRelease :trial:assembleDebug
cd tools && python run_experiments.py && python make_figures.py      # needs numpy, opencv-python, matplotlib, pillow, node
# set MARK_PHOTOS=<folder of your own JPEGs named "TEST PHOTOS (1).jpg" ...> to rerun on other photos
```

Benchmark honesty notes: attacks were run on the JavaScript reference engine, which uses the same format and maths as the Kotlin engine (cross-checked by shared fixtures in both directions); on-phone timings and the two real monitor photos come from the Kotlin engine on a 1220 × 2712 Android phone. Seven photos is a small set: treat all percentages as indicative, not as a guarantee for every scene.

## Licence and credit

Copyright © 2026 Vijay Parmar. Free to use, modify and ship inside your own apps, including commercially, **provided you credit the author** (for example "Uses Mark Engine by Vijay Parmar, github.com/thevijayparmar/MarkEngine" in your About or credits screen). The engine may not be resold or republished as a stand-alone library or SDK. See [LICENSE](LICENSE) for the binding text.
