# Show HN

**Title:** Show HN: Ghostmark – invisible photo watermark for location and time that survives WhatsApp

**URL:** https://github.com/thevijayparmar/Ghostmark-Image

**First comment (post it yourself right after submitting):**
Hi HN. Chat apps and screenshots strip EXIF, so a shared photo loses where and when it was taken. Ghostmark writes that record into the pixels instead: two independent layers (colour carries the full record, brightness carries the location so it survives a black-and-white filter), CRC + convolutional code so a read is either right or "damaged".

What I measured, 40 photos / 11 cameras / 480 edited copies: 371 full records, 0 wrong values, 0 false alarms on 320 unmarked reads. Where it fails is in the README too: fog, night, flat sky, small crops, and black-and-white-plus-crop.

It is not tamper-proof: anyone with the engine can write a mark. It keeps honest metadata alive, nothing more. Engines in Kotlin, Python (numpy only) and JS, all reading each other's marks. Format spec in engine/FORMAT-SPEC.md. Happy to answer anything about the signal processing.

(Tips: post on a weekday morning US time; stay online for 2-3 hours; do not ask friends to upvote.)
