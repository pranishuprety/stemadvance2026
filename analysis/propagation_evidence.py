"""
First evidence experiment: does delay propagate through the Northeast-corridor graph?

Hypothesis (H1): an airport's next-hour delay is better predicted when we add its
upstream neighbors' recent delays, beyond the airport's own history alone.

Data: BTS Reporting Carrier On-Time Performance, January 2023 (real).
Method: hourly airport panel; for each NYC-metro airport compare a local-only
autoregressive model vs. the same model plus corridor-neighbor lags.
Metric: out-of-sample R^2 and MAE on a temporal holdout (last 25% of hours).
"""
import glob
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score, mean_absolute_error
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV = glob.glob("analysis/bts_2023_01/*.csv")[0]

CORRIDOR = ["EWR", "JFK", "LGA", "BOS", "PHL", "DCA", "IAD", "BWI"]
NYC_METRO = ["EWR", "JFK", "LGA"]          # our niche, the prediction targets
LAGS = [1, 2, 3]                            # hours

cols = ["FlightDate", "Origin", "CRSDepTime", "DepDelayMinutes", "Cancelled"]
print("Loading BTS January 2023 ...")
df = pd.read_csv(CSV, usecols=cols, low_memory=False)
df = df[df["Origin"].isin(CORRIDOR)].copy()
df = df[df["Cancelled"] == 0]
df = df.dropna(subset=["DepDelayMinutes", "CRSDepTime"])

# scheduled hour from CRSDepTime (hhmm)
hr = (df["CRSDepTime"].astype(int) // 100).clip(0, 23)
df["ts"] = pd.to_datetime(df["FlightDate"]) + pd.to_timedelta(hr, unit="h")

print(f"{len(df):,} corridor departures after cleaning")

# hourly mean departure delay per airport -> wide panel (rows=hour, cols=airport)
panel = (df.groupby(["ts", "Origin"])["DepDelayMinutes"].mean()
           .unstack("Origin")
           .sort_index())
full_idx = pd.date_range(panel.index.min(), panel.index.max(), freq="h")
panel = panel.reindex(full_idx)
# treat hours with no scheduled departures as 0 delay (quiet overnight)
panel = panel.fillna(0.0)
print(f"panel shape: {panel.shape[0]} hours x {panel.shape[1]} airports")
panel.round(2).to_csv("analysis/hourly_panel.csv", index_label="hour")
print("saved analysis/hourly_panel.csv")

def build_xy(target):
    """Local features = target's own lags. Network features add corridor neighbors' lags."""
    frame = pd.DataFrame(index=panel.index)
    local_cols, net_cols = [], []
    for L in LAGS:
        c = f"{target}_lag{L}"
        frame[c] = panel[target].shift(L)
        local_cols.append(c)
    frame["hour"] = frame.index.hour
    local_cols.append("hour")
    for nb in CORRIDOR:
        if nb == target:
            continue
        c = f"{nb}_lag1"
        frame[c] = panel[nb].shift(1)
        net_cols.append(c)
    frame["y"] = panel[target]
    frame = frame.dropna()
    return frame, local_cols, net_cols

rows = []
for tgt in NYC_METRO:
    frame, local_cols, net_cols = build_xy(tgt)
    n = len(frame)
    split = int(n * 0.75)
    tr, te = frame.iloc[:split], frame.iloc[split:]

    # baseline: local only
    mb = Ridge(alpha=1.0).fit(tr[local_cols], tr["y"])
    pb = mb.predict(te[local_cols])
    r2_b = r2_score(te["y"], pb); mae_b = mean_absolute_error(te["y"], pb)

    # +network: local + neighbor lags
    allc = local_cols + net_cols
    mn = Ridge(alpha=1.0).fit(tr[allc], tr["y"])
    pn = mn.predict(te[allc])
    r2_n = r2_score(te["y"], pn); mae_n = mean_absolute_error(te["y"], pn)

    rows.append(dict(airport=tgt, r2_local=r2_b, r2_network=r2_n,
                     dR2=r2_n - r2_b, mae_local=mae_b, mae_network=mae_n,
                     mae_gain_pct=100 * (mae_b - mae_n) / mae_b))

res = pd.DataFrame(rows)
pd.set_option("display.float_format", lambda v: f"{v:0.3f}")
print("\n=== H1 test: local-only vs local+network (test set, Jan 2023) ===")
print(res.to_string(index=False))
res.to_csv("analysis/results_propagation.csv", index=False)

# figure: R2 baseline vs +network
fig, ax = plt.subplots(figsize=(7, 4.2))
x = np.arange(len(res)); w = 0.38
ax.bar(x - w/2, res["r2_local"], w, label="local-only (own history)", color="#94a3c4")
ax.bar(x + w/2, res["r2_network"], w, label="local + corridor neighbors", color="#6366f1")
ax.set_xticks(x); ax.set_xticklabels(res["airport"])
ax.set_ylabel("out-of-sample $R^2$")
ax.set_title("Adding corridor-neighbor delays improves next-hour delay prediction\nNYC metro, BTS Jan 2023")
ax.legend(frameon=False)
for i, r in res.iterrows():
    ax.text(i + w/2, r["r2_network"] + 0.005, f"+{r['dR2']:.3f}", ha="center", fontsize=9, color="#16b981")
fig.tight_layout()
fig.savefig("analysis/evidence_r2.png", dpi=140)
print("\nsaved analysis/evidence_r2.png and analysis/results_propagation.csv")

# quick lead-lag correlation: EWR delay now vs JFK/LGA delay next hour
print("\n=== lead-lag: EWR(t) vs neighbor(t+1) Pearson r ===")
for nb in ["JFK", "LGA", "PHL", "BOS"]:
    r = panel["EWR"].corr(panel[nb].shift(-1))
    print(f"  EWR(t) -> {nb}(t+1): r = {r:0.3f}")
