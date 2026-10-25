"""Command line: `ghostmark mark in.jpg out.jpg --lat 12.97 --lon 77.59` and `ghostmark read photo.jpg`."""
import argparse
import datetime
import json
import sys

from . import _api as g


def _time(s):
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        d = datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
        return (d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)).timestamp()


def main(argv=None):
    ap = argparse.ArgumentParser(prog='ghostmark', description='Invisible location/time mark for photos (Ghostmark-Image).')
    ap.add_argument('--version', action='version', version='ghostmark ' + g.__version__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('mark', help='write the invisible mark into a copy of a photo')
    m.add_argument('src')
    m.add_argument('dst')
    m.add_argument('--lat', type=float)
    m.add_argument('--lon', type=float)
    m.add_argument('--alt', type=float)
    m.add_argument('--time', help='UTC, ISO-8601 (2026-10-25T12:00:00Z) or unix seconds')
    m.add_argument('--tenth', type=int, default=0)
    m.add_argument('--manual', action='store_true')
    m.add_argument('--quality', type=int, default=95)
    m.add_argument('--strength', type=float, default=1.0)
    m.add_argument('--no-self-test', action='store_true', help='skip the chat-app self-test (faster, fixed --strength)')
    r = sub.add_parser('read', help='read the mark from a photo')
    r.add_argument('file')
    r.add_argument('--crop', action='store_true', help='the picture is a crop of the original')
    r.add_argument('--corners', help='photo of a screen/print: x1,y1,x2,y2,x3,y3,x4,y4 (TL,TR,BR,BL)')
    r.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if a.cmd == 'mark':
        rec = g.Record(a.lat, a.lon, a.alt, _time(a.time), a.tenth, a.manual)
        used = g.mark_file(a.src, a.dst, rec, a.quality, not a.no_self_test, a.strength)
        print('marked %s (strength %.1f)' % (a.dst, used))
        return 0
    corners = None
    if a.corners:
        v = [float(x) for x in a.corners.split(',')]
        corners = [(v[i], v[i + 1]) for i in range(0, 8, 2)]
    res = g.read_file(a.file, a.crop, corners)
    if res is None:
        print('no frame position fits (not a crop of a marked picture)')
        return 1
    if a.json:
        print(json.dumps(dict(status=res.status, l1=res.l1, l2=res.l2, z1=res.z1, z2=res.z2, **res.extra), default=float))
    else:
        print('status: %s   (z1 %.1f, z2 %.1f)' % (res.status, res.z1, res.z2))
        if res.l1:
            print('  full record: lat %.6f lon %.6f alt %s  time %s  id %s' % (res.l1['lat'], res.l1['lon'], res.l1['alt'], res.time, res.id))
        elif res.l2:
            print('  location only (+-10 m): lat %.4f lon %.4f' % (res.l2['lat'], res.l2['lon']))
    return 0 if res.status in ('ok', 'part') else 2


if __name__ == '__main__':
    sys.exit(main())
