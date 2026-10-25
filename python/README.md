# 🐍 ghostmark (Python)

The **Python engine** of [Ghostmark-Image](../README.md): an invisible two-layer photo mark that hides location, altitude and UTC time inside the pixels of a photo, so the record survives chat apps, screenshots, crops and black-and-white filters.

It writes and reads **exactly the same mark** as the Android (Kotlin) engine and the JavaScript reference engine: a photo marked on a phone can be read by a Python server, and the other way round.

* depends on **numpy** only (Pillow optional: file helpers and the capture-time self-test)
* Python 3.9+
* no network, no native code, no model files

## Install

```bash
pip install "ghostmark-image[files]"   # from PyPI; [files] adds Pillow
pip install -e ./python[test]    # for development and the tests
```

## 30-second tour

```python
import numpy as np
from PIL import Image
import ghostmark as gm

rgb = np.asarray(Image.open("photo.jpg").convert("RGB"))      # uint8, shape (H, W, 3)

# write: the self-test squeezes a copy like a chat app and strengthens the mark only if needed
marked, strength = gm.mark_verified(rgb, gm.Record(lat=12.9716, lon=77.5946, alt=920, t=1792929600))
Image.fromarray(marked).save("marked.jpg", quality=95, subsampling=0)

# read any copy: WhatsApp, a screenshot, a black-and-white version ...
r = gm.read(np.asarray(Image.open("copy.jpg").convert("RGB")))
print(r.status)      # 'ok' full record | 'part' location only (about 10 m) | 'damaged' | 'none'
print(r.location)    # (lat, lon) from the best layer that was read, or None
print(r.time, r.id)  # UTC datetime and a 10-letter ID (full record only)
```

Command line:

```bash
ghostmark mark photo.jpg marked.jpg --lat 12.9716 --lon 77.5946 --alt 920 --time 2026-10-25T12:00:00Z
ghostmark read copy.jpg                   # exit code 0 = ok or part, 2 = damaged or none
ghostmark read cropped.jpg --crop         # the picture is a crop of the original
ghostmark read screen.jpg --corners 830,155,2312,135,2219,2126,808,2016   # photo of a screen or print (TL,TR,BR,BL)
```

## API

| Function | What it does |
|---|---|
| `Record(lat, lon, alt, t, tenth, manual)` | what to hide; `t` is unix seconds or a `datetime`; leave a field `None` for "not known" |
| `mark(rgb, record, strength=1.0)` | returns a marked copy (about 0.1 grey levels of change on average; at most 10) |
| `mark_verified(rgb, record)` | `mark` plus the capture-time self-test (chat-app copy, strengths 1.0, 1.4, 1.9). Returns `(marked, strength)` |
| `read(rgb, try_turns=False)` | reads a full-frame picture of any size; `try_turns=True` also tries it turned by 90, 270 and 180 degrees; returns a `ReadResult` |
| `read_cropped(rgb)` | finds where a plain crop (no turn, no tilt) sat inside the original frame, then reads it |
| `read_perspective(rgb, corners)` | reads a phone photo of a screen or a print; `corners` are four rough taps, TL TR BR BL |
| `auto_corners(rgb)` | first guess for those corners (bright picture on a dark surround) |
| `mark_file(src, dst, record)` / `read_file(path)` | file helpers (Pillow); `mark_file` keeps EXIF |

`ReadResult`: `status`, `l1` (full record dict), `l2` (location dict), `z1`/`z2` (detection scores; above 3.5 means "a mark is here"), `.ok`, `.location`, `.time`, `.id`.

**Statuses are honest.** A CRC and an error-correcting code guard every value. If a layer cannot be read it is `None`; the engine never returns a plausible-looking wrong coordinate.

## Interoperability, tested

* The Android engine's test fixtures (marked photos written by the JavaScript reference engine) are read by this package: `pytest -q` fails if they are not.
* On the 40 photos of the benchmark, Python-marked copies were read by the JavaScript engine and the reverse (see the main README for the numbers).
* Both engines produce the same pixels to within one grey level (rounding of the final clamp).

## Tests

```bash
cd python
pip install -e .[test]
pytest -q          # 14 tests, ~10 s
```

## Limits (read these)

* **Speed:** pure numpy. Marking and reading a 12 MP photo takes seconds, not milliseconds (numbers in the main README). `read_perspective` runs about 1,300 trial alignments and takes about a minute; use it for a few photos, not for batches.
* **No rotation inside the crop and screen readers:** `read(..., try_turns=True)` handles a picture saved sideways, but `read_cropped` and `read_perspective` expect the picture upright.
* **Same physical limits as the format:** photos below ~64 px, heavy denoising/AI retouching and small crops (below about a third of the area) are not read; black-and-white copies give the location only.
* It is not a proof of authenticity: anyone with the engine can write a mark.

## Licence

Apache License 2.0, see [`../LICENSE`](../LICENSE) and [`../NOTICE`](../NOTICE). Free for any use, including commercial; keep the NOTICE with your distribution. A line of credit is appreciated:

> Uses Ghostmark by Vijay Parmar, github.com/thevijayparmar/Ghostmark-Image
