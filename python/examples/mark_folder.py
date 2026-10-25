"""Mark every JPEG in a folder with one location, then verify each one.

    python examples/mark_folder.py in_folder out_folder 12.9716 77.5946
"""
import os
import sys

import ghostmark as gm

src, dst, lat, lon = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
os.makedirs(dst, exist_ok=True)
for name in sorted(os.listdir(src)):
    if not name.lower().endswith(('.jpg', '.jpeg')):
        continue
    out = os.path.join(dst, name)
    strength = gm.mark_file(os.path.join(src, name), out, gm.Record(lat=lat, lon=lon, t=None))
    res = gm.read_file(out)
    print('%-32s strength %.1f -> %s' % (name, strength, res.status))
