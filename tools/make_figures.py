"""Builds every chart of the README from results/results.json (run run_experiments.py first). Dark theme."""
import json, os, datetime, subprocess
import numpy as np, cv2
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch
from theme import *
import wmlib as W
import phys_sim

ASSETS = os.path.join(W.HERE, '..', 'assets'); os.makedirs(ASSETS, exist_ok=True)
R = json.load(open(os.path.join(W.HERE, 'results', 'results.json')))
photos = R['photos']; N = len(photos)
files = W.photo_files()
for p in photos:
    p['dev'] = device_group(p['make'], p['model']); p['score'] = robustness(p)
ATT = [a['name'] for a in photos[0]['attacks']]
NA = len(ATT) - 1                      # attacks excluding the control


def save(fig, name, dpi=150):
    fig.savefig(os.path.join(ASSETS, name), dpi=dpi, bbox_inches='tight'); plt.close(fig); print('saved', name)


def box(ax, x, y, w, h, text, fc, fs=8.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.01,rounding_size=0.02', fc=fc, ec=fc, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=fs, color='white', fontweight='bold', linespacing=1.3)


def arrow(ax, x0, y0, x1, y1):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle='-|>', mutation_scale=12, lw=1.4, color=MUTED))


def short(n):
    return (n.replace('CONTROL: unmarked photo, 1600 q70', 'CONTROL (unmarked)').replace('Stored JPEG q95 (full size)', 'Stored q95')
             .replace('Chat app: 1600 px, q70', 'Chat 1600 q70').replace('Social: 1080 px, q50', 'Social 1080 q50').replace('Thumbnail: 800 px, q40', 'Thumb 800 q40')
             .replace('Tiny: 600 px, q50', 'Tiny 600 q50').replace('Shared three times (1600 > 1280 > 1080)', 'Shared 3x')
             .replace('Screenshot-style PNG, 1080 px', 'Screenshot').replace('Brightness/contrast edit + 1600 q70', 'Bright/contrast')
             .replace('Colour drained to 40% + 1600 q70', 'Colour -60%').replace('Blur (sigma 1.2) + 1600 q70', 'Blur').replace('25% of area painted over + 1600 q70', '25% painted')
             .replace('Black and white + 1600 q70', 'Black & white'))


# ================================================================== 1 pipeline
fig, ax = plt.subplots(figsize=(11, 4.1)); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off'); ax.set_facecolor(BG)
ax.text(0.0, 0.97, 'WRITE  (at the shutter, ~1.2 s on a phone)', fontsize=9.5, fontweight='bold', color=CYAN, va='top')
w0, h0, y0 = 0.14, 0.2, 0.62
steps = [('Record\nlat · lon · alt\nUTC time · 0.1 s\nlive/manual', '#30363d'), ('CRC-16 +\nconvolutional code\n118 → 248 coded bits', '#0e7490'), ('Spread over\n~10,000 colour tiles\n+ 50,000 luma tiles', '#0e7490'),
         ('Texture-adaptive\nnudge of 1-2\ngrey levels', '#0e7490'), ('Self-test:\nsimulate chat app,\nstrengthen if needed', '#b45309'), ('Marked JPEG\n(visually\nidentical)', '#30363d')]
xs = np.linspace(0.0, 1 - w0, len(steps))
for (t, c), x in zip(steps, xs): box(ax, x, y0, w0, h0, t, c, 7.8)
for a, b in zip(xs[:-1], xs[1:]): arrow(ax, a + w0 + 0.003, y0 + h0 / 2, b - 0.003, y0 + h0 / 2)
ax.text(0.0, 0.5, 'WhatsApp · Instagram · screenshot · crop · print · re-save   →   metadata (EXIF) is gone, the mark stays in the pixels', fontsize=8.6, color=RED, va='center', style='italic')
ax.text(0.0, 0.40, 'READ  (~0.15 s)', fontsize=9.5, fontweight='bold', color=PURPLE, va='top')
steps2 = [('Any copy of\nthe photo', '#30363d'), ('Per-tile chroma /\nluma means,\nhigh-pass', '#4c1d95'), ('Correlate with the\nknown 20% PILOT\ntiles → detect + align', '#4c1d95'),
          ('Soft Viterbi\ndecoding,\nCRC-16 check', '#4c1d95'), ('Status:  OK · PART\nDAMAGED · NONE\n(never a wrong record)', '#166534'), ('Record → app /\nEXIF restore', '#30363d')]
for (t, c), x in zip(steps2, xs): box(ax, x, 0.08, w0, h0, t, c, 7.8)
for a, b in zip(xs[:-1], xs[1:]): arrow(ax, a + w0 + 0.003, 0.08 + h0 / 2, b - 0.003, 0.08 + h0 / 2)
save(fig, 'fig01_pipeline.png')

# ================================================================== 2 anatomy
i3 = 2
rgb3 = W.load(files[i3]); H3, W3 = rgb3.shape[:2]
plan = json.loads(subprocess.run(['node', os.path.join(W.HERE, 'dump_plan.js'), str(W3), str(H3)], capture_output=True, text=True).stdout)
p1 = plan['l1']; nx, ny = p1['nx'], p1['ny']
pil = np.zeros(nx * ny, bool); pil[p1['pilot']] = True; pil = pil.reshape(ny, nx); pn = np.array(p1['pn']).reshape(ny, nx)
fig = plt.figure(figsize=(11, 4.6)); gs = fig.add_gridspec(2, 2, width_ratios=[1.05, 1.25], hspace=0.55, wspace=0.18)
ax = fig.add_subplot(gs[:, 0]); tx0, ty0, tw, th = nx // 3, ny // 4, 26, 19
sx, sy = W3 / nx, H3 / ny
ax.imshow(rgb3[int(ty0 * sy):int((ty0 + th) * sy), int(tx0 * sx):int((tx0 + tw) * sx)], extent=(tx0, tx0 + tw, ty0 + th, ty0), aspect='equal')
for yy in range(ty0, ty0 + th):
    for xx in range(tx0, tx0 + tw):
        isp = pil[yy, xx]
        ax.add_patch(Rectangle((xx + .12, yy + .12), .76, .76, fc=(ORANGE if isp else (BLUE if pn[yy, xx] > 0 else 'white')), alpha=0.6 if isp else 0.32, ec='none'))
ax.set_xticks([]); ax.set_yticks([]); ax.spines[:].set_visible(False)
ax.set_title('Layer-1 grid: %d × %d = %s tiles (%d × %d shown)' % (nx, ny, format(nx * ny, ','), tw, th), loc='left', fontsize=9, pad=8)
ax.text(0.01, -0.03, '■ orange = pilot tile (known sign, 20 %)   ■ blue = data tile +   □ white = data tile −', transform=ax.transAxes, fontsize=7.6, va='top')
for k, (lab, parts) in enumerate([('Layer 1 · colour · 118 bits', [('flags', 3, MUTED), ('lat 25', 25, '#0e7490'), ('lon 26', 26, '#1d4ed8'), ('alt 14', 14, '#b45309'), ('time 29', 29, '#475569'), ('0.1s', 4, '#7c3aed'), ('M', 1, RED), ('CRC-16', 16, '#166534')]),
                                  ('Layer 2 · brightness · 60 bits', [('f', 1, MUTED), ('lat 21', 21, '#0e7490'), ('lon 22', 22, '#1d4ed8'), ('CRC-16', 16, '#166534')])]):
    a = fig.add_subplot(gs[k, 1]); a.set_xlim(0, 120); a.set_ylim(0, 1); a.axis('off'); a.set_facecolor(BG); x = 0
    for name, n, c in parts:
        a.add_patch(Rectangle((x, 0.35), n, 0.4, fc=c, ec=BG, lw=1))
        if n >= 4: a.text(x + n / 2, 0.55, name, ha='center', va='center', color='white', fontsize=7 if n < 10 else 7.8, fontweight='bold')
        x += n
    a.set_title(lab, loc='left')
    a.text(0, 0.12, '→ +6 tail bits → rate-½ code → 248 coded bits → ~32 tiles vote for every bit' if k == 0 else '→ +6 tail bits → rate-½ code → 132 coded bits → ~300 tiles vote for every bit', fontsize=7.8, color=MUTED)
    if k == 0: a.text(x + 1, 0.55, 'M = manual flag', fontsize=7, color=RED, va='center')
save(fig, 'fig02_anatomy.png')

# ================================================================== 3 invisibility (close-up + metrics for all photos)
cy, cx, ch, cw = int(H3 * .42), int(W3 * .38), 360, 480
marked3, _ = W.embed(rgb3)
o = rgb3[cy:cy + ch, cx:cx + cw]; m = marked3[cy:cy + ch, cx:cx + cw]; diff = m.astype(int) - o.astype(int)
fig = plt.figure(figsize=(11, 3.4)); gs = fig.add_gridspec(1, 4, wspace=0.3)
for k, (img, t) in enumerate([(o, 'Original (100 % crop)'), (m, 'Marked (100 % crop)')]):
    a = fig.add_subplot(gs[0, k]); a.imshow(img); a.set_title(t); a.axis('off')
a = fig.add_subplot(gs[0, 2]); a.imshow(np.clip(128 + diff.sum(2) * 8, 0, 255).astype(np.uint8), cmap='RdBu_r', vmin=0, vmax=255); a.set_title('Difference × 24'); a.axis('off')
a = fig.add_subplot(gs[0, 3]); h_, _ = np.histogram(diff.ravel(), np.arange(-10.5, 11.5, 1))
a.bar(np.arange(-10, 11), h_ / diff.size * 100, color=CYAN); a.set_yscale('log'); a.set_xlabel('change per channel (grey levels /255)'); a.set_ylabel('% of samples'); a.set_title('Size of the change')
save(fig, 'fig03a_closeup.png')

fig, axs = plt.subplots(1, 3, figsize=(11, 3.4))
for ax, key, tt, thr, fmtv in ((axs[0], 'psnr', 'PSNR (dB), higher = less change', 35, '%.1f'), (axs[1], 'ssim', 'SSIM, 1.0 = identical', None, '%.4f'), (axs[2], 'dE', 'Mean colour shift ΔE (Lab); below 2 is hard to see', 2.0, '%.2f')):
    vals = [p[key] for p in photos]
    ax.hist(vals, bins=12, color=CYAN, alpha=.85, edgecolor=BG)
    if thr: ax.axvline(thr, color=ORANGE, ls='--', lw=1.3)
    ax.set_title(tt, fontsize=8.5); ax.set_ylabel('photos'); ax.text(.97, .93, 'median ' + fmtv % np.median(vals), transform=ax.transAxes, ha='right', va='top', color=GREEN, fontsize=8.5, fontweight='bold')
save(fig, 'fig03b_quality_hist.png')

# ================================================================== 4 survival heatmap (photos x attacks)
fig, ax = plt.subplots(figsize=(11.5, 0.34 * N + 2.4))
Z = np.array([[p['attacks'][j]['z1'] for j in range(len(ATT))] for p in photos])
im = ax.imshow(Z, cmap='YlGnBu_r', vmin=0, vmax=40, aspect='auto')
labs = {'ok': 'OK', 'part': 'LOC', 'damaged': 'DMG', 'none': '--'}
for i, p in enumerate(photos):
    for j, a_ in enumerate(p['attacks']):
        col = 'white' if a_['z1'] < 14 else '#0d1117'
        ax.text(j, i, labs[a_['status']] if a_['status'] != 'ok' else '%.0f' % a_['z1'], ha='center', va='center', fontsize=6.5, color=col, fontweight='bold')
        if a_['status'] == 'part': ax.add_patch(Rectangle((j - .5, i - .5), 1, 1, fc='none', ec=ORANGE, lw=1.6))
        if a_['status'] == 'damaged': ax.add_patch(Rectangle((j - .5, i - .5), 1, 1, fc='none', ec=RED, lw=1.6))
ax.set_xticks(range(len(ATT))); ax.set_xticklabels([short(n) for n in ATT], fontsize=7.5)
ax.set_yticks(range(N)); ax.set_yticklabels(['#%d %s %.0f MP' % (p['id'], p['dev'][:9], p['mp']) for p in photos], fontsize=7.2)
for t, p in zip(ax.get_yticklabels(), photos): t.set_color(DEVICE_COLORS.get(p['dev'], MUTED))
ax.spines[:].set_visible(False); ax.tick_params(length=0); ax.xaxis.tick_top(); plt.setp(ax.get_xticklabels(), rotation=40, ha='left')
cb = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01); cb.set_label('colour-layer detection strength z (3.5 = threshold)')
save(fig, 'fig04_survival_matrix.png')

# ================================================================== 5 resolution / quality sweeps
Ls = sorted({r['L'] for r in photos[0]['res_sweep']})
fig, axs = plt.subplots(2, 2, figsize=(11, 6.4), gridspec_kw={'hspace': .5, 'wspace': .22})
def zs(p, L, q): return next(r['z1'] for r in p['res_sweep'] if r['L'] == L and r['q'] == q)
def oks(p, L, q): return next(r['ok1'] for r in p['res_sweep'] if r['L'] == L and r['q'] == q)
for ax, q in ((axs[0, 0], 70), (axs[0, 1], 40)):
    A_ = np.array([[zs(p, L, q) for L in Ls] for p in photos])
    for row in A_: ax.plot(Ls, row, '-', color=MUTED, lw=.7, alpha=.35)
    ax.fill_between(Ls, np.percentile(A_, 25, 0), np.percentile(A_, 75, 0), color=CYAN, alpha=.25, label='middle 50% of photos')
    ax.plot(Ls, np.median(A_, 0), 'o-', color=CYAN, lw=2.2, label='median')
    ax.axhline(3.5, color=RED, ls='--', lw=1); ax.text(Ls[-1], 4.6, 'detection threshold 3.5', color=RED, fontsize=7.5, ha='right')
    ax.set_xscale('log'); ax.set_xticks(Ls); ax.set_xticklabels([str(l) for l in Ls], rotation=60, fontsize=7); ax.minorticks_off()
    ax.set_title('Shrunk, then JPEG q%d (%d photos)' % (q, N)); ax.set_ylabel('layer-1 z'); ax.set_xlabel('long edge (px)'); ax.set_ylim(0, 45)
    if q == 70: ax.legend(frameon=False, fontsize=7.5, loc='upper left')
ax = axs[1, 0]
for q, c in ((70, GREEN), (40, ORANGE)):
    ax.plot(Ls, [np.mean([oks(p, L, q) for p in photos]) * 100 for L in Ls], 'o-', color=c, lw=2, label='JPEG q%d' % q)
ax.set_xscale('log'); ax.set_xticks(Ls); ax.set_xticklabels([str(l) for l in Ls], rotation=60, fontsize=7); ax.minorticks_off(); ax.set_ylim(-3, 104)
ax.set_ylabel('% of photos read in FULL'); ax.set_xlabel('long edge (px)'); ax.set_title('How small can a copy get?'); ax.legend(frameon=False, fontsize=8); ax.grid(True, axis='y')
ax = axs[1, 1]; qs = [r['q'] for r in photos[0]['q_sweep']]
Q = np.array([[r['z1'] for r in p['q_sweep']] for p in photos])
for row in Q: ax.plot(qs, row, '-', color=MUTED, lw=.7, alpha=.35)
ax.fill_between(qs, np.percentile(Q, 25, 0), np.percentile(Q, 75, 0), color=PURPLE, alpha=.25); ax.plot(qs, np.median(Q, 0), 'o-', color=PURPLE, lw=2.2)
ax.axhline(3.5, color=RED, ls='--', lw=1); ax.invert_xaxis(); ax.set_xlabel('JPEG quality (1600 px copy)'); ax.set_ylabel('layer-1 z'); ax.set_title('Pure compression'); ax.set_ylim(0, 45)
save(fig, 'fig05_resolution_quality.png')

# ================================================================== extra controls (false positives on unmarked photos)
sizes = [('full q95', lambda x: W.jpeg(x, 95)[0]), ('2000 q85', lambda x: W.jpeg(W.resize_long(x, 2000), 85)[0]), ('1600 q70', lambda x: W.jpeg(W.resize_long(x, 1600), 70)[0]),
         ('1280 q60', lambda x: W.jpeg(W.resize_long(x, 1280), 60)[0]), ('1080 q50', lambda x: W.jpeg(W.resize_long(x, 1080), 50)[0]), ('800 q40', lambda x: W.jpeg(W.resize_long(x, 800), 40)[0]),
         ('1600 B/W', lambda x: W.jpeg(W.resize_long(cv2.cvtColor(cv2.cvtColor(x, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB), 1600), 70)[0]),
         ('1600 blur', lambda x: W.jpeg(cv2.GaussianBlur(W.resize_long(x, 1600), (0, 0), 1.2), 70)[0])]
cpath = os.path.join(W.HERE, 'results', 'controls.json')
if os.path.exists(cpath) and json.load(open(cpath)).get('n') == N:
    ctl = json.load(open(cpath))['controls']
else:
    from concurrent.futures import ThreadPoolExecutor
    def ctl_one(i):
        o_ = W.load(files[i]); out = []
        for nm, fn in sizes:
            r = W.read(fn(o_)); out.append(dict(photo=photos[i]['id'], attack=nm, status=r['status'], z1=r['z1'], z2=r['z2'], l1=r['l1'] is not None, l2=r['l2'] is not None))
        return out
    with ThreadPoolExecutor(max_workers=5) as ex:
        ctl = [c for part in ex.map(ctl_one, range(N)) for c in part]
    json.dump(dict(n=N, controls=ctl), open(cpath, 'w'))
fp_status = sum(c['status'] != 'none' for c in ctl)
max_ctl = max(max(c['z1'], c['z2']) for c in ctl)
print('controls', len(ctl), 'non-none', fp_status, 'max z', max_ctl)

# ================================================================== 6 false alarms + texture
fig, axs = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={'width_ratios': [1.25, 1]})
ax = axs[0]
marked_z = [a_['z1'] for p in photos for a_ in p['attacks'] if 'CONTROL' not in a_['name'] and a_['status'] == 'ok']
ctl1 = [c['z1'] for c in ctl]; ctl2 = [c['z2'] for c in ctl]; rng = np.random.default_rng(1)
ax.scatter(marked_z, 2 + rng.uniform(-.28, .28, len(marked_z)), s=8, color=GREEN, alpha=.6, label='marked, read OK (n=%d)' % len(marked_z))
ax.scatter(ctl1, 1 + rng.uniform(-.28, .28, len(ctl1)), s=8, color=ORANGE, alpha=.6, label='UNMARKED, colour layer (n=%d)' % len(ctl1))
ax.scatter(ctl2, 0 + rng.uniform(-.28, .28, len(ctl2)), s=8, color=RED, alpha=.6, label='UNMARKED, luma layer')
ax.axvline(3.5, color=TXT, ls='--', lw=1); ax.text(3.8, 2.6, 'threshold 3.5', fontsize=7.5)
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(['unmarked\nluma', 'unmarked\ncolour', 'marked\ncolour']); ax.set_xlabel('detection strength z'); ax.set_ylim(-.6, 2.9); ax.legend(frameon=False, fontsize=7.5, loc='lower right')
ax.set_title('%d of %d unmarked reads raised a false alarm (max z = %.1f)' % (fp_status, len(ctl), max_ctl), loc='left', fontsize=9)
ax = axs[1]
tx = [p['texture'] for p in photos]; zy = [p['attacks'][1]['z1'] for p in photos]
for p, t_, z_ in zip(photos, tx, zy): ax.scatter(t_, z_, s=60, color=DEVICE_COLORS.get(p['dev'], MUTED), edgecolor=BG, zorder=3)
cc = np.corrcoef(tx, zy)[0, 1]; k_, b_ = np.polyfit(tx, zy, 1); xs_ = np.linspace(min(tx) - .02, max(tx) + .02, 10); ax.plot(xs_, k_ * xs_ + b_, '--', color=MUTED)
for d_, c_ in DEVICE_COLORS.items(): ax.scatter([], [], s=40, color=c_, label=d_)
ax.legend(frameon=False, fontsize=6.8, ncol=2, loc='lower right')
ax.set_xlabel('mean tile texture factor (0.25 = flat … 1 = busy)'); ax.set_ylabel('z after chat-app copy'); ax.set_title('Busy scenes carry the mark better (r = %.2f)' % cc, loc='left', fontsize=9)
save(fig, 'fig06_false_alarms_texture.png')

# ================================================================== 7 case study (photo 1 journey)
rgb1 = W.load(files[0]); marked1, _ = W.embed(rgb1); stored1, _ = W.jpeg(marked1, 95)
g1 = cv2.cvtColor(stored1, cv2.COLOR_RGB2GRAY); h1, w1 = stored1.shape[:2]
dm = stored1.copy(); dm[int(.25 * h1):int(.75 * h1), int(.25 * w1):int(.75 * w1)] = (110, 120, 125)
wa1 = W.jpeg(W.resize_long(stored1, 1600), 70)[0]
cam1, tc1 = phys_sim.simulate(cv2.cvtColor(wa1, cv2.COLOR_RGB2BGR), 'monitor', 10, 6, 2, 1.0, 2.5, 85, seed=0)
tapped1 = (tc1 + np.clip(np.random.default_rng(1000).normal(0, 0.0065 * wa1.shape[1] * 1.7 * 0.5, (4, 2)), -40, 40)).tolist()
stages = [('① Original\n(unmarked)', rgb1), ('② Marked\nstored q95', stored1), ('③ Chat app\n1600 px q70', wa1), ('④ Thumbnail\n600 px q50', W.jpeg(W.resize_long(stored1, 600), 50)[0]),
          ('⑤ Black & white\n1600 px', W.jpeg(W.resize_long(cv2.cvtColor(g1, cv2.COLOR_GRAY2RGB), 1600), 70)[0]), ('⑥ 25 % painted over', W.jpeg(W.resize_long(dm, 1600), 70)[0]),
          ('⑦ Cropped 10 %\n+ chat app', W.jpeg(W.resize_long(stored1[:, :int(w1 * .9)], 1600), 70)[0]), ('⑧ Phone photo of\na monitor (simulated)', cv2.cvtColor(cam1, cv2.COLOR_BGR2RGB))]
fig = plt.figure(figsize=(11, 6.2)); gs = fig.add_gridspec(2, 4, hspace=.6, wspace=.08)
def fmt(r):
    if r['status'] == 'none': return 'NO MARK', MUTED
    l1 = r['l1']
    if l1:
        ts = datetime.datetime.fromtimestamp(l1['t'], datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S') + '.%d' % l1['tenth']
        return 'OK  %.5f, %.5f\nalt %d m  %s UTC' % (l1['lat'], l1['lon'], l1['alt'], ts), GREEN
    if r['l2'] and r['l2'].get('lat') is not None: return 'PART  location only\n%.4f, %.4f (~10 m)' % (r['l2']['lat'], r['l2']['lon']), ORANGE
    return 'DAMAGED', RED
for k, (t, img) in enumerate(stages):
    a = fig.add_subplot(gs[k // 4, k % 4]); a.imshow(img); a.axis('off'); a.set_title(t, fontsize=8.5)
    r = W.read(img, 'readcrop') if k == 6 else (W.read(img, 'readpersp', tapped1) if k == 7 else W.read(img))
    txt, col = fmt(r)
    a.text(0.5, -0.04, txt, transform=a.transAxes, ha='center', va='top', fontsize=6.8, color=col, fontweight='bold', linespacing=1.3)
save(fig, 'fig07_case_study.png')

# ================================================================== 8 cost / crops / screens
fig, axs = plt.subplots(1, 3, figsize=(11, 3.7), gridspec_kw={'width_ratios': [1.2, 1.2, 1]})
ax = axs[0]
ops = [('Read (12 MP file)', 0.15, GREEN), ('Mark: embed', 0.65, CYAN), ('Mark: self-test', 0.56, CYAN), ('Read + crop search', 3.5, ORANGE), ('Read photo of screen\n(clean case)', 24, RED), ('… hard case', 55, RED)]
ax.barh(range(len(ops)), [o_[1] for o_ in ops], color=[o_[2] for o_ in ops]); ax.set_xscale('log'); ax.set_yticks(range(len(ops))); ax.set_yticklabels([o_[0] for o_ in ops], fontsize=7.8); ax.invert_yaxis()
for k, o_ in enumerate(ops): ax.text(o_[1] * 1.12, k, '%.2g s' % o_[1], va='center', fontsize=7.8)
ax.set_xlim(0.05, 200); ax.set_xlabel('seconds on a mid-range Android phone (log)'); ax.set_title('Cost on a real phone', loc='left')
ax = axs[1]; cn = [c['name'] for c in photos[0]['crops']]; area = [c['area'] for c in photos[0]['crops']]
order_c = sorted(range(len(cn)), key=lambda j: -area[j])
for x, j in enumerate(order_c):
    full = sum(p['crops'][j]['ok1'] for p in photos); part = sum((not p['crops'][j]['ok1']) and p['crops'][j]['ok2'] for p in photos); fail = N - full - part
    ax.bar(x, full / N * 100, color=GREEN); ax.bar(x, part / N * 100, bottom=full / N * 100, color=ORANGE); ax.bar(x, fail / N * 100, bottom=(full + part) / N * 100, color='#3b1d1d')
    ax.text(x, max(full / N * 100 / 2, 6), '%d' % full, ha='center', va='center', color=BG if full else TXT, fontsize=8, fontweight='bold')
ax.set_xticks(range(len(order_c))); ax.set_xticklabels([cn[j].replace(' ', '\n', 1) + '\n(%d%% area)' % area[j] for j in order_c], fontsize=6.2); ax.set_ylabel('%% of %d photos' % N); ax.set_title('Crop, then chat app', loc='left')
ax = axs[2]
for k, kind in enumerate(['monitor', 'print']):
    full = sum(p['screen'][k]['ok1'] for p in photos); part = sum((not p['screen'][k]['ok1']) and p['screen'][k]['ok2'] for p in photos); fail = N - full - part
    ax.bar(k, full, color=GREEN); ax.bar(k, part, bottom=full, color=ORANGE); ax.bar(k, fail, bottom=full + part, color='#3b1d1d')
    ax.text(k, full / 2, '%d / %d' % (full, N), ha='center', va='center', color=BG, fontsize=9, fontweight='bold')
ax.set_xticks([0, 1]); ax.set_xticklabels(['simulated\nmonitor photo', 'simulated\nprint photo']); ax.set_ylim(0, N); ax.set_title('Photo of a screen / print', loc='left')
save(fig, 'fig08_cost_crops_screens.png')

# ================================================================== 9 attack boxplot
fig, ax = plt.subplots(figsize=(11, 4.6)); rng = np.random.default_rng(3)
for j in range(len(ATT)):
    for p in photos:
        a_ = p['attacks'][j]; c_ = GREEN if a_['status'] == 'ok' else (ORANGE if a_['status'] == 'part' else (RED if a_['status'] == 'damaged' else MUTED))
        ax.scatter(j + rng.uniform(-.28, .28), a_['z1'], s=14, color=c_, alpha=.8, zorder=3)
    ax.boxplot([[p['attacks'][j]['z1'] for p in photos]], positions=[j], widths=.55, showfliers=False, patch_artist=True,
               boxprops=dict(facecolor='none', edgecolor=MUTED), medianprops=dict(color=CYAN, lw=2), whiskerprops=dict(color=MUTED), capprops=dict(color=MUTED))
ax.axhline(3.5, color=RED, ls='--', lw=1); ax.text(len(ATT) - .5, 4.5, 'detection threshold 3.5', color=RED, fontsize=7.5, ha='right')
ax.set_xticks(range(len(ATT))); ax.set_xticklabels([short(n) for n in ATT], rotation=35, ha='right', fontsize=7.5); ax.set_ylabel('colour-layer z'); ax.set_ylim(-1, max(48, Z.max() + 4))
for lab, c_ in (('full record', GREEN), ('location only', ORANGE), ('unreadable', RED), ('no mark', MUTED)): ax.scatter([], [], s=20, color=c_, label=lab)
ax.legend(frameon=False, ncol=4, fontsize=8, loc='upper right'); ax.set_title('Detection strength for every photo and every edit (box = quartiles, cyan = median)', loc='left', fontsize=9.5)
save(fig, 'fig09_attack_boxplot.png')

# ================================================================== 10 devices + speed (timings re-measured serially, no parallel load)
tpath = os.path.join(W.HERE, 'results', 'timing.json')
if os.path.exists(tpath) and len(json.load(open(tpath))) == N:
    timing = json.load(open(tpath))
else:
    timing = []
    for f in files:
        rgb_ = W.load(f); mk_, ems = W.embed(rgb_); st_, _ = W.jpeg(mk_, 95); rr = W.read(st_)
        timing.append(dict(mp=rgb_.shape[0] * rgb_.shape[1] / 1e6, embed_ms=ems, read_ms=rr['ms']))
    json.dump(timing, open(tpath, 'w'))
fig, axs = plt.subplots(1, 3, figsize=(11, 3.9), gridspec_kw={'width_ratios': [1.1, 1, 1]})
ax = axs[0]; devs = sorted({p['dev'] for p in photos}, key=lambda d: -np.mean([p['score'] for p in photos if p['dev'] == d]))
for x, d_ in enumerate(devs):
    sc = [p['score'] for p in photos if p['dev'] == d_]
    ax.bar(x, np.mean(sc), color=DEVICE_COLORS.get(d_, MUTED), alpha=.9)
    ax.scatter([x] * len(sc), sc, s=16, color='white', zorder=3, alpha=.8); ax.text(x, np.mean(sc) / 2, 'n=%d' % len(sc), ha='center', fontsize=7.5, color=BG, fontweight='bold')
ax.set_xticks(range(len(devs))); ax.set_xticklabels([d.replace(' ', chr(10), 1) for d in devs], fontsize=7); ax.set_ylim(0, NA + 1); ax.set_ylabel('edits survived (full record) of %d' % NA)
ax.set_title('By camera', loc='left')
ax = axs[1]
mp = [t['mp'] for t in timing]; em = [t['embed_ms'] for t in timing]
for p, t in zip(photos, timing): ax.scatter(t['mp'], t['embed_ms'], s=40, color=DEVICE_COLORS.get(p['dev'], MUTED), edgecolor=BG)
k_, b_ = np.polyfit(mp, em, 1); xs_ = np.linspace(min(mp), max(mp), 5); ax.plot(xs_, k_ * xs_ + b_, '--', color=MUTED)
ax.set_xlabel('megapixels'); ax.set_ylabel('ms (JavaScript reference, 1 core)'); ax.set_title('Marking: about %.0f ms per MP' % k_, loc='left')
ax = axs[2]
for p, t in zip(photos, timing): ax.scatter(t['mp'], t['read_ms'], s=40, color=DEVICE_COLORS.get(p['dev'], MUTED), edgecolor=BG)
ax.set_xlabel('megapixels'); ax.set_ylabel('ms'); ax.set_title('Full-size read, JS (median %.0f ms)' % np.median([t['read_ms'] for t in timing]), loc='left')
save(fig, 'fig10_devices_speed.png')

# ================================================================== 11 strength trade-off
fig, axs = plt.subplots(1, 3, figsize=(11, 3.7))
S = [r['s'] for r in photos[0]['strength']]
ps = [np.mean([p['strength'][k]['psnr'] for p in photos]) for k in range(len(S))]
chat = [np.mean([p['strength'][k]['chat_ok1'] for p in photos]) * 100 for k in range(len(S))]
small = [np.mean([p['strength'][k]['small_ok1'] for p in photos]) * 100 for k in range(len(S))]
ax = axs[0]; ax.plot(S, ps, 'o-', color=CYAN, lw=2); ax.set_xlabel('mark strength (x default)'); ax.set_ylabel('mean PSNR (dB)'); ax.set_title('Stronger = more visible', loc='left')
ax.axvline(1.0, color=GREEN, ls=':'); ax.text(1.03, min(ps) + .3, 'default', color=GREEN, fontsize=8)
ax = axs[1]; ax.plot(S, chat, 'o-', color=GREEN, lw=2, label='chat app 1600 q70'); ax.plot(S, small, 'o-', color=ORANGE, lw=2, label='thumbnail 800 q40')
ax.set_xlabel('mark strength (x default)'); ax.set_ylabel('% photos read in full'); ax.set_ylim(0, 105); ax.legend(frameon=False, fontsize=8, loc='lower right'); ax.axvline(1.0, color=GREEN, ls=':'); ax.set_title('Stronger = survives more', loc='left')
ax = axs[2]
for k, s_ in enumerate(S):
    ax.scatter(ps[k], small[k], s=120, color=[RED, ORANGE, GREEN, CYAN, PURPLE][k % 5], zorder=3, edgecolor=BG); ax.annotate('x%g' % s_, (ps[k], small[k]), textcoords='offset points', xytext=(8, -3), fontsize=8.5, color=TXT)
ax.set_xlabel('mean PSNR (dB): left = less visible'); ax.set_ylabel('% read at 800 px q40'); ax.set_title('The trade-off', loc='left'); ax.invert_xaxis()
save(fig, 'fig11_strength_tradeoff.png')

# ================================================================== 12 leaderboard
fig, ax = plt.subplots(figsize=(11, 0.27 * N + 1.4)); lo = sorted(photos, key=lambda p: (p['score'], p['attacks'][1]['z1']))
for y, p in enumerate(lo):
    ax.barh(y, p['score'], color=DEVICE_COLORS.get(p['dev'], MUTED), alpha=.9)
    ax.text(p['score'] + .15, y, '%d / %d   ·   chat z = %.0f   ·   texture %.2f' % (p['score'], NA, p['attacks'][1]['z1'], p['texture']), va='center', fontsize=7.4, color=MUTED)
ax.set_yticks(range(N)); ax.set_yticklabels(['#%d  %s  %.0f MP' % (p['id'], p['dev'], p['mp']) for p in lo], fontsize=7.4); ax.set_xlim(0, NA + 8); ax.set_xlabel('edits survived with the full record intact (of %d)' % NA)
for d_, c_ in DEVICE_COLORS.items(): ax.barh([-5], [0], color=c_, label=d_)
ax.legend(frameon=False, fontsize=7.5, ncol=3, loc='lower right'); ax.set_ylim(-.7, N - .3)
save(fig, 'fig12_leaderboard.png')

# ================================================================== 13 HEIC + totals
hp = [p for p in photos if 'heic' in p and 'ok1' in p['heic']]
fig, axs = plt.subplots(1, 2, figsize=(11, 3.4), gridspec_kw={'width_ratios': [1.6, 1]})
ax = axs[0]
for x, p in enumerate(hp): ax.bar(x, p['heic']['z1'], color=GREEN if p['heic']['ok1'] else RED, alpha=.9)
ax.set_xticks(range(len(hp))); ax.set_xticklabels(['#%d' % p['id'] for p in hp], fontsize=7); ax.axhline(3.5, color=RED, ls='--', lw=1); ax.set_ylabel('colour-layer z')
ax.set_title('HEIC original, marked, saved as JPEG q95: %d of %d read in full' % (sum(p['heic']['ok1'] for p in hp), len(hp)), loc='left', fontsize=9)
ax = axs[1]
tot = dict(full=0, part=0, dmg=0)
for p in photos:
    for a_ in p['attacks']:
        if 'CONTROL' in a_['name']: continue
        if a_['ok1']: tot['full'] += 1
        elif a_['status'] == 'part': tot['part'] += 1
        else: tot['dmg'] += 1
vals = [tot['full'], tot['part'], tot['dmg']]
ax.pie(vals, colors=[GREEN, ORANGE, RED], startangle=90, counterclock=False, wedgeprops=dict(width=.38, edgecolor=BG), autopct=lambda v: '%.0f%%' % v, textprops=dict(color=BG, fontweight='bold', fontsize=9), pctdistance=.8)
ax.text(0, 0, '%d\nedits' % sum(vals), ha='center', va='center', fontsize=12, fontweight='bold', color=TXT)
ax.set_title('All %d marked-photo edits' % sum(vals), fontsize=9)
save(fig, 'fig13_heic_totals.png')
json.dump(dict(totals=tot, fp=[fp_status, len(ctl), float(max_ctl)], texture_r=float(cc), n=N), open(os.path.join(W.HERE, 'results', 'summary.json'), 'w'), indent=1)
print('figures complete', tot)
