"""Helpers: drive the JS reference engine (reference/wm-cli.js) from Python with OpenCV attacks."""
import json, os, subprocess, tempfile, uuid, glob
import numpy as np, cv2
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.join(HERE, '..', 'reference', 'wm-cli.js')
PHOTOS = os.environ.get('MARK_PHOTOS', os.path.join(HERE, '..', '..', 'test-photos'))
TMP = tempfile.mkdtemp(prefix='mark_')
# Demonstration record (not a real place of interest): Bengaluru, 2026-10-25 12:00:00.4 UTC
PAYLOAD = dict(lat=12.971599, lon=77.594566, alt=920, t=1792929600, tenth=4, manual=0)


def photo_files():
    fs = glob.glob(PHOTOS + '/*.jpg') + glob.glob(PHOTOS + '/*.JPG')
    return sorted(set(fs), key=lambda p: int(p.split('(')[1].split(')')[0]))


def load(path):
    return np.asarray(ImageOps.exif_transpose(Image.open(path)).convert('RGB'))


def node(*args):
    r = subprocess.run(['node', CLI] + [str(a) for a in args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


def _tmp(ext):
    return os.path.join(TMP, uuid.uuid4().hex + ext)


def embed(rgb, payload=PAYLOAD, strength=None):
    h, w = rgb.shape[:2]
    pi, po, pj = _tmp('.rgba'), _tmp('.rgba'), _tmp('.json')
    np.dstack([rgb, np.full((h, w), 255, np.uint8)]).tofile(pi)
    json.dump(payload, open(pj, 'w'))
    t = node('embed', pi, w, h, pj, po)
    out = np.fromfile(po, np.uint8).reshape(h, w, 4)[..., :3]
    for f in (pi, po, pj):
        os.remove(f)
    return out, t['ms']


def read(rgb, cmd='read', extra=None):
    h, w = rgb.shape[:2]
    pi = _tmp('.rgba')
    np.dstack([rgb, np.full((h, w), 255, np.uint8)]).tofile(pi)
    args = [cmd, pi, w, h]
    pj = None
    if extra is not None:
        pj = _tmp('.json'); json.dump(extra, open(pj, 'w')); args.append(pj)
    r = node(*args)
    os.remove(pi)
    if pj:
        os.remove(pj)
    return r


def jpeg(rgb, q):
    ok, buf = cv2.imencode('.jpg', cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, q])
    return cv2.cvtColor(cv2.imdecode(buf, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB), len(buf)


def resize_long(rgb, L):
    h, w = rgb.shape[:2]; s = L / max(h, w)
    return rgb if s >= 1 else cv2.resize(rgb, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)


def correct(r, payload=PAYLOAD):
    """(layer 1 exactly right, layer 2 right to about 10 m)"""
    l1, l2 = r.get('l1'), r.get('l2')
    ok1 = l1 is not None and abs(l1['lat'] - payload['lat']) < 2e-5 and abs(l1['lon'] - payload['lon']) < 2e-5 \
        and l1['alt'] == payload['alt'] and l1['t'] == payload['t'] and l1['tenth'] == payload['tenth'] and l1['manual'] == payload['manual']
    ok2 = l2 is not None and l2.get('lat') is not None and abs(l2['lat'] - payload['lat']) < 1.2e-4 and abs(l2['lon'] - payload['lon']) < 1.2e-4
    return ok1, ok2


def psnr(a, b):
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    return 99.0 if mse == 0 else 10 * np.log10(255 ** 2 / mse)
