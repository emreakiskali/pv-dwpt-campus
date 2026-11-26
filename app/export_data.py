"""Export the hourly inputs the interactive app needs from model.py.

Writes app/data.json: PV output per kWp for each of the 8,760 hours (Wh, rounded), the campus
traffic profile and the other model inputs. The app recomputes everything else in the browser.

Usage (from the repository root):  python app/export_data.py
"""
import contextlib, io, json, os, runpy, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.argv = ["model.py", "--out", os.path.join("app", "_run")]
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path("model.py")
P, idx = g["P"], g["idx"]
data = dict(
    pv=[int(round(v * 1000)) for v in g["pv1"].values],   # Wh per kWp per hour
    prof=list(g["PROF"]), weekend=P["weekend_factor"], brk=P["break_factor"], peak=P["peak_veh"],
    e_full=g["e_full"], e_sel=g["e_sel"], yield_=P["annual_yield"], m2=P["m2_per_kWp"],
    eff=P["bat_eff"], dod=P["bat_dod"], dow0=int(idx[0].dayofweek),
)
with open(os.path.join("app", "data.json"), "w") as f:
    json.dump(data, f, separators=(",", ":"))
print("wrote app/data.json")
