"""Writes a marked, EXIF-free 1600 px demo copy of every test photo into ../samples/."""
import os, cv2
import wmlib as W
OUT = os.path.join(W.HERE, '..', 'samples'); os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))
for i, f in enumerate(W.photo_files()):
    mk, _ = W.embed(W.load(f))
    cv2.imwrite(os.path.join(OUT, 'demo_%02d_marked.jpg' % (i + 1)), cv2.cvtColor(W.resize_long(mk, 1600), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
print('samples written')
