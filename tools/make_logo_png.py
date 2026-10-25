"""Rasterises assets/logo.svg's shapes to assets/logo.png (512 px, supersampled) with Pillow, no SVG library needed."""
import os
from PIL import Image, ImageDraw
import wmlib as W

S = 4
A = os.path.join(W.HERE, '..', 'assets')


def bez(p0, p1, p2, p3=None, n=24):
    out = []
    for i in range(1, n + 1):
        t = i / n
        if p3 is None:
            out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))
        else:
            u = 1 - t
            out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0], u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out


pts = [(136, 384), (136, 236)]
pts += bez((136, 236), (136, 152), (190, 100), (256, 100)) + bez((256, 100), (322, 100), (376, 152), (376, 236)) + [(376, 384)]
for a, c, b in [((376, 384), (346, 424), (316, 384)), ((316, 384), (286, 344), (256, 384)), ((256, 384), (226, 424), (196, 384)), ((196, 384), (166, 344), (136, 384))]:
    pts += bez(a, c, b)
im = Image.new('RGBA', (512 * S, 512 * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
d.rounded_rectangle((0, 0, 512 * S, 512 * S), 112 * S, fill=(13, 17, 23, 255))
d.polygon([(x * S, y * S) for x, y in pts], fill=(240, 246, 252, 255))
for cx in (216, 296): d.ellipse(((cx - 20) * S, (224 - 20) * S, (cx + 20) * S, (224 + 20) * S), fill=(13, 17, 23, 255))
CY, PU = (56, 189, 248, 255), (167, 139, 250, 255)
for x, y, w, c, r in [(200, 282, 26, CY, 5), (234, 282, 26, PU, 5), (268, 282, 26, CY, 5), (217, 316, 26, PU, 5), (251, 316, 26, CY, 5), (392, 196, 22, CY, 4), (420, 236, 16, PU, 3),
                      (396, 274, 12, (56, 189, 248, 180), 2), (428, 306, 9, (167, 139, 250, 150), 2)]:
    d.rounded_rectangle((x * S, y * S, (x + w) * S, (y + w) * S), r * S, fill=c)
im.resize((512, 512), Image.LANCZOS).save(os.path.join(A, 'logo.png'))
print('logo.png written')
