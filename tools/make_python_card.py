"""Runs python/examples/mark_and_read.py for real and renders the command + its output as a terminal-style PNG."""
import os, subprocess, sys, tempfile
import matplotlib
from PIL import Image, ImageDraw, ImageFont
import wmlib as W

FD = os.path.join(os.path.dirname(matplotlib.__file__), 'mpl-data', 'fonts', 'ttf')
mono = lambda s, b=False: ImageFont.truetype(os.path.join(FD, 'DejaVuSansMono-Bold.ttf' if b else 'DejaVuSansMono.ttf'), s)
src = os.path.join(tempfile.mkdtemp(), 'photo.jpg')
Image.fromarray(W.resize_long(W.load(W.photo_files()[10]), 2400)).save(src, quality=92)
env = dict(os.environ, PYTHONPATH=os.path.join(W.HERE, '..', 'python'))
out = subprocess.run([sys.executable, os.path.join(W.HERE, '..', 'python', 'examples', 'mark_and_read.py'), src], capture_output=True, text=True, env=env, cwd=os.path.join(W.HERE, '..', 'python')).stdout.strip().split('\n')
cmd = '$ python examples/mark_and_read.py photo.jpg'
lines = [(cmd, (230, 237, 243))] + [(l, (63, 185, 80) if 'ok' in l.split(':')[-1][:4] else (227, 160, 40) if 'part' in l else (139, 148, 158) if 'none' in l else (230, 237, 243)) for l in out]
f = mono(17); w = 1500; h = 70 + 34 * len(lines) + 30
im = Image.new('RGB', (w, h), (13, 17, 23)); d = ImageDraw.Draw(im)
d.rounded_rectangle((0, 0, w - 1, h - 1), 14, fill=(22, 27, 34), outline=(48, 54, 61))
d.rounded_rectangle((0, 0, w - 1, 44), 14, fill=(33, 38, 45)); d.rectangle((0, 30, w, 44), fill=(33, 38, 45))
for k, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]): d.ellipse((20 + k * 26, 14, 34 + k * 26, 28), fill=c)
d.text((w // 2 - 120, 12), 'ghostmark · python', font=mono(15), fill=(139, 148, 158))
for k, (t, c) in enumerate(lines): d.text((28, 66 + k * 34), t, font=mono(17, k == 0), fill=c)
im.save(os.path.join(W.HERE, '..', 'assets', 'python_terminal.png'))
print('\n'.join(out))
