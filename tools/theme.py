"""Shared dark theme + helpers for every README chart."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BG, CARD, LINE, TXT, MUTED = '#0d1117', '#161b22', '#30363d', '#e6edf3', '#8b949e'
CYAN, GREEN, ORANGE, RED, PURPLE, BLUE, PINK = '#38bdf8', '#3fb950', '#e3a028', '#f85149', '#a78bfa', '#58a6ff', '#f778ba'
DEVICE_COLORS = {'iPhone 16 Pro': CYAN, 'iPhone 17 Pro': '#f2cc60', 'DJI drone': GREEN, 'OnePlus': ORANGE, 'vivo': PURPLE, 'realme': PINK, 'LAVA': RED}

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 9, 'text.color': TXT, 'axes.labelcolor': TXT, 'axes.edgecolor': LINE,
    'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.facecolor': CARD, 'figure.facecolor': BG, 'savefig.facecolor': BG,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.titleweight': 'bold', 'axes.titlesize': 10, 'axes.titlecolor': TXT,
    'grid.color': LINE, 'grid.alpha': .6, 'legend.facecolor': CARD, 'legend.edgecolor': LINE, 'legend.labelcolor': TXT,
})


def device_group(make, model):
    m = (make + ' ' + model).lower()
    if 'iphone 17' in m: return 'iPhone 17 Pro'
    if 'iphone' in m: return 'iPhone 16 Pro'
    if 'dji' in m: return 'DJI drone'
    if 'oneplus' in m: return 'OnePlus'
    if 'vivo' in m: return 'vivo'
    if 'realme' in m: return 'realme'
    if 'lava' in m: return 'LAVA'
    return make or 'other'


def robustness(p):
    """number of full-record reads among the 12 marked-photo edits (control excluded)"""
    return sum(a['ok1'] for a in p['attacks'] if 'CONTROL' not in a['name'])
