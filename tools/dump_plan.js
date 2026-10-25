// node dump_plan.js W H  -> tile grid + pilot indices of layer 1 and 2 (for the README figure)
const WM = require('../reference/wm-engine.js');
const W = +process.argv[2], H = +process.argv[3];
const out = {};
for (const [k, L, nc] of [['l1', WM.L1, 2 * (WM.N1 + 6)], ['l2', WM.L2, 2 * (WM.N2 + 6)]]) {
  const [nx, ny] = WM.gridFor(W, H, L.ncells);
  const pl = WM.plan(L, nx, ny, nc);
  out[k] = { nx, ny, pilot: Array.from(pl.pilot), pn: Array.from(pl.pn), coded: nc };
}
console.log(JSON.stringify(out));
