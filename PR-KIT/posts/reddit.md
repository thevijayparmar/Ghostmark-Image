# Reddit posts (each written for its community; read the rules first, many limit self-promotion to a ratio)

## r/androiddev  (flair: Library)
**Title:** I made a 97 KB library that hides GPS + time inside a photo's pixels so it survives WhatsApp

Body:
Chat apps strip EXIF, so a shared photo loses where and when it was taken. Ghostmark writes the record into the pixels (two layers: colour = full record, brightness = location only), with a CRC and a convolutional code, so the reader returns the record or an honest "damaged", never a made-up value.

Kotlin, zero dependencies, no permissions, no network, minSdk 26. `InvisibleMark.mark(bitmap, record)` at capture, `InvisibleMark.read(context, uri)` later. It self-tests at capture (squeezes a copy like a chat app and strengthens the mark if needed).

Tested on 40 photos / 11 cameras: 371 of 480 edited copies gave the full record, 0 wrong values. Failures (fog, night, small crops) are in the README on purpose. Not tamper-proof.
Repo (Apache-2.0): github.com/thevijayparmar/Ghostmark-Image
Feedback on the API welcome.

## r/Python
**Title:** ghostmark: invisible photo watermark in pure numpy (location/time hidden in pixels, survives JPEG, resizing, black & white)

Body:
numpy-only port of an Android library. `mark_verified(rgb, Record(lat=..., lon=..., t=...))` / `read(rgb)`. Soft-decision Viterbi decoding, pilot tiles for detection (it says "no mark" on unmarked photos, 0 false alarms in 320 reads), crop and photo-of-screen readers. ~2 s to mark a 12 MP photo, 0.5 s to read. Same bytes as the Kotlin and JS engines: they read each other's marks (tested on 40 photos).
Code, charts, failures: github.com/thevijayparmar/Ghostmark-Image (folder `python/`). Critique of the signal processing welcome.

## r/opensource
**Title:** Apache-2.0 invisible photo watermark with three interoperable engines (Kotlin, Python, JS)

Body: short version of the above; stress that it is a small library built around a documented format (`engine/FORMAT-SPEC.md`), that contributions for new ports (Swift, Rust) are welcome, and that it is honest about limits.

## r/computervision
**Title:** Spread-spectrum watermark with pilot tiles + Viterbi: where it works and where it fails (40 photos, 480 edits)

Body:
10,000 chroma tiles (118-bit payload, rate-1/2 K=7 code) and 50,000 luma tiles (60 bits), 20% pilot tiles for detection/alignment, texture-adaptive amplitude. Results by edit, by camera, by texture (r = 0.66), false-alarm floor, strength-vs-PSNR trade-off. Black & white: the luma layer reads 29 of 40 at default strength, 39 of 40 at 2x. Crop+B&W fails (crop search uses colour pilots).
Everything is generated from scripts in `tools/`. What would you attack first?
