"""Run with:  pip install -e .[test]  &&  pytest -q   (from the python/ folder)."""
import io
import os
import random

import numpy as np
import pytest
from PIL import Image

import ghostmark as gm
from ghostmark import _core as C

FIXTURES = os.path.join(os.path.dirname(__file__), '..', '..', 'engine', 'src', 'test', 'resources', 'mark')
REC = gm.Record(lat=12.971599, lon=77.594566, alt=920, t=1792929600, tenth=4)


def _scene(w=1200, h=900, seed=3):
    """A synthetic photo with texture (smoothed noise + gradients + edges), so the tests need no image files."""
    rng = np.random.default_rng(seed)
    base = rng.normal(0, 1, (h // 8, w // 8, 3))
    img = np.asarray(Image.fromarray(((base - base.min()) / (np.ptp(base)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), float)
    yy, xx = np.mgrid[0:h, 0:w]
    img = 0.55 * img + 0.45 * np.stack([xx / w * 255, yy / h * 255, (xx + yy) / (w + h) * 255], -1)
    img += rng.normal(0, 22, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def _jpeg(rgb, q, long_edge=None):
    im = Image.fromarray(rgb)
    if long_edge:
        s = long_edge / max(im.size)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, 'JPEG', quality=q)
    return np.asarray(Image.open(io.BytesIO(b.getvalue())).convert('RGB'))


def test_crc_known_value():
    # CRC-16/CCITT-FALSE of "123456789" is 0x29B1
    bits = [int(b) for ch in b'123456789' for b in format(ch, '08b')]
    assert C.crc16(bits) == 0x29B1


def test_payload_roundtrip():
    got = C.unpack_l1(C.pack_l1(REC.to_dict()))
    assert abs(got['lat'] - REC.lat) < 2e-5 and abs(got['lon'] - REC.lon) < 2e-5
    assert got['alt'] == 920 and got['t'] == 1792929600 and got['tenth'] == 4 and len(got['id']) == 10
    loc = C.unpack_l2(C.pack_l2(REC.to_dict()))
    assert abs(loc['lat'] - REC.lat) < 1.2e-4 and abs(loc['lon'] - REC.lon) < 1.2e-4


def test_unknown_fields_stay_unknown():
    got = C.unpack_l1(C.pack_l1(dict(lat=None, lon=None, alt=None, t=None, tenth=0, manual=0)))
    assert got['lat'] is None and got['alt'] is None and got['t'] is None


def test_viterbi_repairs_flipped_bits():
    bits = C.pack_l1(REC.to_dict())
    soft = [1.0 if b else -1.0 for b in C.conv_encode(bits)]
    rnd = random.Random(1)
    for i in rnd.sample(range(len(soft)), 12):
        soft[i] = -soft[i]
    assert C.viterbi(soft) == bits


def test_prng_matches_reference_engine():
    # first outputs of mulberry32(1) from the JavaScript reference engine
    r = C.mulberry32(1)
    assert [round(r(), 6) for _ in range(3)] == [0.627074, 0.002736, 0.527447]


def test_mark_and_read_back():
    rgb = _scene()
    marked = gm.mark(rgb, REC)
    assert marked.shape == rgb.shape and marked.dtype == np.uint8
    assert np.abs(marked.astype(int) - rgb.astype(int)).max() <= 10   # invisible: a few grey levels at most
    r = gm.read(marked)
    assert r.status == 'ok' and r.ok and r.id
    assert abs(r.l1['lat'] - REC.lat) < 2e-5 and r.l1['alt'] == 920 and r.time.year == 2026
    assert r.location[0] == pytest.approx(REC.lat, abs=2e-5)


def test_survives_jpeg_and_resize():
    marked = gm.mark(_scene(), REC)
    r = gm.read(_jpeg(marked, 70, 900))
    assert r.status == 'ok' and abs(r.l1['lon'] - REC.lon) < 2e-5


def test_unmarked_picture_is_none():
    r = gm.read(_scene(seed=9))
    assert r.status == 'none' and r.l1 is None and r.l2 is None and r.location is None


def test_black_and_white_keeps_location_only():
    marked = gm.mark(_scene(), REC)
    grey = np.asarray(Image.fromarray(marked).convert('L').convert('RGB'))
    r = gm.read(_jpeg(grey, 70, 900))
    assert r.status == 'part' and r.l1 is None
    assert abs(r.l2['lat'] - REC.lat) < 1.2e-4 and abs(r.l2['lon'] - REC.lon) < 1.2e-4


def test_self_test_picks_a_strength():
    marked, strength = gm.mark_verified(_scene(), REC)
    assert strength in (1.0, 1.4, 1.9)
    assert gm.read(marked).status == 'ok'


def test_bad_input_is_rejected():
    with pytest.raises(ValueError):
        gm.mark(np.zeros((10, 10), np.uint8), REC)


# ---- interoperability with marks written by the Kotlin / JavaScript engines (the fixtures of the Android engine tests)
needs_fixtures = pytest.mark.skipif(not os.path.isdir(FIXTURES), reason='engine fixtures not found')


def _fx(name):
    return np.asarray(Image.open(os.path.join(FIXTURES, name)).convert('RGB'))


@needs_fixtures
def test_reads_marks_written_by_the_other_engines():
    r = gm.read(_fx('photo1_wa1600.jpg'))
    assert r.status == 'ok' and abs(r.l1['lat'] - 40.18323928) < 2e-5 and abs(r.l1['lon'] + 83.08500622) < 2e-5
    assert r.l1['alt'] == 253 and r.l1['t'] == 1791392322 and r.l1['tenth'] == 7 and len(r.id) == 10


@needs_fixtures
def test_fixture_unmarked_and_bw():
    assert gm.read(_fx('photo1_unmarked.jpg')).status == 'none'
    r = gm.read(_fx('photo1_bw.jpg'))
    assert r.status == 'part' and abs(r.l2['lat'] - 40.18323928) < 1.2e-4


def test_turned_picture_is_found_with_try_turns():
    marked = gm.mark(_scene(), REC)
    sideways = np.ascontiguousarray(np.rot90(marked, 1))
    assert gm.read(sideways).status != 'ok'
    r = gm.read(sideways, try_turns=True)
    assert r.status == 'ok' and r.extra.get('turned') in (90, 270)


def test_cli_prints_records_without_location(capsys):
    # a mark can carry only a time (or only a location); the CLI must print '-' for the missing fields
    from ghostmark import cli
    from ghostmark._api import ReadResult
    cli._print_human(ReadResult(status='ok', l1=dict(id='ABCDEFGHIJ', lat=None, lon=None, alt=None, t=1792929600, tenth=0, manual=0), z1=5.0, z2=4.0))
    out = capsys.readouterr().out
    assert 'lat - lon -' in out and 'ABCDEFGHIJ' in out
    cli._print_human(ReadResult(status='part', l2=dict(lat=None, lon=None), z1=0.0, z2=5.0))
    out = capsys.readouterr().out
    assert 'lat - lon -' in out