# Quantifying and Forecasting the Impact of the 2025 U.S. Government Shutdown on New York–Metro Flight Delays

**Pranish Uprety** · Advisor: **Dr. Sushil Poudel**
Department of Computer Science, Caldwell University · STEM Advance, Summer 2026

The 2025 U.S. government shutdown (Oct 1 – Nov 12, 2025) left air-traffic
controllers working without pay, and on Nov 7 the FAA ordered flight cuts at
40 high-traffic airports. This project measures what that did to departures at
Newark (EWR), JFK and LaGuardia (LGA), compared with the same months of 2024.

## Key results

| Question | Method | Result |
|---|---|---|
| Did delays rise? | Daily mean delay, 2024 vs. 2025, Welch t-test | JFK +107%, LGA +149% (p < 0.001); EWR +27% (p = 0.07, n.s.) |
| What did it cost? | 3 baselines × A4A $100.76 per delay minute | ≈ $41M extra airline cost ($40.5M–$42.4M); weather does not explain it |
| Was it predictable? | Gradient-boosted forecast using calendar, schedule and shutdown flag only | R² 0.12–0.23 vs. ≤ 0.09 for a normal-year baseline |
| Did airports become linked? | 1-hour lagged correlation, Newark → JFK | r = 0.19 (normal 2024) vs. 0.55 (2025 shutdown) |

Cancellations after the FAA cuts reached 3.3–4.8% (vs. ≤ 0.4% in 2024).

## Repository layout

```
analysis/   analysis scripts, result CSVs and figures
data/       data-source notes (data/README.md) and a sample METAR file
demo/       live OpenSky flight-map demo (server.py + index.html)
poster/     Fall Research Day 2026 poster (final PDF/PPTX) and its build scripts
*.tex       IEEE paper draft, literature review, proposals, progress reports
references.bib
```

Main scripts:

- `analysis/shutdown_poc.py` – raw 2024 vs. 2025 comparison, normal-expectation model, cost estimate
- `analysis/shutdown_predict.py` – leakage-free shutdown forecast (train 2024 + Oct 2025, test Nov 2025)
- `analysis/propagation_evidence.py` – network coupling on the Jan 2023 NOTAM outage
- `analysis/shutdown_evidence.py`, `analysis/fig_finance.py` – paper figures
- `analysis/poster_graphs.py` – poster charts
- `poster/build_poster_36x24.py` – builds the 36" × 24" poster

## Reproducing

The raw BTS on-time files are not stored here (each month is ~30 MB). Download
them from the [BTS On-Time portal](https://www.transtats.bts.gov/ONTIME/) and
save them as:

```
data/01_delay_ontime/BTS_OnTime_2024_10.zip
data/01_delay_ontime/BTS_OnTime_2024_11.zip
data/01_delay_ontime/BTS_OnTime_2025_10.zip
data/01_delay_ontime/BTS_OnTime_2025_11.zip
analysis/bts_2023_01/   (extracted January 2023 CSV, for propagation_evidence.py)
```

Then, from the repository root:

```
pip install -r requirements.txt
python analysis/shutdown_poc.py
python analysis/shutdown_predict.py
python analysis/poster_graphs.py
python poster/build_poster_36x24.py poster/Fall_Research_Day_2026_Poster_36x24_final.pptx
```

All data sources, download links and the reference documents used are listed in
[`data/README.md`](data/README.md).
