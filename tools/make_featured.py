"""Featured images: the name 'Ghostmark' as imagery (hidden ink under UV, dissolving pixel tiles, constellation, double exposure).
Writes PR-KIT/featured-images/*.png (1920x1080)."""
import os, sys, math, random
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import wmlib as W
from make_social_v2 import (FT, SEG, SEGL, SEGB, BLK, IMP, CON, CONB, GEO, GEOB, GEOI, BAH, CAMB, WW, HH, photo, cover, glow, grain, vignette, T, ghost_mask, ghost_signed, art_norm, DIV, NEON, LOGO)

ROOT = os.path.join(W.HERE, '..'); OUT = os.path.join(ROOT, 'PR-KIT', 'featured-images'); os.makedirs(OUT, exist_ok=True)


def text_mask(txt, font, size=None, center=(WW // 2, HH // 2), spacing=0):
    m = Image.new('L', (WW, HH), 0); d = ImageDraw.Draw(m)
    if spacing:
        widths = [d.textlength(c, font=font) for c in txt]; total = sum(widths) + spacing * (len(txt) - 1); x = center[0] - total / 2
        for c, w_ in zip(txt, widths): d.text((x, center[1]), c, font=font, fill=255, anchor='lm'); x += w_ + spacing
    else: d.text(center, txt, font=font, fill=255, anchor='mm')
    return m


# ============================================================ 1  hidden ink under a UV torch
def f1_uv():
    i = 36; rgb = photo(i, 2400); marked, _ = W.embed(rgb); g = art_norm(ghost_signed(rgb, marked, 1.2), 10)
    base = cover(marked, WW, HH); dark = Image.blend(base, Image.new('RGB', base.size, (4, 2, 14)), 0.80).filter(ImageFilter.GaussianBlur(1.5))
    art = cover(Image.fromarray(DIV(g)), WW, HH)
    yy, xx = np.mgrid[0:HH, 0:WW]; cx, cy = 1010, 520; r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2); light = np.clip(1 - r / 760, 0, 1) ** 1.6
    # the torch lights the photo a little, in violet
    lit = np.asarray(dark).astype(np.float32) * (1 + 1.5 * light[..., None]) + light[..., None] * np.array([50, 10, 90]); im = Image.fromarray(np.clip(lit, 0, 255).astype(np.uint8))
    m = text_mask('GHOSTMARK', FT(BAH, 190), spacing=16, center=(WW // 2, 520)); ma = (np.asarray(m).astype(np.float32) / 255) * np.clip(1.15 - r / 640, 0, 1) ** 1.2
    inkc = np.asarray(art).astype(np.float32); inkc = inkc * 0.9 + np.array([40, 40, 80]); layer = Image.fromarray(np.clip(inkc, 0, 255).astype(np.uint8)); alpha = Image.fromarray((ma * 255).astype(np.uint8))
    glw = Image.new('RGB', (WW, HH), (0, 0, 0)); glw.paste(Image.new('RGB', (WW, HH), (130, 60, 255)), (0, 0), alpha.filter(ImageFilter.GaussianBlur(26)))
    im = Image.fromarray(np.clip(np.asarray(im).astype(np.int32) + (np.asarray(glw) * 0.9).astype(np.int32), 0, 255).astype(np.uint8)); im.paste(layer, (0, 0), alpha)
    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); od = ImageDraw.Draw(ov); od.ellipse((cx - 770, cy - 770, cx + 770, cy + 770), outline=(170, 120, 255, 40), width=3); im = Image.alpha_composite(im.convert('RGBA'), ov).convert('RGB')
    d = ImageDraw.Draw(im, 'RGBA'); T(d, (WW // 2, HH - 70), 'under UV, the photo shows what it was hiding', FT(GEOI, 34), (200, 180, 255, 210), 'mm')
    grain(vignette(im, 0.55), 6).save(os.path.join(OUT, '01_hidden-ink.png'), optimize=True)


# ============================================================ 2  a ghost made of pixels, dissolving into the name
FONT = {'G': ['.XXX.', 'X...X', 'X....', 'X.XXX', 'X...X', 'X...X', '.XXX.'], 'H': ['X...X'] * 3 + ['XXXXX'] + ['X...X'] * 3, 'O': ['.XXX.'] + ['X...X'] * 5 + ['.XXX.'], 'S': ['.XXXX', 'X....', 'X....', '.XXX.', '....X', '....X', 'XXXX.'],
        'T': ['XXXXX'] + ['..X..'] * 6, 'M': ['X...X', 'XX.XX', 'X.X.X', 'X.X.X', 'X...X', 'X...X', 'X...X'], 'A': ['.XXX.', 'X...X', 'X...X', 'XXXXX', 'X...X', 'X...X', 'X...X'], 'R': ['XXXX.', 'X...X', 'X...X', 'XXXX.', 'X.X..', 'X..X.', 'X...X'], 'K': ['X...X', 'X..X.', 'X.X..', 'XX...', 'X.X..', 'X..X.', 'X...X']}


def f2_pixels():
    rs = np.random.default_rng(8); rnd = random.Random(8)
    bgm = np.zeros((HH, WW, 3), np.float32); yy, xx = np.mgrid[0:HH, 0:WW]
    for cx, cy, c, s in [(500, 540, (60, 40, 170), 700), (1500, 700, (0, 120, 200), 800)]: bgm += np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s * s)))[..., None] * np.array(c) * 0.55
    im = Image.fromarray(np.clip(bgm + np.array([6, 8, 22]), 0, 255).astype(np.uint8)).convert('RGBA'); T_ = 16
    gw, gh = 760, 840; gm = np.asarray(ghost_mask(gw, gh, 0)) > 128; ph = np.asarray(cover(photo(24, 1400), gw, gh)); gx0, gy0 = 150, 120; layer = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
    for ty in range(0, gh, T_):
        for tx in range(0, gw, T_):
            cy2, cx2 = min(ty + T_ // 2, gh - 1), min(tx + T_ // 2, gw - 1)
            if gm[cy2, cx2]:
                c = tuple(int(v) for v in ph[cy2, cx2]); frac = tx / gw; p = max(0.0, (frac - 0.45) / 0.55) ** 1.3
                if rnd.random() < p * 0.95:
                    dx = rnd.random() * 780 * p + 40 * p; dy = rnd.gauss(0, 70) * p; a = int(255 * (1 - 0.8 * p)); s = max(4, int(T_ * (1 - 0.6 * p * rnd.random()))); col = c if rnd.random() < 0.55 else rnd.choice([(80, 220, 255), (170, 130, 255), (255, 90, 190)])
                    x, y = gx0 + tx + dx, gy0 + ty + dy; ld.rectangle((x, y, x + s, y + s), fill=col + (a,))
                else: ld.rectangle((gx0 + tx, gy0 + ty, gx0 + tx + T_ - 2, gy0 + ty + T_ - 2), fill=c + (255,))
    # eyes: dark tiles
    for ex in (0.36, 0.62): cx_, cy_ = gx0 + int(gw * ex), gy0 + int(gh * 0.40); ld.ellipse((cx_ - 40, cy_ - 46, cx_ + 40, cy_ + 46), fill=(8, 8, 24, 255))
    im = Image.alpha_composite(im, layer)
    # the name, built from tiles that are still arriving
    t2 = 14; word = 'GHOSTMARK'; total = len(word) * 6 * t2 - t2; ox, oy = 1010, 840 - 7 * t2; wl = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); wd = ImageDraw.Draw(wl)
    for k, ch in enumerate(word):
        for r_, row in enumerate(FONT[ch]):
            for c_, v in enumerate(row):
                if v == 'X':
                    x, y = ox + (k * 6 + c_) * t2 - 0, oy + r_ * t2; col = (255, 255, 255)
                    if rnd.random() < 0.10 + 0.05 * k: px_, py_ = x + rnd.randint(-30, 30), y + rnd.randint(-40, 40); wd.rectangle((px_, py_, px_ + t2 - 3, py_ + t2 - 3), fill=(80, 220, 255, 150))
                    else: wd.rectangle((x, y, x + t2 - 3, y + t2 - 3), fill=col + (255,))
    im = im.convert('RGB'); gl = Image.new('RGB', (WW, HH)); gl.paste(wl.convert('RGB'), (0, 0), wl.split()[3]); gl = gl.filter(ImageFilter.GaussianBlur(14)); im = Image.fromarray(np.clip(np.asarray(im).astype(np.int32) + (np.asarray(gl) * 0.9).astype(np.int32), 0, 255).astype(np.uint8)); im.paste(wl.convert('RGB'), (0, 0), wl.split()[3])
    grain(im, 5).save(os.path.join(OUT, '02_dissolve.png'), optimize=True)


# ============================================================ 3  constellation
def f3_stars():
    i = 36; base = cover(photo(i, 2400), WW, HH); im = Image.blend(base, Image.new('RGB', base.size, (1, 3, 12)), 0.78).filter(ImageFilter.GaussianBlur(2)); rnd = random.Random(5)
    m = np.asarray(text_mask('GHOSTMARK', FT(GEOB, 190), spacing=14, center=(WW // 2, 440))) > 128; ys, xs = np.nonzero(m); pts = []
    idx = list(range(len(xs))); rnd.shuffle(idx)
    for k in idx:
        x, y = xs[k], ys[k]
        if all((x - px) ** 2 + (y - py) ** 2 > 26 ** 2 for px, py in pts): pts.append((x, y))
        if len(pts) > 420: break
    d = ImageDraw.Draw(im, 'RGBA'); lines = Image.new('RGB', (WW, HH), (0, 0, 0)); ld = ImageDraw.Draw(lines)
    for a in range(len(pts)):
        for b in range(a + 1, len(pts)):
            dd = math.hypot(pts[a][0] - pts[b][0], pts[a][1] - pts[b][1])
            if dd < 46: ld.line((pts[a], pts[b]), fill=(90, 150, 255), width=2)
    sm = lines.filter(ImageFilter.GaussianBlur(5)); im = Image.fromarray(np.clip(np.asarray(im).astype(np.int32) + np.asarray(lines).astype(np.int32) * 0.8 + np.asarray(sm).astype(np.int32) * 0.8, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im, 'RGBA')
    for (x, y) in pts:
        r = rnd.choice([3, 3, 4, 5, 7]); im = glow(im, lambda dd, x=x, y=y, r=r: dd.ellipse((x - r * 2, y - r * 2, x + r * 2, y + r * 2), fill=(120, 170, 255)), 8, 0.55)
    d = ImageDraw.Draw(im, 'RGBA')
    for (x, y) in pts: r = rnd.choice([2, 3, 3, 4]); d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 255))
    for _ in range(420): x, y = rnd.randrange(WW), rnd.randrange(HH); r = rnd.choice([1, 1, 1, 2]); d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, rnd.randrange(60, 200)))
    gm = ghost_mask(150, 165, 0); gl_ = Image.new('RGBA', (150, 165), (255, 255, 255, 0)); gl_.putalpha(gm.point(lambda v: int(v * 0.85))); im.paste(gl_.convert('RGB'), (WW // 2 - 75, 700), gl_.split()[3])
    T(d, (WW // 2, 930), 'a constellation of tiny changes', FT(GEOI, 38), (190, 210, 255, 220), 'mm')
    grain(vignette(im, 0.5), 5).save(os.path.join(OUT, '03_constellation.png'), optimize=True)


# ============================================================ 4  double exposure
def f4_double():
    bg = np.zeros((HH, WW, 3), np.float32); yy, xx = np.mgrid[0:HH, 0:WW]; t = (yy / HH)[..., None]; bg = np.array([238, 232, 222]) * (1 - t) + np.array([206, 214, 222]) * t
    im = Image.fromarray(bg.astype(np.uint8)).convert('RGB'); rs = np.random.default_rng(1); im = grain(im, 3)
    gw, gh = 760, 860; gm = ghost_mask(gw, gh, 0); a = cover(photo(35, 2000), gw, gh); b = cover(photo(23, 1400), gw, gh)
    A = np.asarray(a).astype(np.float32) / 255; B = np.asarray(b).astype(np.float32) / 255; ex = 1 - (1 - A) * (1 - B * 0.65); ex = np.clip((ex - 0.18) * 1.25, 0, 1); inside = Image.fromarray((ex * 255).astype(np.uint8))
    gx, gy = 220, 110
    for k, c in ((2, (255, 60, 150)), (1, (40, 190, 255))):
        eg = ImageChops.subtract(gm.filter(ImageFilter.MaxFilter(9)), gm); col = Image.new('RGB', (gw, gh), c); im.paste(col, (gx + 14 * k * (1 if k == 2 else -1), gy + 10 * k), eg.point(lambda v: int(v * 0.55)))
    sh = Image.new('RGBA', (gw + 200, gh + 200), (0, 0, 0, 0)); sh.paste(Image.new('RGBA', (gw, gh), (30, 30, 60, 120)), (110, 140), gm); sh = sh.filter(ImageFilter.GaussianBlur(30)); base = im.convert('RGBA'); base.alpha_composite(sh, (gx - 100, gy - 70)); im = base.convert('RGB')
    im.paste(inside, (gx, gy), gm)
    for ex_ in (0.36, 0.62): cx_, cy_ = gx + int(gw * ex_), gy + int(gh * 0.40)
    d = ImageDraw.Draw(im, 'RGBA'); d.line((1150, 330, 1150, 700), fill=(40, 50, 80, 120), width=2)
    sp = 'G H O S T M A R K'; T(d, (1200, 400), sp, FT(CAMB, 62), (36, 44, 72)); T(d, (1204, 500), 'two exposures.', FT(GEOI, 46), (70, 80, 110)); T(d, (1204, 560), 'the second one is invisible.', FT(GEOI, 46), (70, 80, 110))
    l = LOGO.resize((96, 96), Image.LANCZOS); im.paste(l, (1204, 700), l)
    grain(im, 4).save(os.path.join(OUT, '04_double-exposure.png'), optimize=True)


if __name__ == '__main__':
    fns = [f1_uv, f2_pixels, f3_stars, f4_double]; sel = [int(a) for a in sys.argv[1:]]
    for k, f in enumerate(fns, 1):
        if sel and k not in sel: continue
        f(); print('done', k, flush=True)
