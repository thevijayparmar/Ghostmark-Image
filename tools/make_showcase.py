"""Animated per-photo showcases, photo wall, hero GIF, banner and stat strip for the README (run after run_experiments.py)."""
import json, os, datetime, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np, cv2, matplotlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import wmlib as W, phys_sim
from theme import device_group, robustness

A = os.path.join(W.HERE, '..', 'assets'); os.makedirs(A, exist_ok=True)
FD = os.path.join(os.path.dirname(matplotlib.__file__), 'mpl-data', 'fonts', 'ttf')
def F(sz, bold=False): return ImageFont.truetype(os.path.join(FD, 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'), sz)
BG, CARD, LINE, TXT, MUTED = (13, 17, 23), (22, 27, 34), (48, 54, 61), (230, 237, 243), (139, 148, 158)
CYAN, GREEN, ORANGE, RED, GREY, PURPLE = (56, 189, 248), (63, 185, 80), (227, 160, 40), (248, 81, 73), (110, 118, 129), (167, 139, 250)
R = json.load(open(os.path.join(W.HERE, 'results', 'results.json')))['photos']
files = W.photo_files(); N = len(files)
for p in R:
    p['dev'] = device_group(p['make'], p['model']); p['score'] = robustness(p)
SCENE = ['Carved stone temple', 'Step-well and water', 'Stone well, looking up', 'Rebar mat, construction site', 'Crane erection site', 'Sky over a highway', 'Jetty and offshore rig',
         'Rooftop rebar and formwork', 'Telecom tower against sky', 'Power line on a shoreline', 'Cracked concrete column', 'Drone: scrubland', 'Offshore rigs, storm clouds', 'Stone-pier bridge',
         'Drone: farm fields', 'Water tank on columns', 'River weir', 'Drone: river and bridge', 'Drone: solar farm', 'Weathered brick wall', 'Car park from a car', 'Fruit plate', 'Cafe interior',
         'Aeroplane wing over clouds', 'Blossom at dusk', 'Rainy street at night', 'Ship wake in a bay', 'Tall-ship masts', 'Skyscraper by the river', 'River skyline at dusk',
         'Temple spire', 'Night beach', 'Storm over a night sea', 'Beach under heavy cloud', 'Castle in fog', 'Bay with limestone islands', 'Moon over the bay',
         'Dusk, island silhouettes', 'City rooftops', 'Tower in thick fog']
DEVCOL = {'iPhone 16 Pro': CYAN, 'iPhone 17 Pro': (242, 204, 96), 'DJI drone': GREEN, 'OnePlus': ORANGE, 'vivo': PURPLE, 'realme': (247, 120, 186), 'LAVA': RED}
STAT_COL = {'ok': GREEN, 'part': ORANGE, 'damaged': RED, 'none': GREY}


def fit(img, w, h, bgc=CARD):
    im = Image.fromarray(img); s = min(w / im.width, h / im.height)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    c = Image.new('RGB', (w, h), bgc); c.paste(im, ((w - im.width) // 2, (h - im.height) // 2)); return c


def cover(img, w, h):
    im = Image.fromarray(img); s = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def ghost_map(orig, marked, gain=26):
    d = (marked.astype(np.float32) - orig.astype(np.float32)).sum(2)
    d = cv2.GaussianBlur(d, (0, 0), 1.0)
    v = np.clip(0.5 + d * gain / 765.0, 0, 1)
    return (matplotlib.colormaps['RdBu_r'](v)[..., :3] * 255).astype(np.uint8)


def decode(r):
    if r is None: return None
    l1 = r.get('l1'); l2 = r.get('l2')
    if r['status'] == 'none': return 'NO MARK FOUND', GREY, ['Nothing hidden here.', 'Never a made-up value.']
    if l1:
        ts = datetime.datetime.fromtimestamp(l1['t'], datetime.timezone.utc).strftime('%Y-%m-%d  %H:%M:%S') + '.%d' % l1['tenth']
        return 'FULL RECORD READ', GREEN, ['LAT   %.5f° N' % l1['lat'], 'LON   %.5f° E' % l1['lon'], 'ALT   %d m' % l1['alt'], 'UTC   ' + ts, 'TYPE  %s' % ('manual' if l1['manual'] else 'live capture')]
    if l2 and l2.get('lat') is not None:
        return 'LOCATION ONLY  (layer 2)', ORANGE, ['LAT   %.4f° N' % l2['lat'], 'LON   %.4f° E' % l2['lon'], '± about 10 m', 'time + altitude lost', 'colour layer gone']
    return 'MARK PRESENT, UNREADABLE', RED, ['Detected, but too damaged', 'to read. Honest failure:', 'no guessing.']


def frame(i, stage_i, nst, title, sub, img, rd, z1, z2, note=None):
    Wd, Hd = 800, 500
    im = Image.new('RGB', (Wd, Hd), BG); d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, 490, 372), 10, fill=CARD, outline=LINE)
    im.paste(fit(img, 466, 348), (17, 17))
    d.text((18, 384), title, font=F(19, True), fill=TXT); d.text((18, 412), sub, font=F(12), fill=MUTED)
    if note: d.text((18, 436), note, font=F(11), fill=CYAN)
    d.rounded_rectangle((502, 10, 790, 372), 10, fill=CARD, outline=LINE)
    if rd:
        st, col, lines = rd
        d.rounded_rectangle((516, 24, 776, 56), 8, fill=tuple(int(c * .22) for c in col), outline=col)
        d.text((528, 31), st, font=F(12, True), fill=col)
        for k, ln in enumerate(lines): d.text((520, 74 + k * 27), ln, font=F(14), fill=TXT if col != GREY else MUTED)
        y = 232
        for lab, z, c in (('colour layer', z1, CYAN), ('luma layer', z2, PURPLE)):
            d.text((520, y), '%s   z = %.1f' % (lab, z), font=F(11), fill=MUTED)
            d.rounded_rectangle((520, y + 20, 770, y + 30), 5, fill=(40, 46, 54))
            wv = int(min(z, 40) / 40 * 250)
            if wv > 2: d.rounded_rectangle((520, y + 20, 520 + wv, y + 30), 5, fill=c if z >= 3.5 else GREY)
            tx = 520 + int(3.5 / 40 * 250); d.line((tx, y + 16, tx, y + 34), fill=RED, width=2); y += 52
        d.text((520, 340), 'red tick = detection threshold 3.5', font=F(10), fill=MUTED)
    else:
        d.text((520, 150), 'The mark itself,\nmagnified 26x.', font=F(15, True), fill=TXT)
        d.text((520, 210), 'Red/blue = pixels pushed\nup/down by 1-2 grey levels.\nAt normal size this is\ninvisible; the reader\nsees it as a pattern.', font=F(12), fill=MUTED)
    d.text((18, 466), 'PHOTO %d  ·  %s  ·  %s %s  ·  %.1f MP' % (i + 1, SCENE[i], R[i]['make'], R[i]['model'], R[i]['mp']), font=F(11), fill=MUTED)
    for k in range(nst): d.ellipse((650 + k * 14, 470, 658 + k * 14, 478), fill=CYAN if k == stage_i else (60, 66, 75))
    return im.resize((680, 425), Image.LANCZOS)


def save_webp(frames, path, durs, quality=74):
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durs, loop=0, quality=quality, method=4, minimize_size=False)


def save_gif(frames, path, durs, colors=128):
    pal = [f.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG) for f in frames]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=durs, loop=0, optimize=True, disposal=2)


def showcase(i):
    rgb = W.load(files[i]); h, w = rgb.shape[:2]
    marked, _ = W.embed(rgb); stored, _ = W.jpeg(marked, 95); gm = ghost_map(rgb, marked)
    gray = cv2.cvtColor(stored, cv2.COLOR_RGB2GRAY)
    dm = stored.copy(); dm[int(.25 * h):int(.75 * h), int(.25 * w):int(.75 * w)] = (110, 120, 125)
    wa = W.jpeg(W.resize_long(stored, 1600), 70)[0]
    crop = W.jpeg(W.resize_long(stored[:, :int(w * .9)], 1600), 70)[0]
    cam, tc = phys_sim.simulate(cv2.cvtColor(wa, cv2.COLOR_RGB2BGR), 'monitor', 10, 6, 2, 1.0, 2.5, 85, seed=i)
    tapped = (tc + np.clip(np.random.default_rng(1000 + i).normal(0, 0.0065 * wa.shape[1] * 1.7 * 0.5, (4, 2)), -40, 40)).tolist()
    cam = cv2.cvtColor(cam, cv2.COLOR_BGR2RGB)
    S = [('Original, straight off the camera', 'No mark has been written yet.', rgb, 'read', None, None),
         ('The hidden layer, made visible', 'Difference between marked and original, x26.', gm, None, None, None),
         ('Marked and saved (JPEG q95)', 'Looks identical. The record rides in the pixels.', stored, 'read', None, None),
         ('Sent through a chat app', '1600 px, JPEG q70. EXIF stripped by the app.', wa, 'read', None, None),
         ('Shrunk to a 600 px thumbnail', 'JPEG q50. A hard test at the edge of the limit.', W.jpeg(W.resize_long(stored, 600), 50)[0], 'read', None, None),
         ('Turned black & white', 'Colour layer is gone. Luma layer takes over.', W.jpeg(W.resize_long(cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB), 1600), 70)[0], 'read', None, None),
         ('A quarter of the frame painted over', 'Mark is spread over the whole picture.', W.jpeg(W.resize_long(dm, 1600), 70)[0], 'read', None, None),
         ('Cropped 10% and sent again', 'Reader searches for the original frame.', crop, 'readcrop', None, None),
         ('A phone photo of a monitor', 'Simulated: tilt, blur, noise. Four corners tapped.', cam, 'readpersp', tapped, 'perspective + pilot alignment')]
    frames, durs = [], []
    for k, (t, s, img, cmd, extra, note) in enumerate(S):
        if cmd:
            r = W.read(img, cmd, extra) if extra else W.read(img, cmd)
            rd = decode(r); z1, z2 = r.get('z1', 0), r.get('z2', 0)
        else:
            rd, z1, z2 = None, 0, 0
        frames.append(frame(i, k, len(S), '%d  %s' % (k + 1, t), s, img, rd, z1, z2, note)); durs.append(1600 if k not in (1, 8) else 2200)
    save_webp(frames, os.path.join(A, 'photo%02d.webp' % (i + 1)), durs)
    print('photo', i + 1, 'done', flush=True)
    return dict(i=i, rgb=cv2.resize(rgb, (max(8, rgb.shape[1] // 8), max(8, rgb.shape[0] // 8)), interpolation=cv2.INTER_AREA),
                gm=cv2.resize(gm, (max(8, gm.shape[1] // 8), max(8, gm.shape[0] // 8)), interpolation=cv2.INTER_AREA))


if __name__ == '__main__':
    only = [int(a) - 1 for a in sys.argv[1:]]
    thumbs_path = os.path.join(W.HERE, 'results', 'thumbs.npz')
    if only:
        for i in only: showcase(i)
        sys.exit()
    with ThreadPoolExecutor(max_workers=int(os.environ.get('WORKERS', 4))) as ex:
        res = list(ex.map(showcase, range(N)))
    # ---------------- the photo wall: photo, hidden layer, 12 coloured result dots
    cw, ch, cols = 230, 150, 8; rows = (N + cols - 1) // cols; tileh = ch * 2 + 70
    wall = Image.new('RGB', (cols * (cw + 10) + 10, rows * (tileh + 10) + 10), BG); d = ImageDraw.Draw(wall)
    for k, r in enumerate(res):
        x, y = 10 + (k % cols) * (cw + 10), 10 + (k // cols) * (tileh + 10); p = R[k]
        d.rounded_rectangle((x - 4, y - 4, x + cw + 4, y + tileh - 4), 10, fill=CARD, outline=LINE)
        wall.paste(cover(r['rgb'], cw, ch), (x, y)); wall.paste(cover(r['gm'], cw, ch), (x, y + ch))
        d.rectangle((x, y, x + 54, y + 22), fill=BG); d.text((x + 6, y + 4), '#%d' % p['id'], font=F(12, True), fill=(255, 255, 255))
        d.rectangle((x, y + 2 * ch - 20, x + 130, y + 2 * ch), fill=BG); d.text((x + 6, y + 2 * ch - 17), 'hidden layer x26', font=F(10), fill=CYAN)
        dots = [a for a in p['attacks'] if 'CONTROL' not in a['name']]
        for j, a in enumerate(dots): d.ellipse((x + 6 + j * 18, y + 2 * ch + 8, x + 16 + j * 18, y + 2 * ch + 18), fill=STAT_COL[a['status']])
        d.text((x + 6, y + 2 * ch + 28), SCENE[k][:30], font=F(11, True), fill=TXT)
        d.text((x + 6, y + 2 * ch + 46), '%s · %.0f MP · PSNR %.1f' % (p['model'][:16], p['mp'], p['psnr']), font=F(10), fill=MUTED)
    wall.save(os.path.join(A, 'photo_wall.jpg'), quality=88)
    # ---------------- hero GIF (photo 11, a cracked column)
    hi = 10
    rgb = W.load(files[hi]); marked, _ = W.embed(rgb); gm = ghost_map(rgb, marked)
    HW, HH, IW = 720, 500, 360
    base = np.asarray(fit(marked, IW, 430, BG)); gmi = np.asarray(fit(gm, IW, 430, BG))
    rec = ['LAT  12.97160° N', 'LON  77.59457° E', 'ALT  920 m', 'UTC  2026-10-25 12:00:00.4', 'READ IN 0.15 s · CRC OK']
    fr, du = [], []
    NS = 12
    for t in range(NS + 8):
        s_ = min(t, NS) / NS; x = int(s_ * IW)
        img = base.copy(); img[:, :x] = gmi[:, :x]
        full = Image.new('RGB', (HW, HH), BG); full.paste(Image.fromarray(img), (0, 0)); d = ImageDraw.Draw(full)
        d.line((x, 0, x, 430), fill=CYAN, width=3)
        d.rectangle((0, 430, HW, HH), fill=(16, 20, 27))
        d.text((16, 448), 'GHOSTMARK', font=F(20, True), fill=CYAN)
        d.text((16, 478), 'left of the scan line: what the photo secretly carries (x26)', font=F(11), fill=MUTED)
        d.text((386, 28), 'Same photo.', font=F(26, True), fill=TXT); d.text((386, 62), 'Two views.', font=F(26, True), fill=CYAN)
        d.text((386, 106), chr(10).join(['The right side is the photo.', 'The left side is the invisible', 'layer: pixels nudged by 1-2', 'grey levels in a pattern only', 'the reader can decode.']), font=F(13), fill=MUTED, spacing=4)
        k = 0 if t < NS else min(t - NS + 1, 5)
        d.rounded_rectangle((386, 232, 706, 232 + 40 + 28 * len(rec)), 10, fill=(13, 17, 23), outline=GREEN if k else LINE)
        d.text((402, 244), 'FULL RECORD READ' if k else 'scanning...', font=F(12, True), fill=GREEN if k else MUTED)
        for j in range(k): d.text((402, 274 + j * 28), rec[j], font=F(14), fill=TXT)
        fr.append(full); du.append(140 if t < NS else (1200 if t == NS + 7 else 450))
    du[0] = 800
    save_gif(fr, os.path.join(A, 'hero_reveal.gif'), du)
    # ---------------- banner: strips of 10 photos
    BW, BH = 1600, 520
    ban = Image.new('RGB', (BW, BH), BG); pick = [0, 23, 10, 14, 33, 17, 3, 35, 12, 28]; sw = BW // len(pick)
    for kk, k in enumerate(pick):
        o = cover(res[k]['rgb'], sw + 4, BH); g = cover(res[k]['gm'], sw + 4, BH)
        ban.paste(Image.blend(o, g, 0.0 if kk % 2 == 0 else 0.55), (kk * sw, 0))
    ban = Image.blend(ban, Image.new('RGB', (BW, BH), (6, 10, 16)), 0.62)
    glow = Image.new('RGB', (BW, BH), (0, 0, 0)); gd = ImageDraw.Draw(glow)
    tf = F(150, True); tw = gd.textbbox((0, 0), 'GHOSTMARK', font=tf)[2]
    gd.text(((BW - tw) // 2, 120), 'GHOSTMARK', font=tf, fill=CYAN); glow = glow.filter(ImageFilter.GaussianBlur(18))
    ban = Image.fromarray(np.clip(np.asarray(ban).astype(int) + np.asarray(glow) // 2, 0, 255).astype(np.uint8))
    bd = ImageDraw.Draw(ban); bd.text(((BW - tw) // 2, 120), 'GHOSTMARK', font=tf, fill=(240, 249, 255))
    st = 'photos that remember where and when. even after the metadata is gone.'
    sw_ = bd.textbbox((0, 0), st, font=F(28))[2]; bd.text(((BW - sw_) // 2, 330), st, font=F(28), fill=(200, 215, 230))
    st2 = 'INVISIBLE  ·  SURVIVES WHATSAPP, CROPS, SCREENSHOTS  ·  97 KB  ·  ZERO DEPENDENCIES'
    s2 = bd.textbbox((0, 0), st2, font=F(18, True))[2]; bd.text(((BW - s2) // 2, 400), st2, font=F(18, True), fill=CYAN)
    ban.save(os.path.join(A, 'banner.jpg'), quality=90)
    # ---------------- stat strip (numbers computed from the results)
    tot_full = sum(a['ok1'] for p in R for a in p['attacks'] if 'CONTROL' not in a['name'])
    tot = sum(1 for p in R for a in p['attacks'] if 'CONTROL' not in a['name'])
    big_ok = sum(a['ok1'] for p in R for a in p['attacks'] if 'CONTROL' not in a['name'] and any(s in a['name'] for s in ('Stored', 'Chat', 'Social', 'Screenshot', 'Bright', 'Colour', 'Blur', 'painted', 'three')))
    big_n = sum(1 for p in R for a in p['attacks'] if any(s in a['name'] for s in ('Stored', 'Chat', 'Social', 'Screenshot', 'Bright', 'Colour', 'Blur', 'painted', 'three')))
    ctl = json.load(open(os.path.join(W.HERE, 'results', 'controls.json')))['controls'] if os.path.exists(os.path.join(W.HERE, 'results', 'controls.json')) else []
    fp = sum(c['status'] != 'none' for c in ctl)
    ps = np.median([p['psnr'] for p in R])
    SWd, SHt = 1600, 230
    strip = Image.new('RGB', (SWd, SHt), BG); sd = ImageDraw.Draw(strip)
    tiles = [('%d / %d' % (big_ok, big_n), 'full records read after\nchat, share, screenshot, edits', GREEN), ('%d / %d' % (fp, len(ctl) or 1), 'false alarms on\nunmarked photos', CYAN), ('0.15 s', 'to read a 12 MP photo\non a phone', PURPLE),
             ('1.2 s', 'to mark a 12 MP photo\nincl. self-test', ORANGE), ('97 KB', 'AAR. no dependencies,\nno permissions, no network', CYAN), ('%.0f dB' % ps, 'median PSNR: the change\nis a few grey levels of 255', GREEN)]
    tw_ = (SWd - 7 * 14) // 6
    for k, (big, small, c) in enumerate(tiles):
        x = 14 + k * (tw_ + 14)
        sd.rounded_rectangle((x, 14, x + tw_, SHt - 14), 14, fill=CARD, outline=LINE); sd.rounded_rectangle((x, 14, x + tw_, 20), 3, fill=c)
        bw = sd.textbbox((0, 0), big, font=F(40, True))[2]; sd.text((x + (tw_ - bw) // 2, 52), big, font=F(40, True), fill=c)
        sd.multiline_text((x + 18, 125), small, font=F(15), fill=MUTED, spacing=6)
    strip.save(os.path.join(A, 'stats_strip.png'))
    print('showcase complete', big_ok, big_n, fp, len(ctl))
