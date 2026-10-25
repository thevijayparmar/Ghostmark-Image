"""Builds every figure and sample image of the README from results/results.json (run run_experiments.py first)."""
import json, os, subprocess, datetime
import numpy as np, cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch
import wmlib as W

ASSETS = os.path.join(W.HERE, '..', 'assets'); os.makedirs(ASSETS, exist_ok=True)
SAMPLES = os.path.join(W.HERE, '..', 'samples'); os.makedirs(SAMPLES, exist_ok=True)
R = json.load(open(os.path.join(W.HERE, 'results', 'results.json')))
photos = R['photos']
files = W.photo_files()

TEAL, ORANGE, SLATE, GREEN, RED, GREY, BLUE, INK = '#0f766e', '#ea580c', '#334155', '#16a34a', '#dc2626', '#94a3b8', '#2563eb', '#0f172a'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.edgecolor': '#475569', 'axes.labelcolor': INK, 'text.color': INK,
                     'axes.spines.top': False, 'axes.spines.right': False, 'figure.facecolor': 'white', 'axes.facecolor': 'white',
                     'savefig.facecolor': 'white', 'axes.titleweight': 'bold', 'axes.titlesize': 10})


def save(fig, name):
    fig.savefig(os.path.join(ASSETS, name), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('saved', name)


def box(ax, x, y, w, h, text, fc, ec=None, fs=8.5, tc='white', bold=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.01,rounding_size=0.02', fc=fc, ec=ec or fc, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=fs, color=tc, fontweight='bold' if bold else 'normal', linespacing=1.3)


def arrow(ax, x0, y0, x1, y1, c=SLATE):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle='-|>', mutation_scale=12, lw=1.4, color=c))


# ------------------------------------------------------------------ data used by several figures
i3 = 2
rgb3 = W.load(files[i3]); marked3, _ = W.embed(rgb3)
stored3, _ = W.jpeg(marked3, 95)

# ------------------------------------------------------------------ FIG 1: pipeline
fig, ax = plt.subplots(figsize=(11, 4.1)); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
ax.text(0.0, 0.97, 'WRITE  (at the shutter, ~1.2 s on a phone)', fontsize=9.5, fontweight='bold', color=TEAL, va='top')
w0, h0, y0 = 0.14, 0.2, 0.62
steps = [('Record\nlat · lon · alt\nUTC time · 0.1 s\nlive/manual', SLATE), ('CRC-16 +\nconvolutional code\n118 → 248 coded bits', TEAL),
         ('Spread over\n~10,000 colour tiles\n+ 50,000 luma tiles', TEAL), ('Texture-adaptive\nnudge of 1-2\ngrey levels', TEAL), ('Self-test:\nsimulate chat app,\nstrengthen if needed', ORANGE), ('Marked JPEG\n(visually\nidentical)', SLATE)]
xs = np.linspace(0.0, 1 - w0, len(steps))
for (t, c), x in zip(steps, xs):
    box(ax, x, y0, w0, h0, t, c, fs=7.8)
for a, b in zip(xs[:-1], xs[1:]):
    arrow(ax, a + w0 + 0.003, y0 + h0 / 2, b - 0.003, y0 + h0 / 2)
ax.text(0.0, 0.5, 'WhatsApp · Instagram · screenshot · crop · print · re-save   →   metadata (EXIF) is gone, the mark stays in the pixels', fontsize=8.6, color=RED, va='center', style='italic')
ax.text(0.0, 0.40, 'READ  (~0.15 s)', fontsize=9.5, fontweight='bold', color=BLUE, va='top')
steps2 = [('Any copy of\nthe photo', SLATE), ('Per-tile chroma /\nluma means,\nhigh-pass', BLUE), ('Correlate with the\nknown 20% PILOT\ntiles → detect + align', BLUE), ('Soft Viterbi\ndecoding,\nCRC-16 check', BLUE), ('Status:  OK · PART\nDAMAGED · NONE\n(never a wrong record)', GREEN), ('Record → app /\nEXIF restore', SLATE)]
for (t, c), x in zip(steps2, xs):
    box(ax, x, 0.08, w0, h0, t, c, fs=7.8)
for a, b in zip(xs[:-1], xs[1:]):
    arrow(ax, a + w0 + 0.003, 0.08 + h0 / 2, b - 0.003, 0.08 + h0 / 2)
save(fig, 'fig01_pipeline.png')

# ------------------------------------------------------------------ FIG 2: anatomy (tile grid zoom + payload layout)
H3, W3 = rgb3.shape[:2]
plan = json.loads(subprocess.run(['node', os.path.join(W.HERE, 'dump_plan.js'), str(W3), str(H3)], capture_output=True, text=True).stdout)
p1 = plan['l1']; nx, ny = p1['nx'], p1['ny']
pil = np.zeros(nx * ny, bool); pil[p1['pilot']] = True; pil = pil.reshape(ny, nx)
pn = np.array(p1['pn']).reshape(ny, nx)
fig = plt.figure(figsize=(11, 4.6)); gs = fig.add_gridspec(2, 2, width_ratios=[1.05, 1.25], height_ratios=[1, 1], hspace=0.55, wspace=0.18)
ax = fig.add_subplot(gs[:, 0])
tx0, ty0, tw, th = 38, 14, 26, 19                                  # window of tiles shown
sx, sy = W3 / nx, H3 / ny
crop = rgb3[int(ty0 * sy):int((ty0 + th) * sy), int(tx0 * sx):int((tx0 + tw) * sx)]
ax.imshow(crop, extent=(tx0, tx0 + tw, ty0 + th, ty0), aspect='equal')
for yy in range(ty0, ty0 + th):
    for xx in range(tx0, tx0 + tw):
        isp = pil[yy, xx]
        ax.add_patch(Rectangle((xx + .12, yy + .12), .76, .76, fc=(ORANGE if isp else (BLUE if pn[yy, xx] > 0 else 'white')), alpha=0.55 if isp else 0.35, ec='none'))
ax.set_xticks([]); ax.set_yticks([]); ax.spines[:].set_visible(False)
ax.set_title('Layer-1 grid: %d × %d = %s tiles (%d × %d shown)' % (nx, ny, format(nx * ny, ','), tw, th), loc='left', fontsize=9, pad=8)
ax.text(0.01, -0.03, '■ orange = pilot tile (known sign, 20 %)   ■ blue = data tile +   □ white = data tile −', transform=ax.transAxes, fontsize=7.6, va='top')
for k, (lab, parts, tot) in enumerate([('Layer 1 · colour · 118 bits', [('flags', 3, GREY), ('lat 25', 25, TEAL), ('lon 26', 26, BLUE), ('alt 14', 14, ORANGE), ('time 29', 29, SLATE), ('0.1s', 4, '#a855f7'), ('M', 1, RED), ('CRC-16', 16, GREEN)], 118),
                                       ('Layer 2 · brightness · 60 bits', [('f', 1, GREY), ('lat 21', 21, TEAL), ('lon 22', 22, BLUE), ('CRC-16', 16, GREEN)], 60)]):
    a = fig.add_subplot(gs[k, 1]); a.set_xlim(0, 120); a.set_ylim(0, 1); a.axis('off')
    x = 0
    for name, n, c in parts:
        a.add_patch(Rectangle((x, 0.35), n, 0.4, fc=c, ec='white', lw=1))
        if n >= 4:
            a.text(x + n / 2, 0.55, name, ha='center', va='center', color='white', fontsize=7 if n < 10 else 7.8, fontweight='bold')
        x += n
    a.set_title(lab, loc='left')
    sub = ('→ +6 tail bits → rate-½ code → 248 coded bits → ~32 tiles vote for every bit' if k == 0 else '→ +6 tail bits → rate-½ code → 132 coded bits → ~300 tiles vote for every bit')
    a.text(0, 0.12, sub, fontsize=7.8, color=SLATE)
    if k == 0:
        a.text(x + 1, 0.55, 'M = manual flag', fontsize=7, color=RED, va='center')
save(fig, 'fig02_anatomy.png')

# ------------------------------------------------------------------ FIG 3: invisibility
cy, cx, ch, cw = int(H3 * .42), int(W3 * .38), 360, 480
o = rgb3[cy:cy + ch, cx:cx + cw]; m = marked3[cy:cy + ch, cx:cx + cw]
diff = (m.astype(int) - o.astype(int))
fig = plt.figure(figsize=(11, 5.6)); gs = fig.add_gridspec(2, 4, height_ratios=[1.35, 1], hspace=0.45, wspace=0.3)
for k, (img, t) in enumerate([(o, 'Original (100 % crop)'), (m, 'Marked (100 % crop)')]):
    a = fig.add_subplot(gs[0, k]); a.imshow(img); a.set_title(t); a.axis('off')
a = fig.add_subplot(gs[0, 2]); a.imshow(np.clip(128 + diff.sum(2) * 8, 0, 255).astype(np.uint8), cmap='RdBu_r', vmin=0, vmax=255); a.set_title('Difference × 24'); a.axis('off')
a = fig.add_subplot(gs[0, 3]); bins = np.arange(-10.5, 11.5, 1); h_, _ = np.histogram(diff.ravel(), bins)
a.bar(np.arange(-10, 11), h_ / diff.size * 100, color=TEAL); a.set_yscale('log'); a.set_xlabel('change per channel (grey levels /255)'); a.set_ylabel('% of samples'); a.set_title('Size of the change')
a = fig.add_subplot(gs[1, :2]); ids = [p['id'] for p in photos]
bars = a.bar(ids, [p['psnr'] for p in photos], color=[TEAL if p['psnr'] > 36 else ORANGE for p in photos])
for b, p in zip(bars, photos):
    a.text(b.get_x() + b.get_width() / 2, p['psnr'] + .4, '%.1f' % p['psnr'], ha='center', fontsize=8)
a.axhline(35, color=RED, ls='--', lw=1); 
a.set_ylim(30, 50); a.set_xlabel('test photo'); a.set_ylabel('PSNR (dB), higher = less change'); a.set_title('PSNR per photo (dashed = 35 dB, usually invisible)')
a = fig.add_subplot(gs[1, 2:])
a.bar(np.array(ids) - .2, [p['mean_change'] for p in photos], .4, color=BLUE, label='mean |change| (grey levels)')
a.bar(np.array(ids) + .2, [p['max_change'] for p in photos], .4, color=GREY, label='largest single change')
a.set_xlabel('test photo'); a.legend(frameon=False, fontsize=7.5, loc='upper right'); a.set_ylim(0, 12); a.set_title('Mean change ≤ 2.7 levels (of 255)')
save(fig, 'fig03_invisibility.png')

# ------------------------------------------------------------------ FIG 4: survival heatmap
names = [a['name'] for a in photos[0]['attacks']]
Z = np.array([[p['attacks'][j]['z1'] for j in range(len(names))] for p in photos])
fig, ax = plt.subplots(figsize=(11, 4.3))
cmap = plt.get_cmap('YlGnBu')
im = ax.imshow(Z.T, cmap=cmap, vmin=0, vmax=38, aspect='auto')
labs = {'ok': 'OK', 'part': 'PART', 'damaged': 'DMG', 'none': 'NONE'}
for i, p in enumerate(photos):
    for j, a_ in enumerate(p['attacks']):
        col = 'white' if a_['z1'] > 20 else INK
        extra = '' if a_['status'] != 'part' else '\nloc.'
        ax.text(i, j, '%s\n%.0f' % (labs[a_['status']], a_['z1']), ha='center', va='center', fontsize=6.8, color=col, fontweight='bold' if a_['status'] == 'ok' else 'normal')
        if a_['status'] == 'part':
            ax.add_patch(Rectangle((i - .5, j - .5), 1, 1, fc='none', ec=ORANGE, lw=2))
        if a_['status'] == 'damaged':
            ax.add_patch(Rectangle((i - .5, j - .5), 1, 1, fc='none', ec=RED, lw=2))
ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=8); ax.set_xticks(range(len(photos))); ax.set_xticklabels(['Photo %d\n%.0f MP' % (p['id'], p['mp']) for p in photos], fontsize=8)
ax.spines[:].set_visible(False); ax.tick_params(length=0)
cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01); cb.set_label('layer-1 detection strength z (3.5 = threshold)')
ax.set_title('Cell = status and detection strength z.   Orange frame: location-only recovery.   Red frame: mark present but unreadable.', loc='left', fontsize=8.6)
save(fig, 'fig04_survival_matrix.png')

# ------------------------------------------------------------------ FIG 5: sweeps
fig, axs = plt.subplots(1, 3, figsize=(11, 3.5), gridspec_kw={'width_ratios': [1.15, 1.15, 0.9], 'wspace': 0.25})
Ls = sorted({r['L'] for r in photos[0]['res_sweep']})
for ax, q, tt in [(axs[0], 70, 'Shrunk, JPEG q70'), (axs[1], 40, 'Shrunk, JPEG q40')]:
    for p in photos:
        z = [next(r['z1'] for r in p['res_sweep'] if r['L'] == L and r['q'] == q) for L in Ls]
        ax.plot(Ls, z, '-', color=GREY, lw=1, alpha=.8)
    mean = [np.mean([next(r['z1'] for r in p['res_sweep'] if r['L'] == L and r['q'] == q) for p in photos]) for L in Ls]
    rate = [np.mean([next(r['ok1'] for r in p['res_sweep'] if r['L'] == L and r['q'] == q) for p in photos]) * 100 for L in Ls]
    ax.plot(Ls, mean, 'o-', color=TEAL, lw=2.2, label='mean of 7 photos')
    ax.axhline(3.5, color=RED, ls='--', lw=1); ax.text(Ls[-1], 4.2, 'detection threshold 3.5', color=RED, fontsize=7.5, ha='right')
    for p in photos:
        bad = [(L, next(r['z1'] for r in p['res_sweep'] if r['L'] == L and r['q'] == q)) for L in Ls if not next(r['ok1'] for r in p['res_sweep'] if r['L'] == L and r['q'] == q)]
        if bad:
            ax.scatter(*zip(*bad), marker='x', color=RED, s=26, zorder=5, label='record NOT read' if (p['id'] == 6 and q == 40) else None)
    ax.text(Ls[0], 38, '%d of 7 photos read in full at 800 px' % sum(next(r['ok1'] for r in p['res_sweep'] if r['L'] == 800 and r['q'] == q) for p in photos), fontsize=7.8, color=INK, va='top')
    ax.set_xlabel('long edge (px)'); ax.set_ylabel('layer-1 z'); ax.set_title(tt); ax.set_ylim(0, 40); ax.set_xscale('log'); ax.set_xticks(Ls); ax.set_xticklabels([str(l) for l in Ls], rotation=60, fontsize=7); ax.minorticks_off()
    if q == 40:
        ax.legend(frameon=False, fontsize=7.5, loc='upper left', bbox_to_anchor=(0, 0.9))
ax = axs[2]; qs = [r['q'] for r in photos[0]['q_sweep']]
for p in photos:
    ax.plot(qs, [r['z1'] for r in p['q_sweep']], '-', color=GREY, lw=1, alpha=.8)
ax.plot(qs, [np.mean([p['q_sweep'][k]['z1'] for p in photos]) for k in range(len(qs))], 'o-', color=TEAL, lw=2.2)
ax.axhline(3.5, color=RED, ls='--', lw=1); ax.invert_xaxis(); ax.set_xlabel('JPEG quality (1600 px copy)'); ax.set_ylabel('layer-1 z'); ax.set_title('Pure compression'); ax.set_ylim(0, 40)
save(fig, 'fig05_resolution_quality.png')

# ------------------------------------------------------------------ extra controls (false positives) + texture
sizes = [('full q95', lambda x: W.jpeg(x, 95)[0]), ('2000 q85', lambda x: W.jpeg(W.resize_long(x, 2000), 85)[0]), ('1600 q70', lambda x: W.jpeg(W.resize_long(x, 1600), 70)[0]),
         ('1280 q60', lambda x: W.jpeg(W.resize_long(x, 1280), 60)[0]), ('1080 q50', lambda x: W.jpeg(W.resize_long(x, 1080), 50)[0]), ('800 q40', lambda x: W.jpeg(W.resize_long(x, 800), 40)[0]),
         ('1600 B/W', lambda x: W.jpeg(W.resize_long(cv2.cvtColor(cv2.cvtColor(x, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB), 1600), 70)[0]),
         ('1600 blur', lambda x: W.jpeg(cv2.GaussianBlur(W.resize_long(x, 1600), (0, 0), 1.2), 70)[0])]
ctl = []
tex_mean = []
for p, f in zip(photos, files):
    o_ = W.load(f)
    for nm, fn in sizes:
        r = W.read(fn(o_)); ctl.append(dict(photo=p['id'], attack=nm, status=r['status'], z1=r['z1'], z2=r['z2'], l1=r['l1'] is not None, l2=r['l2'] is not None))
    s_ = W.resize_long(o_, 1600); g = cv2.cvtColor(s_, cv2.COLOR_RGB2GRAY).astype(np.float32)
    mu = cv2.resize(g, (nx, ny), interpolation=cv2.INTER_AREA); mu2 = cv2.resize(g * g, (nx, ny), interpolation=cv2.INTER_AREA)
    tex = np.clip(np.sqrt(np.maximum(mu2 - mu * mu, 0)) / 14, 0, 1)
    tex_mean.append(float(np.maximum(tex, .25).mean()))
json.dump(dict(controls=ctl, texture=tex_mean), open(os.path.join(W.HERE, 'results', 'controls.json'), 'w'), indent=1)
fp_status = sum(c['status'] != 'none' for c in ctl); fp_l1 = sum(c['l1'] for c in ctl); fp_l2 = sum(c['l2'] for c in ctl)
print('controls', len(ctl), 'non-none', fp_status, 'l1', fp_l1, 'l2', fp_l2, 'max z1', max(c['z1'] for c in ctl), 'max z2', max(c['z2'] for c in ctl))

# FIG 6: separation + texture
fig, axs = plt.subplots(1, 2, figsize=(11, 3.7), gridspec_kw={'width_ratios': [1.25, 1]})
ax = axs[0]
marked_z = [a_['z1'] for p in photos for a_ in p['attacks'] if 'CONTROL' not in a_['name'] and a_['status'] in ('ok',)]
ctl_z1 = [c['z1'] for c in ctl]; ctl_z2 = [c['z2'] for c in ctl]
rng = np.random.default_rng(1)
ax.scatter(marked_z, 2 + rng.uniform(-.25, .25, len(marked_z)), s=14, color=TEAL, alpha=.75, label='marked, read OK (n=%d)' % len(marked_z))
ax.scatter(ctl_z1, 1 + rng.uniform(-.25, .25, len(ctl_z1)), s=14, color=ORANGE, alpha=.75, label='UNMARKED photos, layer 1 (n=%d)' % len(ctl_z1))
ax.scatter(ctl_z2, 0 + rng.uniform(-.25, .25, len(ctl_z2)), s=14, color=RED, alpha=.75, label='UNMARKED photos, layer 2')
ax.axvline(3.5, color=INK, ls='--', lw=1); ax.text(3.7, 2.55, 'threshold 3.5', fontsize=7.5)
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(['unmarked\nlayer 2', 'unmarked\nlayer 1', 'marked\nlayer 1']); ax.set_xlabel('detection strength z'); ax.set_ylim(-.6, 2.8); ax.legend(frameon=False, fontsize=7.5, loc='lower right')
ax.set_title('False alarms: %d of %d unmarked reads said "mark" (max z = %.1f)' % (fp_status, len(ctl), max(max(ctl_z1), max(ctl_z2))), loc='left', fontsize=9)
ax = axs[1]
zmean = [np.mean([a_['z1'] for a_ in p['attacks'][1:2]]) for p in photos]
ax.scatter(tex_mean, zmean, s=70, color=TEAL, zorder=3)
for t_, z_, p in zip(tex_mean, zmean, photos):
    ax.annotate(str(p['id']), (t_, z_), textcoords='offset points', xytext=(7, 4), fontsize=9, fontweight='bold')
cc = np.corrcoef(tex_mean, zmean)[0, 1]
k_, b_ = np.polyfit(tex_mean, zmean, 1); xs_ = np.linspace(min(tex_mean) - .02, max(tex_mean) + .02, 10); ax.plot(xs_, k_ * xs_ + b_, '--', color=GREY)
ax.set_xlabel('mean tile texture factor (0.25 = flat … 1 = busy)'); ax.set_ylabel('z after chat-app copy'); ax.set_title('Busy scenes carry the mark better (r = %.2f)' % cc, loc='left', fontsize=9)
save(fig, 'fig06_false_alarms_texture.png')

# ------------------------------------------------------------------ FIG 7: case study (photo 1 and its journey)
i1 = 0
rgb1 = W.load(files[i1]); marked1, _ = W.embed(rgb1); stored1, _ = W.jpeg(marked1, 95)
g1 = cv2.cvtColor(stored1, cv2.COLOR_RGB2GRAY)
h1, w1 = stored1.shape[:2]
dm = stored1.copy(); dm[int(.25 * h1):int(.75 * h1), int(.25 * w1):int(.75 * w1)] = (110, 120, 125)
crop1 = W.jpeg(W.resize_long(stored1[:, :int(w1 * .9)], 1600), 70)[0]
import phys_sim
wa1 = W.jpeg(W.resize_long(stored1, 1600), 70)[0]
cam1, tc1 = phys_sim.simulate(cv2.cvtColor(wa1, cv2.COLOR_RGB2BGR), 'monitor', 10, 6, 2, 1.0, 2.5, 85, seed=0)
tapped1 = (tc1 + np.clip(np.random.default_rng(1000).normal(0, 0.0065 * wa1.shape[1] * 1.7 * 0.5, (4, 2)), -40, 40)).tolist()
stages = [('① Original\n(unmarked)', rgb1), ('② Marked\nstored q95', stored1), ('③ Chat app\n1600 px q70', W.jpeg(W.resize_long(stored1, 1600), 70)[0]),
          ('④ Thumbnail\n600 px q50', W.jpeg(W.resize_long(stored1, 600), 50)[0]), ('⑤ Black & white\n1600 px', W.jpeg(W.resize_long(cv2.cvtColor(g1, cv2.COLOR_GRAY2RGB), 1600), 70)[0]),
          ('⑥ 25 % painted over', W.jpeg(W.resize_long(dm, 1600), 70)[0]), ('⑦ Cropped 10 %\n+ chat app', crop1)]
stages.append(('⑧ Phone photo of\na monitor (simulated)', cv2.cvtColor(cam1, cv2.COLOR_BGR2RGB)))
fig = plt.figure(figsize=(11, 6.2)); gs = fig.add_gridspec(2, 4, hspace=.55, wspace=.08)
def fmt(r):
    if r['status'] == 'none':
        return 'NO MARK', GREY
    l1 = r['l1']
    if l1:
        ts = datetime.datetime.fromtimestamp(l1['t'], datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S') + '.%d' % l1['tenth']
        return 'OK  %.5f, %.5f\nalt %d m  %s UTC' % (l1['lat'], l1['lon'], l1['alt'], ts), GREEN
    if r['l2'] and r['l2'].get('lat') is not None:
        return 'PART  location only\n%.4f, %.4f (~10 m)' % (r['l2']['lat'], r['l2']['lon']), ORANGE
    return 'DAMAGED', RED
for k, (t, img) in enumerate(stages):
    a = fig.add_subplot(gs[k // 4, k % 4]); a.imshow(img); a.axis('off'); a.set_title(t, fontsize=8.5)
    if k == 0:
        r = W.read(rgb1)
    elif k == 7:
        r = W.read(img, 'readpersp', tapped1)
    elif k == 6:
        r = W.read(img, 'readcrop')
    else:
        r = W.read(img)
    if r is None:
        continue
    txt, col = fmt(r)
    a.text(0.5, -0.04, txt, transform=a.transAxes, ha='center', va='top', fontsize=6.8, color=col, fontweight='bold', linespacing=1.3)
save(fig, 'fig07_case_study.png')

# ------------------------------------------------------------------ FIG 8: cost + crop/screen outcomes
fig, axs = plt.subplots(1, 3, figsize=(11, 3.6), gridspec_kw={'width_ratios': [1.2, 1, 1]})
ax = axs[0]
ops = [('Read (12 MP file)', 0.15, TEAL), ('Mark: embed', 0.65, BLUE), ('Mark: self-test', 0.56, BLUE), ('Read + crop search', 3.5, ORANGE), ('Read photo of screen\n(clean case)', 24, RED), ('… hard case', 55, RED)]
ax.barh(range(len(ops)), [o_[1] for o_ in ops], color=[o_[2] for o_ in ops]); ax.set_xscale('log'); ax.set_yticks(range(len(ops))); ax.set_yticklabels([o_[0] for o_ in ops], fontsize=7.8); ax.invert_yaxis()
for k, o_ in enumerate(ops):
    ax.text(o_[1] * 1.12, k, '%.2g s' % o_[1], va='center', fontsize=7.8)
ax.set_xlim(0.05, 200); ax.set_xlabel('seconds on a mid-range Android phone (log)'); ax.set_title('Cost on a real phone', loc='left')
ax = axs[1]
cn = [c['name'] for c in photos[0]['crops']]
cs = np.array([[ (2 if c['ok1'] else (1 if c['ok2'] else 0)) for c in p['crops']] for p in photos])
for j, n_ in enumerate(cn):
    ax.bar(j, (cs[:, j] == 2).sum(), color=GREEN); ax.bar(j, (cs[:, j] == 1).sum(), bottom=(cs[:, j] == 2).sum(), color=ORANGE); ax.bar(j, (cs[:, j] == 0).sum(), bottom=(cs[:, j] >= 1).sum(), color=RED)
ax.set_xticks(range(len(cn))); ax.set_xticklabels([c.replace(' ', '\n', 1) for c in cn], fontsize=7); ax.set_ylabel('photos (of 7)'); ax.set_title('Plain crops + chat app', loc='left')
ax = axs[2]
sc = [[p['screen'][k] for p in photos] for k in range(2)]
for k, kind in enumerate(['monitor', 'print']):
    full = sum(s['ok1'] for s in sc[k]); part = sum((not s['ok1']) and s['ok2'] for s in sc[k]); fail = 7 - full - part
    ax.bar(k, full, color=GREEN, label='full record' if k == 0 else None); ax.bar(k, part, bottom=full, color=ORANGE); ax.bar(k, fail, bottom=full + part, color=RED)
ax.set_xticks([0, 1]); ax.set_xticklabels(['simulated\nmonitor photo', 'simulated\nprint photo']); ax.set_ylim(0, 7.5); ax.set_title('Photo of a screen / print', loc='left')
ax.text(0.5, 7.25, 'green = full · orange = partial · red = failed', fontsize=7, ha='center')
save(fig, 'fig08_cost_crops_screens.png')

# ------------------------------------------------------------------ sample images for the repo (EXIF-free, 1600 px)
for p, f in zip(photos, files):
    o_ = W.load(f); mk, _ = W.embed(o_)
    s = W.resize_long(mk, 1600)
    cv2.imwrite(os.path.join(SAMPLES, 'demo_%d_marked.jpg' % p['id']), cv2.cvtColor(s, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
print('ok')
