"""Ghostmark-Image for Python: an invisible two-layer photo mark (location, time, altitude) that survives chat apps.

    import ghostmark as gm
    rec = gm.Record(lat=12.9716, lon=77.5946, alt=920, t=1792929600)
    marked = gm.mark(rgb, rec)            # rgb: uint8 array (H, W, 3); returns a marked copy
    result = gm.read(marked)              # result.status: 'ok' | 'part' | 'damaged' | 'none'

Same mark format as the Android (Kotlin) and JavaScript engines; any engine reads any engine's marks.
Uses Ghostmark by Vijay Parmar - github.com/thevijayparmar/Ghostmark-Image
"""
from ._api import Record, ReadResult, mark, mark_verified, read, read_cropped, read_perspective, auto_corners, mark_file, read_file, __version__
from ._core import EPOCH, DETECT_Z, layer_disagreement_meters

__all__ = ['Record', 'ReadResult', 'mark', 'mark_verified', 'read', 'read_cropped', 'read_perspective', 'auto_corners',
           'mark_file', 'read_file', 'EPOCH', 'DETECT_Z', 'layer_disagreement_meters', '__version__']
