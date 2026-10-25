"""Measures the Python engine: cross-engine agreement on every photo, and its speed. Writes results/python.json."""
import json, os, sys, time
import numpy as np, cv2
import wmlib as W, phys_sim

sys.path.insert(0, os.path.join(W.HERE, '..', 'python'))
import ghostmark as gm
from ghostmark import _core as C

files = W.photo_files(); P = W.PAYLOAD
rec = gm.Record(lat=P['lat'], lon=P['lon'], alt=P['alt'], t=P['t'], tenth=P['tenth'])
ok = lambda r: bool(r.l1 and abs(r.l1['lat'] - P['lat']) < 2e-5 and abs(r.l1['lon'] - P['lon']) < 2e-5 and r.l1['alt'] == P['alt'] and r.l1['t'] == P['t'])
out = dict(n=len(files), py_marked_js_read=0, js_marked_py_read=0, py_read_py_marked=0, js_read_js_marked=0, both_agree_status=0, max_pixel_diff=0, mean_pixel_diff=[])
for i, f in enumerate(files):
    rgb = W.resize_long(W.load(f), 1600)
    js_m, _ = W.embed(rgb); py_m = gm.mark(rgb, rec)
    d = np.abs(js_m.astype(int) - py_m.astype(int)); out['max_pixel_diff'] = max(out['max_pixel_diff'], int(d.max())); out['mean_pixel_diff'].append(float(d.mean()))
    a = W.jpeg(py_m, 70)[0]; b = W.jpeg(js_m, 70)[0]
    r_js_on_py = W.read(a); r_py_on_js = gm.read(b); r_py_on_py = gm.read(a); r_js_on_js = W.read(b)
    out['py_marked_js_read'] += int(W.correct(r_js_on_py)[0]); out['js_marked_py_read'] += int(ok(r_py_on_js))
    out['py_read_py_marked'] += int(ok(r_py_on_py)); out['js_read_js_marked'] += int(W.correct(r_js_on_js)[0])
    out['both_agree_status'] += int(r_py_on_js.status == r_js_on_js['status'])
    print('interop', i + 1, flush=True)
out['mean_pixel_diff'] = float(np.mean(out['mean_pixel_diff']))
# speed on a real 12 MP photo (photo 1) on one core, nothing else running
rgb = W.load(files[0]); mp = rgb.shape[0] * rgb.shape[1] / 1e6
t = time.time(); m = gm.mark(rgb, rec); t_mark = time.time() - t
t = time.time(); r = gm.read(W.jpeg(m, 95)[0]); t_read = time.time() - t
t = time.time(); mv, s = gm.mark_verified(rgb, rec); t_ver = time.time() - t
small = W.jpeg(W.resize_long(W.jpeg(m, 95)[0], 1600), 70)[0]
h, w = small.shape[:2]; crop = W.jpeg(W.resize_long(small[int(.125 * h):int(.875 * h), int(.125 * w):int(.875 * w)], 1600), 70)[0]
t = time.time(); rc = gm.read_cropped(crop); t_crop = time.time() - t
cam, tc = phys_sim.simulate(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), 'monitor', 10, 6, 2, 1.0, 2.5, 85, seed=0)
tapped = (tc + np.clip(np.random.default_rng(1000).normal(0, 0.0065 * small.shape[1] * 1.7 * 0.5, (4, 2)), -40, 40)).tolist()
t = time.time(); rp = gm.read_perspective(cv2.cvtColor(cam, cv2.COLOR_BGR2RGB), tapped); t_persp = time.time() - t
out['speed'] = dict(mp=round(mp, 1), mark_s=round(t_mark, 2), read_s=round(t_read, 2), mark_verified_s=round(t_ver, 2), strength=s, crop_s=round(t_crop, 1), crop_status=rc.status if rc else None,
                    persp_s=round(t_persp, 1), persp_status=rp.status if rp else None, read_status=r.status)
json.dump(out, open(os.path.join(W.HERE, 'results', 'python.json'), 'w'), indent=1)
print(json.dumps(out['speed']), {k: v for k, v in out.items() if k != 'speed'})
