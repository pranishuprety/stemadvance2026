"""
HONEST predict-the-interruption test (no leakage).

Earlier version used the airport's own delay from the previous 1-3 hours as
inputs, so the model just copied "delay now ~ delay an hour ago" and its line
hugged the actuals (looked fake). This version forecasts with NO peeking: it
uses only information known ahead of time -- calendar, scheduled traffic, and a
shutdown/disruption factor -- so the prediction is a real forecast, not a copy.

  - Features: hour, day-of-week, scheduled flights that hour, shutdown factor.
             (NO recent-delay inputs of any airport.)
  - Train : ALL of 2024 (shutdown=0) + October 2025 (shutdown=1).
  - Test  : November 2025 (unseen), which contains the FAA flight-cut peak.
  - Baselines to beat: (a) naive climatology = average delay by hour/day-of-week
    learned from 2024 only (a "normal year"); the model must beat this to prove
    the disruption factor adds real predictive value.

Outputs:
  - shutdown_predict_results.csv
  - shutdown_predict_vs_actual.png
"""
import zipfile
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA_DIR = "data/01_delay_ontime"
ZIPS = {
    2024: [f"{DATA_DIR}/BTS_OnTime_2024_10.zip", f"{DATA_DIR}/BTS_OnTime_2024_11.zip"],
    2025: [f"{DATA_DIR}/BTS_OnTime_2025_10.zip", f"{DATA_DIR}/BTS_OnTime_2025_11.zip"],
}
CORRIDOR = ["EWR", "JFK", "LGA", "BOS", "PHL", "DCA", "IAD", "BWI"]
NYC_METRO = ["EWR", "JFK", "LGA"]
USECOLS = ["FlightDate", "Origin", "CRSDepTime", "DepDelayMinutes", "Cancelled"]

SHUTDOWN_START = pd.Timestamp("2025-10-01")
SHUTDOWN_END = pd.Timestamp("2025-11-13")


def load_zip_csv(path):
    with zipfile.ZipFile(path) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(name) as f:
            return pd.read_csv(f, usecols=USECOLS, low_memory=False)


def load_year(year):
    df = pd.concat([load_zip_csv(p) for p in ZIPS[year]], ignore_index=True)
    df = df[df["Origin"].isin(CORRIDOR)].copy()
    df = df[df["Cancelled"] == 0]
    df = df.dropna(subset=["DepDelayMinutes", "CRSDepTime"])
    hr = (df["CRSDepTime"].astype(int) // 100).clip(0, 23)
    df["ts"] = pd.to_datetime(df["FlightDate"]) + pd.to_timedelta(hr, unit="h")
    return df


def panels(df):
    """mean delay and scheduled-flight counts per airport-hour."""
    mean_p = (df.groupby(["ts", "Origin"])["DepDelayMinutes"].mean()
                .unstack("Origin").sort_index())
    cnt_p = (df.groupby(["ts", "Origin"])["DepDelayMinutes"].size()
               .unstack("Origin").sort_index())
    idx = pd.date_range(mean_p.index.min(), mean_p.index.max(), freq="h")
    mean_p = mean_p.reindex(idx).fillna(0.0)
    cnt_p = cnt_p.reindex(idx).fillna(0.0)
    for a in CORRIDOR:
        if a not in mean_p:
            mean_p[a] = 0.0; cnt_p[a] = 0.0
    return mean_p, cnt_p


def features(mean_p, cnt_p, target, shutdown_year):
    f = pd.DataFrame(index=mean_p.index)
    f["hour"] = f.index.hour
    f["dow"] = f.index.dayofweek
    f["sched_flights"] = cnt_p[target]                       # known ahead of time
    if shutdown_year:
        f["shutdown"] = ((f.index >= SHUTDOWN_START) &
                         (f.index <= SHUTDOWN_END)).astype(int)
    else:
        f["shutdown"] = 0
    f["y"] = mean_p[target]
    return f, ["hour", "dow", "sched_flights", "shutdown"]


def mk():
    return HistGradientBoostingRegressor(max_depth=4, learning_rate=0.05,
                                         max_iter=400, l2_regularization=1.0,
                                         random_state=0)


print("Loading BTS 2024 + 2025 ...")
m24, c24 = panels(load_year(2024))
m25, c25 = panels(load_year(2025))

rows, plot = [], {}
for a in NYC_METRO:
    f24, cols = features(m24, c24, a, shutdown_year=False)
    f25, _ = features(m25, c25, a, shutdown_year=True)
    both = pd.concat([f24, f25]).dropna()
    is25 = both.index.year == 2025
    train = both[(~is25) | (is25 & (both.index.month == 10))]
    test = both[is25 & (both.index.month == 11)]

    # honest forecast (calendar + traffic + shutdown factor, NO delay lags)
    model = mk().fit(train[cols], train["y"])
    pred = model.predict(test[cols])

    # naive climatology baseline: mean delay by (hour, dow) from 2024 only
    clim = (f24.dropna().groupby(["hour", "dow"])["y"].mean())
    base = test.apply(lambda r: clim.get((int(r["hour"]), int(r["dow"])),
                                         f24["y"].mean()), axis=1).values

    rows.append(dict(airport=a,
        mae_model=mean_absolute_error(test["y"], pred),
        mae_naive=mean_absolute_error(test["y"], base),
        r2_model=r2_score(test["y"], pred),
        r2_naive=r2_score(test["y"], base)))
    plot[a] = (test.index, test["y"].values, pred, base)

res = pd.DataFrame(rows)
res.to_csv("analysis/shutdown_predict_results.csv", index=False)
print("\n=== Forecast Nov 2025 (unseen), no leakage ===")
print(res.to_string(index=False, float_format=lambda v: f"{v:.3f}"))

fig, axes = plt.subplots(len(NYC_METRO), 1, figsize=(9, 7.5), sharex=True)
for ax, a in zip(axes, NYC_METRO):
    idx, y, p, b = plot[a]
    dy = pd.Series(y, index=idx).resample("D").mean()
    dp = pd.Series(p, index=idx).resample("D").mean()
    db = pd.Series(b, index=idx).resample("D").mean()
    ax.plot(dy.index, dy.values, label="actual", color="#ef4444", lw=1.9)
    ax.plot(dp.index, dp.values, label="model forecast (calendar+traffic+shutdown, no delay lags)",
            color="#2563eb", lw=1.7, ls="--")
    ax.plot(db.index, db.values, label="naive 'normal year' baseline",
            color="#9ca3af", lw=1.3, ls=":")
    ax.set_ylabel(f"{a}\ndelay (min)")
    r = res[res.airport == a].iloc[0]
    ax.text(0.99, 0.92, f"model MAE {r.mae_model:.1f}  vs  naive {r.mae_naive:.1f}",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, color="#334155")
    ax.axvline(pd.Timestamp("2025-11-07"), color="#6b7280", ls="-", lw=0.8, alpha=0.6)
    ax.margins(x=0.01)
axes[0].legend(frameon=False, fontsize=7.5, loc="upper left")
axes[0].set_title("Honest forecast (no peeking) vs actual, November 2025\n"
                  "model uses only calendar, scheduled traffic, and a shutdown factor")
fig.tight_layout()
fig.savefig("analysis/shutdown_predict_vs_actual.png", dpi=140)
print("\nsaved analysis/shutdown_predict_vs_actual.png")
print("done.")
