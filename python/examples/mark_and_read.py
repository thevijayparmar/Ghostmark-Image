"""Mark a photo, simulate a chat app and a black-and-white filter, and read the record back.

    python examples/mark_and_read.py path/to/photo.jpg
"""
import io
import sys

import numpy as np
from PIL import Image

import ghostmark as gm

src = sys.argv[1]
rgb = np.asarray(Image.open(src).convert('RGB'))
record = gm.Record(lat=12.971599, lon=77.594566, alt=920, t=1792929600, tenth=4)

marked, strength = gm.mark_verified(rgb, record)           # self-test picks the weakest strength that survives a chat app
print('marked, strength', strength, ' max change', int(np.abs(marked.astype(int) - rgb).max()), 'grey levels')


def whatsapp(a, long_edge=1600, q=70):
    im = Image.fromarray(a)
    s = min(1.0, long_edge / max(im.size))
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=q)
    return np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert('RGB'))


shared = whatsapp(marked)
r = gm.read(shared)
print('after a chat app :', r.status, r.location, r.time)

grey = np.asarray(Image.fromarray(shared).convert('L').convert('RGB'))
r = gm.read(whatsapp(grey))
print('after black&white:', r.status, r.location, '(time and altitude are gone, the location is not)')

print('unmarked photo   :', gm.read(rgb).status)
