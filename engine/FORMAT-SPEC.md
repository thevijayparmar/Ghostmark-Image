# Ghostmark: invisible mark format spec (v1)

`reference/wm-engine.js` is the reference implementation and wins over this text if they disagree.
The Kotlin engine (`engine/`) must read and write exactly this format.

## What it is

Two invisible layers written into the pixels, so the record survives a chat app, a format
change or a re-save (EXIF does not):

| | Layer 1 (colour) | Layer 2 (brightness) |
|---|---|---|
| Carries | location (about 1 m), altitude, UTC time, tenths of a second, Live/Manual flag | location only (about 10 m) |
| Channel | Cb and Cr, same sign | Y (luma) |
| Tiles | about 10,000 | about 50,000 |
| Max strength (steps of 255) | 2.0 (less on smooth areas, floor 25% of max) | 4.5 (none on perfectly smooth areas) |
| Pilot tiles | 20% | 20% |
| Payload bits | 118 | 60 |

Minimum picture size for a reliable layer 1 read: about 800 px on the long side.

## Payloads (bits, MSB first)

Layer 1 (118): `hasLoc(1) hasAlt(1) hasTime(1)  lat(25) lon(26) alt(14) time(29) tenth(4) manual(1)  crc16(16)`
- lat = round((lat+90)/180 * (2^25 - 1)); lon = round((lon+180)/360 * (2^26 - 1))
- alt = clamp(round(alt)+500, 0, 16383)
- time = unix seconds - 1767225600 (2026-01-01 UTC), clamp 0..2^29-1
- tenth = 0..9 (floor of the sub-second part x 10); manual = 1 when the location was added by hand to an existing photo
- a field that was not known is written as zeros with its flag 0; the reader must say "not present in the original"
- CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) over the preceding bits, zero padded to a whole byte

Layer 2 (60): `hasLoc(1)  lat(21) lon(22)  crc16(16)` with 21 and 22 bit scaling as above.

Mark ID (never stored): first 8 bytes of SHA-256 over the layer 1 body bits (one byte per bit, 0 or 1),
read as a big-endian integer, written as 10 letters base 26 (A = 0), least significant letter first.

## Coding

Rate 1/2, constraint length 7 convolutional code, generators 133 and 171 octal, 6 zero tail bits;
output order per input bit: g1 then g2. Soft-decision Viterbi, positive soft value = bit 1.
Coded bits: layer 1 has 2*(118+6) = 248, layer 2 has 2*(60+6) = 132.

## Tiles

For a picture W x H: `nx = max(8, floor(sqrt(ncells * W / H) + 0.5))`, `ny = max(8, floor(ncells / nx + 0.5))`.
Tile (tx, ty) covers pixels `floor(x*nx/W) == tx`, `floor(y*ny/H) == ty`.
Seeds: `seed32 = (layerSeed * 1000003 + nx * 1009 + ny) mod 2^32`, layerSeed 11 (layer 1) and 77 (layer 2).
PRNG mulberry32. Per tile sign `pn = rng() < 0.5 ? -1 : +1` for all tiles in order; then a Fisher-Yates
shuffle of 0..N-1 (`for i = N-1 down to 1: j = floor(rng()*(i+1)); swap`); the first `round(0.20*N)` tiles
of the shuffled list are pilot tiles, the rest are data tiles. Coded bit k owns data tiles k, k+M, k+2M, ...
(M = number of coded bits, indexes into the data part of the shuffled list).
Tile value: pilot tiles `pn`; data tiles `pn * (bit ? +1 : -1)`.

## Writing

1. Per tile mean of Y and Y^2 (Y = 0.299R + 0.587G + 0.114B, 0..255) on both grids, from the ORIGINAL pixels.
2. texture = clamp(sqrt(max(E[Y^2] - E[Y]^2, 0)) / 14, 0, 1); amplitude = amax * max(texture, floor).
3. Grid value g = tileValue * amplitude. Bilinear interpolation of each grid to every pixel
   (sample position u = (x + 0.5) * nx / W - 0.5, clamped to the grid edge).
4. Layer 1 adds p1 to Cb and Cr, layer 2 adds p2 to Y, which in RGB is:
   `R += p2 + 1.403*p1`, `G += p2 - 1.058*p1`, `B += p2 + 1.773*p1`; round and clamp to 0..255.
5. The mark is written LAST, after any burned-in overlay is drawn, so it sits in the final pixels.

## Reading

1. Per tile mean of chroma `C = ((R-Y)*0.713 + (B-Y)*0.564)/2 + 128` (layer 1) or Y (layer 2), and the
   texture, on the grid of the picture being read. For big pictures sample every s-th pixel (s = floor(sqrt(W*H/3e6))).
2. High-pass per tile: `hp = r - mean of the other k*k-1 tiles` (k = 5 for layer 1, 3 for layer 2, reflect at the edges).
3. weight `w = max(texture, floor)` (floor 0.02 for layer 2).
4. Per coded bit: `soft = sum(w*pn*hp) / sqrt(sum(w^2))` over its tiles. Viterbi, then CRC.
5. Detection score `z = sum_pilot(w*pn*hp) / sqrt(sum_pilot((w*hp)^2))`; `z > 3.5` with a failed CRC means
   "mark detected but too damaged to read".
6. If the CRC fails, retry with the neighbouring grids `nx +- 1` (and +-2 for layer 2) because a resized copy can round its size.
7. Result status: `ok` (layer 1 read), `part` (only layer 2), `damaged`, `none`. If both layers read and
   their locations differ by more than 30 m, warn of tampering.

## Honest limits (tested 2026-10-22, 4 photos)

Layer 1 reads after WhatsApp-style 1600 px q70 and down to 800 px q50; at 600 px it fails.
Layer 2 is weaker (fails at 900 px on some photos) but survives black-and-white conversion, which kills layer 1.
A plain crop or a tilt breaks the tile grid: the reader needs a frame search (not in this version of the engine).
The Live/Manual flag is not signed: anyone with this spec can write a mark.
