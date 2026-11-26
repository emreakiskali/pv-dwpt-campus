"""PV-supplied DWPT on Göztepe Campus: hourly matching of PV generation and DWPT energy demand.
All inputs are documented in P; outputs are results.json and three figures.

Usage:  python model.py [--lang en|tr] [--out results] [--sky haydavies|isotropic|perez]
        --lang only changes the figure labels (tr adds a _tr suffix to the figure files);
        the numerical results do not depend on it.
        --sky selects the transposition model used to convert horizontal irradiance to the
        tilted PV plane (default: haydavies; the other two are for the sensitivity check)."""
import argparse, json, os, numpy as np, pandas as pd, pvlib
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--lang", choices=["en", "tr"], default="en", help="language of the figure labels")
ap.add_argument("--out", default="results", help="output directory")
ap.add_argument("--sky", choices=["haydavies", "isotropic", "perez"], default="haydavies",
                help="transposition model, horizontal -> tilted plane")
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
SUF = "" if args.lang == "en" else "_tr"
outpath = lambda name: os.path.join(args.out, name)
L = {
    "en": dict(months3=[(3, "March"), (6, "June"), (12, "December")], pv_supply="PV supply", demand="DWC energy demand",
               hour="Hour of day", e_hour="Energy (kWh/h)", pv_gen="PV generation",
               months=["J","F","M","A","M","J","J","A","S","O","N","D"], e_month="Energy (kWh/month)",
               bat=lambda n: "No storage" if n == 0 else f"Storage = {n}% of mean daily demand",
               pv_size="PV size / required PV size (–)", ss="Share of demand met by PV (%)"),
    "tr": dict(months3=[(3, "Mart"), (6, "Haziran"), (12, "Aralık")], pv_supply="PV üretimi", demand="Dinamik kablosuz şarj enerji ihtiyacı",
               hour="Günün saati", e_hour="Enerji (kWh/sa)", pv_gen="PV üretimi",
               months=["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"], e_month="Enerji (kWh/ay)",
               bat=lambda n: "Depolama yok" if n == 0 else
                   f"Depolama = ortalama günlük ihtiyacın %{n}" + {25: "'i", 50: "'si", 100: "'ü"}[n],
               pv_size="PV gücü / gerekli PV gücü (–)", ss="PV karşılama oranı (%)"),
}[args.lang]

P = dict(
    lat=40.987, lon=29.062, alt=30, tz="Europe/Istanbul",
    tilt=30, azimuth=180,
    # IJLCT (Akıskalıoğlu & Atmaca 2026): 103 veh, 12:00-13:00, 8 Mar 2024
    peak_veh=103, E_full_kWh=15.225, E_sel_kWh=1.94, eta=0.90,
    # Ekici 2016 (TJEECS 24:4693), Istanbul. Monthly mean irradiance on a HORIZONTAL surface (W/m2),
    # read from the bar charts: Fig. 2 (global) and Fig. 3 (diffuse). Jan..Dec.
    monthly_ghi_Wm2=[60.8,91.2,138.4,185.7,232.6,262.2,264.9,231.7,178.5,115.4,73.1,53.9],
    monthly_dhi_Wm2=[17.9,33.1,48.7,70.6,83.0,98.1,102.3,101.5,74.2,49.9,26.0,17.5],
    sky=args.sky,                  # transposition model to the tilted plane
    annual_yield=1311.0,           # kWh/kWp, mono-Si, PR 81.2%, PVsyst at the optimum tilt of 36 deg (Ekici Table 4)
    m2_per_kWp=5.0,                # ~20% module efficiency
    weekend_factor=0.45, break_factor=0.50,  # assumptions (campus)
    bat_eff=0.90, bat_dod=0.90,
)
# assumed weekday campus profile (relative to 12:00 = 1.0); hours 0..23
PROF = np.array([0.03,0.02,0.02,0.02,0.03,0.08,0.20,0.55,0.90,0.85,0.80,0.90,
                 1.00,0.95,0.85,0.85,0.90,0.95,0.70,0.45,0.30,0.20,0.10,0.05])

idx = pd.date_range("2026-01-01", "2026-12-31 23:00", freq="h", tz=P["tz"])
loc = pvlib.location.Location(P["lat"], P["lon"], P["tz"], P["alt"])
cs = loc.get_clearsky(idx, model="ineichen")
sp = loc.get_solarposition(idx)
# 1) hourly horizontal irradiance: clear-sky shape, each month scaled to the published monthly means
hours = np.array([(idx.month == m).sum() for m in range(1, 13)])
ghi, dhi = cs.ghi.copy(), cs.dhi.copy()
for m in range(1, 13):
    sel = idx.month == m
    ghi[sel] = cs.ghi[sel] * P["monthly_ghi_Wm2"][m-1] * hours[m-1] / cs.ghi[sel].sum()
    dhi[sel] = np.minimum(cs.dhi[sel] * P["monthly_dhi_Wm2"][m-1] * hours[m-1] / cs.dhi[sel].sum(), ghi[sel])
# 2) beam component and transposition to the tilted PV plane
dni_extra = pvlib.irradiance.get_extra_radiation(idx)
cosz = np.cos(np.radians(sp.apparent_zenith)).clip(lower=0.087)          # limit at 85 deg zenith
dni = ((ghi - dhi) / cosz).where(sp.apparent_zenith < 90, 0).clip(lower=0)
dni = np.minimum(dni, dni_extra)
airmass = pvlib.atmosphere.get_relative_airmass(sp.apparent_zenith)
poa = pvlib.irradiance.get_total_irradiance(P["tilt"], P["azimuth"], sp.apparent_zenith, sp.azimuth,
                                            dni, ghi, dhi, dni_extra=dni_extra, airmass=airmass,
                                            model=P["sky"])["poa_global"].fillna(0)
# 3) PV output: tilted-plane irradiance scaled to the published annual yield (constant performance ratio)
pv1 = poa / poa.sum() * P["annual_yield"]                                 # kWh per kWp per hour
assert abs(pv1.sum() - P["annual_yield"]) < 1e-6

# traffic
f = np.where(idx.dayofweek >= 5, P["weekend_factor"], 1.0)
f = f * np.where(idx.month.isin([7, 8]), P["break_factor"], 1.0)
veh = P["peak_veh"] * PROF[idx.hour] * f
veh = pd.Series(veh, index=idx)
e_full = P["E_full_kWh"] / P["peak_veh"] / P["eta"]   # grid-side kWh per vehicle
e_sel = P["E_sel_kWh"] / P["peak_veh"] / P["eta"]

def metrics(D, kwp, bat_kWh=0.0):
    pv = pv1.values * kwp; d = D.values
    if bat_kWh == 0:
        direct = np.minimum(pv, d); served = direct.sum()
    else:
        soc = 0.0; cap = bat_kWh * P["bat_dod"]; served = 0.0
        for g, l in zip(pv, d):
            dirc = min(g, l); served += dirc
            surplus = g - dirc; deficit = l - dirc
            ch = min(surplus * P["bat_eff"]**0.5, cap - soc); soc += ch
            dis = min(deficit, soc * P["bat_eff"]**0.5); soc -= dis / P["bat_eff"]**0.5; served += dis
    return dict(SS=served / d.sum(), SC=served / pv.sum() if pv.sum() else 0)

res = {"params": P,
       "ghi_annual_kWh_m2": float(ghi.sum() / 1000), "poa_annual_kWh_m2": float(poa.sum() / 1000),
       "implied_PR": float(P["annual_yield"] / (poa.sum() / 1000)),
       "poa_monthly_kWh_m2": dict(zip(range(1, 13), (poa.groupby(idx.month).sum() / 1000).round(1).tolist())),
       "e_full_kWh_per_veh": e_full, "e_sel_kWh_per_veh": e_sel,
       "annual_veh": float(veh.sum()), "pv_monthly_kWh_per_kWp": dict(zip(range(1,13),
        pv1.groupby(idx.month).sum().round(1).tolist()))}
shares = [0.10, 0.25, 0.50, 1.00]
tab = []
for strat, e in [("full", e_full), ("selective", e_sel)]:
    for s in shares:
        D = veh * s * e
        Dann = D.sum(); kwp_nz = Dann / P["annual_yield"]
        row = dict(strategy=strat, ev_share=s, demand_MWh=Dann/1000, peak_kW=D.max(),
                   kWp_netzero=kwp_nz, area_m2=kwp_nz * P["m2_per_kWp"])
        for lbl, k, b in [("nz", kwp_nz, 0), ("nz_bat", kwp_nz, None)]:
            if b is None:
                b = D.groupby(idx.date).sum().mean() * 0.5  # half of mean daily demand
                row["bat_kWh"] = b
            m = metrics(D, k, b); row[f"SS_{lbl}"] = m["SS"]; row[f"SC_{lbl}"] = m["SC"]
        tab.append(row)
res["table"] = tab
# sensitivity: full, 100% EV, PV size multiplier x battery hours
D100 = veh * e_full
Dann = D100.sum(); base = Dann / P["annual_yield"]; mean_day = D100.groupby(idx.date).sum().mean()
mult = [0.5, 0.75, 1.0, 1.5, 2.0]; bfr = [0, 0.25, 0.5, 1.0]
grid = [[metrics(D100, base*m, mean_day*b)["SS"] for b in bfr] for m in mult]
res["sens"] = dict(mult=mult, bat_frac_of_mean_day=bfr, SS=grid, mean_day_kWh=mean_day)
# monthly balance full 100%
mon = pd.DataFrame({"pv": pv1 * base, "d": D100}).groupby(idx.month).sum()
res["monthly_full100"] = mon.round(1).to_dict()
# daily-profile correlation
res["corr_hourly"] = float(np.corrcoef(pv1.values, D100.values)[0, 1])
json.dump(res, open(outpath("results.json"), "w"), indent=1, default=float)

# ---------- figures ----------
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
C1, C2 = "#2a6f97", "#e09f3e"
# Fig1 typical weekday profiles Mar/Jun/Dec
fig, axs = plt.subplots(1, 3, figsize=(9, 2.8), sharey=True)
for ax, (m, name) in zip(axs, L["months3"]):
    sel = (idx.month == m) & (idx.dayofweek < 5)
    pvh = (pv1[sel] * base).groupby(idx[sel].hour).mean()
    dh = D100[sel].groupby(idx[sel].hour).mean()
    ax.fill_between(pvh.index, pvh.values, color=C2, alpha=.35, label=L["pv_supply"])
    ax.plot(dh.index, dh.values, color=C1, lw=2, label=L["demand"])
    ax.set_title(name); ax.set_xlabel(L["hour"]); ax.set_xticks([0,6,12,18,23])
axs[0].set_ylabel(L["e_hour"]); axs[0].legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(outpath(f"fig1_profiles{SUF}.png"), dpi=300)
# Fig2 monthly balance
fig, ax = plt.subplots(figsize=(6, 3))
x = np.arange(12); w = .38
ax.bar(x - w/2, mon.pv, w, color=C2, label=L["pv_gen"])
ax.bar(x + w/2, mon.d, w, color=C1, label=L["demand"])
ax.set_xticks(x, L["months"]); ax.set_ylabel(L["e_month"])
ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2); ax.spines[["top","right"]].set_visible(False)
fig.tight_layout(); fig.savefig(outpath(f"fig2_monthly{SUF}.png"), dpi=300)
# Fig3 sensitivity
fig, ax = plt.subplots(figsize=(5, 3.2))
for j, b in enumerate(bfr):
    ax.plot(mult, [100*grid[i][j] for i in range(len(mult))], marker="o",
            label=L["bat"](int(b*100)))
ax.set_xlabel(L["pv_size"]); ax.set_ylabel(L["ss"])
ax.legend(frameon=False, fontsize=7); ax.grid(alpha=.3)
if args.lang == "tr": ax.set_xticks(mult, [str(v).replace(".", ",") for v in mult])
ax.spines[["top","right"]].set_visible(False)
fig.tight_layout(); fig.savefig(outpath(f"fig3_sensitivity{SUF}.png"), dpi=300)
print(json.dumps({k: res[k] for k in ["e_full_kWh_per_veh","e_sel_kWh_per_veh","annual_veh","corr_hourly"]}, indent=1))
print(pd.DataFrame(tab).round(3).to_string())
print(pd.DataFrame(grid, index=mult, columns=bfr).round(3))
print(mon.round(0).T)

# ---------- robustness: day-to-day cloud variability (monthly totals preserved) ----------
rng = np.random.default_rng(42)
cv = np.array([.45,.42,.38,.30,.22,.15,.12,.12,.18,.30,.40,.45])  # assumed daily CV by month
days = pd.Index(idx.date)
out = []
for r in range(30):
    pvr = pv1.copy()
    for m in range(1, 13):
        sel = idx.month == m
        ud = pd.unique(days[sel])
        k = np.clip(rng.gamma(1/cv[m-1]**2, cv[m-1]**2, len(ud)), 0.05, None)
        k = k / k.mean()
        fac = pd.Series(k, index=ud).reindex(days[sel]).values
        pvr[sel] = pv1[sel].values * fac
        pvr[sel] *= pv1[sel].sum() / pvr[sel].sum()
    pv_b = pv1.copy(); pv1[:] = pvr.values
    out.append([metrics(D100, base*m, mean_day*b)["SS"] for m, b in [(1,0),(1,.5),(2,1)]])
    pv1[:] = pv_b.values
out = np.array(out)
res["stoch"] = dict(cases=["1x,0bat","1x,0.5day","2x,1day"], mean=out.mean(0).tolist(),
                    p5=np.percentile(out,5,0).tolist(), p95=np.percentile(out,95,0).tolist())
json.dump(res, open(outpath("results.json"), "w"), indent=1, default=float)
print(res["stoch"])
