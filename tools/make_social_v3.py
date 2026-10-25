"""Social images v3: ten use-case pieces (field inspection, survey, evidence, travel ...), each its own style.
Every decoded value shown is read back from a real marked, compressed copy. Inspection photos carry DEMO coordinates; travel photos carry their own EXIF GPS/time.
Writes PR-KIT/social-images-v3/*.png"""
import os, sys, json, math, random, datetime
import numpy as np, cv2, matplotlib
import matplotlib.figure, matplotlib.backends.backend_agg
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import wmlib as W
from make_social_v2 import (FT, SEG, SEGB, SEGL, BLK, IMP, CON, CONB, GEO, GEOB, GEOI, BAH, INK, CAMB, WW, HH, files, photo, cover, exif_gps, glow, grain, vignette, T, ghost_mask, LOGO)

ROOT = os.path.join(W.HERE, '..'); OUT = os.path.join(ROOT, 'PR-KIT', 'social-images-v3'); os.makedirs(OUT, exist_ok=True)
_pc = {}


def run(i, lat, lon, alt=0, t=1792929600, long=2000, quality=70, edge=1600, bw=False):
    """mark photo i with the record, store q95, make a chat-app copy; return (marked, chat_copy, read-result)."""
    key = (i, round(lat, 5), round(lon, 5), alt, t, long, bw)
    if key not in _pc:
        rgb = photo(i, long); marked, _ = W.embed(rgb, dict(lat=lat, lon=lon, alt=alt, t=t, tenth=0, manual=0)); stored, _ = W.jpeg(marked, 95)
        if bw: stored = cv2.cvtColor(cv2.cvtColor(stored, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
        chat = W.jpeg(W.resize_long(stored, edge), quality)[0]; _pc[key] = (marked, chat, W.read(chat))
    return _pc[key]


def ts(t): return datetime.datetime.fromtimestamp(t, datetime.timezone.utc)
def pin(d, x, y, r, col, ring=(255, 255, 255)):
    d.polygon([(x - r * .8, y - r * .5), (x + r * .8, y - r * .5), (x, y + r * 1.7)], fill=col); d.ellipse((x - r, y - r * 2, x + r, y), fill=col); d.ellipse((x - r * .42, y - r * 1.42, x + r * .42, y - r * .58), fill=ring)


# ============================================================ 01 inspector HUD
def p01():
    i = 10; lat, lon, alt, t = 12.971599, 77.594566, 920, 1792929600; marked, chat, r = run(i, lat, lon, alt, t, 2400); l1 = r['l1']; assert l1
    im = cover(marked, WW, HH); im = Image.blend(im, Image.new('RGB', im.size, (0, 12, 22)), 0.35); d = ImageDraw.Draw(im, 'RGBA'); C = (70, 230, 255)
    for k in range(0, WW, 60): d.line((k, 0, k, 12), fill=C + (130,), width=2); d.line((k, HH - 12, k, HH), fill=C + (130,), width=2)
    for k in range(0, HH, 60): d.line((0, k, 12, k), fill=C + (130,), width=2); d.line((WW - 12, k, WW, k), fill=C + (130,), width=2)
    cx, cy = 870, 560
    for rr in (150, 220): d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=C + (200 if rr == 150 else 90,), width=3)
    for a in range(0, 360, 15):
        x0, y0 = cx + 150 * math.cos(math.radians(a)), cy + 150 * math.sin(math.radians(a)); x1, y1 = cx + (165 if a % 45 else 182) * math.cos(math.radians(a)), cy + (165 if a % 45 else 182) * math.sin(math.radians(a)); d.line((x0, y0, x1, y1), fill=C + (220,), width=3)
    d.line((cx - 40, cy, cx + 40, cy), fill=C, width=3); d.line((cx, cy - 40, cx, cy + 40), fill=C, width=3)
    d.line((cx + 220, cy - 80, 1180, 300, 1260, 300), fill=C, width=3)
    px = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); ImageDraw.Draw(px).rounded_rectangle((1260, 150, 1820, 780), 18, fill=(2, 14, 26, 205), outline=C + (255,), width=3); im = Image.alpha_composite(im.convert('RGBA'), px).convert('RGB'); d = ImageDraw.Draw(im, 'RGBA')
    T(d, (1295, 180), 'GEO-LOCK', FT(BAH, 52), C); d.ellipse((1735, 192, 1769, 226), fill=(60, 230, 120)); T(d, (1752, 209), '', FT(SEG, 20), (0, 0, 0), 'mm')
    d.line((1738, 209, 1747, 218, 1763, 198), fill=(0, 30, 10), width=5)
    rows = [('LAT', '%.5f° N' % l1['lat']), ('LON', '%.5f° E' % l1['lon']), ('ALT', '%d m' % l1['alt']), ('UTC', ts(l1['t']).strftime('%Y-%m-%d %H:%M:%S')), ('SURVIVED', 'chat app · 1600 px · q70'), ('EXIF', 'none')]
    for k, (a, b) in enumerate(rows): y = 270 + k * 76; T(d, (1295, y), a, FT(CON, 24), (120, 180, 200)); T(d, (1295, y + 28), b, FT(CONB, 36 if k < 4 else 30), (255, 255, 255) if k < 4 else (255, 210, 120))
    T(d, (60, 56), 'SITE INSPECTION', FT(BAH, 40), C); T(d, (60, 106), 'location travels with the photo, even when the file does not', FT(CON, 24), (170, 215, 230))
    T(d, (60, HH - 70), 'demo coordinates', FT(CON, 22), (120, 160, 180)); l = LOGO.resize((70, 70), Image.LANCZOS); im.paste(l, (WW - 130, HH - 110), l)
    grain(vignette(im, 0.4), 5).save(os.path.join(OUT, '01_inspector-hud.png'), optimize=True)


# ============================================================ 02 site map
def p02():
    rs = np.random.default_rng(5); n = rs.normal(0, 1, (30, 54)).astype(np.float32); n = cv2.resize(cv2.GaussianBlur(n, (0, 0), 2.2), (WW, HH), interpolation=cv2.INTER_CUBIC)
    fig = matplotlib.figure.Figure(figsize=(WW / 100, HH / 100), dpi=100); matplotlib.backends.backend_agg.FigureCanvasAgg(fig); ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor((4 / 255, 16 / 255, 20 / 255)); fig.patch.set_facecolor((4 / 255, 16 / 255, 20 / 255))
    ax.contour(n, levels=np.linspace(n.min(), n.max(), 30), colors=[(0.1, 0.5, 0.5, 0.45)], linewidths=1.0); ax.set_xlim(0, WW); ax.set_ylim(HH, 0); ax.axis('off')
    for g in range(0, WW, 120): ax.plot([g, g], [0, HH], color=(1, 1, 1, .05), lw=1)
    for g in range(0, HH, 120): ax.plot([0, WW], [g, g], color=(1, 1, 1, .05), lw=1)
    fig.canvas.draw(); im = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()); d = ImageDraw.Draw(im, 'RGBA')
    sites = [(3, 12.99, 77.54), (4, 13.00, 77.66), (6, 12.94, 77.61), (8, 12.97, 77.52), (9, 13.02, 77.60), (13, 12.92, 77.57), (15, 12.95, 77.69), (18, 12.98, 77.63)]
    lat0, lat1, lon0, lon1 = 12.90, 13.04, 77.48, 77.72; X = lambda lo: 480 + (lo - lon0) / (lon1 - lon0) * 960; Y = lambda la: 960 - (la - lat0) / (lat1 - lat0) * 820
    cards = []
    for k, (i, la, lo) in enumerate(sites):
        marked, chat, r = run(i, la, lo, 100 + k * 7, 1792929600 + k * 600); l1 = r['l1']; assert l1, i; cards.append((i, l1, chat))
    cards.sort(key=lambda c: c[1]['lon']); left = sorted(cards[:4], key=lambda c: -c[1]['lat']); right = sorted(cards[4:], key=lambda c: -c[1]['lat']); cw, ch = 330, 214
    for side, lst in ((0, left), (1, right)):
        for k, (i, l1, chat) in enumerate(lst):
            x = 60 if side == 0 else WW - 60 - cw; y = 80 + k * 245; px, py = X(l1['lon']), Y(l1['lat'])
            d.line((x + (cw if side == 0 else 0), y + ch // 2, px, py), fill=(80, 255, 220, 150), width=2); im.paste(cover(chat, cw, ch), (x, y)); d = ImageDraw.Draw(im, 'RGBA'); d.rectangle((x, y + ch - 34, x + cw, y + ch), fill=(0, 12, 14, 215)); d.rectangle((x, y, x + cw, y + ch), outline=(80, 255, 220, 230), width=2)
            T(d, (x + 10, y + ch - 17), '%.4f° N  %.4f° E' % (l1['lat'], l1['lon']), FT(CONB, 20), (255, 255, 255), 'lm')
    for (i, l1, chat) in cards:
        px, py = X(l1['lon']), Y(l1['lat']); im = glow(im, lambda dd, px=px, py=py: dd.ellipse((px - 20, py - 20, px + 20, py + 20), fill=(0, 255, 200)), 18, 0.7); d = ImageDraw.Draw(im, 'RGBA'); pin(d, px, py - 6, 12, (0, 255, 200), (4, 16, 20))
    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); od = ImageDraw.Draw(ov); od.rounded_rectangle((640, 20, 1280, 130), 40, fill=(2, 10, 12, 225)); im = Image.alpha_composite(im.convert('RGBA'), ov).convert('RGB'); d = ImageDraw.Draw(im)
    T(d, (WW // 2, 58), '8 photos. 8 pins.', FT(BAH, 46), (255, 255, 255), 'mm'); T(d, (WW // 2, 102), 'nobody typed a single coordinate', FT(SEGL, 27), (110, 240, 220), 'mm'); T(d, (WW // 2, HH - 24), 'demo coordinates', FT(CON, 20), (90, 140, 140), 'mm')
    grain(im, 4).save(os.path.join(OUT, '02_site-map.png'), optimize=True)


# ============================================================ 03 rubber stamp
def p03():
    i = 3; lat, lon, alt, t = 23.0225, 72.5714, 53, 1792929600; marked, chat, r = run(i, lat, lon, alt, t); l1 = r['l1']; assert l1
    rs = np.random.default_rng(2); paper = np.full((HH, WW, 3), (214, 196, 160), np.float32); paper += cv2.resize(rs.normal(0, 7, (HH // 8, WW // 8)).astype(np.float32), (WW, HH))[..., None]; im = Image.fromarray(np.clip(paper, 0, 255).astype(np.uint8)); im = vignette(im, 0.5)
    ph = cover(chat, 930, 640); card = Image.new('RGBA', (1010, 760), (250, 248, 242, 255)); card.paste(ph, (40, 40)); sh = Image.new('RGBA', (1250, 1000), (0, 0, 0, 0)); sh.paste(Image.new('RGBA', card.size, (0, 0, 0, 150)), (90, 120)); sh = sh.filter(ImageFilter.GaussianBlur(24)).rotate(-3, expand=True, resample=Image.BICUBIC)
    c = card.rotate(-3, expand=True, resample=Image.BICUBIC); base = im.convert('RGBA'); base.alpha_composite(sh, (50, 60)); base.alpha_composite(c, (90, 150))
    for (x, y, a) in [(110, 160, -35), (1020, 230, 30)]: tp = Image.new('RGBA', (200, 60), (240, 230, 160, 190)).rotate(a, expand=True); base.alpha_composite(tp, (x - 60, y - 20))
    im = base.convert('RGB'); S = 560; st = Image.new('RGBA', (S, S), (0, 0, 0, 0)); sd = ImageDraw.Draw(st); ink = (40, 60, 190, 255)
    sd.ellipse((8, 8, S - 8, S - 8), outline=ink, width=12); sd.ellipse((40, 40, S - 40, S - 40), outline=ink, width=4); sd.ellipse((150, 150, S - 150, S - 150), outline=ink, width=4)
    txt = 'LOCATION READ FROM THE PIXELS  ·  NO EXIF NEEDED  ·  '; f = FT(BLK, 38); R_ = 222; n = len(txt)
    for k, ch in enumerate(txt):
        a = k / n * 2 * math.pi - math.pi / 2; g = Image.new('RGBA', (60, 60), (0, 0, 0, 0)); ImageDraw.Draw(g).text((30, 30), ch, font=f, fill=ink, anchor='mm'); g = g.rotate(-math.degrees(a) - 90, resample=Image.BICUBIC)
        st.alpha_composite(g, (int(S / 2 + R_ * math.cos(a) - 30), int(S / 2 + R_ * math.sin(a) - 30)))
    T(sd, (S // 2, S // 2 - 52), '%.4f N' % l1['lat'], FT(BLK, 44), ink, 'mm'); T(sd, (S // 2, S // 2), '%.4f E' % l1['lon'], FT(BLK, 44), ink, 'mm'); T(sd, (S // 2, S // 2 + 56), ts(l1['t']).strftime('%d.%m.%Y'), FT(BLK, 34), ink, 'mm')
    noise = (np.random.default_rng(9).random((S, S)) > 0.16).astype(np.uint8) * 255; a = np.asarray(st.split()[3]); st.putalpha(Image.fromarray((a * (noise / 255.0)).astype(np.uint8))); st = st.rotate(14, expand=True, resample=Image.BICUBIC)
    base = im.convert('RGBA'); base.alpha_composite(st, (1250, 130)); im = base.convert('RGB'); d = ImageDraw.Draw(im)
    T(d, (1290, 790), 'sent on chat.', FT(INK, 64), (50, 50, 80), 'lm'); T(d, (1290, 870), 'stamped by the pixels.', FT(INK, 64), (50, 50, 80), 'lm'); T(d, (1290, 960), 'demo coordinates', FT(INK, 28), (110, 100, 90), 'lm')
    grain(im, 5).save(os.path.join(OUT, '03_stamp.png'), optimize=True)


# ============================================================ 04 drone flight line
def p04():
    im = Image.new('RGB', (WW, HH), (7, 12, 22)); d = ImageDraw.Draw(im, 'RGBA')
    for g in range(0, WW, 80): d.line((g, 0, g, HH), fill=(255, 255, 255, 12))
    for g in range(0, HH, 80): d.line((0, g, WW, g), fill=(255, 255, 255, 12))
    ids = [11, 12, 13, 14, 15, 16, 17, 18]; cards = []
    for k, i in enumerate(ids):
        la = 19.0760 + k * 0.0012 + 0.0009 * math.sin(k * 0.9); lo = 72.8777 + k * 0.0019; marked, chat, r = run(i, la, lo, 118, 1792929600 + k * 45); l1 = r['l1']; assert l1, i; cards.append((i, l1, chat))
    xs = [190 + k * (WW - 380) / 7 for k in range(8)]; ys = [560 + 55 * math.sin(k * 0.9) for k in range(8)]
    pts = [(xs[k], ys[k]) for k in range(8)]
    for a in range(7):
        for s in range(0, 20, 2): t0, t1 = s / 20, (s + 1) / 20; d.line((pts[a][0] + (pts[a + 1][0] - pts[a][0]) * t0, pts[a][1] + (pts[a + 1][1] - pts[a][1]) * t0, pts[a][0] + (pts[a + 1][0] - pts[a][0]) * t1, pts[a][1] + (pts[a + 1][1] - pts[a][1]) * t1), fill=(255, 190, 60, 220), width=3)
    cw, ch = 330, 220
    for k, (i, l1, chat) in enumerate(cards):
        x, y = xs[k], ys[k]; up = k % 2 == 1; cy = y - 70 - (ch + 74) if up else y + 70; ang = -3 if up else 3
        cd = Image.new('RGBA', (cw + 20, ch + 74), (14, 18, 28, 255)); cd.paste(cover(chat, cw, ch).convert('RGBA'), (10, 10)); cdd = ImageDraw.Draw(cd)
        cdd.text((12, ch + 16), '%.4f N   %.4f E' % (l1['lat'], l1['lon']), font=FT(CONB, 21), fill=(255, 255, 255)); cdd.text((12, ch + 44), 'alt %d m  ·  frame %d' % (l1['alt'], k + 1), font=FT(CONB, 19), fill=(255, 200, 100))
        cd = cd.rotate(ang, expand=True, resample=Image.BICUBIC); base = im.convert('RGBA'); d.line((x, y, x, cy + (ch + 74 if up else 0)), fill=(255, 190, 60, 130), width=2); base.alpha_composite(cd, (int(x - cd.width / 2), int(cy))); im = base.convert('RGB'); d = ImageDraw.Draw(im, 'RGBA')
        d.ellipse((x - 12, y - 12, x + 12, y + 12), fill=(255, 190, 60)); d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(7, 12, 22))
    T(d, (60, 64), 'ONE', FT(BAH, 64), (255, 255, 255)); T(d, (60, 130), 'FLIGHT', FT(BAH, 64), (255, 190, 60)); T(d, (62, 215), '8 frames', FT(CON, 26), (200, 210, 230)); T(d, (62, 250), '8 locations', FT(CON, 26), (200, 210, 230)); T(d, (62, 285), 'from the pixels', FT(CON, 26), (200, 210, 230))
    T(d, (WW - 60, HH - 40), 'demo coordinates', FT(CON, 22), (120, 140, 170), 'ra')
    grain(im, 4).save(os.path.join(OUT, '04_one-flight.png'), optimize=True)


# ============================================================ 05 chat phone
def p05():
    bgm = np.zeros((HH, WW, 3), np.float32); yy, xx = np.mgrid[0:HH, 0:WW]
    for cx, cy, c, s in [(500, 300, (0, 150, 120), 800), (1500, 850, (20, 90, 160), 900)]: bgm += np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s * s)))[..., None] * np.array(c) * 0.6
    im = Image.fromarray(np.clip(bgm + 8, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im, 'RGBA'); px, py, pw, ph = 250, 36, 520, 1010
    d.rounded_rectangle((px - 18, py - 18, px + pw + 18, py + ph + 18), 70, fill=(10, 12, 16), outline=(70, 76, 90), width=4); d.rounded_rectangle((px, py, px + pw, py + ph), 54, fill=(236, 229, 221))
    d.rounded_rectangle((px, py, px + pw, py + 120), 54, fill=(18, 110, 96)); d.rectangle((px, py + 60, px + pw, py + 120), fill=(18, 110, 96)); d.ellipse((px + 70, py + 38, px + 128, py + 96), fill=(190, 225, 215)); T(d, (px + 148, py + 58), 'Site team', FT(SEGB, 32), (255, 255, 255)); T(d, (px + 148, py + 94), 'Ravi, Meena, Arjun, +9', FT(SEG, 22), (200, 235, 225))
    msgs = [(3, 12.9716, 77.5946, 'Rebar mat, level 3'), (7, 12.9790, 77.6020, 'Rooftop formwork done'), (4, 12.9650, 77.5890, 'Crane base, east side')]
    y = py + 150
    for k, (i, la, lo, cap) in enumerate(msgs):
        marked, chat, r = run(i, la, lo, 900, 1792929600 + k * 1200, 1600); l1 = r['l1']; assert l1, i
        bw_, bh = 410, 250; bx = px + pw - bw_ - 24; d.rounded_rectangle((bx, y, bx + bw_, y + bh + 120), 22, fill=(217, 253, 211)); im.paste(cover(chat, bw_ - 20, bh - 10), (bx + 10, y + 10)); d = ImageDraw.Draw(im, 'RGBA')
        T(d, (bx + 16, y + bh + 8), cap, FT(SEG, 26), (30, 40, 35)); d.rounded_rectangle((bx + 12, y + bh + 50, bx + bw_ - 12, y + bh + 100), 14, fill=(255, 255, 255, 230)); pin(d, bx + 38, y + bh + 82, 8, (230, 70, 60), (255, 255, 255))
        T(d, (bx + 60, y + bh + 75), '%.4f, %.4f' % (l1['lat'], l1['lon']), FT(CONB, 23), (20, 30, 30), 'lm'); y += bh + 150
    X0 = 900
    T(d, (X0, 250), 'The site photos', FT(GEOI, 84), (255, 255, 255)); T(d, (X0, 350), 'came in on', FT(GEOI, 84), (255, 255, 255)); T(d, (X0, 450), 'the group chat.', FT(GEOI, 84), (255, 255, 255)); T(d, (X0, 640), 'The locations', FT(SEGL, 72), (140, 255, 220)); T(d, (X0, 730), 'came with them.', FT(SEGL, 72), (140, 255, 220))
    T(d, (X0 + 4, 880), 'demo coordinates', FT(CON, 24), (160, 200, 200)); l = LOGO.resize((96, 96), Image.LANCZOS); im.paste(l, (X0, 930), l)
    grain(im, 4).save(os.path.join(OUT, '05_group-chat.png'), optimize=True)


# ============================================================ 06 clipboard report
def p06():
    rs = np.random.default_rng(3); conc = np.full((HH, WW, 3), 78, np.float32) + cv2.resize(rs.normal(0, 9, (HH // 5, WW // 5)).astype(np.float32), (WW, HH))[..., None] + cv2.resize(rs.normal(0, 4, (HH // 40, WW // 40)).astype(np.float32), (WW, HH))[..., None]
    im = Image.fromarray(np.clip(conc * np.array([1.0, 1.0, 1.04]), 0, 255).astype(np.uint8)); im = vignette(im, 0.6)
    sheet = Image.new('RGBA', (900, 1150), (252, 251, 247, 255)); sd = ImageDraw.Draw(sheet); sd.rectangle((0, 0, 900, 110), fill=(30, 60, 110)); sd.text((40, 55), 'SITE REPORT', font=FT(BAH, 52), fill=(255, 255, 255), anchor='lm'); sd.text((860, 55), 'all photos geotagged', font=FT(CON, 24), fill=(200, 220, 255), anchor='rm')
    picks = [(3, 12.9716, 77.5946), (7, 12.9719, 77.5951), (10, 12.9722, 77.5949), (13, 12.9730, 77.5958), (15, 12.9741, 77.5962), (19, 12.9748, 77.5970)]
    for k, (i, la, lo) in enumerate(picks):
        marked, chat, r = run(i, la, lo, 920 + k, 1792929600 + k * 420, 1600); l1 = r['l1']; assert l1, i
        x, y = 40 + (k % 2) * 430, 140 + (k // 2) * 330; sheet.paste(cover(chat, 390, 230).convert('RGBA'), (x, y)); sd.text((x, y + 242), 'P-%02d' % (k + 1), font=FT(CONB, 22), fill=(30, 60, 110)); sd.text((x + 70, y + 242), '%.4fN %.4fE  %dm' % (l1['lat'], l1['lon'], l1['alt']), font=FT(CON, 21), fill=(60, 60, 70)); sd.text((x + 70, y + 270), ts(l1['t']).strftime('%H:%M:%S UTC'), font=FT(CON, 19), fill=(120, 120, 130))
    sd.line((560, 1090, 860, 1090), fill=(60, 60, 70), width=2); sd.text((560, 1110), 'inspector', font=FT(CON, 20), fill=(120, 120, 130))
    board = Image.new('RGBA', (1000, 1290), (150, 108, 70, 255)); board.paste(sheet, (50, 110)); bd = ImageDraw.Draw(board); bd.rounded_rectangle((300, 20, 700, 150), 24, fill=(190, 195, 205), outline=(120, 125, 135), width=4)
    board = board.resize((int(1000 * .78), int(1290 * .78)), Image.LANCZOS)
    sh = Image.new('RGBA', (board.width + 160, board.height + 160), (0, 0, 0, 0)); sh.paste(Image.new('RGBA', board.size, (0, 0, 0, 170)), (70, 100)); sh = sh.filter(ImageFilter.GaussianBlur(26)).rotate(-4, expand=True, resample=Image.BICUBIC); bo = board.rotate(-4, expand=True, resample=Image.BICUBIC)
    base = im.convert('RGBA'); base.alpha_composite(sh, (1000 - 60, 20 - 60)); base.alpha_composite(bo, (1000, 20)); im = base.convert('RGB'); d = ImageDraw.Draw(im, 'RGBA')
    T(d, (90, 240), 'All six photos', FT(GEOI, 76), (255, 255, 255)); T(d, (90, 335), 'came from the chat.', FT(GEOI, 76), (255, 255, 255)); T(d, (90, 480), 'Every caption', FT(SEGL, 60), (255, 220, 120)); T(d, (90, 555), 'was read, not typed.', FT(SEGL, 60), (255, 220, 120))
    d.rounded_rectangle((90, 760, 640, 782), 11, fill=(240, 200, 40)); d.polygon([(640, 760), (640, 782), (684, 771)], fill=(60, 60, 60)); T(d, (92, 960), 'demo coordinates', FT(CON, 22), (170, 170, 175))
    grain(im, 5).save(os.path.join(OUT, '06_site-report.png'), optimize=True)


# ============================================================ 07 broadcast lower third
def p07():
    i = 32; g = exif_gps(i); ex = __import__('PIL.Image', fromlist=['x']).open(files[i]).getexif().get_ifd(0x8769).get(36867); t = int(datetime.datetime.strptime(ex, '%Y:%m:%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc).timestamp())
    marked, chat, r = run(i, g['lat'], g['lon'], 0, t, 2400); l1 = r['l1']; assert l1
    full = cover(chat, WW, HH); a = np.asarray(full).astype(np.float32); a = np.clip((a - 128) * 1.1 + 128, 0, 255); a[::3] *= 0.9; im = Image.fromarray(a.astype(np.uint8)); im = im.filter(ImageFilter.GaussianBlur(0.8)); im = vignette(im, 0.5); d = ImageDraw.Draw(im, 'RGBA')
    d.rectangle((0, 0, WW, 120), fill=(0, 0, 0)); d.rectangle((0, HH - 120, WW, HH), fill=(0, 0, 0))
    d.rectangle((110, 720, 520, 790), fill=(210, 20, 40)); T(d, (140, 755), 'RECEIVED VIA CHAT', FT(BAH, 38), (255, 255, 255), 'lm')
    d.rectangle((110, 790, 1560, 930), fill=(10, 14, 24, 235)); T(d, (150, 828), '%.3f° N   %.3f° E' % (l1['lat'], l1['lon']), FT(BAH, 62), (255, 255, 255), 'lm'); T(d, (150, 892), 'metadata: none   ·   location & time: read from the pixels   ·   %s UTC' % ts(l1['t']).strftime('%Y-%m-%d %H:%M'), FT(SEG, 28), (160, 200, 255), 'lm')
    d.ellipse((60, 170, 84, 194), fill=(210, 20, 40)); T(d, (100, 182), 'RECOVERED', FT(CONB, 28), (255, 255, 255), 'lm'); T(d, (WW - 60, 182), 'GHOSTMARK', FT(CONB, 28), (255, 255, 255, 170), 'rm')
    grain(im, 9).save(os.path.join(OUT, '07_lower-third.png'), optimize=True)


# ============================================================ 08 film contact sheet
def p08():
    im = Image.new('RGB', (WW, HH), (34, 20, 10)); d = ImageDraw.Draw(im, 'RGBA'); idx = [23, 26, 28, 29, 35, 38]; fw, fh = 590, 400
    for row in range(2):
        y0 = 20 + row * 505; d.rectangle((0, y0, WW, y0 + 480), fill=(14, 10, 8))
        for k in range(0, WW, 46): d.rounded_rectangle((k + 10, y0 + 10, k + 30, y0 + 30), 5, fill=(34, 20, 10)); d.rounded_rectangle((k + 10, y0 + 450, k + 30, y0 + 470), 5, fill=(34, 20, 10))
        for c in range(3):
            k = row * 3 + c; i = idx[k]; g = exif_gps(i); ex = __import__('PIL.Image', fromlist=['x']).open(files[i]).getexif().get_ifd(0x8769).get(36867)
            t = int(datetime.datetime.strptime(ex, '%Y:%m:%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc).timestamp()); marked, chat, r = run(i, g['lat'], g['lon'], 0, t, 1800); l1 = r['l1']; assert l1, i
            x = 22 + c * (fw + 18); ph = cover(chat, fw, fh); im.paste(ph, (x, y0 + 40)); d = ImageDraw.Draw(im, 'RGBA'); d.rectangle((x, y0 + 40, x + fw, y0 + 40 + fh), outline=(60, 40, 20), width=3)
            d.rectangle((x + fw - 300, y0 + 40 + fh - 78, x + fw, y0 + 40 + fh), fill=(0, 0, 0, 110))
            T(d, (x + fw - 18, y0 + 40 + fh - 62), ts(l1['t']).strftime("'%y  %m  %d"), FT(CONB, 36), (255, 150, 30), 'rm'); T(d, (x + fw - 18, y0 + 40 + fh - 26), '%.3fN %.3fE' % (l1['lat'], l1['lon']), FT(CONB, 24), (255, 150, 30), 'rm')
            T(d, (x + 6, y0 + 462), '%dA' % (k + 1), FT(CON, 18), (255, 170, 60), 'ls')
    d.rectangle((0, 1030, WW, HH), fill=(34, 20, 10)); T(d, (WW // 2, 1056), 'every frame remembers where, and when.   (the orange stamp is not printed on the photo: it was read from it)', FT(INK, 34), (255, 200, 130), 'mm')
    grain(im, 6).save(os.path.join(OUT, '08_contact-sheet.png'), optimize=True)


# ============================================================ 09 forwarded four times
def p09():
    i = 13; lat, lon = 12.9716, 77.5946; run(i, lat, lon, 920, 1792929600, 2400)
    marked = _pc[(i, round(lat, 5), round(lon, 5), 920, 1792929600, 2400, False)][0]; stored, _ = W.jpeg(marked, 95); cur = stored; chain = [(1600, 70), (1280, 60), (1080, 50), (900, 45)]; outs = []
    for L, q in chain:
        cur = W.jpeg(W.resize_long(cur, L), q)[0]; r = W.read(cur); outs.append((L, q, cur, r))
    im = Image.new('RGB', (WW, HH), (10, 10, 18)); yy, xx = np.mgrid[0:HH, 0:WW]; bg = np.exp(-(((xx - 1300) ** 2 + (yy - 600) ** 2) / (2 * 900 ** 2)))[..., None] * np.array([40, 30, 110]) * 1.2; im = Image.fromarray(np.clip(np.asarray(im).astype(np.float32) + bg, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im, 'RGBA')
    for k, (L, q, img, r) in enumerate(outs):
        w = int(860 * 0.86 ** k); h = int(w * 0.68); x, y = 780 + 130 * k, 40 + 150 * k
        sh = Image.new('RGBA', (w + 80, h + 80), (0, 0, 0, 0)); sh.paste(Image.new('RGBA', (w, h), (0, 0, 0, 180)), (50, 60)); sh = sh.filter(ImageFilter.GaussianBlur(18)); base = im.convert('RGBA'); base.alpha_composite(sh, (x - 20, y - 20)); im = base.convert('RGB'); d = ImageDraw.Draw(im, 'RGBA')
        im.paste(cover(img, w, h), (x, y)); ok = r['status'] == 'ok'; col = (60, 230, 120) if ok else (240, 170, 50); d.rectangle((x, y, x + w, y + h), outline=col, width=4)
        d.rounded_rectangle((x + 10, y + 10, x + 10 + 290, y + 10 + 42), 10, fill=(0, 0, 0, 200)); T(d, (x + 24, y + 31), 'copy %d  ·  %d px  ·  q%d' % (k + 1, L, q), FT(CON, 21), (255, 255, 255), 'lm')
        lay = r['l1'] or r['l2']
        if lay: d.rounded_rectangle((x + 10, y + 60, x + 10 + 400, y + 60 + 44), 10, fill=(0, 0, 0, 200)); T(d, (x + 24, y + 82), '%.4f N  %.4f E%s' % (lay['lat'], lay['lon'], '' if ok else '  (location only)'), FT(CONB, 21), col, 'lm')
    T(d, (70, 560), 'forwarded', FT(GEOI, 118), (255, 255, 255)); T(d, (70, 695), 'four times.', FT(GEOI, 118), (255, 255, 255)); T(d, (74, 860), 'still knows where it is.', FT(SEGL, 56), (150, 255, 190)); T(d, (74, 940), 'demo coordinates', FT(CON, 22), (130, 130, 160))
    grain(im, 5).save(os.path.join(OUT, '09_forwarded-four-times.png'), optimize=True); print('chain', [(L, r['status']) for L, q, _, r in outs])


# ============================================================ 10 safety board
def p10():
    N = 480; im = cover(photo(7, 1600), WW, HH).filter(ImageFilter.GaussianBlur(14)); im = Image.blend(im, Image.new('RGB', im.size, (0, 0, 0)), 0.72); d = ImageDraw.Draw(im, 'RGBA')
    bx0, by0, bx1, by1 = 120, 90, 1800, 990; d.rounded_rectangle((bx0, by0, bx1, by1), 26, fill=(250, 250, 244)); d.rounded_rectangle((bx0 + 20, by0 + 20, bx1 - 20, by1 - 20), 14, outline=(20, 20, 20), width=6)
    st = Image.new('RGBA', (bx1 - bx0 - 40, 70), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
    for k in range(-2, 60): sd.polygon([(k * 70, 70), (k * 70 + 35, 70), (k * 70 + 70, 0), (k * 70 + 35, 0)], fill=(20, 20, 20, 255))
    band = Image.new('RGBA', st.size, (250, 200, 20, 255)); band.alpha_composite(st); im.paste(band.convert('RGB'), (bx0 + 20, by0 + 20)); im.paste(band.convert('RGB'), (bx0 + 20, by1 - 90)); d = ImageDraw.Draw(im, 'RGBA')
    T(d, (WW // 2, 262), 'SAFETY FIRST.', FT(IMP, 120), (20, 20, 20), 'mm'); T(d, (WW // 2, 352), 'ALSO: KNOW WHERE THE PHOTO WAS TAKEN.', FT(BAH, 44), (20, 20, 20), 'mm')
    T(d, (WW // 2, 425), 'WRONG LOCATIONS READ', FT(IMP, 56), (200, 30, 30), 'mm')
    x = WW // 2 - 115; d.rounded_rectangle((x, 460, x + 230, 740), 20, fill=(25, 25, 28)); d.line((x, 600, x + 230, 600), fill=(8, 8, 8), width=6); T(d, (x + 115, 605), '0', FT(IMP, 330), (250, 250, 240), 'mm')
    d.ellipse((x - 8, 592, x + 8, 608), fill=(8, 8, 8)); d.ellipse((x + 222, 592, x + 238, 608), fill=(8, 8, 8))
    T(d, (WW // 2, 790), 'IN %d EDITED COPIES TESTED  (chat apps, resizing, filters, crops)' % N, FT(BAH, 36), (20, 20, 20), 'mm'); T(d, (WW // 2, 842), 'UNREADABLE? IT SAYS SO. IT NEVER GUESSES.', FT(BAH, 32), (90, 90, 90), 'mm')
    grain(im, 4).save(os.path.join(OUT, '10_safety-board.png'), optimize=True)


if __name__ == '__main__':
    fns = [p01, p02, p03, p04, p05, p06, p07, p08, p09, p10]; sel = [int(a) for a in sys.argv[1:]]
    for k, f in enumerate(fns, 1):
        if sel and k not in sel: continue
        f(); print('done', k, flush=True)
