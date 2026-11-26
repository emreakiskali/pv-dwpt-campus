# Interactive app

`docs/index.html` is a single-file web page that runs the model in the browser. It shows the
campus road network with the charging strips, PV generation, the charging energy demand, storage
and grid flows hour by hour, and recomputes the full year (8,760 hours) whenever a setting
changes: layout (full coverage / selective), EV share, PV size and storage capacity.

| File | Content |
|---|---|
| `model.js` | JavaScript port of the hourly matching in `model.py` (demand, PV, storage) |
| `template.html` | Page layout, charts and the animated campus scene |
| `campus.json` | Road centre lines of Göztepe Campus with the strip coverage of both layouts, traced from the SUMO network figures of Akıskalıoğlu & Atmaca (2026), Figs. 5–6 (`m_per_px` from the 100 m scale bar) |
| `export_data.py` | Writes `data.json` (hourly PV per kWp and the traffic inputs) from `model.py` |
| `build.py` | Assembles `docs/index.html` |

Rebuild after changing the model:

```bash
python app/export_data.py
python app/build.py
```

The JavaScript port reproduces the Python results: for full coverage and 100% EV, 55.8 MWh/year,
42.5 kWp and a self-sufficiency of 63.8% without storage, 78.0% with half a day of storage and
98.6% with twice the PV size and one day of storage (largest difference over the 20 sensitivity
cases below 2 × 10⁻⁵, from rounding the hourly PV values to whole Wh).

Individual vehicles on the map are representative (their number follows the hourly traffic), and
the PV array is drawn to scale at a representative position.
