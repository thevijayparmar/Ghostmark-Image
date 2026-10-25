"""Social images v2: ten 1920x1080 pieces that show the OUTPUT, not the explanation. Real photos, real measurements.
Writes PR-KIT/social-images-v2/*.png"""
import os, sys, json, math, random, datetime
import numpy as np, cv2, matplotlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageOps
import wmlib as W

ROOT = os.path.join(W.HERE, '..'); OUT = os.path.join(ROOT, 'PR-KIT', 'social-images-v2'); os.makedirs(OUT, exist_ok=True)
FD = r'C:\Windows\Fonts'
def FT(n, s): return ImageFont.truetype(os.path.join(FD, n), s)
SEG, SEGB, SEGL, BLK, IMP, CON, CONB, GEO, GEOB, GEOI, BAH, INK, CAMB = 'segoeui.ttf', 'segoeuib.ttf', 'segoeuil.ttf', 'ariblk.ttf', 'impact.ttf', 'consola.ttf', 'consolab.ttf', 'georgia.ttf', 'georgiab.ttf', 'georgiai.ttf', 'bahnschrift.ttf', 'Inkfree.ttf', 'cambriab.ttf'
WW, HH = 1920, 1080
files = W.photo_files()
R = json.load(open(os.path.join(W.HERE, 'results', 'results.json')))['photos']
LOGO = Image.open(os.path.join(ROOT, 'assets', 'logo.png')).convert('RGBA')
_c = {}


def photo(i, long=2400):
    if (i, long) not in _c: _c[(i, long)] = W.resize_long(W.load(files[i]), long)
    return _c[(i, long)]


def cover(a, w, h):
    im = a if isinstance(a, Image.Image) else Image.fromarray(a); s = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS); x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h)).convert('RGB')


def exif_gps(i):
    g = Image.open(files[i]).getexif().get_ifd(0x8825)
    dms = lambda v: float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
    return dict(lat=dms(g[2]) * (1 if g[1] == 'N' else -1), lon=dms(g[4]) * (1 if g[3] == 'E' else -1), alt=int(float(g.get(6, 0))))


def payload_for(i, real=True):
    if real: g = exif_gps(i); return dict(lat=g['lat'], lon=g['lon'], alt=max(g['alt'], 0), t=1792929600, tenth=0, manual=0)
    return W.PAYLOAD


def prep(i, long=2400, real=True):
    rgb = photo(i, long); marked, _ = W.embed(rgb, payload_for(i, real)); stored, _ = W.jpeg(marked, 95); return rgb, marked, stored


def bw_chat(stored): return W.jpeg(W.resize_long(cv2.cvtColor(cv2.cvtColor(stored, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB), 1600), 70)[0]


def ghost_signed(rgb, marked, sigma=1.0):
    d = (marked.astype(np.float32) - rgb.astype(np.float32)).sum(2) / 3.0
    return cv2.GaussianBlur(d, (0, 0), sigma)


def art_norm(g, sig=14):
    hp = g - cv2.GaussianBlur(g, (0, 0), sig); sc = np.percentile(np.abs(hp), 97) + 1e-6
    return 0.5 + 0.5 * np.clip(hp / sc, -1, 1)


def lut(stops):
    xs = np.array([s[0] for s in stops]); cols = np.array([s[1] for s in stops], np.float32)
    def f(v):
        v = np.clip(v, 0, 1); return np.stack([np.interp(v, xs, cols[:, c]) for c in range(3)], -1).astype(np.uint8)
    return f


NEON = lut([(0, (6, 4, 30)), (.25, (60, 20, 150)), (.5, (255, 40, 160)), (.75, (255, 170, 70)), (1, (120, 255, 240))])
DIV = lut([(0, (255, 40, 170)), (.28, (150, 30, 160)), (.5, (6, 8, 30)), (.72, (20, 120, 230)), (1, (140, 255, 245))])
ICE = lut([(0, (4, 10, 34)), (.4, (20, 80, 200)), (.7, (60, 220, 255)), (1, (255, 255, 255))])


def ghost_poly(w, h, pad=0):
    def bez(p0, p1, p2, p3=None, n=30):
        o = []
        for i in range(1, n + 1):
            t = i / n; u = 1 - t
            o.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0], u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]) if p3 else (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0], u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
        return o
    pts = [(136, 384), (136, 236)] + bez((136, 236), (136, 152), (190, 100), (256, 100)) + bez((256, 100), (322, 100), (376, 152), (376, 236)) + [(376, 384)]
    for a, c, b in [((376, 384), (346, 424), (316, 384)), ((316, 384), (286, 344), (256, 384)), ((256, 384), (226, 424), (196, 384)), ((196, 384), (166, 344), (136, 384))]: pts += bez(a, c, b)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys); s = min((w - 2 * pad) / (x1 - x0), (h - 2 * pad) / (y1 - y0))
    return [((x - x0) * s + pad + ((w - 2 * pad) - (x1 - x0) * s) / 2, (y - y0) * s + pad + ((h - 2 * pad) - (y1 - y0) * s) / 2) for x, y in pts], s, (x0, y0)


def ghost_mask(w, h, pad=0, eyes=True):
    ss = 3; m = Image.new('L', (w * ss, h * ss), 0); pts, s, (x0, y0) = ghost_poly(w * ss, h * ss, pad * ss); ImageDraw.Draw(m).polygon(pts, fill=255)
    if eyes:
        ox = pts[0][0] - 136 * s + x0 * s * 0; d = ImageDraw.Draw(m)
        # eye positions relative to the ghost box
        bx0 = min(p[0] for p in pts); by0 = min(p[1] for p in pts)
        for cx in (216, 296): d.ellipse((bx0 + (cx - 20 - 136) * s, by0 + (224 - 20 - 100) * s, bx0 + (cx + 20 - 136) * s, by0 + (224 + 20 - 100) * s), fill=0)
    return m.resize((w, h), Image.LANCZOS)


def glow(im, fn, radius=20, k=1.0):
    layer = Image.new('RGB', im.size, (0, 0, 0)); fn(ImageDraw.Draw(layer)); g = layer.filter(ImageFilter.GaussianBlur(radius))
    return Image.fromarray(np.clip(np.asarray(im).astype(np.int32) + (np.asarray(g) * k).astype(np.int32), 0, 255).astype(np.uint8))


def grain(im, amt=10, seed=1):
    r = np.random.default_rng(seed); a = np.asarray(im).astype(np.float32) + r.normal(0, amt, (im.height, im.width, 1)); return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def vignette(im, k=0.55):
    yy, xx = np.mgrid[0:im.height, 0:im.width]; d = np.sqrt(((xx - im.width / 2) / (im.width / 2)) ** 2 + ((yy - im.height / 2) / (im.height / 2)) ** 2)
    f = 1 - k * np.clip(d - 0.35, 0, 1) ** 1.6; return Image.fromarray((np.asarray(im).astype(np.float32) * f[..., None]).clip(0, 255).astype(np.uint8))


def T(d, xy, s, f, fill, anchor='la'): d.text(xy, s, font=f, fill=fill, anchor=anchor)
def dms(v, pos, neg): return '%.4f° %s' % (abs(v), pos if v >= 0 else neg)


# ============================================================ A  coordinates as giant type, filled with the photo
def a_coords():
    i = 35; rgb, marked, stored = prep(i); r = W.read(bw_chat(stored)); l2 = r['l2']; assert l2
    bg = Image.new('RGB', (WW, HH), (5, 7, 12)); ph = cover(marked, WW, HH)
    m = Image.new('L', (WW, HH), 0); md = ImageDraw.Draw(m)
    f = FT(IMP, 430); md.text((WW // 2, 280), '%.3f°N' % l2['lat'], font=f, fill=255, anchor='mm'); md.text((WW // 2, 770), '%.3f°E' % l2['lon'], font=f, fill=255, anchor='mm')
    dim = Image.blend(ph, Image.new('RGB', ph.size, (0, 0, 0)), 0.78); im = dim.filter(ImageFilter.GaussianBlur(3)); im.paste(ph, (0, 0), m)
    im = glow(im, lambda dd: (dd.text((WW // 2, 280), '%.3f°N' % l2['lat'], font=f, fill=(40, 160, 230), anchor='mm'), dd.text((WW // 2, 770), '%.3f°E' % l2['lon'], font=f, fill=(40, 160, 230), anchor='mm')), 26, 0.55)
    im = vignette(im, 0.5); d = ImageDraw.Draw(im)
    T(d, (80, HH - 66), 'black & white  ·  WhatsApp  ·  read back from the pixels', FT(CON, 28), (200, 215, 230))
    l = LOGO.resize((84, 84), Image.LANCZOS); im.paste(l, (WW - 150, HH - 112), l)
    grain(im, 6).save(os.path.join(OUT, '01_coordinates.png'), optimize=True)


# ============================================================ B  forty invisible fingerprints
def b_fingerprints():
    cols, rows = 8, 5; tw, th = WW // cols, HH // rows + 1; im = Image.new('RGB', (WW, HH), (0, 0, 0))
    for k in range(40):
        rgb = photo(k, 700); marked, _ = W.embed(rgb); g = ghost_signed(rgb, marked, 1.5); v = art_norm(g)
        t = Image.fromarray(DIV(v)); im.paste(cover(t, tw, th), ((k % cols) * tw, (k // cols) * th))
    im = glow(im, lambda dd: None, 1, 0); d = ImageDraw.Draw(im, 'RGBA')
    pill = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); pd = ImageDraw.Draw(pill); pd.rounded_rectangle((560, 470, 1360, 610), 70, fill=(4, 4, 14, 215), outline=(255, 255, 255, 90), width=2)
    im = Image.alpha_composite(im.convert('RGBA'), pill).convert('RGB'); d = ImageDraw.Draw(im)
    T(d, (WW // 2, 520), '40 photos', FT(BAH, 64), (255, 255, 255), 'mm'); T(d, (WW // 2, 572), '40 invisible fingerprints', FT(SEGL, 38), (255, 190, 220), 'mm')
    im.save(os.path.join(OUT, '02_forty-fingerprints.png'), optimize=True)


# ============================================================ C  exploded layers in space
def c_layers():
    i = 30; rgb, marked, stored = prep(i, 1600, real=False)
    ph = cover(marked, 1000, 640)
    g1 = ghost_signed(rgb, marked, 1.0); chroma = cover(Image.fromarray(ICE(0.5 + cv2.GaussianBlur(((marked.astype(np.float32) - rgb.astype(np.float32)) @ np.array([0.5, -0.4, 0.9], np.float32)), (0, 0), 1.6) / 9)), 1000, 640)
    luma = cover(Image.fromarray(DIV(art_norm(g1))), 1000, 640)
    bg = np.zeros((HH, WW, 3), np.float32); yy, xx = np.mgrid[0:HH, 0:WW]
    for cx, cy, c, s in [(500, 300, (90, 30, 180), 800), (1500, 900, (0, 110, 200), 900)]: bg += np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s * s)))[..., None] * np.array(c) * 0.6
    canvas = Image.fromarray(np.clip(bg + 6, 0, 255).astype(np.uint8)).convert('RGBA')
    dst = lambda dy: np.float32([[330, 300 + dy], [1500, 160 + dy], [1760, 380 + dy], [590, 560 + dy]])
    src = np.float32([[0, 0], [1000, 0], [1000, 640], [0, 640]])
    for img, dy, a in [(luma, 330, 235), (chroma, 130, 215), (ph, -70, 255)]:
        rgba = np.dstack([np.asarray(img), np.full((640, 1000), a, np.uint8)]); M = cv2.getPerspectiveTransform(src, dst(dy))
        w_ = cv2.warpPerspective(rgba, M, (WW, HH), flags=cv2.INTER_AREA, borderValue=(0, 0, 0, 0)); layer = Image.fromarray(w_, 'RGBA')
        edge = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); ImageDraw.Draw(edge).polygon([tuple(p) for p in dst(dy)], outline=(255, 255, 255, 200), width=3)
        sh = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); ImageDraw.Draw(sh).polygon([tuple(p + [30, 50]) for p in dst(dy)], fill=(0, 0, 0, 130)); sh = sh.filter(ImageFilter.GaussianBlur(26))
        canvas = Image.alpha_composite(canvas, sh); canvas = Image.alpha_composite(canvas, layer); canvas = Image.alpha_composite(canvas, edge)
    im = canvas.convert('RGB'); d = ImageDraw.Draw(im)
    for y, s, c in [(140, 'the photo', (255, 255, 255)), (340, 'colour layer', (120, 220, 255)), (540, 'brightness layer', (255, 150, 200))]:
        T(d, (80, y), s, FT(CON, 30), c); d.line((80 + int(FT(CON, 30).getlength(s)) + 14, y + 17, 340, y + 17), fill=c, width=2)
    T(d, (80, HH - 150), 'one file.', FT(BAH, 44), (255, 255, 255)); T(d, (80, HH - 96), 'three layers. you only ever see the top one.', FT(SEGL, 30), (170, 190, 220))
    im = grain(im, 5); im.save(os.path.join(OUT, '03_layers.png'), optimize=True)


# ============================================================ D  the actual bits, raining
def d_bits():
    i = 28; rgb, marked, stored = prep(i, real=True)
    import importlib.util
    spec = importlib.util.spec_from_file_location('mark_engine', os.path.join(ROOT, 'python', 'ghostmark', '_core.py')); sys.path.insert(0, os.path.join(ROOT, 'python'))
    from ghostmark import _core as C
    bits = C.conv_encode(C.pack_l1(payload_for(i))); base = Image.blend(cover(marked, WW, HH), Image.new('RGB', (WW, HH), (0, 14, 10)), 0.82)
    im = base.convert('RGB'); d = ImageDraw.Draw(im); rng = random.Random(7); f = FT(CON, 30); cw = 34; ncol = WW // cw
    for c in range(ncol):
        head = rng.randrange(-300, HH + 200); L = rng.randrange(8, 34); off = rng.randrange(0, len(bits))
        for k in range(L):
            y = head - k * 34
            if 0 <= y < HH:
                ch = str(bits[(off + k) % len(bits)]); a = 1 - k / L; col = (int(40 + 215 * a * (k == 0)), int(255 * a ** 1.5), int(120 + 100 * a * (k == 0)))
                d.text((c * cw + 6, y), ch, font=f, fill=col)
    im = glow(im, lambda dd: [dd.text((c * cw + 6, 0), '', font=f) for c in range(1)], 1, 0)
    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); od = ImageDraw.Draw(ov); od.ellipse((660, 190, 1260, 890), fill=(0, 10, 8, 235)); ov = ov.filter(ImageFilter.GaussianBlur(40)); im = Image.alpha_composite(im.convert('RGBA'), ov).convert('RGB')
    gl = LOGO.resize((420, 420), Image.LANCZOS); im = glow(im, lambda dd: dd.ellipse((760, 270, 1160, 670), fill=(0, 255, 160)), 60, 0.35); im.paste(gl, (750, 300), gl); d = ImageDraw.Draw(im)
    d.rounded_rectangle((330, 755, 1590, 825), 35, fill=(0, 12, 8)); T(d, (WW // 2, 790), '248 bits. this is the photo\'s location, written in its own pixels.', FT(CON, 30), (120, 255, 190), 'mm')
    grain(im, 6).save(os.path.join(OUT, '04_the-bits.png'), optimize=True)


# ============================================================ E  film strip of abuse
def e_gauntlet():
    i = 35; rgb, marked, stored = prep(i); P = payload_for(i); gray = lambda im_: cv2.cvtColor(cv2.cvtColor(im_, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
    blur = cv2.GaussianBlur(W.resize_long(stored, 1600), (0, 0), 1.4)
    V = [('1600 px · q70', W.jpeg(W.resize_long(stored, 1600), 70)[0]), ('shared 3×', W.jpeg(W.resize_long(W.jpeg(W.resize_long(W.jpeg(W.resize_long(stored, 1600), 70)[0], 1280), 60)[0], 1080), 50)[0]),
         ('1080 px · q50', W.jpeg(W.resize_long(stored, 1080), 50)[0]), ('800 px · q40', W.jpeg(W.resize_long(stored, 800), 40)[0]), ('black & white', W.jpeg(W.resize_long(gray(stored), 1600), 70)[0]),
         ('blurred', W.jpeg(blur, 70)[0]), ('washed out', W.jpeg(np.clip(W.resize_long(stored, 1600).astype(np.float32) * 1.25 - 20, 0, 255).astype(np.uint8), 70)[0]), ('colour drained', None)]
    hsv = cv2.cvtColor(W.resize_long(stored, 1600), cv2.COLOR_RGB2HSV); hsv[..., 1] = (hsv[..., 1] * 0.4).astype(np.uint8); V[-1] = ('colour drained', W.jpeg(cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB), 70)[0])
    im = Image.new('RGB', (WW, HH), (7, 8, 11)); d = ImageDraw.Draw(im)
    m = Image.new('L', (WW, 400), 0); ImageDraw.Draw(m).text((WW // 2, 230), 'STILL KNOWS.', font=FT(IMP, 330), fill=255, anchor='mm')
    im.paste(cover(marked, WW, 400), (0, 40), m); d = ImageDraw.Draw(im)
    fw, fh, gap, y0 = 214, 300, 16, 500; x0 = (WW - (8 * fw + 7 * gap)) // 2
    d.rectangle((0, y0 - 70, WW, y0 + fh + 120), fill=(14, 15, 20))
    for k in range(0, WW, 40): d.rounded_rectangle((k + 8, y0 - 54, k + 26, y0 - 36), 4, fill=(7, 8, 11)); d.rounded_rectangle((k + 8, y0 + fh + 90, k + 26, y0 + fh + 108), 4, fill=(7, 8, 11))
    for k, (lab, img) in enumerate(V):
        r = W.read(img); ok = r['status'] == 'ok'; col = (60, 220, 110) if ok else (240, 170, 50)
        x = x0 + k * (fw + gap); im.paste(cover(img, fw, fh), (x, y0)); d.rectangle((x, y0, x + fw, y0 + fh), outline=(60, 62, 70), width=2)
        T(d, (x + fw // 2, y0 + fh + 28), lab, FT(CON, 22), (200, 205, 215), 'mm'); d.ellipse((x + fw // 2 - 9, y0 + fh + 50, x + fw // 2 + 9, y0 + fh + 68), fill=col)
        T(d, (x + fw // 2, y0 + fh + 92 - 6), 'full record' if ok else 'location', FT(SEG, 18), col, 'mm')
    T(d, (WW // 2, 985), 'same photo. same coordinates. eight ways to ruin it.', FT(GEOI, 44), (225, 230, 240), 'mm')
    grain(im, 5).save(os.path.join(OUT, '05_still-knows.png'), optimize=True)


# ============================================================ F  pixel macro
def f_macro():
    rgb, marked, _ = prep(0, 4000, real=False); D = (marked.astype(int) - rgb.astype(int)).sum(2); h, w = D.shape; rs = random.Random(11); best, pos = -1e9, (0, 0)
    for _ in range(5000):
        y, x = rs.randrange(h // 5, h - 40), rs.randrange(w // 5, w - 64); p = D[y:y + 34, x:x + 60]; sc = p.std() * 10 - abs(p.mean()) - (999 if rgb[y:y + 34, x:x + 60].max() > 245 else 0) - 3 * np.abs(np.diff(p, axis=1)).mean()
        if sc > best: best, pos = sc, (y, x)
    y0, x0 = pos; pm = marked[y0:y0 + 34, x0:x0 + 60]; pd_ = D[y0:y0 + 34, x0:x0 + 60]; cs = 32; im = Image.new('RGB', (WW, HH), (3, 3, 8)); d = ImageDraw.Draw(im, 'RGBA')
    for j in range(34):
        for i in range(60):
            c = tuple(int(v) for v in pm[j, i]); x, y = i * cs, j * cs; d.rectangle((x, y, x + cs - 2, y + cs - 2), fill=c + (255,)); v = int(pd_[j, i])
            if v: a = min(255, 60 + abs(v) * 28); col = (60, 235, 255) if v > 0 else (255, 60, 190); d.rectangle((x + 3, y + 3, x + cs - 5, y + cs - 5), outline=col + (a,), width=3)
    im = glow(im, lambda dd: None, 1, 0); ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for yy in range(HH - 230, HH): od.line((0, yy, WW, yy), fill=(0, 0, 8, int(235 * ((yy - (HH - 230)) / 230) ** 1.2)))
    im = Image.alpha_composite(im.convert('RGBA'), ov).convert('RGB'); d = ImageDraw.Draw(im)
    T(d, (70, HH - 190), 'this is what', FT(SEGL, 50), (210, 220, 235)); T(d, (70, HH - 140), '"invisible"', FT(GEOI, 92), (255, 255, 255)); T(d, (70 + int(FT(GEOI, 92).getlength('"invisible"')) + 24, HH - 112), 'looks like.', FT(SEGL, 50), (210, 220, 235))
    d.rectangle((1330, HH - 96, 1362, HH - 64), outline=(60, 235, 255), width=4); T(d, (1376, HH - 80), 'pushed up', FT(CON, 24), (60, 235, 255), 'lm'); d.rectangle((1530, HH - 96, 1562, HH - 64), outline=(255, 60, 190), width=4); T(d, (1576, HH - 80), 'pushed down', FT(CON, 24), (255, 60, 190), 'lm')
    T(d, (WW - 70, HH - 150), '×32 zoom', FT(CON, 24), (140, 150, 170), 'ra')
    im.save(os.path.join(OUT, '06_what-invisible-looks-like.png'), optimize=True)


# ============================================================ G  polaroid
def g_polaroid():
    i = 33; rgb, marked, stored = prep(i); r = W.read(bw_chat(stored)); l2 = r['l2']; assert l2
    rs = np.random.default_rng(4); tex = rs.normal(0, 1, (HH // 6, WW // 6)); tex = cv2.resize(cv2.GaussianBlur(tex.astype(np.float32), (0, 0), 1.5), (WW, HH)); bgm = 36 + 10 * tex
    wood = np.stack([bgm * 1.05 + 10, bgm * 0.78 + 6, bgm * 0.58 + 4], -1); streak = np.sin(np.arange(HH)[:, None] * 0.09 + cv2.resize(rs.normal(0, 1, (HH // 20, 1)).astype(np.float32), (1, HH)) * 2) * 6
    im = Image.fromarray(np.clip(wood + streak[..., None], 0, 255).astype(np.uint8)); im = vignette(im, 0.8)

    def polaroid(content, size=(560, 680), ang=0, back=False):
        W_, H_ = size; card = Image.new('RGBA', (W_, H_), (248, 245, 236, 255)); cd = ImageDraw.Draw(card)
        if not back: card.paste(cover(content, W_ - 56, H_ - 150).convert('RGBA'), (28, 28))
        return card, cd
    front, fd = polaroid(marked); T(fd, (280, 600), 'remember this place', FT(INK, 44), (60, 55, 70), 'mm')
    back, bd = polaroid(None, back=True, size=(560, 680)); lat, lon = l2['lat'], l2['lon']
    T(bd, (50, 70), 'where was this?', FT(INK, 54), (40, 55, 120)); T(bd, (50, 170), dms(lat, 'N', 'S'), FT(INK, 74), (30, 40, 110)); T(bd, (50, 262), dms(lon, 'E', 'W'), FT(INK, 74), (30, 40, 110))
    T(bd, (50, 380), 'the photo told me.', FT(INK, 48), (60, 55, 70)); T(bd, (50, 440), 'even after WhatsApp,', FT(INK, 40), (90, 85, 100)); T(bd, (50, 490), 'even in black & white.', FT(INK, 40), (90, 85, 100))
    gl = LOGO.resize((120, 120), Image.LANCZOS); back.paste(gl, (420, 520), gl)

    def place(card, cx, cy, ang):
        sh = Image.new('RGBA', (card.width + 120, card.height + 120), (0, 0, 0, 0)); sh.paste(Image.new('RGBA', card.size, (0, 0, 0, 170)), (70, 90)); sh = sh.filter(ImageFilter.GaussianBlur(26)).rotate(ang, expand=True, resample=Image.BICUBIC)
        c = card.rotate(ang, expand=True, resample=Image.BICUBIC); base = im.convert('RGBA'); base.alpha_composite(sh, (cx - sh.width // 2, cy - sh.height // 2)); base.alpha_composite(c, (cx - c.width // 2, cy - c.height // 2)); return base.convert('RGB')
    im = place(back, 560, 560, 7); im = place(front, 1280, 520, -6)
    d = ImageDraw.Draw(im); T(d, (WW // 2, HH - 56), 'g h o s t m a r k', FT(CAMB, 28), (210, 190, 160), 'mm')
    grain(im, 5).save(os.path.join(OUT, '07_polaroid.png'), optimize=True)


# ============================================================ H  ghost-shaped flashlight
def h_ghost_reveal():
    i = 10; rgb, marked, _ = prep(i, 2400, real=False); g = ghost_signed(rgb, marked, 1.0); art = cover(Image.fromarray(NEON(0.5 + g / 11)), WW, HH); ph = cover(marked, WW, HH)
    base = Image.blend(ph, Image.new('RGB', ph.size, (2, 3, 10)), 0.72).filter(ImageFilter.GaussianBlur(2))
    gm = Image.new('L', (WW, HH), 0); gs = ghost_mask(860, 960, 0); gm.paste(gs, ((WW - 860) // 2, 60)); im = base.copy(); im.paste(art, (0, 0), gm)
    edge = ImageChops.subtract(gm.filter(ImageFilter.MaxFilter(9)), gm); glw = Image.merge('RGB', [edge.point(lambda v: v * 0.5), edge.point(lambda v: v * 0.9), edge]).convert('RGB')
    im = Image.fromarray(np.clip(np.asarray(im).astype(int) + np.asarray(glw.filter(ImageFilter.GaussianBlur(14))).astype(int) * 2 + np.asarray(glw).astype(int), 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    T(d, (90, 150), 'it was', FT(SEGL, 70), (230, 235, 245)); T(d, (90, 232), 'always', FT(GEOI, 120), (255, 255, 255)); T(d, (90, 380), 'there.', FT(SEGL, 70), (230, 235, 245))
    T(d, (WW - 90, HH - 90), 'ghostmark', FT(CAMB, 40), (255, 190, 220), 'ra')
    grain(vignette(im, 0.45), 5).save(os.path.join(OUT, '08_ghost-reveal.png'), optimize=True)


# ============================================================ J  magazine cover
def j_cover():
    i = 38; rgb, marked, stored = prep(i); ph = cover(marked, WW, HH); im = ph.copy(); ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for y in range(0, 300): od.line((0, y, WW, y), fill=(0, 0, 0, int(190 * (1 - y / 300))))
    for x in range(0, 760): od.line((x, 300, x, HH), fill=(0, 0, 0, int(165 * (1 - x / 760) ** 1.2)))
    im = Image.alpha_composite(im.convert('RGBA'), ov).convert('RGB'); d = ImageDraw.Draw(im)
    f = FT(GEOB, 200); T(d, (WW // 2 + 160, 130), 'GHOSTMARK', f, (255, 255, 255), 'mm')
    T(d, (WW // 2 + 160, 252), 'THE INVISIBLE PHOTO ISSUE  ·  V1.1.0  ·  OCTOBER 2026', FT(SEG, 26), (240, 240, 245), 'mm')
    lines = [('WHATSAPP', 'CAN\'T DELETE THIS', (255, 255, 255)), ('480 ATTACKS', 'ZERO WRONG ANSWERS', (255, 220, 90)), ('BLACK & WHITE?', 'STILL HERE.', (255, 255, 255)), ('40 PHOTOS', '11 CAMERAS, 1 MARK', (255, 255, 255)), ('NOW IN PYTHON', 'pip install ghostmark-image', (120, 230, 255))]
    for k, (a, b, c) in enumerate(lines):
        y = 330 + k * 128; T(d, (70, y), a, FT(IMP, 58), c); T(d, (70, y + 62), b, FT(SEGB, 30), (235, 235, 240))
    # barcode from the real payload bits
    from ghostmark import _core as C
    sys.path.insert(0, os.path.join(ROOT, 'python')); bits = C.conv_encode(C.pack_l1(W.PAYLOAD))
    bx, by = WW - 420, HH - 200; d.rectangle((bx - 20, by - 20, bx + 340, by + 150), fill=(255, 255, 255))
    for k, b in enumerate(bits[:120]): d.rectangle((bx + k * 2.6, by, bx + k * 2.6 + (2 if b else 1), by + 105), fill=(0, 0, 0))
    T(d, (bx + 160, by + 128), 'the actual bits of the mark', FT(CON, 18), (30, 30, 30), 'mm')
    grain(vignette(im, 0.35), 4).save(os.path.join(OUT, '09_magazine-cover.png'), optimize=True)


# ============================================================ K  ghost-shaped photo cutouts
def k_ghosts():
    im = Image.new('RGB', (WW, HH), (8, 10, 24)); yy, xx = np.mgrid[0:HH, 0:WW]; bg = np.zeros((HH, WW, 3), np.float32)
    for cx, cy, c, s in [(300, 250, (120, 40, 200), 700), (1600, 800, (0, 140, 230), 800), (960, 540, (255, 60, 150), 500)]: bg += np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s * s)))[..., None] * np.array(c) * 0.42
    im = Image.fromarray(np.clip(bg + np.array([8, 10, 24]), 0, 255).astype(np.uint8)); picks = [0, 10, 14, 28, 33, 35, 24, 16, 38, 4]
    spots = [(40 + c * 350 + r * 175, 60 + r * 390, 300) for r in range(2) for c in range(5)]
    for k, (x, y, s) in enumerate(spots):
        h = int(s * 1.1); gm = ghost_mask(s, h, 0); ph = cover(photo(picks[k], 900), s, h); layer = Image.new('RGBA', (s, h), (0, 0, 0, 0)); layer.paste(ph.convert('RGBA'), (0, 0), gm)
        sh = Image.new('RGBA', (s + 160, h + 160), (0, 0, 0, 0)); sh.paste(Image.new('RGBA', (s, h), (0, 0, 0, 190)), (80, 110), gm); sh = sh.filter(ImageFilter.GaussianBlur(24))
        base = im.convert('RGBA'); base.alpha_composite(sh, (x - 80, y - 60)); edge = ImageChops.subtract(gm.filter(ImageFilter.MaxFilter(5)), gm); rim = Image.new('RGBA', (s, h), (190, 235, 255, 0)); rim.putalpha(edge); base.alpha_composite(layer, (x, y)); base.alpha_composite(rim, (x, y)); im = base.convert('RGB')
    d = ImageDraw.Draw(im); T(d, (WW // 2 - 20, HH - 130), 'every photo', FT(SEGL, 56), (235, 240, 250), 'rm'); T(d, (WW // 2 + 10, HH - 120), 'remembers.', FT(GEOI, 110), (255, 255, 255), 'lm')
    grain(im, 4).save(os.path.join(OUT, '10_ghosts.png'), optimize=True)


if __name__ == '__main__':
    fns = dict(a=a_coords, b=b_fingerprints, c=c_layers, d=d_bits, e=e_gauntlet, f=f_macro, g=g_polaroid, h=h_ghost_reveal, j=j_cover, k=k_ghosts)
    sel = sys.argv[1:] or list(fns)
    for k in sel: fns[k](); print('done', k, flush=True)
