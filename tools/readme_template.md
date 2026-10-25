<div align="center">
  <img src="assets/banner.jpg" width="100%" alt="Ghostmark: photos that remember where and when, even after the metadata is gone"/>
</div>

<br>

<div align="center">

  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Attribution-orange?logo=opensourceinitiative&logoColor=white" alt="Attribution licence"></a>
  <img src="https://img.shields.io/badge/Android-minSdk%2026-3DDC84?logo=android&logoColor=white" alt="Android minSdk 26">
  <img src="https://img.shields.io/badge/Kotlin-100%25-7F52FF?logo=kotlin&logoColor=white" alt="Kotlin">
  <img src="https://img.shields.io/badge/Dependencies-0-2F7CF6" alt="Zero dependencies">
  <img src="https://img.shields.io/badge/AAR-97%20KB-2F7CF6" alt="97 KB AAR">
  <img src="https://img.shields.io/badge/Tests-29%20passing-3fb950" alt="29 tests passing">
  <img src="https://img.shields.io/badge/Test%20photos-{{N}}-ff69b4" alt="{{N}} test photos">
  <img src="https://img.shields.io/badge/Cameras-{{NDEV}}-00b8d9" alt="{{NDEV}} cameras">
  <img src="https://img.shields.io/badge/Edits%20tested-{{TOT}}-blueviolet" alt="{{TOT}} edits tested">

</div>

<br>

<div align="center">
  <h1>👻 Ghostmark</h1>
  <p><strong>Photos that remember where and when they were taken, even after the metadata is gone.</strong></p>
  <p>An Android library that hides <b>location (~1 m), altitude, UTC time (0.1 s)</b> and a live/manual flag <i>inside the pixels</i> of a photo, invisibly, so the record survives WhatsApp, screenshots, crops and even a phone photo of a screen.</p>
  <p><code>Ghostmark-Image</code> · engine 1.1.0 · no UI · no permissions · no network · no native code</p>
</div>

<div align="center">
  <a href="https://www.linkedin.com/in/thevijayparmar/">
    <img src="https://img.shields.io/badge/LinkedIn-Vijay%20Parmar-0077B5?logo=linkedin&logoColor=white" alt="LinkedIn">
  </a>
  &nbsp;
  <a href="../../issues">
    <img src="https://img.shields.io/badge/Report%20Bug-Issues-red?logo=github" alt="Report Bug">
  </a>
  &nbsp;
  <a href="../../issues">
    <img src="https://img.shields.io/badge/Request%20Feature-Ideas-blueviolet?logo=github" alt="Request Feature">
  </a>
</div>

---

> ⏳ **Heads up: this page is long and GIF-heavy on purpose.** It is a lab notebook as much as a README: {{N}} real photos from {{NDEV}} different cameras (phones and drones), {{TOT}} attacked copies, 14 charts and {{N}} animated test reels. Skim the pictures, or read every number. Everything is generated from scripts in [`tools/`](tools/), nothing is typed by hand.

<div align="center">
  <img src="assets/stats_strip.png" width="100%" alt="Headline numbers"/>
</div>

---

## 📖 Contents

| | | |
|---|---|---|
| [🎬 See it in action](#-see-it-in-action) | [📊 The lab results](#-the-lab-results) | [🔬 What we learned](#-what-we-learned) |
| [🧪 The test bench](#-the-test-bench-23-photos-10-cameras) | [🎞️ The gauntlet (23 reels)](#️-the-gauntlet-23-test-reels) | [⚙️ How it works](#️-how-it-works) |
| [🧬 The hidden layer](#-the-hidden-layer-made-visible) | [🏆 Leaderboard](#-leaderboard-who-survives-best) | [⚠️ Honest limits](#️-honest-limits) |

---

## 🎬 See it in action

<div align="center">
  <img src="assets/hero_reveal.gif" width="75%" alt="A photo and the invisible layer it secretly carries, then the decoded record"/>
  <p><em>One photo, two views. The scan line reveals the invisible pattern that carries the record, then the reader decodes it in 0.15 s.</em></p>
</div>

<table>
<tr>
<td width="33%" valign="top">

### 😶 The problem

GPS and time live in **file metadata**. A chat app, a screenshot, a "save as" or a crop deletes them silently, and then the photo is just a picture. For anyone whose photos are *evidence* (inspectors, surveyors, insurers) that is a real loss.

</td>
<td width="33%" valign="top">

### 👻 The trick

Spread a 118-bit record over ~10,000 colour tiles (and a 60-bit location backup over ~50,000 brightness tiles), protect it with a CRC and an error-correcting code, and push each tile by only **1 to 2 grey levels**. Invisible to the eye, readable by the reader.

</td>
<td width="33%" valign="top">

### ✅ The proof

**{{BIG_OK}} of {{BIG_N}}** chat, share, screenshot and edit copies gave back the **full record**; **{{FP_N}} false alarms** in {{FP_TOTAL}} unmarked reads; **0 wrong values** across {{TOT}} edits. Median image change: **{{PSNR_MED}} dB PSNR**, SSIM **{{SSIM_MED}}**.

</td>
</tr>
</table>

## 🧪 The test bench: 23 photos, 10 cameras

Not studio shots: real field photos from **{{NDEV}} camera models**: flagship phones, budget phones, an old vivo, and DJI drones, from {{MP_MIN}} MP to {{MP_MAX}} MP. Stone carvings, water, rebar, steel rigs, solar panels, open sky, a plate of fruit and a café table. Easy, textured scenes **and** the awkward ones (flat sky, dark water, smooth plates).

<div align="center">
  <img src="assets/photo_wall.jpg" width="100%" alt="All 23 test photos with their hidden layer and the results of 12 edits as coloured dots"/>
  <p><em>Every test photo, its hidden layer (×26) and 12 result dots: <b>green</b> = full record read, <b>orange</b> = location only, <b>red</b> = mark present but unreadable, <b>grey</b> = nothing found. Hover-free, no cherry-picking: this is the whole bench.</em></p>
</div>

{{DEVICE_TABLE}}

## 🧬 The hidden layer, made visible

The mark is the **difference** between the marked and the original photo, magnified 26 times (red/blue = pixels pushed up/down). Notice where it *isn't*: flat sky, dark water and smooth plates receive almost nothing. That is the **texture-adaptive** rule keeping the change invisible exactly where your eye would catch it.

<div align="center">
  <img src="assets/fig03a_closeup.png" width="100%" alt="A 100 percent crop of original and marked, the amplified difference, and the histogram of change"/>
  <p><em>A 100 % crop, before and after. The difference map (×24) shows a smooth, low-frequency pattern; the histogram shows no pixel channel moves by more than {{MAX_CH}} levels.</em></p>
</div>

<div align="center">
  <img src="assets/fig03b_quality_hist.png" width="100%" alt="Histograms of PSNR, SSIM and colour shift across all photos"/>
  <p><em>How big is the change, across all {{N}} photos? Median PSNR <b>{{PSNR_MED}} dB</b> (range {{PSNR_MIN}} to {{PSNR_MAX}}), median SSIM <b>{{SSIM_MED}}</b>, median colour shift ΔE <b>{{DE_MED}}</b> (a ΔE of about 2 is the edge of what a trained eye notices side by side). Mean absolute change {{MEAN_CH}} grey levels of 255; the file grows by at most {{BYTES_MAX}} %.</em></p>
</div>

## 🎞️ The gauntlet: 23 test reels

Every photo was marked with the same demo record (12.97160 N, 77.59457 E, 920 m, 2026-10-25 12:00:00.4 UTC) and put through the **same nine steps**: original, hidden layer, saved, chat app, 600 px thumbnail, black &amp; white, a quarter painted over, a 10 % crop, and a (simulated) phone photo of a monitor. Green = full record back, orange = location only, red = mark present but unreadable. **Failures are shown on purpose.**

{{GALLERY}}

## 📊 The lab results

### 🔥 Survival matrix: every photo × every edit

<div align="center">
  <img src="assets/fig04_survival_matrix.png" width="100%" alt="Survival matrix of 23 photos by 13 edits"/>
  <p><em>Each cell is the colour-layer detection strength z (threshold 3.5) or a status: <b>LOC</b> = location only (orange frame), <b>DMG</b> = mark present but unreadable (red frame), <b>--</b> = no mark found. Photo labels are coloured by camera.</em></p>
</div>

<table>
<tr>
<td width="55%" align="center">
  <img src="assets/fig13_heic_totals.png" width="100%" alt="Totals donut and HEIC test"/>
</td>
<td width="45%" valign="middle">

### The scoreboard

**{{TOT}}** attacked copies (23 photos × {{NA}} edits):

- ✅ **{{FULL}}** full records ({{FULLPCT}} %)
- 🟠 **{{PART}}** location-only recoveries
- 🔴 **{{DMG}}** honestly unreadable
- ❌ **0** wrong values
- 🚫 **{{FP_N}}** false alarms on {{FP_TOTAL}} unmarked reads (highest z {{FP_MAX}} vs threshold 3.5)

</td>
</tr>
</table>

{{ATT_TABLE}}

### 📦 How strong is the signal? Distribution per edit

<div align="center">
  <img src="assets/fig09_attack_boxplot.png" width="100%" alt="Box plot of detection strength per edit"/>
  <p><em>Every dot is one photo. Boxes are quartiles; cyan is the median. Healthy copies sit at z = 15 to 35, the threshold is 3.5, and the unmarked control stays flat on the floor.</em></p>
</div>

### 📉 How small, how squashed?

<div align="center">
  <img src="assets/fig05_resolution_quality.png" width="100%" alt="Detection strength versus resolution and JPEG quality for all photos"/>
  <p><em>Top: z versus long edge (grey = each photo, cyan band = middle 50 %). Bottom left: the share of photos still read in full. Bottom right: JPEG quality alone, on a 1600 px copy.</em></p>
</div>

### 🕵️ Never cries wolf, and why busy scenes win

<div align="center">
  <img src="assets/fig06_false_alarms_texture.png" width="100%" alt="False alarm test and texture correlation"/>
  <p><em>Left: {{FP_TOTAL}} reads of unmarked photos (8 degradations × {{N}} photos) never crossed the threshold; real reads start at z ≈ {{MIN_OK_Z}}. Right: detection strength follows scene texture (r = {{TEX_R}}).</em></p>
</div>

### ✂️ Crops, 📺 screens and ⏱️ speed

<div align="center">
  <img src="assets/fig08_cost_crops_screens.png" width="100%" alt="Cost on a phone, crop outcomes and simulated screen and print results"/>
  <p><em>Crop, then chat app: a 10 % trim or centred 90 % / 75 % / 60 % crop is found and read in most photos ({{CTRIM}}, {{C90}}, {{C75}}, {{C60}} of {{N}}); a 45 % or quarter-frame crop is not ({{C45}} and {{CQ}} of {{N}}). Simulated phone photos of a monitor: {{SCR0}} of {{N}} read in full; of a print: {{SCR1}} of {{N}}.</em></p>
</div>

### 📱 Does the camera matter?

<div align="center">
  <img src="assets/fig10_devices_speed.png" width="100%" alt="Robustness by camera and marking and reading time against megapixels"/>
  <p><em>Left: edits survived per camera (dots = individual photos). Middle: marking time on the JavaScript reference engine, measured one photo at a time on one PC core (about {{KMS}} ms per megapixel, median {{EMB_MED}} ms; the Kotlin engine on a phone takes ~1.2 s for 12 MP including the self-test). Right: a full-size read, median {{READ_MED}} ms.</em></p>
</div>

### 🎚️ The visibility ↔ survival trade-off

The mark strength is a dial. We re-marked every photo at five strengths and measured both invisibility and survival.

<div align="center">
  <img src="assets/fig11_strength_tradeoff.png" width="100%" alt="PSNR and survival against mark strength"/>
</div>

{{STRENGTH_TABLE}}

**Take-away:** the default (1×) already reads {{CHAT_OK}} of {{N}} photos after a chat app, but only about three quarters survive an 800 px / q40 thumbnail. Raising the strength to 1.5× to 2× rescues most of the rest, at a visible cost (PSNR drops from about 40 to 35 dB). That is exactly why Ghostmark ships a **capture-time self-test**: it simulates a chat app on the fresh photo and raises the strength (up to 1.9×) *only for the photos that need it*, so a textured temple stays subtle and a smooth plate gets help. In this benchmark {{N_SMALL_FAIL}} photos are lost at 800 px / q40 with the 1× mark, and **{{N_RESCUED}} of them are read in full once the strength is doubled**. The only photo that fails even as a stored copy at 1× is {{FAIL_STORED}}, a dark, smooth plate: exactly the case the self-test exists for.

## 🏆 Leaderboard: who survives best?

<div align="center">
  <img src="assets/fig12_leaderboard.png" width="100%" alt="Photos ranked by number of edits survived"/>
</div>

<table>
<tr>
<td width="50%" valign="top">

{{STRONG}}

</td>
<td width="50%" valign="top">

{{WEAK}}

</td>
</tr>
</table>

## 🔬 What we learned

1. **Texture is destiny.** The marks that survive best live in rubble, rebar, stone and foliage. Flat sky, dark water and smooth plates are the weak spots, by design: the adaptive rule withholds the mark where it would be visible, and there is less pattern to hide in.
2. **Resolution matters more than JPEG quality.** The reader keeps working down to JPEG q10 at 1600 px, but falls apart below roughly 600 to 800 px on the long edge. Chat apps resize; they rarely crush quality that far.
3. **The luma layer earns its place.** Convert a photo to black &amp; white and the colour layer is gone for every photo. The brightness layer still returned the location for **{{BW_LOC}} of {{N}}** photos, which is the whole point of having two independent layers.
4. **Never a wrong answer.** The CRC-16 plus the convolutional code turned every uncertain read into an honest `PART` or `DAMAGED`, not into a plausible-looking wrong coordinate: **0 wrong values** across {{TOT}} edits and {{FP_TOTAL}} unmarked controls.
5. **It survives a format change.** HEIC originals decoded, marked and saved as JPEG q95 were read in full for **{{HEIC_OK}} of {{HEIC_N}}** photos.
6. **Photos of screens and prints are viable, with help.** With four tapped corners the reader aligned and decoded {{SCR0}} of {{N}} simulated monitor shots and {{SCR1}} of {{N}} print shots; that takes about {{SCRMS0}} s per photo on a PC core, and 24 to 55 s on a phone. Real hardware is harsher than the simulator, see the limits below.
7. **Drones are fine.** Aerial scenes (fields, scrub, solar panels) are almost pure texture: the 8 DJI photos survived {{DJI_AVG}} of {{NA}} edits on average, on par with the flagship phones ({{IPH_AVG}}); the weakest group was the budget LAVA phone ({{LAVA_AVG}}), whose photos here were the smoothest and darkest.

## ⚙️ How it works

<div align="center">
  <img src="assets/fig01_pipeline.png" width="100%" alt="Write and read pipeline"/>
</div>

<table>
<tr>
<td width="25%" valign="top">

**🎨 Layer 1: colour**

~10,000 tiles in Cb/Cr, ±(≤2) grey levels. 118 bits: location, altitude, time, 0.1 s, live/manual, CRC-16. Rate-½ convolutional code → 248 coded bits, ~32 tiles per bit.

</td>
<td width="25%" valign="top">

**💡 Layer 2: brightness**

~50,000 tiles in luma carry only the location (60 bits, ~10 m). Weaker, but it **survives black &amp; white**.

</td>
<td width="25%" valign="top">

**📍 Pilot tiles**

20% of tiles have a known sign. The reader correlates against them to detect, to align after a crop, to fix a tilted photo of a screen, and as a built-in false-alarm test.

</td>
<td width="25%" valign="top">

**🛡️ Self-test**

At capture the engine squeezes a copy like a chat app would, reads it, and strengthens the mark (up to ×1.9) if it did not survive.

</td>
</tr>
</table>

<div align="center">
  <img src="assets/fig02_anatomy.png" width="92%" alt="Tile grid with pilot tiles and the payload bit layout"/>
</div>

<div align="center">
  <img src="assets/fig07_case_study.png" width="85%" alt="One photo through eight stages with decoded records"/>
  <p><em>Case study: photo #1 through eight stages. The unmarked original returns "no mark", never a guess.</em></p>
</div>

Exact bit layout: [FORMAT-SPEC.md](engine/FORMAT-SPEC.md). The JavaScript implementation in [`reference/`](reference/) wins over the text if they ever disagree.

## ⚠️ Honest limits

<table>
<tr>
<td width="50%" valign="top">

- **Not a proof of authenticity.** Anyone with the engine can write a mark. It keeps *honest* metadata alive; a tamper hint fires if the two layers disagree by more than 30 m.
- **Flat, dark or smooth photos are fragile** (see the leaderboard): fine at chat size, lost at small sizes unless the self-test strengthens them.
- **Black &amp; white** keeps the location only, and very dark or flat photos can lose even that.
- **Crops:** centred crops down to about 36 % of the area were found; a 20 % or quarter-frame crop was not.

</td>
<td width="50%" valign="top">

- **Photos of screens:** the simulator is kinder than reality. A real monitor photo read (z = 12.7, 24 s on the phone); another, shown at 100 % zoom with strong moiré, was lost.
- **Not supported:** heavy denoising or AI retouching, pictures below 64 px, times before 2026-01-01 or after ~2043.
- **Benchmark scope:** attacks ran on the JavaScript reference engine at default strength, on {{N}} photos from {{NDEV}} cameras. Treat percentages as indicative, not as a guarantee for every scene.

</td>
</tr>
</table>

## 🚀 Quick start

```kotlin
// settings.gradle.kts → include(":engine")   |   app → implementation(project(":engine"))
// 1. At capture, after your overlay is drawn and before JPEG encoding (background thread):
val record = MarkRecord(lat, lon, altitudeMeters = alt, timeSeconds = Math.floorDiv(shutterMillis, 1000L),
                        tenth = (Math.floorMod(shutterMillis, 1000L) / 100).toInt())
InvisibleMark.mark(finalBitmap, record)            // null = failed: save the photo unmarked

// 2. Any time later, on any copy:
val read = InvisibleMark.read(context, uri, ReadOptions(searchCrops = true))
when (read?.result?.status) {                      // OK · PART · DAMAGED · NONE
    MarkStatus.OK   -> read.result.layer1          // lat, lon, alt, time, manual flag
    MarkStatus.PART -> read.result.layer2          // location only, ~10 m
    else -> { /* tell the user. never invent a value */ }
}
```

Full API, four integration flows and an AI-assistant checklist: [`engine/ENGINE.md`](engine/ENGINE.md).

| | Measured on a real phone (12 MP) |
|---|---|
| Mark (embed + self-test) | ~0.65 s + ~0.56 s |
| Read | ~0.15 s |
| Read with crop search | 2.5 to 4.6 s |
| Read a photo of a screen / print | 24 s (clean case) to ~55 s |

## 📦 What's in the box

```
engine/       the library: source, ENGINE.md, FORMAT-SPEC.md, 29 JVM tests with cross-language fixtures
dist/         prebuilt ghostmark-1.1.0.aar (97 KB)
trial/        small Compose sample app: Capture, Read, Screen/print with a corner editor
reference/    JavaScript reference implementation + CLI
samples/      demo photos, marked (1600 px, EXIF-free): send them through any messenger and read them back
tools/        run_experiments.py → make_figures.py → make_showcase.py → make_readme.py (builds this page from the data)
assets/       README media
```

```
gradlew :engine:testDebugUnitTest :engine:assembleRelease :trial:assembleDebug
cd tools && python run_experiments.py && python make_figures.py && python make_showcase.py && python make_readme.py
# needs numpy, opencv-python, matplotlib, pillow, pillow-heif, node. Set MARK_PHOTOS=<folder> to use your own photos.
```

Benchmark note: attacks ran on the JavaScript reference engine, which shares format and maths with the Kotlin engine (cross-checked by shared fixtures in both directions). Photos above 24 MP are downscaled to a 4096 px long edge first, as the Android engine does. On-phone timings and the two real monitor photos come from the Kotlin engine on a 1220 × 2712 Android phone.

## 📜 Licence and credit

Copyright © 2026 **Vijay Parmar**. Free to use, modify and ship inside your own apps, including commercial ones, **as long as you credit the author**, for example in your About screen:

> Uses Ghostmark by Vijay Parmar, github.com/thevijayparmar/Ghostmark-Image

The engine may not be resold or republished as a stand-alone library or SDK. The binding text is in [LICENSE](LICENSE).

**Contributors:** [Vijay Parmar](https://github.com/thevijayparmar) · [Prathvi Bhatti](https://github.com/poronita) (co-author)

<div align="center">
  <br/>
  <sub>👻 Built by <a href="https://github.com/thevijayparmar">Vijay Parmar</a> · the photo remembers, even when the file forgets.</sub>
</div>
