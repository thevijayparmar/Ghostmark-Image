"""Social preview card (1280x640) and a GIF copy of the black-and-white demo, for PR-KIT/."""
import os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import wmlib as W
from make_showcase import F, cover

ROOT = os.path.join(W.HERE, '..'); KIT = os.path.join(ROOT, 'PR-KIT'); MEDIA = os.path.join(KIT, 'media'); os.makedirs(MEDIA, exist_ok=True)
R = json.load(open(os.path.join(W.HERE, 'results', 'results.json')))['photos']
BWS = json.load(open(os.path.join(W.HERE, 'results', 'bw_summary.json')))
N = len(R); NDEV = len({(p['make'], p['model']) for p in R})
BG, CARD, LINE, TXT, MUTED, CYAN, PURPLE, GREEN = (13, 17, 23), (22, 27, 34), (48, 54, 61), (240, 246, 252), (139, 148, 158), (56, 189, 248), (167, 139, 250), (63, 185, 80)

im = Image.new('RGB', (1280, 640), BG)
# right: a collage of real photos, dimmed, fading into the background
files = W.photo_files(); pick = [10, 33, 14, 28, 6, 35, 18, 24, 11]
col = Image.new('RGB', (560, 640), BG)
for k, i in enumerate(pick):
    th = Image.fromarray(W.resize_long(W.load(files[i]), 500)); x, y = (k % 3) * 187, (k // 3) * 214
    col.paste(cover(np.asarray(th), 187, 214), (x, y))
col = Image.blend(col, Image.new('RGB', col.size, BG), 0.35)
mask = Image.linear_gradient('L').rotate(90).resize((560, 640))          # left = 0 ... right = 255
im.paste(col, (720, 0), mask)
d = ImageDraw.Draw(im)
logo = Image.open(os.path.join(ROOT, 'assets', 'logo.png')).convert('RGBA').resize((200, 200), Image.LANCZOS)
im.paste(logo, (70, 70), logo)
d.text((300, 84), 'Ghostmark', font=F(88, True), fill=TXT)
d.text((304, 188), 'Photos that remember where and when,', font=F(30), fill=(200, 215, 230))
d.text((304, 228), 'even after the metadata is gone.', font=F(30), fill=CYAN)
chips = [('%d photos · %d cameras' % (N, NDEV), CYAN), ('survives chat apps and B&W filters', PURPLE), ('Android · Python · JS', GREEN)]
x = 70
for t, c in chips:
    w = d.textbbox((0, 0), t, font=F(22, True))[2] + 40
    d.rounded_rectangle((x, 330, x + w, 384), 27, fill=CARD, outline=c, width=2); d.text((x + 20, 343), t, font=F(22, True), fill=c); x += w + 16
d.text((70, 440), 'Invisible location · altitude · UTC time hidden in the pixels', font=F(24), fill=MUTED)
d.text((70, 480), 'Apache-2.0 · zero dependencies · no permissions · no network', font=F(24), fill=MUTED)
d.text((70, 568), 'github.com/thevijayparmar/Ghostmark-Image', font=F(28, True), fill=TXT)
im.save(os.path.join(KIT, 'social-preview.png'))
print('social-preview.png', os.path.getsize(os.path.join(KIT, 'social-preview.png')) // 1024, 'KB (GitHub limit 1 MB)')

# GIF copy of the black-and-white demo (X, LinkedIn and Reddit prefer GIF/MP4 over WebP)
w = Image.open(os.path.join(ROOT, 'assets', 'bw_demo.webp')); fr, du = [], []
for k in range(w.n_frames):
    w.seek(k); fr.append(w.convert('RGB').quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)); du.append(w.info.get('duration', 100))
fr[0].save(os.path.join(MEDIA, 'bw_demo.gif'), save_all=True, append_images=fr[1:], duration=du, loop=0, optimize=True, disposal=2)
print('bw_demo.gif', os.path.getsize(os.path.join(MEDIA, 'bw_demo.gif')) // 1024, 'KB')
