"""Runs every measurement quoted in the README; writes results/results.json."""
import json, os, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np, cv2
import wmlib as W, phys_sim

OUT = os.path.join(W.HERE, 'results'); os.makedirs(OUT, exist_ok=True)
files = W.photo_files()
res = {'payload': W.PAYLOAD, 'photos': []}


def do_photo(i):
    rgb = W.load(files[i]); h, w = rgb.shape[:2]
    marked, ms = W.embed(rgb)
    d = np.abs(marked.astype(int) - rgb.astype(int))
    stored, nbytes = W.jpeg(marked, 95)
    _, orig_bytes = W.jpeg(rgb, 95)
    P = dict(id=i + 1, w=w, h=h, mp=round(w * h / 1e6, 1), embed_ms=ms, psnr=round(W.psnr(rgb, marked), 2),
             mean_change=round(float(d.mean()), 3), max_change=int(d.max()), p_ge3=round(float((d.max(2) >= 3).mean()) * 100, 2),
             p_ge2=round(float((d.max(2) >= 2).mean()) * 100, 2), bytes_added_pct=round((nbytes / orig_bytes - 1) * 100, 1))
    r = W.read(stored); P['read_full_ms'] = r['ms']
    gray = cv2.cvtColor(stored, cv2.COLOR_RGB2GRAY)
    dm = stored.copy(); dm[int(.25 * h):int(.75 * h), int(.25 * w):int(.75 * w)] = (110, 120, 125)
    blur = cv2.GaussianBlur(W.resize_long(stored, 1600), (0, 0), 1.2)
    adj = np.clip(W.resize_long(stored, 1600).astype(np.float32) * 1.25 - 20, 0, 255).astype(np.uint8)
    sat = cv2.cvtColor(W.resize_long(stored, 1600), cv2.COLOR_RGB2HSV); sat[..., 1] = (sat[..., 1] * 0.4).astype(np.uint8)
    sat = cv2.cvtColor(sat, cv2.COLOR_HSV2RGB)
    attacks = [
        ('Stored JPEG q95 (full size)', stored),
        ('Chat app: 1600 px, q70', W.jpeg(W.resize_long(stored, 1600), 70)[0]),
        ('Social: 1080 px, q50', W.jpeg(W.resize_long(stored, 1080), 50)[0]),
        ('Thumbnail: 800 px, q40', W.jpeg(W.resize_long(stored, 800), 40)[0]),
        ('Tiny: 600 px, q50', W.jpeg(W.resize_long(stored, 600), 50)[0]),
        ('Screenshot-style PNG, 1080 px', W.resize_long(stored, 1080)),
        ('Brightness/contrast edit + 1600 q70', W.jpeg(adj, 70)[0]),
        ('Colour drained to 40% + 1600 q70', W.jpeg(sat, 70)[0]),
        ('Blur (sigma 1.2) + 1600 q70', W.jpeg(blur, 70)[0]),
        ('25% of area painted over + 1600 q70', W.jpeg(W.resize_long(dm, 1600), 70)[0]),
        ('Black and white + 1600 q70', W.jpeg(W.resize_long(cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB), 1600), 70)[0]),
        ('CONTROL: unmarked photo, 1600 q70', W.jpeg(W.resize_long(rgb, 1600), 70)[0]),
    ]
    P['attacks'] = []
    for name, img in attacks:
        r = W.read(img); ok1, ok2 = W.correct(r)
        P['attacks'].append(dict(name=name, status=r['status'], z1=round(r['z1'], 1), z2=round(r['z2'], 1), ok1=ok1, ok2=ok2,
                                 wrong_l1=(r['l1'] is not None and not ok1), ms=r['ms']))
    P['res_sweep'] = []
    for L in [300, 400, 500, 600, 700, 800, 1000, 1280, 1600, 2000]:
        for q in (70, 40):
            r = W.read(W.jpeg(W.resize_long(stored, L), q)[0]); ok1, ok2 = W.correct(r)
            P['res_sweep'].append(dict(L=L, q=q, z1=round(r['z1'], 1), z2=round(r['z2'], 1), ok1=ok1, ok2=ok2))
    P['q_sweep'] = []
    small = W.resize_long(stored, 1600)
    for q in [95, 80, 60, 40, 30, 20, 15, 10, 5]:
        r = W.read(W.jpeg(small, q)[0]); ok1, ok2 = W.correct(r)
        P['q_sweep'].append(dict(q=q, z1=round(r['z1'], 1), z2=round(r['z2'], 1), ok1=ok1, ok2=ok2))
    P['crops'] = []
    for name, (x0, y0, x1, y1) in {'10% off right edge': (0, 0, .9, 1), 'centre 75%': (.125, .125, .875, .875),
                                    'centre 55%': (.225, .225, .775, .775), 'top-left quarter': (0, 0, .5, .5)}.items():
        c = stored[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
        c = W.jpeg(W.resize_long(c, 1600), 70)[0]
        r = W.read(c, 'readcrop')
        ok1, ok2 = W.correct(r) if r.get('status') != 'nocrop' else (False, False)
        P['crops'].append(dict(name=name, status=r['status'], ok1=ok1, ok2=ok2, z1=round(r.get('z1', 0), 1), ms=r['ms']))
    P['screen'] = []
    wa = W.jpeg(W.resize_long(stored, 1600), 70)[0]
    wa_bgr = cv2.cvtColor(wa, cv2.COLOR_RGB2BGR)
    for kind, yaw, pit, rol, bl, q in [('monitor', 10, 6, 2, 1.0, 85), ('print', 20, 12, -3, 2.1, 80)]:
        cam, tc = phys_sim.simulate(wa_bgr, kind, yaw, pit, rol, bl, 2.5, q, seed=i)
        rng = np.random.default_rng(1000 + i)
        tapped = (tc + np.clip(rng.normal(0, 0.0065 * wa.shape[1] * 1.7 * 0.5, (4, 2)), -40, 40)).tolist()
        camrgb = cv2.cvtColor(cam, cv2.COLOR_BGR2RGB)
        r = W.read(camrgb, 'readpersp', tapped)
        ok1, ok2 = W.correct(r) if r.get('status') != 'nopersp' else (False, False)
        P['screen'].append(dict(kind=kind, status=r['status'], ok1=ok1, ok2=ok2, z1=round(r.get('z1', 0), 1), ms=r['ms']))
        if i == 2:
            cv2.imwrite(os.path.join(OUT, 'screen_%s.jpg' % kind), cam, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print('done photo', i + 1, flush=True)
    return P


with ThreadPoolExecutor(max_workers=4) as ex:
    res['photos'] = list(ex.map(do_photo, range(len(files))))
json.dump(res, open(os.path.join(OUT, 'results.json'), 'w'), indent=1)
print('written')
