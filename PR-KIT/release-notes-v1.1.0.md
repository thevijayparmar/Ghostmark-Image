# Ghostmark 1.1.0: now with Python, black-and-white proof, and Apache-2.0

**Photos that remember where and when they were taken, even after the metadata is gone.**

## New
* 🐍 **Python engine** (`python/`): numpy only, same mark format as Android. `pip install "ghostmark-image[files]"`, CLI `ghostmark mark|read`.
* 🌗 **Black-and-white study:** the brightness layer returned the location after a grey filter plus a chat app for 29 of 40 photos (39 of 40 when the mark is written at 2x strength).
* 📸 **Benchmark widened** to 40 photos from 11 cameras, 480 attacked copies: 371 full records, 0 wrong values, 0 false alarms in 320 unmarked reads.
* ⚖️ **Apache-2.0** licence (was a custom attribution licence). Keep the NOTICE file.

## Files
* `ghostmark-1.1.0.aar` (97 KB, no dependencies) for Android
* `ghostmark-python-1.1.0.zip` for Python

## Honest limits
Not tamper-proof. Black-and-white copies give the location only. Dark, foggy and flat photos are the weak spot. Small crops (below about a third of the frame) are not found.
