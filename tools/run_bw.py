"""Black-and-white study: does the brightness layer (layer 2) survive when the colour is thrown away?
For every photo: mark, store as JPEG q95, then apply several black-and-white conversions and delivery paths.
Each copy is read with the JavaScript reference engine and with the Python port (they must agree).
Writes results/bw.json."""
import json, math, os, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np, cv2
import wmlib as W

sys.path.insert(0, os.path.join(W.HERE, '..', 'python'))
import ghostmark as gm

OUT = os.path.join(W.HERE, 'results'); files = W.photo_files()
P = W.PAYLOAD


def gray_rgb(img, mode='std'):
    f = img.astype(np.float32)
    g = {'std': f @ np.array([0.299, 0.587, 0.114], np.float32), 'avg': f.mean(2), 'red': f[..., 0], 'green': f[..., 1]}[mode]
    g = np.clip(g + .5, 0, 255).astype(np.uint8)
    return np.dstack([g, g, g])


def err_m(l2):
    if not l2 or l2.get('lat') is None: return None
    dy = (l2['lat'] - P['lat']) * 111320; dx = (l2['lon'] - P['lon']) * 111320 * math.cos(math.radians(P['lat']))
    return round(math.hypot(dx, dy), 1)


def variants(stored):
    bw = gray_rgb(stored)
    s1600 = lambda im: W.resize_long(im, 1600)
    adj = np.clip(s1600(bw).astype(np.float32) * 1.4 - 40, 0, 255).astype(np.uint8)
    return [
        ('B&W, stored q95', 'std', bw, None),
        ('B&W + chat app (1600 px, q70)', 'std', W.jpeg(s1600(bw), 70)[0], None),
        ('B&W + social (1080 px, q50)', 'std', W.jpeg(W.resize_long(bw, 1080), 50)[0], None),
        ('B&W + thumbnail (800 px, q40)', 'std', W.jpeg(W.resize_long(bw, 800), 40)[0], None),
        ('B&W + strong contrast + chat app', 'std', W.jpeg(adj, 70)[0], None),
        ('B&W + centre 75% crop + chat app', 'std', W.jpeg(W.resize_long(bw[int(.125 * bw.shape[0]):int(.875 * bw.shape[0]), int(.125 * bw.shape[1]):int(.875 * bw.shape[1])], 1600), 70)[0], 'crop'),
        ('Filter: equal-weight grey + chat app', 'avg', W.jpeg(s1600(gray_rgb(stored, 'avg')), 70)[0], None),
        ('Filter: red-filter B&W + chat app', 'red', W.jpeg(s1600(gray_rgb(stored, 'red')), 70)[0], None),
        ('Filter: green-filter B&W + chat app', 'green', W.jpeg(s1600(gray_rgb(stored, 'green')), 70)[0], None),
    ]


def do(i):
    rgb = W.load(files[i]); marked, _ = W.embed(rgb); stored, _ = W.jpeg(marked, 95)
    rows = []
    for name, mode, img, kind in variants(stored):
        r = W.read(img, 'readcrop') if kind == 'crop' else W.read(img)
        ok1, ok2 = W.correct(r) if r.get('status') != 'nocrop' else (False, False)
        row = dict(name=name, mode=mode, status=r['status'], ok1=ok1, ok2=ok2, z1=round(r.get('z1', 0), 1), z2=round(r.get('z2', 0), 1), err_m=err_m(r.get('l2')))
        if kind != 'crop':
            py = gm.read(img)
            row['py_status'] = py.status; row['py_ok2'] = bool(py.l2 and abs(py.l2['lat'] - P['lat']) < 1.2e-4 and abs(py.l2['lon'] - P['lon']) < 1.2e-4)
            row['py_z2'] = round(py.z2, 1)
        rows.append(row)
    # a stronger mark (what a B&W-aware self-test could choose): same B&W + chat path
    P_STR = {}
    for sf in (1.5, 2.0):
        ms, _ = W.embed(rgb, strength=sf); st2, _ = W.jpeg(ms, 95)
        r = W.read(W.jpeg(W.resize_long(gray_rgb(st2), 1600), 70)[0]); ok1, ok2 = W.correct(r)
        P_STR[str(sf)] = dict(status=r['status'], ok2=ok2, z2=round(r['z2'], 1), err_m=err_m(r.get('l2')), psnr=round(W.psnr(rgb, ms), 2))
    # the control: the same B&W path on an UNMARKED photo must find nothing
    c = W.read(W.jpeg(W.resize_long(gray_rgb(rgb), 1600), 70)[0])
    print('done', i + 1, flush=True)
    return dict(id=i + 1, rows=rows, strong=P_STR, control=dict(status=c['status'], z2=round(c['z2'], 1)))


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=int(os.environ.get('WORKERS', 4))) as ex:
        res = list(ex.map(do, range(len(files))))
    json.dump(res, open(os.path.join(OUT, 'bw.json'), 'w'), indent=1)
