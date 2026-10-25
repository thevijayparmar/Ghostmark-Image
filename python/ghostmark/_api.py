"""Friendly wrappers around the numpy core."""
import datetime
import io
from dataclasses import dataclass, field
from typing import Optional, Union

import numpy as np

from . import _core as core

__version__ = '1.1.0'
STRENGTH_STEPS = (1.0, 1.4, 1.9)  # the self-test tries these, weakest first (same as the Android engine)


@dataclass
class Record:
    """What to hide. Leave a field as None for "not known". t is unix seconds, a datetime, or None."""
    lat: Optional[float] = None
    lon: Optional[float] = None
    alt: Optional[float] = None
    t: Union[int, float, datetime.datetime, None] = None
    tenth: int = 0
    manual: bool = False

    def to_dict(self):
        t = self.t
        if isinstance(t, datetime.datetime):
            t = (t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)).timestamp()
        return dict(lat=self.lat, lon=self.lon, alt=self.alt, t=t, tenth=self.tenth, manual=int(bool(self.manual)))


@dataclass
class ReadResult:
    status: str                      # 'ok' (colour layer read), 'part' (location only), 'damaged' (mark seen, unreadable), 'none'
    l1: Optional[dict] = None        # full record: id, lat, lon, alt, t, tenth, manual
    l2: Optional[dict] = None        # location only (about 10 m): lat, lon
    z1: float = 0.0                  # detection scores (above 3.5 means "a mark is here")
    z2: float = 0.0
    extra: dict = field(default_factory=dict)  # 'crop' / 'perspective' details when those readers were used

    @property
    def ok(self):
        return self.status == 'ok'

    @property
    def location(self):
        """(lat, lon) from the best layer that was read, else None."""
        for layer in (self.l1, self.l2):
            if layer and layer.get('lat') is not None:
                return layer['lat'], layer['lon']
        return None

    @property
    def time(self):
        """UTC datetime of the capture, or None (layer 1 only)."""
        if self.l1 and self.l1.get('t') is not None:
            return datetime.datetime.fromtimestamp(self.l1['t'], datetime.timezone.utc)
        return None

    @property
    def id(self):
        return self.l1['id'] if self.l1 else None


def _wrap(r):
    if r is None:
        return None
    extra = {k: v for k, v in r.items() if k not in ('status', 'l1', 'l2', 'z1', 'z2')}
    return ReadResult(r['status'], r['l1'], r['l2'], float(r['z1']), float(r['z2']), extra)


def _check(rgb):
    a = np.asarray(rgb)
    if a.ndim != 3 or a.shape[2] < 3 or a.dtype != np.uint8:
        raise ValueError('expected a uint8 array of shape (H, W, 3)')
    return np.ascontiguousarray(a[..., :3])


def _rec(record):
    return record.to_dict() if isinstance(record, Record) else dict(record)


def mark(rgb, record, strength=1.0):
    """Returns a marked copy of the picture. strength 1.0 is the default; 2.0 is twice the amplitude (more robust, more visible)."""
    return core.embed(_check(rgb), _rec(record), strength, strength)


def _small(rgb, long_edge=1600):
    from PIL import Image
    im = Image.fromarray(rgb)
    s = min(1.0, long_edge / max(im.size))
    return rgb if s >= 1 else np.asarray(im.resize((max(8, int(im.width * s)), max(8, int(im.height * s))), Image.BILINEAR))


def _jpeg70(rgb):
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, 'JPEG', quality=70)
    return np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert('RGB'))


def mark_verified(rgb, record):
    """Like mark(), plus the capture-time self-test: squeeze a copy like a chat app (1600 px, JPEG 70), read it back,
    and use the weakest strength (1.0, 1.4, 1.9) that still reads in full. Needs Pillow. Returns (marked, strength)."""
    rgb, rec = _check(rgb), _rec(record)
    small = _small(rgb)
    strength = STRENGTH_STEPS[-1]
    for s in STRENGTH_STEPS:
        try:
            ok = core.read(_jpeg70(core.embed(small, rec, s, s)))['status'] == 'ok'
        except Exception:
            ok = True  # a failed test must not make the mark stronger than necessary
        if ok:
            strength = s
            break
    return core.embed(rgb, rec, strength, strength), strength


_RANK = {'ok': 3, 'part': 2, 'damaged': 1, 'none': 0}


def read(rgb, try_turns=False):
    """Reads a picture as it is (full frame, any size). try_turns=True also tries it turned by 90, 270 and 180 degrees
    (what the Android reader does for a photo that was saved sideways); result.extra['turned'] then says which.
    For crops use read_cropped, for photos of a screen read_perspective."""
    rgb = _check(rgb)
    best = core.read(rgb)
    turned = 0
    if try_turns and best['status'] != 'ok':
        for deg, k in ((90, 3), (270, 1), (180, 2)):
            r = core.read(np.ascontiguousarray(np.rot90(rgb, k)))
            if _RANK[r['status']] > _RANK[best['status']]:
                best, turned = r, deg
            if best['status'] == 'ok':
                break
    out = _wrap(best)
    if turned:
        out.extra['turned'] = turned
    return out


def read_cropped(rgb):
    """Reads a plain crop (no turn, no tilt) of a marked picture. Slower: it searches where the frame sat. None if nothing fits."""
    return _wrap(core.read_cropped(_check(rgb)))


def read_perspective(rgb, corners, aspect=None, on_progress=None):
    """Reads a phone photo of a screen or print. corners: four (x, y) points TL, TR, BR, BL in picture pixels (rough is fine)."""
    return _wrap(core.read_perspective(_check(rgb), corners, aspect, on_progress))


def auto_corners(rgb):
    """First guess at the corners of a bright picture on a dark surround; a starting point for read_perspective."""
    return core.auto_corners(_check(rgb))


def mark_file(src, dst, record, quality=95, self_test=True, strength=1.0, keep_exif=True):
    """Marks an image file and saves it as JPEG. Returns the strength used. Needs Pillow."""
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(src))
    exif = im.getexif() if keep_exif else None
    rgb = np.asarray(im.convert('RGB'))
    out, used = mark_verified(rgb, record) if self_test else (mark(rgb, record, strength), strength)
    kw = dict(quality=quality, subsampling=0)
    if exif:
        kw['exif'] = exif
    Image.fromarray(out).save(dst, 'JPEG', **kw)
    return used


def read_file(path, crop=False, corners=None):
    """Reads an image file. crop=True uses the crop reader; corners=[(x, y) x4] uses the screen/print reader."""
    from PIL import Image, ImageOps
    rgb = np.asarray(ImageOps.exif_transpose(Image.open(path)).convert('RGB'))
    if corners is not None:
        return read_perspective(rgb, corners)
    return read_cropped(rgb) if crop else read(rgb)
