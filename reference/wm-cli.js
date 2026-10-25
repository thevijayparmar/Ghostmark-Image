// Command-line wrapper around wm-engine.js, for tests.
//   node wm-cli.js embed in.rgba W H payload.json out.rgba
//   node wm-cli.js read  in.rgba W H
const fs = require('fs');
const WM = require('./wm-engine.js');
const [cmd, inp, w, h, a, b] = process.argv.slice(2);
const W = +w, H = +h;
const buf = fs.readFileSync(inp);
const rgba = new Uint8ClampedArray(buf.buffer, buf.byteOffset, buf.length);
if (cmd === 'embed') {
  const payload = JSON.parse(fs.readFileSync(a, 'utf8'));
  const t0 = Date.now();
  const sf = +(process.env.WM_STRENGTH || 1);
  WM.embed(rgba, W, H, payload, { strength1: sf, strength2: sf });
  fs.writeFileSync(b, Buffer.from(rgba.buffer, rgba.byteOffset, rgba.length));
  console.log(JSON.stringify({ ms: Date.now() - t0 }));
} else if (cmd === 'read') {
  const t0 = Date.now();
  const r = WM.read(rgba, W, H);
  console.log(JSON.stringify({ status: r.status, l1: r.l1, l2: r.l2, z1: r.z1, z2: r.z2, ms: Date.now() - t0 }));
} else if (cmd === 'readcrop') {
  const t0 = Date.now();
  const r = WM.readCropped(rgba, W, H);
  console.log(JSON.stringify(r ? { status: r.status, l1: r.l1, l2: r.l2, z1: r.z1, z2: r.z2, crop: r.crop, ms: Date.now() - t0 } : { status: 'nocrop', ms: Date.now() - t0 }));
} else if (cmd === 'readpersp') {
  const corners = JSON.parse(fs.readFileSync(a, 'utf8'));
  const t0 = Date.now();
  const r = WM.readPerspective(rgba, W, H, corners, { fast: process.env.WM_FAST === '1' });
  console.log(JSON.stringify(r ? { status: r.status, l1: r.l1, l2: r.l2, z1: r.z1, z2: r.z2, persp: r.perspective, ms: Date.now() - t0 } : { status: 'nopersp', ms: Date.now() - t0 }));
} else if (cmd === 'autocorners') {
  console.log(JSON.stringify(WM.autoCorners(rgba, W, H)));
} else { console.error('usage'); process.exit(2); }
