"""
Proof of concept: train a lean delay-prediction model on NORMAL operations,
then test it on the 2025 U.S. government shutdown window, and report the error
in two currencies: delay minutes and dollars (industry cost of delay).

Design (agreed scope, ~publishable proof of concept, no GNN):
  - Niche: NYC metro departures (EWR, JFK, LGA), Northeast-corridor neighbors as
    extra features.
  - Train window : Oct + Nov 2024  (normal operations, the baseline year).
  - Test  window : Oct + Nov 2025  (the shutdown began Oct 1, 2025; the FAA
    flight-cut order is dated Nov 6, 2025).
  - Models: Ridge (linear baseline) and HistGradientBoosting (trees), chosen so
    the whole thing runs with stock scikit-learn (no extra installs).
  - Finance: A4A CY2024 cost of delay = $100.76 per block-minute.

Outputs (all written to analysis/):
  - shutdown_raw_compare.csv     normal vs shutdown delay levels
  - shutdown_model_results.csv   per-airport test error (minutes)
  - shutdown_finance.csv         delay minutes -> dollars
  - shutdown_delay_compare.png   bar chart of mean delay 2024 vs 2025
  - shutdown_pred_vs_actual.png  model prediction vs actual over the window
"""
import zipfile
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------- config
DATA_DIR = "data/01_delay_ontime"
ZIPS = {
    2024: [f"{DATA_DIR}/BTS_OnTime_2024_10.zip", f"{DATA_DIR}/BTS_OnTime_2024_11.zip"],
    2025: [f"{DATA_DIR}/BTS_OnTime_2025_10.zip", f"{DATA_DIR}/BTS_OnTime_2025_11.zip"],
}
CORRIDOR = ["EWR", "JFK", "LGA", "BOS", "PHL", "DCA", "IAD", "BWI"]
NYC_METRO = ["EWR", "JFK", "LGA"]           # prediction targets (our niche)
LAGS = [1, 2, 3]                            # hours
COST_PER_MIN = 100.76                       # A4A CY2024 $/block-minute
USECOLS = ["FlightDate", "Origin", "CRSDepTime", "DepDelayMinutes",
           "Cancelled", "WeatherDelay"]


# ---------------------------------------------------------------- load
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


def hourly_panels(df):
    """Return (mean_delay_panel, flight_count_panel) indexed by continuous hour."""
    mean_p = (df.groupby(["ts", "Origin"])["DepDelayMinutes"].mean()
                .unstack("Origin").sort_index())
    cnt_p = (df.groupby(["ts", "Origin"])["DepDelayMinutes"].size()
               .unstack("Origin").sort_index())
    idx = pd.date_range(mean_p.index.min(), mean_p.index.max(), freq="h")
    mean_p = mean_p.reindex(idx).fillna(0.0)
    cnt_p = cnt_p.reindex(idx).fillna(0.0)
    for a in CORRIDOR:
        if a not in mean_p:
            mean_p[a] = 0.0
            cnt_p[a] = 0.0
    return mean_p, cnt_p


# ---------------------------------------------------------------- features
def build_features(mean_panel, target):
    frame = pd.DataFrame(index=mean_panel.index)
    cols = []
    for L in LAGS:
        c = f"{target}_lag{L}"
        frame[c] = mean_panel[target].shift(L)
        cols.append(c)
    frame["hour"] = frame.index.hour
    frame["dow"] = frame.index.dayofweek
    cols += ["hour", "dow"]
    for nb in CORRIDOR:
        if nb == target:
            continue
        c = f"{nb}_lag1"
        frame[c] = mean_panel[nb].shift(1)
        cols.append(c)
    frame["y"] = mean_panel[target]
    return frame, cols


def build_calendar_features(mean_panel, target):
    """Calendar-only 'normal expectation' baseline: NO recent-delay inputs, so
    the model cannot see the shutdown. Its prediction is what a normal day looks
    like; actual minus this = the shutdown effect."""
    frame = pd.DataFrame(index=mean_panel.index)
    frame["hour"] = frame.index.hour
    frame["dow"] = frame.index.dayofweek
    frame["y"] = mean_panel[target]
    return frame, ["hour", "dow"]


# ---------------------------------------------------------------- main
print("Loading BTS 2024 (normal) and 2025 (shutdown) ...")
df24 = load_year(2024)
df25 = load_year(2025)
print(f"  2024: {len(df24):,} corridor departures")
print(f"  2025: {len(df25):,} corridor departures")

mean24, cnt24 = hourly_panels(df24)
mean25, cnt25 = hourly_panels(df25)

# ---- (1) raw comparison: normal vs shutdown -------------------------------
raw_rows = []
for a in NYC_METRO:
    d24 = df24[df24["Origin"] == a]["DepDelayMinutes"]
    d25 = df25[df25["Origin"] == a]["DepDelayMinutes"]
    raw_rows.append(dict(
        airport=a,
        flights_2024=len(d24), flights_2025=len(d25),
        mean_delay_2024=d24.mean(), mean_delay_2025=d25.mean(),
        total_delaymin_2024=d24.sum(), total_delaymin_2025=d25.sum(),
    ))
raw = pd.DataFrame(raw_rows)
raw["mean_delay_change_pct"] = 100 * (raw["mean_delay_2025"] - raw["mean_delay_2024"]) / raw["mean_delay_2024"]
raw.to_csv("analysis/shutdown_raw_compare.csv", index=False)
print("\n=== Raw normal (2024) vs shutdown (2025), NYC metro departures ===")
print(raw.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

# ---- (2) model: train on 2024 normal, test on 2025 shutdown ---------------
model_rows = []
preds_for_plot = {}
for a in NYC_METRO:
    f24, cols = build_features(mean24, a)
    f25, _ = build_features(mean25, a)
    tr = f24.dropna()
    te = f25.dropna()

    # reference: normal holdout (last 25% of 2024) so we see normal-period skill
    split = int(len(tr) * 0.75)
    tr_fit, tr_hold = tr.iloc[:split], tr.iloc[split:]

    for name, mk in [("ridge", lambda: Ridge(alpha=1.0)),
                     ("gbt", lambda: HistGradientBoostingRegressor(
                         max_depth=4, learning_rate=0.05, max_iter=400,
                         l2_regularization=1.0, random_state=0))]:
        m = mk().fit(tr_fit[cols], tr_fit["y"])
        # normal holdout skill
        p_hold = m.predict(tr_hold[cols])
        r2_h = r2_score(tr_hold["y"], p_hold)
        mae_h = mean_absolute_error(tr_hold["y"], p_hold)
        # shutdown test skill (model refit on ALL of 2024 for the real test)
        m_full = mk().fit(tr[cols], tr["y"])
        p_sd = m_full.predict(te[cols])
        r2_s = r2_score(te["y"], p_sd)
        mae_s = mean_absolute_error(te["y"], p_sd)
        rmse_s = np.sqrt(mean_squared_error(te["y"], p_sd))
        model_rows.append(dict(
            airport=a, model=name,
            r2_normalhold=r2_h, mae_normalhold=mae_h,
            r2_shutdown=r2_s, mae_shutdown=mae_s, rmse_shutdown=rmse_s,
        ))
    # calendar-only "normal expectation" baseline (no delay lags -> blind to the
    # shutdown). The gap between actual and this line is the shutdown effect.
    cf24, ccols = build_calendar_features(mean24, a)
    cf25, _ = build_calendar_features(mean25, a)
    ctr, cte = cf24.dropna(), cf25.dropna()
    cm = HistGradientBoostingRegressor(max_depth=4, learning_rate=0.05,
                                       max_iter=400, l2_regularization=1.0,
                                       random_state=0).fit(ctr[ccols], ctr["y"])
    p_normal = cm.predict(cte[ccols])
    preds_for_plot[a] = (cte.index, cte["y"].values, p_normal)

model_res = pd.DataFrame(model_rows)
model_res.to_csv("analysis/shutdown_model_results.csv", index=False)
print("\n=== Model error: trained on 2024 normal, tested on 2025 shutdown ===")
print(model_res.to_string(index=False, float_format=lambda v: f"{v:.3f}"))

# ---- (3) finance: delay minutes -> dollars --------------------------------
tot24 = raw["total_delaymin_2024"].sum()
tot25 = raw["total_delaymin_2025"].sum()
excess_vs_baseline = tot25 - tot24

# model-based counterfactual excess: for each NYC airport-hour in 2025, the
# model's predicted "normal" mean delay is the counterfactual; actual minus
# predicted, times flights that actually operated, summed and floored at 0.
model_excess_min = 0.0
for a in NYC_METRO:
    f24, cols = build_features(mean24, a)
    f25, _ = build_features(mean25, a)
    tr = f24.dropna()
    te = f25.dropna()
    m = HistGradientBoostingRegressor(max_depth=4, learning_rate=0.05,
                                      max_iter=400, l2_regularization=1.0,
                                      random_state=0).fit(tr[cols], tr["y"])
    pred_normal = m.predict(te[cols])
    excess_per_hr = np.clip(te["y"].values - pred_normal, 0, None)
    flights_hr = cnt25[a].reindex(te.index).fillna(0.0).values
    model_excess_min += float((excess_per_hr * flights_hr).sum())

fin = pd.DataFrame([
    dict(metric="Total delay cost, 2025 shutdown window (gross)",
         delay_minutes=tot25, dollars=tot25 * COST_PER_MIN),
    dict(metric="Excess vs 2024 same-window baseline",
         delay_minutes=excess_vs_baseline, dollars=excess_vs_baseline * COST_PER_MIN),
    dict(metric="Excess vs model normal-counterfactual (shutdown-attributable)",
         delay_minutes=model_excess_min, dollars=model_excess_min * COST_PER_MIN),
])
fin.to_csv("analysis/shutdown_finance.csv", index=False)
print("\n=== Finance (A4A $100.76/block-minute), NYC metro departures ===")
print(fin.to_string(index=False, float_format=lambda v: f"{v:,.0f}"))

# ---- figures --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 4.2))
x = np.arange(len(raw)); w = 0.38
ax.bar(x - w/2, raw["mean_delay_2024"], w, label="2024 (normal)", color="#94a3c4")
ax.bar(x + w/2, raw["mean_delay_2025"], w, label="2025 (shutdown)", color="#ef4444")
ax.set_xticks(x); ax.set_xticklabels(raw["airport"])
ax.set_ylabel("mean departure delay (min)")
ax.set_title("NYC-metro departure delay: normal (2024) vs shutdown (2025)\nOct+Nov, BTS on-time data")
ax.legend(frameon=False)
for i, r in raw.iterrows():
    ax.text(i + w/2, r["mean_delay_2025"] + 0.3,
            f"+{r['mean_delay_change_pct']:.0f}%", ha="center", fontsize=9, color="#b91c1c")
fig.tight_layout()
fig.savefig("analysis/shutdown_delay_compare.png", dpi=140)

fig, axes = plt.subplots(len(NYC_METRO), 1, figsize=(9, 7.5), sharex=True)
for ax, a in zip(axes, NYC_METRO):
    idx, y, p = preds_for_plot[a]
    daily_y = pd.Series(y, index=idx).resample("D").mean()
    daily_p = pd.Series(p, index=idx).resample("D").mean()
    ax.plot(daily_y.index, daily_y.values, label="actual (2025 shutdown)",
            color="#ef4444", lw=1.9)
    ax.plot(daily_p.index, daily_p.values,
            label="normal expectation (calendar model, trained on 2024)",
            color="#334155", lw=1.6, ls="--")
    # shade the shutdown-attributable gap (actual above normal expectation)
    ax.fill_between(daily_y.index, daily_p.values, daily_y.values,
                    where=(daily_y.values >= daily_p.values),
                    color="#ef4444", alpha=0.18, label="excess delay (shutdown effect)")
    ax.set_ylabel(f"{a}\ndelay (min)")
    ax.margins(x=0.01)
axes[0].legend(frameon=False, fontsize=8, loc="upper left")
axes[0].set_title("2025 shutdown delays vs a normal-expectation baseline (daily mean)\n"
                  "shaded area = delay above what a normal year would produce")
fig.tight_layout()
fig.savefig("analysis/shutdown_pred_vs_actual.png", dpi=140)
print("\nsaved figures: shutdown_delay_compare.png, shutdown_pred_vs_actual.png")
print("done.")
