"""Black-and-white showcase: wall of B&W photos with the location read back, survival matrix, 'why it works' figure,
statistics, and an animated demo. Needs results/bw.json (run_bw.py). Writes assets/fig14..fig17 + bw_demo.webp + results/bw_summary.json."""
import json, os, math
from concurrent.futures import ThreadPoolExecutor
import numpy as np, cv2, matplotlib
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from theme import *
import wmlib as W
import make_showcase as MS
from make_showcase import F, fit, cover, SCENE
BG_, CARD_, LINE_, TXT_, MUTED_, GREEN_, ORANGE_, RED_ = MS.BG, MS.CARD, MS.LINE, MS.TXT, MS.MUTED, MS.GREEN, MS.ORANGE, MS.RED
from run_bw import gray_rgb, err_m

A = os.path.join(W.HERE, '..', 'assets')
BW = json.load(open(os.path.join(W.HERE, 'results', 'bw.json')))
files = W.photo_files(); N = len(files)
R = json.load(open(os.path.join(W.HERE, 'results', 'results.json')))['photos']
VAR = [r['name'] for r in BW[0]['rows']]
SHORT = ['B&W\nstored', 'B&W +\nchat app', 'B&W +\nsocial 1080', 'B&W +\nthumb 800', 'B&W +\ncontrast', 'B&W +\n75% crop', 'equal-weight\ngrey', 'red-filter\nB&W', 'green-filter\nB&W']
CHAT = 1  # variant index: B&W + chat app


def save(fig, name, dpi=150):
    fig.savefig(os.path.join(A, name), dpi=dpi, bbox_inches='tight'); plt.close(fig); print('saved', name)


# ------------------------------------------------------------------ numbers
ok = np.array([[r['ok2'] for r in p['rows']] for p in BW])                    # N x 9
z2 = np.array([[r['z2'] for r in p['rows']] for p in BW])
strong = {k: np.array([p['strong'][k]['ok2'] for p in BW]) for k in ('1.5', '2.0')}
errs = [r['err_m'] for p in BW for r in p['rows'] if r['ok2'] and r['err_m'] is not None]
chat_err = [p['rows'][CHAT]['err_m'] for p in BW if p['rows'][CHAT]['ok2']]
agree = sum(1 for p in BW for r in p['rows'] if 'py_ok2' in r and r['py_ok2'] == r['ok2'] and r['py_status'] == r['status'])
n_py = sum(1 for p in BW for r in p['rows'] if 'py_ok2' in r)
ctl_clean = sum(p['control']['status'] == 'none' for p in BW)
S = dict(n=N, variants=VAR, ok=ok.sum(0).tolist(), strong15=int(strong['1.5'].sum()), strong20=int(strong['2.0'].sum()),
         chat_ok=int(ok[:, CHAT].sum()), median_err=float(np.median(chat_err)) if chat_err else None, p90_err=float(np.percentile(chat_err, 90)) if chat_err else None,
         all_median_err=float(np.median(errs)), all_p90_err=float(np.percentile(errs, 90)), max_err=float(max(errs)), n_reads=len(errs),
         py_agree=agree, py_n=n_py, control_clean=ctl_clean, never_wrong=bool(all(r['err_m'] is None or r['err_m'] < 25 or not r['ok2'] for p in BW for r in p['rows'])),
         full_in_bw=int(sum(r['ok1'] for p in BW for r in p['rows'])),
         strong15_psnr=float(np.mean([p['strong']['1.5']['psnr'] for p in BW])), strong20_psnr=float(np.mean([p['strong']['2.0']['psnr'] for p in BW])),
         strong15_err=None)
json.dump(S, open(os.path.join(W.HERE, 'results', 'bw_summary.json'), 'w'), indent=1)
print({k: v for k, v in S.items() if k != 'variants'})


# ------------------------------------------------------------------ delivered B&W copies (for the wall and the demo)
def bw_copy(i):
    rgb = W.load(files[i]); marked, _ = W.embed(rgb); stored, _ = W.jpeg(marked, 95)
    return W.jpeg(W.resize_long(gray_rgb(stored), 1600), 70)[0], rgb, marked


with ThreadPoolExecutor(max_workers=6) as ex:
    copies = list(ex.map(bw_copy, range(N)))


# ================================================================== fig14: the wall
cw, ch, cols = 226, 156, 8; rows = (N + cols - 1) // cols; th = ch + 46
wall = Image.new('RGB', (cols * (cw + 10) + 10, rows * (th + 10) + 10), BG_); d = ImageDraw.Draw(wall)
for k in range(N):
    x, y = 10 + (k % cols) * (cw + 10), 10 + (k // cols) * (th + 10); row = BW[k]['rows'][CHAT]
    col = GREEN_ if row['ok2'] else RED_
    d.rounded_rectangle((x - 3, y - 3, x + cw + 3, y + th - 3), 9, fill=CARD_, outline=col, width=2)
    th_img = cv2.resize(copies[k][0], (max(8, copies[k][0].shape[1] // 6), max(8, copies[k][0].shape[0] // 6)), interpolation=cv2.INTER_AREA)
    wall.paste(cover(th_img, cw, ch), (x, y))
    d.rectangle((x, y, x + 46, y + 21), fill=BG_); d.text((x + 6, y + 4), '#%d' % (k + 1), font=F(12, True), fill=(255, 255, 255))
    if row['ok2']:
        d.text((x + 6, y + ch + 6), '✓ location read', font=F(12, True), fill=col)
        d.text((x + 6, y + ch + 25), '%.0f m off  ·  z = %.1f' % (row['err_m'], row['z2']), font=F(11), fill=MUTED_)
    else:
        d.text((x + 6, y + ch + 6), '✗ not read', font=F(12, True), fill=col)
        d.text((x + 6, y + ch + 25), 'z = %.1f  (needs > 3.5)' % row['z2'], font=F(11), fill=MUTED_)
wall.save(os.path.join(A, 'fig14_bw_wall.jpg'), quality=88); print('saved fig14_bw_wall.jpg')

# ================================================================== fig15: matrix
cols_lab = SHORT + ['mark x1.5\nB&W + chat', 'mark x2\nB&W + chat']
M = np.concatenate([ok.astype(int), strong['1.5'][:, None].astype(int), strong['2.0'][:, None].astype(int)], 1)
Z = np.concatenate([z2, np.array([[p['strong']['1.5']['z2'], p['strong']['2.0']['z2']] for p in BW])], 1)
fig, ax = plt.subplots(figsize=(11.5, 0.3 * N + 2.4))
ax.imshow(M, cmap=matplotlib.colors.ListedColormap([RED, GREEN]), aspect='auto', vmin=0, vmax=1, alpha=.88)
for y in range(N):
    for x in range(M.shape[1]): ax.text(x, y, '%.0f' % Z[y, x], ha='center', va='center', fontsize=6.4, color=BG)
ax.set_xticks(range(len(cols_lab))); ax.set_xticklabels(cols_lab, fontsize=7); ax.xaxis.tick_top()
ax.set_yticks(range(N)); ax.set_yticklabels(['#%d %s' % (p['id'], device_group(p['make'], p['model'])[:12]) for p in R], fontsize=6.8)
ax.axvline(8.5, color=TXT, lw=1.4)
ax.set_title('Location (layer 2) read from a black-and-white copy: green = read to about 10 m, number = detection score z', loc='left', pad=48, fontsize=9)
ax.spines[:].set_visible(False); ax.tick_params(length=0)
save(fig, 'fig15_bw_matrix.png')

# ================================================================== fig16: why it survives
hi = 10                                                                      # photo 11: cracked column
bwc, rgb, marked = copies[hi]
orig_c = W.jpeg(W.resize_long(gray_rgb(W.jpeg(rgb, 95)[0]), 1600), 70)[0]
ghost = lambda a, b, g: np.clip(0.5 + cv2.GaussianBlur((a.astype(np.float32) - b.astype(np.float32)), (0, 0), 1.0) * g / 255, 0, 1)
Y = lambda im: im.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
Cc = lambda im: (((im[..., 0] - Y(im)) * 0.713 + (im[..., 2] - Y(im)) * 0.564) * 0.5).astype(np.float32)
sm = lambda im: cv2.resize(im, (max(8, im.shape[1] // 4), max(8, im.shape[0] // 4)), interpolation=cv2.INTER_AREA)
panels = [('1  Your photo, marked', sm(marked), None),
          ('2  Colour layer (Cb/Cr), x60', ghost(Cc(sm(marked)), Cc(sm(rgb)), 60), 'RdBu_r'),
          ('3  Brightness layer (luma), x20', ghost(Y(sm(marked)), Y(sm(rgb)), 20), 'RdBu_r'),
          ('4  After B&W + chat app: what is left', ghost(Y(sm(bwc)), Y(sm(orig_c)), 20), 'RdBu_r')]
fig, axs = plt.subplots(1, 4, figsize=(11.5, 3.5))
for a, (t, im, cm) in zip(axs, panels):
    if cm: a.imshow(im, cmap=cm, vmin=0, vmax=1)
    else: a.imshow(im)
    a.set_title(t, fontsize=8.4, loc='left'); a.axis('off')
axs[1].text(0.5, -0.06, 'deleted by black & white', transform=axs[1].transAxes, ha='center', va='top', color=RED, fontsize=8.5, fontweight='bold')
axs[2].text(0.5, -0.06, 'kept: it is the picture\'s own brightness', transform=axs[2].transAxes, ha='center', va='top', color=GREEN, fontsize=8.5, fontweight='bold')
axs[3].text(0.5, -0.06, 'still readable', transform=axs[3].transAxes, ha='center', va='top', color=GREEN, fontsize=8.5, fontweight='bold')
fig.subplots_adjust(wspace=.04)
save(fig, 'fig16_bw_why.png')

# ================================================================== fig17: statistics
fig, axs = plt.subplots(1, 3, figsize=(11.5, 4), gridspec_kw={'width_ratios': [1.25, 1.25, 1]})
ax = axs[0]
names = SHORT + ['mark x1.5\nB&W + chat', 'mark x2\nB&W + chat']
vals = list(ok.sum(0)) + [strong['1.5'].sum(), strong['2.0'].sum()]
cols_ = [CYAN] * 9 + [PURPLE, PURPLE]
ax.barh(range(len(vals)), vals, color=cols_, alpha=.9); ax.invert_yaxis()
for y, v in enumerate(vals): ax.text(v + .4, y, '%d' % v, va='center', fontsize=7.5, color=TXT)
ax.set_yticks(range(len(vals))); ax.set_yticklabels([n.replace('\n', ' ') for n in names], fontsize=7); ax.set_xlim(0, N + 4); ax.axvline(N, color=MUTED, ls=':', lw=1)
ax.set_xlabel('photos with the location read (of %d)' % N); ax.set_title('How many photos keep their location', loc='left')
ax = axs[1]
data = [z2[:, j] for j in range(9)] + [np.array([p['strong'][k]['z2'] for p in BW]) for k in ('1.5', '2.0')]
bp = ax.boxplot(data, vert=False, patch_artist=True, widths=.55, showfliers=False, medianprops=dict(color=BG, lw=1.6))
for b, c in zip(bp['boxes'], cols_): b.set(facecolor=c, alpha=.85, edgecolor=c)
for k in ('whiskers', 'caps'):
    for l in bp[k]: l.set(color=MUTED)
ax.axvline(3.5, color=RED, ls='--', lw=1); ax.invert_yaxis(); ax.set_yticks(range(1, len(data) + 1)); ax.set_yticklabels([])
ax.set_xlabel('brightness-layer z (red line = detection limit 3.5)'); ax.set_title('Signal strength', loc='left')
ax = axs[2]
tex = np.array([p['texture'] for p in R]); zc = z2[:, CHAT]; okc = ok[:, CHAT]
ax.scatter(tex[okc], zc[okc], s=34, color=GREEN, edgecolor=BG, label='location read')
ax.scatter(tex[~okc], zc[~okc], s=34, color=RED, edgecolor=BG, label='not read')
ax.axhline(3.5, color=RED, ls='--', lw=1); ax.legend(frameon=False, fontsize=7.5, loc='upper left')
ax.set_xlabel('scene texture (0 = flat, 1 = busy)'); ax.set_ylabel('brightness-layer z, B&W + chat app'); ax.set_title('Busy scenes keep the location', loc='left')
fig.tight_layout(); save(fig, 'fig17_bw_stats.png')

# ================================================================== the animated demo (photo 11)
rgbc, k = rgb, hi
r = W.read(bwc); row = BW[k]['rows'][CHAT]
gmap = (matplotlib.colormaps['RdBu_r'](ghost(Y(sm(bwc)), Y(sm(orig_c)), 20))[..., :3] * 255).astype(np.uint8)
colour = sm(marked); grey = sm(gray_rgb(marked))
PW, PH, IW = 760, 440, 420
base_col, base_bw, base_gm = [np.asarray(fit(x, IW, 400, CARD_)) for x in (colour, grey, gmap)]
stat_lines = ['LAT  %.4f° N' % r['l2']['lat'], 'LON  %.4f° E' % r['l2']['lon'], '± about 10 m  (%.0f m off here)' % (row['err_m'] or 0)] if r.get('l2') else ['not read']


def demo_frame(stage, t):
    """stage 0 colour, 1 colour->B&W, 2 B&W, 3 B&W->hidden layer, 4 hidden layer, 5 decoded"""
    im = {0: base_col, 1: (base_col * (1 - t) + base_bw * t).astype(np.uint8), 2: base_bw, 3: (base_bw * (1 - t) + base_gm * t).astype(np.uint8), 4: base_gm, 5: base_gm}[stage]
    f = Image.new('RGB', (PW, PH), BG_); d = ImageDraw.Draw(f)
    d.rounded_rectangle((10, 10, IW + 30, 430), 10, fill=CARD_, outline=LINE_); f.paste(Image.fromarray(im), (20, 20))
    head = {0: ('1  Marked photo, in colour', 'Looks like any photo.'), 1: ('2  Someone turns it black & white', 'Throws away every colour value.'), 2: ('2  ...and sends it through a chat app', '1600 px, JPEG q70.'),
            3: ('3  The brightness layer is still there', 'Magnified x20. Red/blue = lighter/darker.'), 4: ('3  The brightness layer is still there', 'Magnified x20. Red/blue = lighter/darker.'), 5: ('4  Read back', 'Colour layer gone, location recovered.')}[stage]
    d.text((452, 24), head[0], font=F(15, True), fill=TXT_); d.text((452, 50), head[1], font=F(12), fill=MUTED_)
    gone = stage >= 2
    d.rounded_rectangle((452, 96, 750, 150), 8, fill=(40, 22, 22) if gone else (20, 40, 28), outline=RED_ if gone else GREEN_)
    d.text((464, 104), 'COLOUR LAYER (layer 1)', font=F(11, True), fill=RED_ if gone else GREEN_); d.text((464, 126), 'gone: no colour left to carry it' if gone else 'present in the colour channels', font=F(11), fill=TXT_)
    live = stage >= 3
    d.rounded_rectangle((452, 162, 750, 216), 8, fill=(22, 40, 28) if live or stage == 2 else (28, 28, 34), outline=GREEN_ if live or stage == 2 else LINE_)
    d.text((464, 170), 'BRIGHTNESS LAYER (layer 2)', font=F(11, True), fill=GREEN_ if live or stage == 2 else MUTED_); d.text((464, 192), 'rides in the brightness, which B&W keeps', font=F(11), fill=TXT_)
    if stage == 5:
        d.rounded_rectangle((452, 236, 750, 400), 10, fill=(13, 17, 23), outline=ORANGE_)
        d.text((466, 248), 'LOCATION ONLY  (layer 2)', font=F(13, True), fill=ORANGE_)
        for j, ln in enumerate(stat_lines): d.text((466, 282 + j * 28), ln, font=F(14), fill=TXT_)
        d.text((466, 372), 'time and altitude: lost with the colour', font=F(10), fill=MUTED_)
    d.text((452, 412), 'PHOTO 11 · z(layer 2) = %.1f' % row['z2'], font=F(10), fill=MUTED_)
    return f


frs, du = [], []
for stage, n_, dur in [(0, 1, 1400), (1, 6, 90), (2, 1, 1200), (3, 6, 90), (4, 1, 1100), (5, 1, 2800)]:
    for q in range(n_):
        frs.append(demo_frame(stage, (q + 1) / n_)); du.append(dur)
frs[0].save(os.path.join(A, 'bw_demo.webp'), save_all=True, append_images=frs[1:], duration=du, loop=0, quality=80, method=4)
print('saved bw_demo.webp', os.path.getsize(os.path.join(A, 'bw_demo.webp')) // 1024, 'KB')
