"""Ten 1920x1080 social-media images, each in its own visual style, built from the real photos and real measured results.
Writes PR-KIT/social-images/*.png"""
import os, json, math, subprocess, sys, random, datetime
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import wmlib as W

ROOT = os.path.join(W.HERE, '..'); OUT = os.path.join(ROOT, 'PR-KIT', 'social-images'); os.makedirs(OUT, exist_ok=True)
FD = r'C:\Windows\Fonts'
def FT(name, size): return ImageFont.truetype(os.path.join(FD, name), size)
SEG, SEGB, SEGL, BLK, IMP, CON, CONB, GEO, GEOI, BAH = 'segoeui.ttf', 'segoeuib.ttf', 'segoeuil.ttf', 'ariblk.ttf', 'impact.ttf', 'consola.ttf', 'consolab.ttf', 'georgiab.ttf', 'georgiai.ttf', 'bahnschrift.ttf'
WW, HH = 1920, 1080
R = json.load(open(os.path.join(W.HERE, 'results', 'results.json')))['photos']
BWR = json.load(open(os.path.join(W.HERE, 'results', 'bw.json')))
files = W.photo_files()
CYAN, PURPLE, GREEN, ORANGE, RED, PINK, WHITE, MUTED = (56, 189, 248), (167, 139, 250), (63, 185, 80), (227, 160, 40), (248, 81, 73), (247, 120, 186), (240, 246, 252), (139, 148, 158)
LOGO = Image.open(os.path.join(ROOT, 'assets', 'logo.png')).convert('RGBA')
_cache = {}


def photo(i, long=2400):
    if (i, long) not in _cache: _cache[(i, long)] = W.resize_long(W.load(files[i]), long)
    return _cache[(i, long)]


def cover(a, w, h):
    im = a if isinstance(a, Image.Image) else Image.fromarray(a); s = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS); x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h)).convert('RGB')


def grad(w, h, c1, c2, vertical=True):
    t = np.linspace(0, 1, h if vertical else w)[:, None] if vertical else np.linspace(0, 1, w)[None, :]
    a = np.array(c1)[None, None, :] * (1 - t[..., None]) + np.array(c2)[None, None, :] * t[..., None]
    a = np.broadcast_to(a, (h, w, 3)) if vertical else np.broadcast_to(a, (h, w, 3))
    return Image.fromarray(a.astype(np.uint8))


def text(d, xy, s, font, fill, anchor='la', shadow=None):
    if shadow: d.text((xy[0] + 3, xy[1] + 4), s, font=font, fill=shadow, anchor=anchor)
    d.text(xy, s, font=font, fill=fill, anchor=anchor)


def glass(im, box, r=28, tint=(10, 14, 22), alpha=150, blur=22, outline=(255, 255, 255, 60)):
    x0, y0, x1, y1 = box; reg = im.crop(box).filter(ImageFilter.GaussianBlur(blur)).convert('RGBA')
    reg = Image.alpha_composite(reg, Image.new('RGBA', reg.size, tint + (alpha,)))
    m = Image.new('L', reg.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, x1 - x0, y1 - y0), r, fill=255)
    im.paste(reg.convert('RGB'), (x0, y0), m)
    if outline: ImageDraw.Draw(im, 'RGBA').rounded_rectangle(box, r, outline=outline, width=2)


def glow(im, draw_fn, radius=18, strength=1.0):
    layer = Image.new('RGB', im.size, (0, 0, 0)); draw_fn(ImageDraw.Draw(layer)); g = layer.filter(ImageFilter.GaussianBlur(radius))
    return Image.fromarray(np.clip(np.asarray(im).astype(np.int32) + (np.asarray(g) * strength).astype(np.int32), 0, 255).astype(np.uint8))


def gradient_text(im, xy, s, font, c1, c2, anchor='la'):
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).text(xy, s, font=font, fill=255, anchor=anchor)
    bb = m.getbbox()
    if not bb: return
    g = grad(bb[2] - bb[0], bb[3] - bb[1], c1, c2); im.paste(g, (bb[0], bb[1]), m.crop(bb))


def tick(d, cx, cy, r, col, w=8):
    d.line((cx - r, cy, cx - r * .3, cy + r * .75, cx + r, cy - r * .7), fill=col, width=w, joint='curve')


def cross(d, cx, cy, r, col, w=8):
    d.line((cx - r, cy - r, cx + r, cy + r), fill=col, width=w); d.line((cx - r, cy + r, cx + r, cy - r), fill=col, width=w)


def logo(im, x, y, size):
    l = LOGO.resize((size, size), Image.LANCZOS); im.paste(l, (x, y), l)


def footer(d, col=MUTED, y=HH - 54, center=True, s='github.com/thevijayparmar/Ghostmark-Image   ·   pip install ghostmark-image   ·   Apache-2.0'):
    text(d, (WW // 2, y), s, FT(SEG, 26), col, 'mm')


# ------------------------------------------------------------------ real data
def chat_copy(img, long=1600, q=70): return W.jpeg(W.resize_long(img, long), q)[0]
def read_of(img): return W.read(img)
def ts(t, tenth): return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%d  %H:%M:%S') + '.%d UTC' % tenth


def prep(i, long=2400):
    rgb = photo(i, long); marked, _ = W.embed(rgb); stored, _ = W.jpeg(marked, 95); return rgb, marked, stored


# ================================================================== 01  glass: WhatsApp deletes GPS
def img01():
    rgb, marked, stored = prep(35)
    r = read_of(chat_copy(stored)); l1 = r['l1']; assert l1, 'photo 36 must read'
    bg = cover(photo(35), WW, HH).filter(ImageFilter.GaussianBlur(10)); bg = Image.blend(bg, Image.new('RGB', bg.size, (4, 8, 16)), 0.62)
    im = bg.copy(); d = ImageDraw.Draw(im, 'RGBA')
    text(d, (WW // 2, 118), "WhatsApp deletes your photo's GPS.", FT(BLK, 84), WHITE, 'mm', shadow=(0, 0, 0, 150))
    text(d, (WW // 2, 206), 'Ghostmark puts it back.', FT(SEGL, 64), CYAN, 'mm')
    glass(im, (110, 300, 920, 900)); glass(im, (1000, 300, 1810, 900), outline=GREEN + (170,))
    d = ImageDraw.Draw(im, 'RGBA')
    text(d, (150, 340), 'FILE DETAILS (EXIF)', FT(SEGB, 34), (200, 205, 215)); text(d, (150, 386), 'what the shared copy contains', FT(SEG, 26), MUTED)
    for k, (lab, _) in enumerate([('GPS location', 0), ('Date & time', 0), ('Altitude', 0), ('Camera', 0)]):
        y = 470 + k * 105
        text(d, (150, y), lab, FT(SEG, 30), MUTED); text(d, (150, y + 38), 'removed', FT(SEGB, 40), (120, 125, 135))
        d.line((150, y + 62, 270, y + 62), fill=(120, 125, 135, 255), width=3); cross(d, 850, y + 40, 18, RED, 7)
    text(d, (1040, 340), 'HIDDEN IN THE PIXELS', FT(SEGB, 34), GREEN); text(d, (1040, 386), 'read back from the same shared copy', FT(SEG, 26), MUTED)
    rows = [('Location', '%.5f° N   %.5f° E' % (l1['lat'], l1['lon'])), ('Date & time', ts(l1['t'], l1['tenth'])), ('Altitude', '%d m' % l1['alt']), ('Integrity', 'CRC check passed')]
    for k, (lab, val) in enumerate(rows):
        y = 470 + k * 105; text(d, (1040, y), lab, FT(SEG, 30), MUTED); text(d, (1040, y + 38), val, FT(SEGB, 40 if k != 1 else 36), WHITE); tick(d, 1770, y + 40, 18, GREEN, 7)
    text(d, (960, 600), 'VS', FT(IMP, 56), (255, 255, 255, 110), 'mm')
    text(d, (WW // 2, 970), 'Demo record. Photo: 1600 px, JPEG q70, as a chat app sends it.', FT(SEG, 24), (170, 180, 195), 'mm'); footer(d)
    im.save(os.path.join(OUT, '01_whatsapp-deletes-gps.png'), optimize=True)


# ================================================================== 02  neon scan reveal
def ghost(rgb, marked, gain=44):
    dlt = (marked.astype(np.float32) - rgb.astype(np.float32)).sum(2); dlt = cv2.GaussianBlur(dlt, (0, 0), 1.2)
    import matplotlib
    return (matplotlib.colormaps['RdBu_r'](np.clip(0.5 + dlt * gain / 765.0, 0, 1))[..., :3] * 255).astype(np.uint8)


def img02():
    rgb, marked, _ = prep(10); a = cover(marked, WW, HH); g = cover(ghost(rgb, marked), WW, HH)
    sx = 1130; im = a.copy(); im.paste(g.crop((sx, 0, WW, HH)), (sx, 0))
    # darken the left for text
    ov = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for x in range(0, 1130): od.line((x, 0, x, HH), fill=(2, 6, 14, int(235 * (1 - x / 1130) ** 0.9)))
    od.rectangle((0, HH - 250, sx, HH), fill=(2, 6, 14, 150)); im = Image.alpha_composite(im.convert('RGBA'), ov).convert('RGB')
    im = glow(im, lambda dd: dd.line((sx, 0, sx, HH), fill=(40, 190, 255), width=10), 22, 1.4); d = ImageDraw.Draw(im); d.line((sx, 0, sx, HH), fill=(210, 245, 255), width=4)
    text(d, (90, 150), 'YOUR PHOTO', FT(BLK, 118), WHITE, shadow=(0, 0, 0, 160)); text(d, (90, 280), 'HAS A SECRET.', FT(BLK, 118), CYAN, shadow=(0, 0, 0, 160))
    text(d, (96, 440), 'Same photo, two views.', FT(SEGL, 52), WHITE)
    text(d, (96, 520), 'Left: what you see.', FT(SEG, 36), (225, 235, 245)); text(d, (96, 576), 'Right: the invisible layer that carries', FT(SEG, 36), (225, 235, 245)); text(d, (96, 622), 'location, altitude and time (magnified 44x).', FT(SEG, 36), (225, 235, 245))
    logo(im, 90, HH - 215, 130); text(d, (250, HH - 190), 'Ghostmark', FT(BLK, 62), WHITE); text(d, (254, HH - 108), 'photos that remember where and when', FT(SEG, 28), CYAN)
    im.save(os.path.join(OUT, '02_your-photo-has-a-secret.png'), optimize=True)


# ================================================================== 03  film-noir B&W split
def img03():
    rgb, marked, stored = prep(0)
    bw = cv2.cvtColor(cv2.cvtColor(stored, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB); r = read_of(W.jpeg(W.resize_long(bw, 1600), 70)[0]); l2 = r['l2']; assert l2, 'photo 1 B&W must read'
    col = cover(stored, WW, HH); gray = cover(bw, WW, HH).convert('L').convert('RGB')
    gray = Image.fromarray(np.clip((np.asarray(gray).astype(np.float32) - 128) * 1.12 + 128, 0, 255).astype(np.uint8))
    mask = Image.new('L', (WW, HH), 0); ImageDraw.Draw(mask).polygon([(1010, 0), (WW, 0), (WW, HH), (900, HH)], fill=255)
    im = col.copy(); im.paste(gray, (0, 0), mask); d = ImageDraw.Draw(im, 'RGBA')
    for y in range(0, 330): d.line((0, y, WW, y), fill=(0, 0, 0, int(210 * (1 - y / 330) ** 1.4)))
    for y in range(HH - 380, HH): d.line((0, y, WW, y), fill=(0, 0, 0, int(225 * ((y - (HH - 380)) / 380) ** 1.2)))
    d.line((1010, 0, 900, HH), fill=(255, 255, 255, 235), width=5)
    text(d, (WW // 2, 100), 'Turn it black & white.', FT(BLK, 96), WHITE, 'mm', shadow=(0, 0, 0, 170)); text(d, (WW // 2, 196), 'It still knows where it was taken.', FT(GEOI, 62), (255, 255, 255), 'mm')
    text(d, (110, 800), 'COLOUR', FT(SEGB, 30), (255, 190, 90)); text(d, (110, 842), 'full record', FT(SEG, 40), WHITE); text(d, (110, 892), 'lat · lon · altitude · time', FT(SEG, 28), (210, 210, 210))
    text(d, (1230, 800), 'BLACK & WHITE + CHAT APP', FT(SEGB, 30), (200, 200, 200)); text(d, (1230, 842), '%.4f° N   %.4f° E' % (l2['lat'], l2['lon']), FT(SEGB, 50), WHITE)
    text(d, (1230, 910), 'location recovered, about 10 m', FT(SEG, 28), (200, 200, 200)); tick(d, 1858, 870, 24, (120, 235, 140), 9)
    footer(d, (200, 200, 200)); im.save(os.path.join(OUT, '03_black-and-white-still-knows.png'), optimize=True)


# ================================================================== 04  typographic numbers
def img04():
    N = len(R); tot = N * 12; full = sum(a['ok1'] for p in R for a in p['attacks'] if 'CONTROL' not in a['name'])
    ctl = len(json.load(open(os.path.join(W.HERE, 'results', 'controls.json')))['controls'])
    bgm = np.zeros((HH, WW, 3), np.float32); yy, xx = np.mgrid[0:HH, 0:WW]
    for cx, cy, c, s in [(300, 200, (90, 40, 200), 900), (1700, 900, (0, 140, 220), 1000)]:
        bgm += np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s ** 2)))[..., None] * np.array(c) * 0.55
    im = Image.fromarray(np.clip(bgm + 8, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im, 'RGBA')
    text(d, (110, 92), 'THE RECEIPTS', FT(SEGB, 34), CYAN); text(d, (110, 140), 'we attacked it %d times. here is what happened.' % tot, FT(SEGL, 44), (210, 220, 235))
    cells = [(str(tot), 'edited copies tested', 'chat apps · resizes · filters · crops · screenshots', (56, 189, 248), (167, 139, 250)), ('0', 'wrong values', 'it says "damaged" before it ever guesses', (63, 185, 80), (150, 240, 160)),
             ('0', 'false alarms', 'on %d photos that were never marked' % ctl, (63, 185, 80), (150, 240, 160)), (str(N), 'photos · 11 cameras', 'iPhones, OnePlus, vivo, realme, DJI drones', (247, 120, 186), (255, 190, 90))]
    for k, (big, lab, sub, c1, c2) in enumerate(cells):
        x, y = 110 + (k % 2) * 900, 235 + (k // 2) * 390
        gradient_text(im, (x, y), big, FT(BAH, 200), c1, c2); d = ImageDraw.Draw(im, 'RGBA')
        text(d, (x + 4, y + 218), lab, FT(SEGB, 54), WHITE); text(d, (x + 4, y + 284), sub, FT(SEG, 30), (170, 185, 205))
    text(d, (WW // 2, HH - 38), 'Every number is in the README, including the failures.', FT(SEG, 30), (170, 180, 195), 'mm')
    im.save(os.path.join(OUT, '04_the-receipts.png'), optimize=True)


# ================================================================== 05  mosaic of all 40
def img05():
    cols, rows = 8, 5; tw, th = WW // cols, HH // rows + 1; im = Image.new('RGB', (WW, HH), (8, 10, 14))
    for k in range(40):
        t = cover(photo(k, 500), tw, th); im.paste(t, ((k % cols) * tw, (k // cols) * th))
    im = Image.blend(im, Image.new('RGB', im.size, (3, 6, 12)), 0.50); d = ImageDraw.Draw(im, 'RGBA')
    glass(im, (330, 270, 1590, 810), 44, tint=(6, 10, 18), alpha=190, blur=30, outline=CYAN + (150,)); d = ImageDraw.Draw(im, 'RGBA')
    logo(im, 390, 330, 230)
    text(d, (660, 340), '40 photos.', FT(BLK, 110), WHITE); text(d, (660, 462), '11 cameras.', FT(BLK, 110), WHITE); text(d, (660, 584), 'One invisible mark.', FT(BLK, 80), CYAN)
    text(d, (664, 700), 'iPhone · OnePlus · vivo · realme · LAVA · DJI drones', FT(SEG, 34), (200, 212, 228)); text(d, (664, 748), 'every photo marked, attacked 12 ways, and read back', FT(SEG, 30), MUTED)
    im.save(os.path.join(OUT, '05_forty-photos-eleven-cameras.png'), optimize=True)


# ================================================================== 06  code + terminal (gradient)
def img06():
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, 'python'))
    src = os.path.join(os.environ.get('TEMP', '.'), 'p06.jpg'); Image.fromarray(photo(10, 2400)).save(src, quality=92)
    out = subprocess.run([sys.executable, os.path.join(ROOT, 'python', 'examples', 'mark_and_read.py'), src], capture_output=True, text=True, env=env, cwd=os.path.join(ROOT, 'python')).stdout.strip().split('\n')
    im = grad(WW, HH, (30, 16, 90), (190, 40, 120), True); d = ImageDraw.Draw(im, 'RGBA')
    d.ellipse((1250, -300, 2250, 700), fill=(255, 140, 80, 40)); d.ellipse((-300, 600, 700, 1500), fill=(80, 120, 255, 45))
    text(d, (WW // 2, 105), 'Invisible GPS for any photo.', FT(BLK, 86), WHITE, 'mm', shadow=(0, 0, 0, 120)); text(d, (WW // 2, 190), 'five lines of Python.', FT(SEGL, 60), (255, 220, 160), 'mm')
    d.rounded_rectangle((680, 255, 1240, 335), 40, fill=(255, 255, 255, 235)); text(d, (960, 296), 'pip install ghostmark-image', FT(CONB, 36), (30, 20, 70), 'mm')

    def win(x, y, w, h, title):
        d.rounded_rectangle((x, y, x + w, y + h), 24, fill=(13, 17, 28, 245), outline=(255, 255, 255, 50), width=2); d.rounded_rectangle((x, y, x + w, y + 54), 24, fill=(30, 36, 52, 255)); d.rectangle((x, y + 30, x + w, y + 54), fill=(30, 36, 52, 255))
        for k, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]): d.ellipse((x + 22 + k * 32, y + 18, x + 40 + k * 32, y + 36), fill=c)
        text(d, (x + w // 2, y + 28), title, FT(SEG, 24), MUTED, 'mm')
    win(90, 400, 860, 560, 'tag.py'); win(990, 400, 840, 560, 'terminal')
    code = [[('import', PINK), (' ghostmark ', WHITE), ('as', PINK), (' gm', WHITE)], [], [('rec ', WHITE), ('= gm.', WHITE), ('Record', CYAN), ('(lat=12.9716, lon=77.5946,', WHITE)], [('                t=1792929600)', WHITE)],
            [('marked, _ ', WHITE), ('= gm.', WHITE), ('mark_verified', CYAN), ('(rgb, rec)', WHITE)], [], [('r ', WHITE), ('= gm.', WHITE), ('read', CYAN), ('(whatsapp_copy)', WHITE)], [('print', CYAN), ('(r.status, r.location)', WHITE)]]
    for k, segs in enumerate(code):
        x = 130
        for s, c in segs: d.text((x, 482 + k * 56), s, font=FT(CON, 33), fill=c); x += int(FT(CON, 33).getlength(s))
    text(d, (1030, 478), '$ python tag.py', FT(CONB, 31), WHITE)
    for k, ln in enumerate(out):
        c = GREEN if ': ok' in ln else ORANGE if ': part' in ln else MUTED if ': none' in ln else WHITE
        import re
        ln2 = re.sub(r'(\d+\.\d{4})\d+', r'\1', ln.replace('(time and altitude are gone, the location is not)', '')).replace('+00:00', '').strip().split(' 2026')[0]
        d.text((1030, 540 + k * 70), ln2, font=FT(CON, 27), fill=c)
    text(d, (1030, 868), '# after a chat app, after B&W,', FT(CON, 26), MUTED); text(d, (1030, 916), '# and on a photo never marked: none', FT(CON, 26), MUTED)
    footer(d, (255, 230, 240)); im.save(os.path.join(OUT, '06_five-lines-of-python.png'), optimize=True)


# ================================================================== 07  blueprint pixels
def img07():
    rgb, marked, _ = prep(0, 4000)
    Rr, Rm = rgb[..., 0].astype(int), marked[..., 0].astype(int); D = Rm - Rr; h, w = D.shape; best, pos = -1, (0, 0); rs = random.Random(3)
    for _ in range(6000):
        y, x = rs.randrange(h // 4, h - 12), rs.randrange(w // 4, w - 12); sc = D[y:y + 5, x:x + 8].std() * 10 - abs(D[y:y + 5, x:x + 8].mean()) - (1000 if (Rr[y:y + 5, x:x + 8].max() > 235 or Rr[y:y + 5, x:x + 8].min() < 25) else 0)
        if sc > best: best, pos = sc, (y, x)
    y0, x0 = pos; o, m, dd = Rr[y0:y0 + 5, x0:x0 + 8], Rm[y0:y0 + 5, x0:x0 + 8], D[y0:y0 + 5, x0:x0 + 8]
    im = Image.new('RGB', (WW, HH), (8, 36, 84)); d = ImageDraw.Draw(im, 'RGBA')
    for x in range(0, WW, 48): d.line((x, 0, x, HH), fill=(255, 255, 255, 14), width=1)
    for y in range(0, HH, 48): d.line((0, y, WW, y), fill=(255, 255, 255, 14), width=1)
    text(d, (110, 100), 'THE WHOLE TRICK', FT(SEGB, 34), (140, 200, 255)); text(d, (110, 150), 'Nudge pixels by a few shades.', FT(BLK, 78), WHITE)
    text(d, (112, 252), 'Typical change %.1f shades of 255, never more than %d. Nobody sees it. The reader counts it.' % (float(np.median([q['mean_change'] for q in R])), max(q['max_change'] for q in R)), FT(SEGL, 40), (170, 210, 255))
    cs = 66; gw, gh = 8 * cs, 5 * cs

    def grid(x, y, vals, title, sub, mode):
        text(d, (x, y - 92), title, FT(SEGB, 40), WHITE); text(d, (x, y - 44), sub, FT(SEG, 26), (140, 190, 240))
        for j in range(5):
            for i in range(8):
                v = int(vals[j, i]); cx, cy = x + i * cs, y + j * cs
                if mode == 'img': g = v; fill = (g, g // 2 + 10, 40 + g // 6) if False else (v, v, v)
                else: fill = (30, 40, 70) if v == 0 else ((235, 90, 90) if v > 0 else (90, 150, 255))
                d.rectangle((cx, cy, cx + cs - 3, cy + cs - 3), fill=fill + (255,))
                tcol = (0, 0, 0) if mode == 'img' and v > 130 else (255, 255, 255)
                text(d, (cx + cs // 2, cy + cs // 2), ('%+d' % v if v else '0') if mode == 'diff' else str(v), FT(CONB if mode != 'img' else CON, 26 if mode == 'diff' else 25), tcol, 'mm')
    gx = [88, 696, 1304]; gy = 500
    grid(gx[0], gy, o, 'Your photo', 'red channel, 8x5 pixels, 0-255', 'img'); grid(gx[1], gy, m, 'With Ghostmark', 'same pixels, marked', 'img'); grid(gx[2], gy, dd, 'The difference', 'this is the mark', 'diff')
    text(d, (gx[0] + gw + 40, gy + gh // 2), '+', FT(IMP, 80), (140, 200, 255), 'mm'); text(d, (gx[1] + gw + 40, gy + gh // 2), '=', FT(IMP, 80), (140, 200, 255), 'mm')
    text(d, (88, gy + gh + 56), 'Real values from photo #1. Spread over ~10,000 tiles with error correction,', FT(SEG, 32), (200, 225, 255)); text(d, (88, gy + gh + 100), 'the sign of each nudge is one bit of the record.', FT(SEG, 32), (200, 225, 255))
    logo(im, WW - 220, 70, 120); footer(d, (140, 190, 240))
    im.save(os.path.join(OUT, '07_nudge-pixels-by-a-few-shades.png'), optimize=True)


# ================================================================== 08  light paper pipeline
def img08():
    rgb, marked, stored = prep(0, 2000); wa = chat_copy(stored); bw = W.jpeg(W.resize_long(cv2.cvtColor(cv2.cvtColor(stored, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB), 1600), 70)[0]
    r = read_of(bw); l2 = r['l2']
    BG, INK, ACC = (244, 241, 234), (28, 30, 38), (20, 120, 200)
    im = Image.new('RGB', (WW, HH), BG); d = ImageDraw.Draw(im, 'RGBA')
    text(d, (110, 92), 'FOLLOW ONE PHOTO', FT(SEGB, 30), ACC); text(d, (110, 140), 'Camera, WhatsApp, black & white. The location is still there.', FT(GEO, 52), INK)
    cw, ch, gap, x0, y0 = 400, 600, 40, 110, 290
    cards = [('1', 'Mark it', 'at capture, invisibly', stored, None), ('2', 'WhatsApp strips it', 'EXIF gone, resized', wa, 'EXIF  —  empty'), ('3', 'Someone filters it', 'black & white, sent again', bw, 'colour layer  —  gone'), ('4', 'Ghostmark reads it', 'brightness layer survives', None, None)]
    for k, (n, ttl, sub, img, tag) in enumerate(cards):
        x = x0 + k * (cw + gap + 20)
        d.rounded_rectangle((x + 6, y0 + 8, x + cw + 6, y0 + ch + 8), 30, fill=(0, 0, 0, 28)); d.rounded_rectangle((x, y0, x + cw, y0 + ch), 30, fill=(255, 255, 255, 255), outline=(220, 214, 200), width=2)
        d.ellipse((x + 24, y0 + 22, x + 84, y0 + 82), fill=ACC); text(d, (x + 54, y0 + 52), n, FT(BLK, 36), WHITE, 'mm'); text(d, (x + 104, y0 + 34), ttl, FT(SEGB, 31), INK); text(d, (x + 104, y0 + 76), sub, FT(SEG, 22), (100, 104, 116))
        if img is not None:
            t = cover(img, cw - 48, 330); im.paste(t, (x + 24, y0 + 130)); d = ImageDraw.Draw(im, 'RGBA')
            if tag: d.rounded_rectangle((x + 24, y0 + 482, x + cw - 24, y0 + 540), 14, fill=(255, 235, 230)); text(d, (x + cw // 2, y0 + 511), tag, FT(CONB, 25), (190, 50, 40), 'mm')
            else: d.rounded_rectangle((x + 24, y0 + 482, x + cw - 24, y0 + 540), 14, fill=(225, 245, 230)); text(d, (x + cw // 2, y0 + 511), 'looks identical to you', FT(SEGB, 25), (30, 130, 60), 'mm')
        else:
            d.rounded_rectangle((x + 24, y0 + 130, x + cw - 24, y0 + 540), 20, fill=(16, 22, 34)); text(d, (x + 48, y0 + 160), 'LOCATION ONLY', FT(CONB, 28), ORANGE)
            text(d, (x + 48, y0 + 220), 'LAT', FT(CON, 24), (140, 150, 170)); text(d, (x + 48, y0 + 250), '%.4f° N' % l2['lat'], FT(CONB, 46), WHITE); text(d, (x + 48, y0 + 330), 'LON', FT(CON, 24), (140, 150, 170)); text(d, (x + 48, y0 + 360), '%.4f° E' % l2['lon'], FT(CONB, 46), WHITE)
            text(d, (x + 48, y0 + 450), 'about 10 m · CRC ok', FT(SEG, 26), (140, 230, 160))
        if k < 3: d.polygon([(x + cw + 6, y0 + 300), (x + cw + 6 + 34, y0 + 320), (x + cw + 6, y0 + 340)], fill=ACC)
    text(d, (110, 990), 'Open source · Android, Python, JavaScript · github.com/thevijayparmar/Ghostmark-Image', FT(SEG, 28), (100, 104, 116)); logo(im, WW - 210, 40, 110)
    im.save(os.path.join(OUT, '08_one-photo-four-steps.png'), optimize=True)


# ================================================================== 09  honest heatmap art
def img09():
    im = Image.new('RGB', (WW, HH), (11, 13, 18)); d = ImageDraw.Draw(im, 'RGBA')
    text(d, (110, 92), 'Most projects hide the red cells.', FT(BLK, 84), WHITE); text(d, (110, 196), 'We put them on page one.', FT(BLK, 84), RED)
    cs, g = 38, 5; gx0, gy0 = (WW - (40 * (cs + g) - g)) // 2, 330
    cnt = dict(full=0, part=0, dmg=0)
    for j in range(12):
        for i, p in enumerate(R):
            a = [x for x in p['attacks'] if 'CONTROL' not in x['name']][j]
            c, key = (GREEN, 'full') if a['ok1'] else ((ORANGE, 'part') if a['status'] == 'part' else (RED, 'dmg')); cnt[key] += 1
            x, y = gx0 + i * (cs + g), gy0 + j * (cs + g); d.rounded_rectangle((x, y, x + cs, y + cs), 8, fill=c + (235,))
    text(d, (gx0, gy0 + 12 * (cs + g) + 22), '40 photos across,  12 attacks down.  Each square is one edited copy.', FT(SEG, 30), MUTED)
    for k, (n, lab, c) in enumerate([(cnt['full'], 'full record read', GREEN), (cnt['part'], 'location only', ORANGE), (cnt['dmg'], 'unreadable', RED)]):
        x = 280 + k * 560; d.rounded_rectangle((x, 930, x + 44, 974), 10, fill=c); text(d, (x + 64, 928), str(n), FT(BAH, 54), WHITE); text(d, (x + 64 + int(FT(BAH, 54).getlength(str(n))) + 16, 940), lab, FT(SEG, 32), MUTED)
    text(d, (WW // 2, HH - 28), 'the weak spots are fog, night and flat sky. see the leaderboard.', FT(SEG, 26), (140, 148, 158), 'mm')
    im.save(os.path.join(OUT, '09_we-show-the-red-cells.png'), optimize=True)


# ================================================================== 10  synthwave three engines
def img10():
    im = grad(WW, HH, (22, 8, 56), (255, 90, 120), True); d = ImageDraw.Draw(im, 'RGBA'); hz = 640
    d.rectangle((0, hz, WW, HH), fill=(20, 6, 44))
    sun = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); sd = ImageDraw.Draw(sun); sd.ellipse((700, 450, 1220, 970), fill=(255, 200, 80, 255))
    sg = grad(WW, HH, (255, 230, 90), (255, 60, 140), True).convert('RGBA'); sg.putalpha(sun.split()[3]); im.paste(sg, (0, 0), sg); d = ImageDraw.Draw(im, 'RGBA')
    for k in range(1, 8): d.rectangle((600, hz - 190 + k * 24, 1320, hz - 190 + k * 24 + k * 2), fill=(22, 8, 56, 255))
    d.rectangle((0, hz, WW, HH), fill=(20, 6, 44, 255))
    for k in range(-14, 15): d.line((WW // 2 + k * 40, hz, WW // 2 + k * 330, HH), fill=(255, 80, 200, 150), width=2)
    for k in range(1, 12): y = hz + (k / 12) ** 2.2 * (HH - hz); d.line((0, y, WW, y), fill=(255, 80, 200, 150), width=2)
    im = glow(im, lambda dd: (dd.text((WW // 2, 120), 'ONE MARK.', font=FT(IMP, 150), fill=(255, 80, 200), anchor='mm'), dd.text((WW // 2, 270), 'THREE ENGINES.', font=FT(IMP, 150), fill=(60, 220, 255), anchor='mm')), 20, 1.0); d = ImageDraw.Draw(im, 'RGBA')
    text(d, (WW // 2, 120), 'ONE MARK.', FT(IMP, 150), (255, 235, 250), 'mm'); text(d, (WW // 2, 270), 'THREE ENGINES.', FT(IMP, 150), (215, 250, 255), 'mm')
    text(d, (WW // 2, 392), "They read each other's marks.", FT(SEGL, 54), (255, 240, 246), 'mm')
    for k, (ttl, sub, c) in enumerate([('ANDROID', 'Kotlin · 97 KB · 0 deps', GREEN), ('PYTHON', 'pip install ghostmark-image', CYAN), ('JAVASCRIPT', 'the reference engine', ORANGE)]):
        x = 150 + k * 570; glass(im, (x, 760, x + 500, 930), 26, tint=(14, 4, 34), alpha=215, blur=10, outline=c + (220,)); d = ImageDraw.Draw(im, 'RGBA')
        text(d, (x + 250, 812), ttl, FT(IMP, 54), c, 'mm'); text(d, (x + 250, 880), sub, FT(SEG, 28), (235, 225, 245), 'mm')
    logo(im, WW - 190, 40, 120); footer(d, (255, 220, 235), HH - 50)
    im.save(os.path.join(OUT, '10_one-mark-three-engines.png'), optimize=True)


if __name__ == '__main__':
    fns = [img01, img02, img03, img04, img05, img06, img07, img08, img09, img10]
    only = [int(a) for a in sys.argv[1:]]
    for k, f in enumerate(fns, 1):
        if only and k not in only: continue
        f(); print('done', k, flush=True)
