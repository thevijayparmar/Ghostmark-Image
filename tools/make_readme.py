"""Assembles README.md from the measured results (so every number in the README is generated, not typed)."""
import json, os
import numpy as np
from theme import device_group, robustness
import wmlib as W

ROOT = os.path.join(W.HERE, '..')
R = json.load(open(os.path.join(W.HERE, 'results', 'results.json')))
S = json.load(open(os.path.join(W.HERE, 'results', 'summary.json')))
P = R['photos']; N = len(P)
for p in P:
    p['dev'] = device_group(p['make'], p['model']); p['score'] = robustness(p)
NA = len(P[0]['attacks']) - 1
SCENE = ['Carved stone temple', 'Step-well and water', 'Stone well, looking up', 'Rebar mat, construction site', 'Crane erection site', 'Sky over a highway', 'Jetty and offshore rig',
         'Rooftop rebar and formwork', 'Telecom tower against sky', 'Power line on a shoreline', 'Cracked concrete column', 'Drone: scrubland', 'Offshore rigs, storm clouds', 'Stone-pier bridge',
         'Drone: farm fields', 'Water tank on columns', 'River weir', 'Drone: river and bridge', 'Drone: solar farm', 'Weathered brick wall', 'Car park from a car', 'Fruit plate', 'Cafe interior']
DEVICES = [('iPhone 16 Pro', '📱'), ('DJI drone', '🚁'), ('OnePlus', '📱'), ('vivo', '📱'), ('realme', '📱'), ('LAVA', '📱')]
med = lambda k: float(np.median([p[k] for p in P]))
full, part, dmg = S['totals']['full'], S['totals']['part'], S['totals']['dmg']
tot = full + part + dmg
fp_n, fp_total, fp_max = S['fp']
EASY = ('Stored', 'Chat', 'Social', 'Screenshot', 'Bright', 'Colour', 'Blur', 'painted', 'three')


def att(j): return [p['attacks'][j] for p in P]


big_ok = sum(a['ok1'] for p in P for a in p['attacks'] if any(s in a['name'] for s in EASY))
big_n = sum(1 for p in P for a in p['attacks'] if any(s in a['name'] for s in EASY))
chat_ok = sum(a['ok1'] for a in att(1)); chat_z = float(np.median([a['z1'] for a in att(1) if a['ok1']]))
crops = [(c['name'], c['area'], sum(p['crops'][k]['ok1'] for p in P)) for k, c in enumerate(P[0]['crops'])]
scr = [sum(p['screen'][k]['ok1'] for p in P) for k in range(2)]
scr_ms = [np.mean([p['screen'][k]['ms'] for p in P]) / 1000 for k in range(2)]
heic = [p for p in P if 'heic' in p and 'ok1' in p['heic']]; heic_ok = sum(p['heic']['ok1'] for p in heic)
strength = [(s['s'], np.mean([p['strength'][k]['psnr'] for p in P]), np.mean([p['strength'][k]['chat_ok1'] for p in P]) * 100, np.mean([p['strength'][k]['small_ok1'] for p in P]) * 100) for k, s in enumerate(P[0]['strength'])]
T = json.load(open(os.path.join(W.HERE, 'results', 'timing.json')))
kms = np.polyfit([t['mp'] for t in T], [t['embed_ms'] for t in T], 1)[0]
emb_med = float(np.median([t['embed_ms'] for t in T])); read_med = float(np.median([t['read_ms'] for t in T]))
tex_r = S['texture_r']
weak = sorted(P, key=lambda p: (p['score'], p['attacks'][1]['z1']))[:5]
strong = sorted(P, key=lambda p: (-p['score'], -p['attacks'][1]['z1']))[:5]
small_fail = [p['id'] for p in P if not p['strength'][2]['small_ok1']]
rescued = [i for i in small_fail if P[i - 1]['strength'][4]['small_ok1']]
fail_stored = [p['id'] for p in P if not p['attacks'][0]['ok1']]


def chip(p):
    o = [a for a in p['attacks'] if 'CONTROL' not in a['name']]
    f = sum(a['ok1'] for a in o); pt = sum((not a['ok1']) and a['status'] == 'part' for a in o); d = len(o) - f - pt
    bits = ['✅ %d full' % f]
    if pt: bits.append('🟠 %d location-only' % pt)
    if d: bits.append('🔴 %d unreadable' % d)
    return ' · '.join(bits) + ' (of %d edits)' % len(o)


def cell(p):
    i = p['id']
    return ('<td width="50%%" align="center">\n  <img src="assets/photo%02d.gif" width="100%%" alt="Photo %d, %s, through nine tests"/>\n'
            '  <br/><sub><b>#%d · %s</b><br/>%s %s · %.0f MP · PSNR %.1f dB · chat-app z = %.0f<br/>%s</sub>\n</td>') % (
        i, i, SCENE[i - 1], i, SCENE[i - 1], p['make'], p['model'], p['mp'], p['psnr'], p['attacks'][1]['z1'], chip(p))


def gallery():
    out = []
    for dev, ico in DEVICES:
        ps = [p for p in P if p['dev'] == dev]
        if not ps: continue
        mean = np.mean([p['score'] for p in ps])
        out.append('### %s %s &nbsp;<sub>%d photo%s · average %.1f of %d edits survived with the full record</sub>\n' % (ico, dev, len(ps), 's' if len(ps) > 1 else '', mean, NA))
        out.append('<table>')
        for k in range(0, len(ps), 2):
            out.append('<tr>')
            out.append(cell(ps[k]))
            out.append(cell(ps[k + 1]) if k + 1 < len(ps) else '<td width="50%"></td>')
            out.append('</tr>')
        out.append('</table>\n')
    return '\n'.join(out)


def board(lst, title):
    rows = ['| # | Scene | Camera | Texture | Brightness | Chat-app z | Full reads |', '|:-:|---|---|:-:|:-:|:-:|:-:|']
    for p in lst:
        rows.append('| %d | %s | %s | %.2f | %.0f | %.0f | %d / %d |' % (p['id'], SCENE[p['id'] - 1], p['model'], p['texture'], p['luma'], p['attacks'][1]['z1'], p['score'], NA))
    return '**%s**\n\n' % title + '\n'.join(rows)


def att_table():
    rows = ['| Edit applied to the stored JPEG | Full record | Location only (layer 2 alone) | Median z |', '|---|:-:|:-:|:-:|']
    for j, a in enumerate(P[0]['attacks']):
        if 'CONTROL' in a['name']: continue
        ok1 = sum(x['ok1'] for x in att(j)); ok2 = sum(x['ok2'] for x in att(j)); pt = sum(x['status'] == 'part' for x in att(j))
        zs = [x['z1'] for x in att(j) if x['ok1']]
        loc = '%d / %d' % (ok2, N) if 'Black' not in a['name'] else '**%d / %d** (as `PART`)' % (ok2, N)
        rows.append('| %s | %d / %d | %s | %s |' % (a['name'], ok1, N, loc, ('%.0f' % np.median(zs)) if zs else 'n/a'))
    for name, area, ok in crops:
        rows.append('| Crop to %d%% of the area (%s), then chat app | %d / %d | n/a | n/a |' % (area, name, ok, N))
    rows.append('| Simulated phone photo of a **monitor** (4 tapped corners) | %d / %d | n/a | n/a |' % (scr[0], N))
    rows.append('| Simulated phone photo of a **print** (4 tapped corners) | %d / %d | n/a | n/a |' % (scr[1], N))
    rows.append('| HEIC original → mark → save as JPEG q95 | %d / %d | n/a | n/a |' % (heic_ok, len(heic)))
    return '\n'.join(rows)


def device_table():
    rows = ['| Camera | Photos | Sensor / type | Avg. edits survived | Median PSNR |', '|---|:-:|---|:-:|:-:|']
    for dev, ico in DEVICES:
        ps = [p for p in P if p['dev'] == dev]
        if not ps: continue
        kind = ', '.join(sorted({p['model'] for p in ps}))
        rows.append('| %s %s | %d | %s | %.1f / %d | %.1f dB |' % (ico, dev, len(ps), kind, np.mean([p['score'] for p in ps]), NA, np.median([p['psnr'] for p in ps])))
    return '\n'.join(rows)


def strength_table():
    rows = ['| Strength (× default) | Mean PSNR | Chat app (1600 px q70) read in full | Thumbnail (800 px q40) read in full |', '|:-:|:-:|:-:|:-:|']
    for s, ps, c, sm in strength:
        rows.append('| %s%g× | %.1f dB | %.0f%% | %.0f%% |' % ('**' if s == 1.0 else '', s, ps, c, sm) if s != 1.0 else '| **1× (default)** | **%.1f dB** | **%.0f%%** | **%.0f%%** |' % (ps, c, sm))
    return '\n'.join(rows)


TEMPLATE = open(os.path.join(W.HERE, 'readme_template.md'), encoding='utf8').read()
vals = dict(
    N=N, NA=NA, TOT=tot, FULL=full, PART=part, DMG=dmg, FULLPCT=full / tot * 100, FP_N=fp_n, FP_TOTAL=fp_total, FP_MAX=fp_max,
    BIG_OK=big_ok, BIG_N=big_n, CHAT_OK=chat_ok, CHAT_Z=chat_z, PSNR_MED=med('psnr'), PSNR_MIN=min(p['psnr'] for p in P), PSNR_MAX=max(p['psnr'] for p in P),
    SSIM_MED=med('ssim'), DE_MED=med('dE'), MEAN_CH=med('mean_change'), MAX_CH=max(p['max_change'] for p in P), BYTES_MAX=max(p['bytes_added_pct'] for p in P),
    TEX_R=tex_r, KMS=kms, MP_MIN=min(p['mp'] for p in P), MP_MAX=max(p['mp'] for p in P), EMB_MED=emb_med, READ_MED=read_med,
    SCR0=scr[0], SCR1=scr[1], SCRMS0=scr_ms[0], SCRMS1=scr_ms[1], HEIC_OK=heic_ok, HEIC_N=len(heic),
    C90=crops[0][2], C75=crops[1][2], C60=crops[2][2], C45=crops[3][2], CTRIM=crops[4][2], CQ=crops[5][2],
    FAIL_STORED=', '.join('#%d' % i for i in fail_stored) or 'none', N_SMALL_FAIL=len(small_fail), N_RESCUED=len(rescued),
    GALLERY=gallery(), ATT_TABLE=att_table(), DEVICE_TABLE=device_table(), STRENGTH_TABLE=strength_table(),
    WEAK=board(weak, 'The five most fragile photos'), STRONG=board(strong, 'The five most robust photos'),
    ALL_Z=len([1 for p in P for a in p['attacks'] if 'CONTROL' not in a['name'] and a['ok1']]),
    NDEV=len({(p['make'], p['model']) for p in P}),
    BW_LOC=sum(a['ok2'] for a in att(11)), MIN_OK_Z=min(a['z1'] for p in P for a in p['attacks'] if a['ok1']),
    DJI_AVG=np.mean([p['score'] for p in P if p['dev'] == 'DJI drone']), IPH_AVG=np.mean([p['score'] for p in P if p['dev'] == 'iPhone 16 Pro']),
    LAVA_AVG=np.mean([p['score'] for p in P if p['dev'] == 'LAVA']),
)
out = TEMPLATE
for k, v in vals.items():
    out = out.replace('{{%s}}' % k, ('%.1f' % v if isinstance(v, float) and k not in ('SSIM_MED', 'TEX_R', 'FP_MAX') else ('%.4f' % v if k == 'SSIM_MED' else ('%.2f' % v if isinstance(v, float) else str(v)))))
open(os.path.join(ROOT, 'README.md'), 'w', encoding='utf8').write(out)
left = [w for w in out.split('{{')[1:]]
print('README written,', len(out), 'chars; unresolved placeholders:', [l.split('}}')[0] for l in left][:5])
