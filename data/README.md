# Data Sources — Flight Delay Prediction & Shutdown Proof of Concept

Collected for: predicting flight delays (NYC metro / Northeast corridor) and
validating the model on the 2025 government shutdown.

Each folder below maps to one or more **model factors** from
`model_and_evaluation_plan.tex`. Files marked **[downloaded]** are already in
this folder; others are links with access notes.

---

## 01_delay_ontime — core delay + schedule data (the target variable)
**Factor groups:** target (delay minutes), temporal, local history, network, operational.

- **BTS Reporting Carrier On-Time Performance** — every U.S. domestic flight:
  scheduled/actual times, DepDelay, ArrDelay, cancellations, and delay-cause
  breakdown (CarrierDelay, WeatherDelay, NASDelay, SecurityDelay, LateAircraftDelay).
  - Portal: https://www.transtats.bts.gov/ONTIME/
  - Direct monthly ZIPs (pattern):
    `https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_YYYY_M.zip`
  - **[downloaded]** `BTS_OnTime_2025_10.zip`, `BTS_OnTime_2025_11.zip` — the 2025
    shutdown window (test period, shutdown began Oct 1).
  - **[downloaded]** `BTS_OnTime_2024_10.zip`, `BTS_OnTime_2024_11.zip` — same months,
    prior (normal) year, the clean control/baseline.
  - Also have January 2023 already extracted under `../analysis/bts_2023_01/`
    (used for the first propagation experiment).
- **BTS T-100 Market/Segment** — passengers, departures, seats per airport
  (for traffic volume and the economic/passenger-impact factor).
  - https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FMF

> Note: the `WeatherDelay` column inside BTS is the simple weather control
> (Option chosen with advisor); METAR below is the richer alternative.

---

## 02_weather — weather controls
**Factor group:** weather (wind, visibility, ceiling, precipitation, conditions).

- **Iowa Environmental Mesonet (IEM) ASOS/METAR archive** — historical hourly
  airport weather, free, no login, CSV via HTTP GET.
  - Docs: https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?help
  - Download UI: https://mesonet.agron.iastate.edu/request/download.phtml?network=NF__ASOS
  - **[downloaded]** `SAMPLE_METAR_EWR_JFK_LGA_2025-11-01_to_03.csv` — proves the
    pipeline (temp, wind, visibility, precip, weather codes for the 3 NYC airports
    over the worst shutdown weekend).
  - Ready-to-use URL template (swap stations/dates):
    ```
    https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=EWR&station=JFK&station=LGA&data=tmpf&data=sknt&data=vsby&data=p01i&data=wxcodes&year1=2025&month1=10&day1=1&year2=2025&month2=11&day2=15&tz=Etc/UTC&format=onlycomma&missing=M&trace=T&direct=yes&report_type=3
    ```
- NOAA Local Climatological Data (alternative): https://www.ncei.noaa.gov/cdo-web/datatools/lcd

---

## 03_traffic — air traffic volume / congestion
**Factor group:** traffic / congestion.

- **OpenSky Network** — ADS-B aircraft positions (already used live in the demo).
  - Live REST API (no historical): used in `../demo/server.py`.
  - **Historical** via Trino SQL interface — FREE for university-affiliated
    researchers (apply with Caldwell email):
    - Apply: https://opensky-network.org/my-opensky/request-data
    - Docs: https://openskynetwork.github.io/opensky-api/trino.html
    - Python lib: `pip install pyopensky` (https://github.com/open-aviation/pyopensky)
  - Note: OpenSky has NO schedules/delays/passengers — pair it with BTS.
- Traffic volume can also be derived directly from BTS (flights per airport-hour).

---

## 04_staffing_shutdown — staffing & disruption factor (the shutdown signal)
**Factor group:** staffing / disruption (Option A: explicit input factor).

- **[downloaded]** `FAA-Emergency-Order-2025-11-06.pdf` — the FAA order mandating
  flight cuts at 40 "High Impact Airports" during the shutdown (lists the airports).
- **[downloaded]** `FAA-Controller-Workforce-Plan-FY2025.pdf` — controller staffing
  levels, attrition, and prior shutdown impacts (2019, COVID).
- **FAA OPSNET / ASPM** — official ground stops, ground delay programs (GDP),
  EDCT delays, delay-by-cause. Finalized data is public 20 days after month-end
  (no login). This is the source for ground-stop / GDP factors.
  - https://aspm.faa.gov/  (OPSNET Delays modules; "Data Download")
  - Manual: https://aspmhelp.faa.gov/index/OPSNET_Manual.html
- **Staffing-trigger reporting** (context): ~393 staffing triggers during the
  2025 shutdown; 98 over Nov 1–3 alone. Reported via FAA operations plans /
  press (CNN, AP). Use as the daily shutdown-intensity proxy.

---

## 05_finance_cost — economic / cost-of-delay factor
**Factor group:** economic (convert delay minutes -> dollars).

- **Airlines for America (A4A) cost of delay** — standard per-minute figure.
  - https://airlines.org/dataset/u-s-passenger-carrier-delay-costs/
  - **Key number:** CY2024 = **$100.76 per block minute** (crew $35.23, fuel
    $33.06, maintenance $18.30, ownership $10.19, other $3.98).
  - FAA fully-allocated alternative: ~$148.60/min (incl. capital).
- **[downloaded]** `ACI-Measuring-Aircraft-Operating-Costs-and-Delay.pdf` —
  methodology white paper for turning operating minutes into cost.

---

## 06_benchmarks — external dataset/benchmark for the model
**Use:** comparison benchmark + a richer multi-modal feature set.

- **Aeolus: Multi-structural Flight Delay Dataset** (NeurIPS 2025 D&B) — 50M+
  flights in tabular + flight-chain (sequential) + flight-network (graph) form,
  with strict temporal-leakage prevention. Directly relevant as a benchmark and
  feature template.
  - **[downloaded]** `Aeolus-Flight-Delay-Dataset-2025.pdf`, `Aeolus-arxiv-2510.26616.pdf`
  - Code: https://github.com/Flnny/Delay-data
  - Data (Kaggle): https://www.kaggle.com/datasets/flnny123/mfddmulti-modal-flight-delay-dataset
  - License: CC BY-NC 4.0 (academic use).

---

## 07_disruption_refs — real disruption events for validation
**Use:** external counterfactual benchmarks (Phase 2.4 / proof of concept).

- **[downloaded]** `ICAO-NOTAM-Outage-Jan2023-IP06.pdf` — timeline of the Jan 11,
  2023 nationwide ground stop (a clean single-shock test event).
- **Richmond Fed (2025)** — difference-in-differences on 76M flight ops; isolates
  ~1M extra delay work-hours / ~$66M from the 2025 shutdown. External counterfactual
  to validate the model's predicted shutdown impact.
  - https://www.richmondfed.org/publications/research/economic_brief/2025/eb_25-45
- **Center for Transportation Policy (2026)** — "Stabilizing the Skies": >9,000
  cancellations, 6M+ passengers, ~$7.25B; argues blunt 10% cuts did more harm than
  good and recommends a targeted, data-driven strategy (motivation for our model).
  - https://transportpolicies.com/news-resources/new-ctp-report-puts-faa-actions-during-2025-government-shutdown-under-the-microscope/
- **US DOT NOTAM testimony**: https://www.transportation.gov/federal-aviation-administrations-notam-system-failure-and-its-impacts-resilient-national-airspace

---

## Quick mapping: model factor -> where to get it
| Factor group | Source | Folder |
|---|---|---|
| Target delay, schedules, delay causes | BTS On-Time | 01 |
| Temporal (hour, dow, holiday) | derived from BTS dates | 01 |
| Local history / network lags | derived from BTS panel | 01 |
| Traffic / congestion | BTS counts; OpenSky | 01 / 03 |
| Weather | IEM METAR; BTS WeatherDelay | 02 / 01 |
| Operational (late aircraft, NAS) | BTS delay-cause columns | 01 |
| Staffing / shutdown | FAA order, OPSNET, staffing triggers | 04 |
| Economic (cost of delay) | A4A $100.76/min; ACI method | 05 |
| Benchmark / extra features | Aeolus | 06 |
| Validation events | Richmond Fed, CTP, ICAO NOTAM | 07 |

---

### Access notes
- BTS and IEM: fully open, scriptable now.
- OpenSky historical (Trino): needs a free academic account — **apply early**,
  approval can take a few days; use your Caldwell email.
- Kaggle (Aeolus data): needs a free Kaggle account to download the large files.
- FAA OPSNET finalized data: open 20 days after month-end (no login).
