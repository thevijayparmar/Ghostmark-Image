"""Runs every measurement quoted in the README; writes results/results.json (all photos in the test folder)."""
import json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np, cv2
import wmlib as W, phys_sim

OUT = os.path.join(W.HERE, 'results'); os.makedirs(OUT, exist_ok=True)
files = W.photo_files()
res = {'payload': W.PAYLOAD, 'photos': []}
CROPS = {'centre 90%': (.05, .05, .95, .95), 'centre 75%': (.125, .125, .875, .875), 'centre 60%': (.2, .2, .8, .8),
         'centre 45%': (.275, .275, .725, .725), 'right 10% trimmed': (0, 0, .9, 1), 'top-left quarter': (0, 0, .5, .5)}
STRENGTHS = [0.5, 0.75, 1.0, 1.5, 2.0]


def tex_stats(rgb):
    s = W.resize_long(rgb, 1600); g = cv2.cvtColor(s, cv2.COLOR_RGB2GRAY).astype(np.float32)
    nx, ny = 115, 87
    mu = cv2.resize(g, (nx, ny), interpolation=cv2.INTER_AREA); mu2 = cv2.resize(g * g, (nx, ny), interpolation=cv2.INTER_AREA)
    tex = np.clip(np.sqrt(np.maximum(mu2 - mu * mu, 0)) / 14, 0, 1)
    return float(np.maximum(tex, .25).mean()), float(g.mean())


def do_photo(i):
    path = files[i]; rgb = W.load(path); h, w = rgb.shape[:2]
    mk, md = W.device(path)
    marked, ms = W.embed(rgb)
    d = np.abs(marked.astype(int) - rgb.astype(int))
    stored, nbytes = W.jpeg(marked, 95)
    _, orig_bytes = W.jpeg(rgb, 95)
    tex, luma = tex_stats(rgb)
    P = dict(id=i + 1, file=os.path.basename(path), make=mk, model=md, w=w, h=h, mp=round(w * h / 1e6, 1), embed_ms=ms,
             psnr=round(W.psnr(rgb, marked), 2), ssim=round(W.ssim(rgb, marked), 5), dE=round(W.delta_e(rgb, marked), 3),
             mean_change=round(float(d.mean()), 3), max_change=int(d.max()), p_ge3=round(float((d.max(2) >= 3).mean()) * 100, 2),
             bytes_added_pct=round((nbytes / orig_bytes - 1) * 100, 1), texture=round(tex, 4), luma=round(luma, 1))
    r = W.read(stored); P['read_full_ms'] = r['ms']
    gray = cv2.cvtColor(stored, cv2.COLOR_RGB2GRAY)
    dm = stored.copy(); dm[int(.25 * h):int(.75 * h), int(.25 * w):int(.75 * w)] = (110, 120, 125)
    blur = cv2.GaussianBlur(W.resize_long(stored, 1600), (0, 0), 1.2)
    adj = np.clip(W.resize_long(stored, 1600).astype(np.float32) * 1.25 - 20, 0, 255).astype(np.uint8)
    sat = cv2.cvtColor(W.resize_long(stored, 1600), cv2.COLOR_RGB2HSV); sat[..., 1] = (sat[..., 1] * 0.4).astype(np.uint8)
    sat = cv2.cvtColor(sat, cv2.COLOR_HSV2RGB)
    triple = W.jpeg(W.resize_long(W.jpeg(W.resize_long(W.jpeg(W.resize_long(stored, 1600), 70)[0], 1280), 60)[0], 1080), 50)[0]
    attacks = [
        ('Stored JPEG q95 (full size)', stored),
        ('Chat app: 1600 px, q70', W.jpeg(W.resize_long(stored, 1600), 70)[0]),
        ('Social: 1080 px, q50', W.jpeg(W.resize_long(stored, 1080), 50)[0]),
        ('Thumbnail: 800 px, q40', W.jpeg(W.resize_long(stored, 800), 40)[0]),
        ('Tiny: 600 px, q50', W.jpeg(W.resize_long(stored, 600), 50)[0]),
        ('Shared three times (1600 > 1280 > 1080)', triple),
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
    for name, (x0, y0, x1, y1) in CROPS.items():
        c = stored[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
        c = W.jpeg(W.resize_long(c, 1600), 70)[0]
        r = W.read(c, 'readcrop')
        ok1, ok2 = W.correct(r) if r.get('status') != 'nocrop' else (False, False)
        P['crops'].append(dict(name=name, area=round((x1 - x0) * (y1 - y0) * 100), status=r['status'], ok1=ok1, ok2=ok2, z1=round(r.get('z1', 0), 1), ms=r['ms']))
    P['screen'] = []
    wa = W.jpeg(W.resize_long(stored, 1600), 70)[0]
    wa_bgr = cv2.cvtColor(wa, cv2.COLOR_RGB2BGR)
    for kind, yaw, pit, rol, bl, q in [('monitor', 10, 6, 2, 1.0, 85), ('print', 20, 12, -3, 2.1, 80)]:
        cam, tc = phys_sim.simulate(wa_bgr, kind, yaw, pit, rol, bl, 2.5, q, seed=i)
        rng = np.random.default_rng(1000 + i)
        tapped = (tc + np.clip(rng.normal(0, 0.0065 * wa.shape[1] * 1.7 * 0.5, (4, 2)), -40, 40)).tolist()
        r = W.read(cv2.cvtColor(cam, cv2.COLOR_BGR2RGB), 'readpersp', tapped)
        ok1, ok2 = W.correct(r) if r.get('status') != 'nopersp' else (False, False)
        P['screen'].append(dict(kind=kind, status=r['status'], ok1=ok1, ok2=ok2, z1=round(r.get('z1', 0), 1), ms=r['ms']))
    # strength ablation: visibility versus survival
    P['strength'] = []
    for sf in STRENGTHS:
        mk_, _ = (marked, 0) if sf == 1.0 else W.embed(rgb, strength=sf)
        st_, _ = W.jpeg(mk_, 95)
        row = dict(s=sf, psnr=round(W.psnr(rgb, mk_), 2))
        for nm, img in (('chat', W.jpeg(W.resize_long(st_, 1600), 70)[0]), ('small', W.jpeg(W.resize_long(st_, 800), 40)[0])):
            r = W.read(img); ok1, ok2 = W.correct(r)
            row[nm + '_z1'] = round(r['z1'], 1); row[nm + '_ok1'] = ok1
        P['strength'].append(row)
    # HEIC original -> mark -> JPEG (format conversion)
    hp = W.heic_for(path)
    if hp:
        try:
            hr = W.load(hp); hm, _ = W.embed(hr); hj, _ = W.jpeg(hm, 95)
            r = W.read(hj); ok1, ok2 = W.correct(r)
            P['heic'] = dict(ok1=ok1, z1=round(r['z1'], 1), mp=round(hr.shape[0] * hr.shape[1] / 1e6, 1))
        except Exception as e:
            P['heic'] = dict(error=str(e))
    print('done photo', i + 1, flush=True)
    return P


if __name__ == '__main__':
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=int(os.environ.get('WORKERS', 4))) as ex:
        res['photos'] = list(ex.map(do_photo, range(len(files))))
    res['seconds'] = round(time.time() - t0)
    json.dump(res, open(os.path.join(OUT, 'results.json'), 'w'), indent=1)
    print('written', res['seconds'], 's')
