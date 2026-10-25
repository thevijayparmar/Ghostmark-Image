<div align="center">
  <img src="assets/banner.jpg" width="100%" alt="Ghostmark: photos that remember where and when, even after the metadata is gone"/>
</div>

<br>

<div align="center">

  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-orange?logo=apache&logoColor=white" alt="Apache 2.0 licence"></a>
  <img src="https://img.shields.io/badge/Android-minSdk%2026-3DDC84?logo=android&logoColor=white" alt="Android minSdk 26">
  <img src="https://img.shields.io/badge/Kotlin-Android%20engine-7F52FF?logo=kotlin&logoColor=white" alt="Kotlin">
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/JavaScript-reference-F7DF1E?logo=javascript&logoColor=black" alt="JavaScript reference engine">
  <a href="https://github.com/thevijayparmar/Ghostmark-Image/actions/workflows/python.yml"><img src="https://github.com/thevijayparmar/Ghostmark-Image/actions/workflows/python.yml/badge.svg" alt="Python CI"></a>
  <img src="https://img.shields.io/badge/Dependencies-0-2F7CF6" alt="Zero dependencies">
  <img src="https://img.shields.io/badge/AAR-97%20KB-2F7CF6" alt="97 KB AAR">
  <img src="https://img.shields.io/badge/Tests-29%20Kotlin%20%2B%2014%20Python-3fb950" alt="42 tests passing">
  <img src="https://img.shields.io/badge/Test%20photos-{{N}}-ff69b4" alt="{{N}} test photos">
  <img src="https://img.shields.io/badge/Cameras-{{NDEV}}-00b8d9" alt="{{NDEV}} cameras">
  <img src="https://img.shields.io/badge/Edits%20tested-{{TOT}}-blueviolet" alt="{{TOT}} edits tested">

</div>

<br>

<div align="center">
  <img src="assets/logo.svg" width="132" alt="Ghostmark logo"/>
  <h1>Ghostmark</h1>
  <p><strong>Photos that remember where and when they were taken, even after the metadata is gone.</strong></p>
  <p>A library that hides <b>location (~1 m), altitude, UTC time (0.1 s)</b> and a live/manual flag <i>inside the pixels</i> of a photo, invisibly, so the record survives WhatsApp, screenshots, crops, <b>black &amp; white filters</b> and even a phone photo of a screen.</p>
  <p><b>One mark format, three engines:</b> 🤖 Android (Kotlin) · 🐍 Python (new) · 🌐 JavaScript reference</p>
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

> ⏳ **Heads up: this page is long and animation-heavy on purpose.** It is a lab notebook as much as a README: {{N}} real photos from {{NDEV}} different cameras (phones and drones), {{TOT}} attacked copies, {{NCHARTS}} charts, {{N}} animated test reels and a black-and-white special. Skim the pictures, or read every number. Everything is generated from scripts in [`tools/`](tools/), nothing is typed by hand.

<div align="center">
  <img src="assets/stats_strip.png" width="100%" alt="Headline numbers"/>
</div>

---

## 📖 Contents

| | | |
|---|---|---|
| [🎬 See it in action](#-see-it-in-action) | [🌗 Black & white special](#-black--white-the-second-layer) | [📊 The lab results](#-the-lab-results) |
| [🧪 The test bench](#-the-test-bench) | [🎞️ The gauntlet (reels)](#️-the-gauntlet) | [🔬 What we learned](#-what-we-learned) |
| [🧬 The hidden layer](#-the-hidden-layer-made-visible) | [🏆 Leaderboard](#-leaderboard-who-survives-best) | [⚙️ How it works](#️-how-it-works) |
| [🐍 Ghostmark for Python](#-ghostmark-for-python) | [🚀 Quick start](#-quick-start) | [⚠️ Honest limits](#️-honest-limits) |

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

## 🧪 The test bench

Not studio shots: **{{N}} real photos from {{NDEV}} camera models**: iPhone 16 Pro and 17 Pro, OnePlus, vivo, realme, a budget LAVA, and DJI drones, from {{MP_MIN}} MP to {{MP_MAX}} MP. Stone carvings, rebar, steel rigs, solar panels, temple spires, a castle in fog, a storm over a night sea, a moon over a bay, rain-soaked streets, blossoms, a plate of fruit and a café table. Easy, textured scenes **and** the awkward ones: flat sky, dark water, fog, night.

<div align="center">
  <img src="assets/photo_wall.jpg" width="100%" alt="All test photos with their hidden layer and the results of 12 edits as coloured dots"/>
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

## 🎞️ The gauntlet

Every photo was marked with the same demo record (12.97160 N, 77.59457 E, 920 m, 2026-10-25 12:00:00.4 UTC) and put through the **same nine steps**: original, hidden layer, saved, chat app, 600 px thumbnail, black &amp; white, a quarter painted over, a 10 % crop, and a (simulated) phone photo of a monitor. Green = full record back, orange = location only, red = mark present but unreadable. **Failures are shown on purpose.**

{{GALLERY}}

## 🌗 Black & white: the second layer

> **The question everyone asks:** *"what if someone just turns the photo black &amp; white?"*  Colour is where the full record lives, so a grey photo loses it. That is exactly why Ghostmark writes a **second, independent layer into the brightness** of the picture: it is the part of the photo a black-and-white filter *keeps*.

<div align="center">
  <img src="assets/bw_demo.webp" width="80%" alt="A marked photo is turned black and white and sent through a chat app; the colour layer is gone, the brightness layer is magnified, and the location is read back"/>
  <p><em>Photo #11, start to finish: marked in colour → turned black &amp; white → squeezed through a chat app (1600 px, JPEG q70) → the brightness layer, magnified ×20 → the location, read back. All of it measured, not mocked up.</em></p>
</div>

### 🔬 Why it survives

<div align="center">
  <img src="assets/fig16_bw_why.png" width="100%" alt="The colour layer and the brightness layer shown separately, and what is left after black and white plus a chat app"/>
  <p><em>The two layers are orthogonal by construction. Panel 2 is the colour layer: a black-and-white filter throws it away. Panel 3 is the brightness layer: a grey picture <b>is</b> brightness, so the filter hands it straight through. Panel 4 is the black-and-white copy that went through a chat app, minus the same copy of the unmarked photo: the pattern is still there.</em></p>
</div>

The brightness layer is built to be the survivor, not the star: ~50,000 small tiles, a 60-bit payload (**location only, about 10 m**), the same pilot tiles, the same error-correcting code, a higher amplitude (up to 4.5 grey levels, still invisible at 100 %). It cannot carry time or altitude, there is no room, but a location that survives the filters people actually apply is the part that matters most.

### 🖼️ All {{N}} photos, turned black &amp; white and sent through a chat app

<div align="center">
  <img src="assets/fig14_bw_wall.jpg" width="100%" alt="Every test photo converted to black and white, with the location read back or not"/>
  <p><em>Every test photo as the receiver sees it: grey, 1600 px, JPEG q70. <b>Green frame</b> = the location was read back (the number is how many metres off it was), <b>red frame</b> = not read. The red ones are mostly the dark, foggy and flat scenes, the same weakness we saw in colour.</em></p>
</div>

**{{BW_CHAT_OK}} of {{N}}** photos gave their location back after a black-and-white filter and a chat app, at the default strength, and every one of those reads landed on the same spot, **{{BW_MEDERR}} m** from the true position: that is the rounding of the 60-bit location grid, not noise.

### 🧪 Nine ways to go grey

Not every "black &amp; white" is the same. A phone filter, a photo editor, a red-filter look and a plain desaturate all mix the colour channels differently, and each is followed by a different delivery path. We tried nine, on every photo:

<div align="center">
  <img src="assets/fig15_bw_matrix.png" width="100%" alt="Matrix of photos by black and white variant showing whether the location was read"/>
</div>

{{BW_TABLE}}

<div align="center">
  <img src="assets/fig17_bw_stats.png" width="100%" alt="Photos that keep their location per variant, signal strength per variant, and location error histogram"/>
  <p><em>Left: how many photos keep their location. Middle: signal strength per variant against the 3.5 detection limit. Right: signal strength against scene texture for the black-and-white chat copy: busy scenes keep their location, flat and dark ones do not.</em></p>
</div>

### 📌 What the black &amp; white study taught us

1. **It works, with a limit you can see.** {{BW_CHAT_OK}} of {{N}} photos at default strength after grey + chat app; the failures are the low-texture photos, the same ones that are fragile in colour ({{BW_FAIL_LIST}}).
2. **A stronger mark buys most of it back.** Written at 1.5× the location was read for **{{BW_S15}} of {{N}}** photos, at 2× for **{{BW_S20}} of {{N}}** (mean PSNR {{BW_P15}} dB and {{BW_P20}} dB instead of the default {{PSNR_MED}} dB). The Android self-test today checks the colour path (a chat app); teaching it to check a grey copy too is the obvious next step.
3. **Heavy sharing hurts more than the grey, and a crop is a hard stop.** The 800 px / q40 thumbnail reads {{BW_THUMB}} of {{N}}. A black-and-white copy that is *also cropped* reads {{BW_CROP}} of {{N}}: the crop search finds the original frame by its colour pilots, and a grey picture has none. Full-frame grey copies are fine; grey crops are not.
4. **The grey recipe matters a little.** Equal-weight grey: {{BW_AVG}}, red filter: {{BW_RED}}, green filter: {{BW_GREEN}}, against {{BW_CHAT_OK}} for the standard luma conversion. A red or green filter lets some of the colour layer leak into the grey picture as noise, an equal-weight grey slightly reweights the brightness layer.
5. **Never a wrong location.** Every location that passed the CRC was within **{{BW_MAXERR}} m** of the truth (the format's grid is about 10 m), across {{BW_NREADS}} reads. The same grey + chat path on the **unmarked** originals returned "no mark" for {{BW_CTL}} of {{N}} photos.
6. **Two engines, same answer.** The Python engine read the {{BW_PYN}} grey copies and agreed with the JavaScript reference engine on status and location in **{{BW_PYAGREE}} of {{BW_PYN}}** cases.

## 📊 The lab results

### 🔥 Survival matrix: every photo × every edit

<div align="center">
  <img src="assets/fig04_survival_matrix.png" width="100%" alt="Survival matrix of all photos by 13 edits"/>
  <p><em>Each cell is the colour-layer detection strength z (threshold 3.5) or a status: <b>LOC</b> = location only (orange frame), <b>DMG</b> = mark present but unreadable (red frame), <b>--</b> = no mark found. Photo labels are coloured by camera.</em></p>
</div>

<table>
<tr>
<td width="55%" align="center">
  <img src="assets/fig13_totals.png" width="100%" alt="Signal strength per photo and totals donut"/>
</td>
<td width="45%" valign="middle">

### The scoreboard

**{{TOT}}** attacked copies ({{N}} photos × {{NA}} edits):

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

**Take-away:** the default (1×) already reads {{CHAT_OK}} of {{N}} photos after a chat app, but only {{SMALL1}} % survive an 800 px / q40 thumbnail. Raising the strength to 1.5× to 2× rescues most of the rest, at a visible cost (mean PSNR drops from {{PS1}} to {{PS2}} dB). That is exactly why Ghostmark ships a **capture-time self-test**: it simulates a chat app on the fresh photo and raises the strength (up to 1.9×) *only for the photos that need it*, so a textured temple stays subtle and a smooth plate gets help. In this benchmark {{N_SMALL_FAIL}} photos are lost at 800 px / q40 with the 1× mark, and **{{N_RESCUED}} of them are read in full once the strength is doubled**. The photos that fail even as a stored copy at 1× are {{FAIL_STORED}} (a dark plate of fruit, and blossoms against a dusk sky): exactly the case the self-test exists for.

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
3. **The luma layer earns its place.** Convert a photo to black &amp; white and the colour layer is gone for every photo. The brightness layer still returned the location for **{{BW_CHAT_OK}} of {{N}}** photos after a chat app (median error {{BW_MEDERR}} m), and **{{BW_S20}} of {{N}}** when the mark is written at twice the strength. That is the whole point of having two independent layers: see the [black &amp; white special](#-black--white-the-second-layer).
4. **Never a wrong answer.** The CRC-16 plus the convolutional code turned every uncertain read into an honest `PART` or `DAMAGED`, not into a plausible-looking wrong coordinate: **0 wrong values** across {{TOT}} edits and {{FP_TOTAL}} unmarked controls.
5. **A new camera generation, same behaviour.** The {{N_I17}} iPhone 17 Pro photos survived {{IPH17_AVG}} of {{NA}} edits on average (iPhone 16 Pro: {{IPH_AVG}}). Many of them are the hard kind (dusk, fog, night sea), which is why the average dropped when they joined the bench.
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
- **Black &amp; white** keeps the location only, and {{BW_LOST}} of {{N}} photos (mostly dark, foggy or flat) lose even that at default strength.
- **Crops:** centred crops down to about 36 % of the area were found; a 20 % or quarter-frame crop was not.

</td>
<td width="50%" valign="top">

- **Photos of screens:** the simulator is kinder than reality. A real monitor photo read (z = 12.7, 24 s on the phone); another, shown at 100 % zoom with strong moiré, was lost.
- **Not supported:** heavy denoising or AI retouching, pictures below 64 px, times before 2026-01-01 or after ~2043.
- **Benchmark scope:** attacks ran on the JavaScript reference engine at default strength, on {{N}} photos from {{NDEV}} cameras (the Python engine reproduced the black-and-white reads exactly, {{BW_PYAGREE}} of {{BW_PYN}}).
- **Python engine:** reading a photo of a screen takes about a minute in pure Python; `read_cropped` and `read_perspective` expect an upright picture; the Android engine is the one phone-tested in the field. Treat percentages as indicative, not as a guarantee for every scene.

</td>
</tr>
</table>

## 🐍 Ghostmark for Python

The Android engine is the production one. For everything that is **not** an Android app (a server that checks uploaded photos, a batch tool for a survey team, a Jupyter notebook, a desktop app, a Raspberry Pi on a drone) there is now a **Python engine** in [`python/`](python/): the same mark format, written with `numpy` only (Pillow optional, for file helpers and the self-test).

<div align="center">
  <img src="assets/python_terminal.png" width="88%" alt="A terminal session: mark a photo, send it through a chat app, turn it black and white, read the record back"/>
  <p><em>A real run of <a href="python/examples/mark_and_read.py"><code>python/examples/mark_and_read.py</code></a> (output not edited).</em></p>
</div>

```bash
pip install ./python[files]          # numpy (+ Pillow for the file helpers); Python 3.9+
ghostmark mark photo.jpg marked.jpg --lat 12.9716 --lon 77.5946 --alt 920 --time 2026-10-25T12:00:00Z
ghostmark read shared_copy.jpg       # status ok = full record; part = location only (+-10 m); none = no mark
```

```python
import numpy as np
from PIL import Image
import ghostmark as gm

rgb = np.asarray(Image.open("photo.jpg").convert("RGB"))
marked, strength = gm.mark_verified(rgb, gm.Record(lat=12.9716, lon=77.5946, alt=920, t=1792929600))
Image.fromarray(marked).save("marked.jpg", quality=95, subsampling=0)

r = gm.read(np.asarray(Image.open("whatsapp_copy.jpg").convert("RGB")))
r.status      # 'ok' | 'part' | 'damaged' | 'none'
r.location    # (lat, lon) from the best layer that was read, or None
r.time        # UTC datetime (full record only)
```

| | Python engine |
|---|---|
| **Same format** | reads every mark the Kotlin and JavaScript engines write, and the other way round ({{PY_INTEROP}}) |
| **API** | `mark` · `mark_verified` (chat-app self-test) · `read` · `read_cropped` · `read_perspective` · `auto_corners` · `mark_file` · `read_file` · CLI `ghostmark` |
| **Dependencies** | `numpy` only; `Pillow` for files and the self-test |
| **Speed (12 MP, one core)** | mark ≈ {{PY_MARK_S}} s · read ≈ {{PY_READ_S}} s · crop search ≈ {{PY_CROP_S}} s · screen/print ≈ {{PY_PERSP_S}} s |
| **Tests** | 14 `pytest` tests, including the Android engine's cross-language fixtures |
| **Not in the Python port** | native speed (it is numpy, not NEON) |

Full guide: [`python/README.md`](python/README.md).

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

Full API, four integration flows and an AI-assistant checklist: [`engine/ENGINE.md`](engine/ENGINE.md). Not on Android? See [Ghostmark for Python](#-ghostmark-for-python).

| | Measured on a real phone (12 MP) |
|---|---|
| Mark (embed + self-test) | ~0.65 s + ~0.56 s |
| Read | ~0.15 s |
| Read with crop search | 2.5 to 4.6 s |
| Read a photo of a screen / print | 24 s (clean case) to ~55 s |

## 📦 What's in the box

```
engine/       the Android library: source, ENGINE.md, FORMAT-SPEC.md, 29 JVM tests with cross-language fixtures
python/       the Python engine (numpy only): package, CLI, 14 tests, examples
PR-KIT/       launch toolkit: social preview, post drafts, release notes, FAQ (not needed to use the library)
dist/         prebuilt ghostmark-1.1.0.aar (97 KB)
trial/        small Compose sample app: Capture, Read, Screen/print with a corner editor
reference/    JavaScript reference implementation + CLI
samples/      demo photos, marked (1600 px, EXIF-free): send them through any messenger and read them back
tools/        run_experiments.py → run_bw.py → make_figures.py → make_bw.py → make_showcase.py → make_readme.py (builds this page from the data)
assets/       README media
```

```
gradlew :engine:testDebugUnitTest :engine:assembleRelease :trial:assembleDebug
cd python && pip install -e .[test] && pytest -q
cd tools && python run_experiments.py && python run_bw.py && python make_figures.py && python make_bw.py && python make_showcase.py && python make_readme.py
# needs numpy, opencv-python, matplotlib, pillow, node. Set MARK_PHOTOS=<folder> to use your own photos.
```

Benchmark note: attacks ran on the JavaScript reference engine, which shares format and maths with the Kotlin engine (cross-checked by shared fixtures in both directions). Photos above 24 MP are downscaled to a 4096 px long edge first, as the Android engine does (that affects only the 50 MP photo). On-phone timings and the two real monitor photos come from the Kotlin engine on a 1220 × 2712 Android phone.

## 📜 Licence and credit

**Open source under the [Apache License 2.0](LICENSE).** Use it, change it, ship it, commercially or not, in any app or tool. The one thing we ask is the thing the licence already requires: **keep the credit.** Keep the [`NOTICE`](NOTICE) file with your distribution, and we would love a line in your About screen or docs:

> Uses Ghostmark by Vijay Parmar, github.com/thevijayparmar/Ghostmark-Image

Copyright © 2026 Vijay Parmar. Contributions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md).

**Contributors:** [Vijay Parmar](https://github.com/thevijayparmar) · [Prathvi Bhatti](https://github.com/poronita) (co-author)

<div align="center">
  <br/>
  <sub>👻 Built by <a href="https://github.com/thevijayparmar">Vijay Parmar</a> · the photo remembers, even when the file forgets.</sub>
</div>
