# Dev.to / Medium article (draft outline + opening)

**Title options**
* I hid GPS inside a photo so WhatsApp can't strip it
* Where did this photo come from? Putting the answer inside the pixels

**Outline**
1. The problem: chat apps strip EXIF (one screenshot of a WhatsApp photo's "details" tab).
2. The idea in one picture: `assets/hero_reveal.gif`.
3. How it works without the maths: tiles, pilots, error correction (`assets/fig01_pipeline.png`, `fig02_anatomy.png`).
4. The black-and-white trick: two layers, why luma survives (`assets/fig16_bw_why.png`, `bw_demo.gif`).
5. 40 photos, 480 edits: the survival matrix (`fig04`), the scoreboard, and the failures (`photo_wall.jpg`).
6. What it cannot do (not tamper-proof; B&W + crop; fog and night).
7. Try it: 5 lines of Python, 5 lines of Kotlin.
8. Links: repo, FORMAT-SPEC, how to add a Swift/Rust port.

**Opening paragraph (draft)**
Send a photo on WhatsApp and look at its details: the GPS, the time, the camera are gone. The app deleted them to save space and protect your privacy. But if that photo is an inspection record, you just lost your evidence. I wanted the photo itself to remember. So I hid the record inside the pixels...
