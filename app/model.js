/* Port of code/model.py (pv-dwpt-campus): demand, PV and hourly matching with storage.
   PV per kWp per hour (Wh) is exported from the Python model (Hay–Davies, Ekici 2016, 1,311 kWh/kWp). */
const MDAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

function buildCalendar(D) {
  const n = D.pv.length, month = new Uint8Array(n), hour = new Uint8Array(n), dow = new Uint8Array(n), doy = new Uint16Array(n);
  let h = 0;
  for (let m = 0, d = 0; m < 12; m++) {
    for (let k = 0; k < MDAYS[m]; k++, d++) {
      for (let hh = 0; hh < 24; hh++, h++) {
        month[h] = m; hour[h] = hh; dow[h] = (D.dow0 + d) % 7; doy[h] = d;
      }
    }
  }
  return { n, month, hour, dow, doy };
}

function vehicles(D, C) {
  const v = new Float64Array(C.n);
  for (let h = 0; h < C.n; h++) {
    let f = C.dow[h] >= 5 ? D.weekend : 1;
    if (C.month[h] === 6 || C.month[h] === 7) f *= D.brk;
    v[h] = D.peak * D.prof[C.hour[h]] * f;
  }
  return v;
}

/* s: { layout: 'full'|'sel', share: 0..1, mult: PV size / required size, days: storage in mean days } */
function simulate(D, C, veh, s) {
  const e = s.layout === 'sel' ? D.e_sel : D.e_full;
  const n = C.n, dem = new Float64Array(n), pv = new Float64Array(n);
  let Dsum = 0;
  for (let h = 0; h < n; h++) { dem[h] = veh[h] * s.share * e; Dsum += dem[h]; }
  const kWpReq = Dsum / D.yield_, kWp = kWpReq * s.mult;
  let Gsum = 0;
  for (let h = 0; h < n; h++) { pv[h] = D.pv[h] / 1000 * kWp; Gsum += pv[h]; }
  const meanDay = Dsum / 365, batKWh = meanDay * s.days, cap = batKWh * D.dod, r = Math.sqrt(D.eff);
  const soc = new Float64Array(n), imp = new Float64Array(n), exp = new Float64Array(n), direct = new Float64Array(n), dis = new Float64Array(n);
  let q = 0, served = 0;
  for (let h = 0; h < n; h++) {
    const g = pv[h], l = dem[h], dir = Math.min(g, l);
    let surplus = g - dir, deficit = l - dir, ds = 0;
    if (cap > 0) {
      const ch = Math.min(surplus * r, cap - q); q += ch; surplus -= ch / r;
      ds = Math.min(deficit, q * r); q -= ds / r; deficit -= ds;
    }
    direct[h] = dir; dis[h] = ds; served += dir + ds;
    imp[h] = deficit; exp[h] = Math.max(surplus, 0); soc[h] = cap > 0 ? q / cap : 0;
  }
  const mon = Array.from({ length: 12 }, () => ({ pv: 0, d: 0, met: 0 }));
  const day = Array.from({ length: 365 }, () => ({ d: 0, met: 0 }));
  for (let h = 0; h < n; h++) {
    const m = mon[C.month[h]]; m.pv += pv[h]; m.d += dem[h]; m.met += direct[h] + dis[h];
    const y = day[C.doy[h]]; y.d += dem[h]; y.met += direct[h] + dis[h];
  }
  return { dem, pv, soc, imp, exp, direct, dis, Dsum, Gsum, kWpReq, kWp, area: kWp * D.m2, meanDay, batKWh,
           SS: served / Dsum, SC: Gsum ? served / Gsum : 0, peak: Math.max(...dem), mon, day };
}

if (typeof module !== 'undefined') module.exports = { buildCalendar, vehicles, simulate };
