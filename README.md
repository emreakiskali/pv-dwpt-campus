# pv-dwpt-campus

Hourly, year-long comparison of photovoltaic (PV) generation with the energy required by a
dynamic wireless charging (DWC) system for electric vehicles on a university campus
(Marmara University, Göztepe Campus, Istanbul).

This repository contains the model behind the conference paper

> Akıskalıoğlu, E. *Elektrikli araçların dinamik kablosuz şarjı için gereken enerjinin
> fotovoltaik üretimle karşılanması: Kampüs örneği* (Meeting the energy required for dynamic
> wireless charging of electric vehicles with photovoltaic generation: A campus case study).

The model is a single script. It is intentionally simple: every input is listed at the top of
`model.py`, and running the script regenerates every number and figure reported in the paper.

**Interactive version:** https://emreakiskali.github.io/pv-dwpt-campus/ runs the same model in the
browser, with an animated view of the campus road network, the charging strips, PV generation and
storage. Its sources are in [`app/`](app/README.md) and the built page is `docs/index.html`.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python model.py              # English figure labels
python model.py --lang tr    # Turkish figure labels (files get a _tr suffix)

# sensitivity to the transposition model (write to separate folders)
python model.py --sky isotropic --out results_isotropic
python model.py --sky perez     --out results_perez
```

Outputs are written to `results/` (change with `--out`):

| File | Content |
|---|---|
| `results.json` | All inputs and all numerical results |
| `fig1_profiles.png` | Mean weekday PV generation and DWC energy demand in March, June and December |
| `fig2_monthly.png` | Monthly PV generation and DWC energy demand for the required PV size |
| `fig3_sensitivity.png` | Share of demand met by PV (self-sufficiency) versus PV size and storage capacity |

`--lang` only changes the figure labels. The numerical results do not depend on it.
`--sky` selects the model that converts horizontal irradiance to the tilted PV plane
(`haydavies`, the default used in the paper; `isotropic` and `perez` for the sensitivity check).
With these three models the self-sufficiency results differ by at most about one percentage point.

## What the model does

1. **DWC energy demand.** The energy delivered to vehicles in a published SUMO scenario is
   divided by the number of vehicles and the transfer efficiency, which gives the grid-side
   energy per vehicle passage. This is multiplied by the number of vehicles in each hour of the
   year and by the EV share.
2. **PV generation.** Hourly clear-sky global and diffuse irradiance on a horizontal surface at the
   campus is computed with pvlib (Ineichen model), and each month is scaled so that its mean
   equals the published monthly mean for Istanbul (Ekici 2016, Figs. 2 and 3, horizontal
   surface). The beam component is the difference of the two, and the irradiance on the
   south-facing, 30° tilted panel plane is computed with the Hay–Davies transposition model.
   Finally the hourly plane-of-array irradiance is scaled so that the annual total equals the
   published PVsyst yield (1,311 kWh/kWp, i.e. a constant performance ratio).
   The Hay–Davies model is used because its annual plane-of-array irradiation (1,591 kWh/m²)
   is closest to the value implied by the published yield and performance ratio
   (1,311 / 0.812 ≈ 1,615 kWh/m²).
3. **Hourly matching.** Demand and generation are compared hour by hour over 8,760 hours, with
   with and without storage (a stationary battery next to the PV system; vehicle batteries are
   not modelled). Surplus PV charges the storage first and is exported afterwards; deficits are
   drawn from the storage first and from the grid afterwards.
4. **Sensitivity analysis.** Thirty synthetic years are generated in which each day's PV output is
   scaled by a random factor while monthly totals are kept unchanged.

Reported indicators: annual energy demand, the PV size whose annual output equals annual demand
("required PV size"), self-sufficiency (share of demand met by PV, directly or through the
storage) and self-consumption (share of PV output used by the DWC system).

## Inputs and their sources

| Input | Value | Source |
|---|---|---|
| Vehicles in the peak hour (8 March 2024, 12:00–13:00) | 103 | Akıskalıoğlu & Atmaca (2026) |
| Energy delivered, full coverage (3.81 km, 182 strips) | 15.225 kWh | Akıskalıoğlu & Atmaca (2026) |
| Energy delivered, selective layout (0.39 km, 5 strips) | 1.94 kWh | Akıskalıoğlu & Atmaca (2026) |
| Charging power / efficiency | 10 kW / 90% | Akıskalıoğlu & Atmaca (2026) |
| Monthly mean global irradiance, horizontal surface, Istanbul | 12 values in `model.py` (53.9–264.9 W/m²) | Ekici (2016), Fig. 2, read from the chart |
| Monthly mean diffuse irradiance, horizontal surface, Istanbul | 12 values in `model.py` (17.5–102.3 W/m²) | Ekici (2016), Fig. 3, read from the chart |
| Annual PV yield (mono-Si, Istanbul, PVsyst, 36° tilt, PR 81.2%) | 1,311 kWh/kWp | Ekici (2016), Table 4 |
| Transposition model (horizontal → tilted plane) | Hay–Davies | Hay & Davies (1980), as implemented in pvlib |
| Grid emission factor (distribution level, 2022) | 0.474 tCO₂/MWh | Ministry of Energy and Natural Resources of Türkiye |

The emission factor is not part of the script; the emission figures in the paper are obtained by
multiplying the energy results by this factor.

## Assumptions

The following inputs are **assumptions**, not measurements. They are the main limitation of the
study and are stated here so that they can be replaced with measured data.

| Assumption | Value |
|---|---|
| Hourly weekday campus traffic profile (`PROF`), normalised to 1.0 at 12:00 | 24 values in `model.py` |
| Weekend traffic factor | 0.45 |
| Summer-break traffic factor (July–August) | 0.50 |
| EV share scenarios | 10, 25, 50, 100% |
| PV tilt / azimuth | 30° / south |
| Panel area per unit capacity | 5.0 m²/kWp |
| Storage (stationary battery) round-trip efficiency / depth of discharge | 90% / 90% |
| Daily coefficient of variation of PV output in the sensitivity analysis | 0.45 (winter) to 0.12 (summer), by month |

Further simplifications: the energy per vehicle comes from a single 600-s peak-hour SUMO
simulation and is assumed constant through the day; the PV series is a scaled clear-sky profile
rather than a measured typical meteorological year; the monthly irradiance values are read from
the bar charts of a single source; the published yield refers to a 36° tilt, whereas the model uses
30° (the difference in annual plane-of-array irradiation is below 1%); standby losses of the
charging strips are ignored; within-hour power peaks are averaged out.

## Reproducibility

- The results in `results/` were produced with Python 3.12 and the package versions pinned in
  `requirements.txt` (pvlib 0.16.1, pandas 3.0.5, numpy 2.5.3, matplotlib 3.11.2).
- The calendar of 2026 is used to assign weekdays and weekends.
- The random seed of the sensitivity analysis is fixed (`42`).
- `results/` contains the outputs of a run with these versions. Re-running the script should
  reproduce `results.json` to within floating-point precision. Figures may differ by a few
  pixels between machines because of font rendering.

## References

- Akıskalıoğlu, E., & Atmaca, M. (2026). Assessing dynamic wireless charging infrastructure using
  real-time traffic data: A Simulation of Urban Mobility approach. *International Journal of
  Low-Carbon Technologies, 21*, ctag130. https://doi.org/10.1093/ijlct/ctag130
- Ekici, B. B. (2016). Variation of photovoltaic system performance due to climatic and
  geographical conditions in Turkey. *Turkish Journal of Electrical Engineering & Computer
  Sciences, 24*(6), 4693–4706. https://doi.org/10.3906/elk-1404-341
- Hay, J. E., & Davies, J. A. (1980). Calculations of the solar radiation incident on an inclined
  surface. In J. E. Hay & T. K. Won (Eds.), *Proceedings of the First Canadian Solar Radiation
  Data Workshop* (p. 59). Ministry of Supply and Services Canada.
- Holmgren, W. F., Hansen, C. W., & Mikofski, M. A. (2018). pvlib python: A python package for
  modeling solar energy systems. *Journal of Open Source Software, 3*(29), 884.

## License

MIT, see `LICENSE`.

---

## Türkçe özet

Bu depo, Marmara Üniversitesi Göztepe Kampüsü'nde elektrikli araçların dinamik kablosuz şarjı
için gereken enerjinin fotovoltaik (PV) üretimle ne ölçüde karşılanabileceğini bir yıl boyunca
saatlik olarak hesaplayan modeli içerir. Bildirideki tüm sayılar ve şekiller `model.py` dosyasının
çalıştırılmasıyla yeniden üretilebilir. Bildirideki Türkçe şekiller için:

```bash
python model.py --lang tr
```

Saatlik trafik profili ile hafta sonu ve yaz tatili katsayıları ölçüme değil varsayıma
dayanmaktadır; tüm varsayımlar yukarıdaki "Assumptions" tablosunda listelenmiştir.

Bildiride kullanılan Türkçe terimler: *PV karşılama oranı* (self-sufficiency, öz yeterlilik),
*yerinde kullanım oranı* (self-consumption, öz tüketim), *gerekli PV gücü* (yıllık üretimi yıllık
ihtiyaca eşit olan PV gücü) ve *depolama* (PV sisteminin yanına kurulan sabit batarya).
