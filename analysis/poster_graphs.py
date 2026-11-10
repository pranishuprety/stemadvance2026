"""
Poster graphs (36 x 24 in poster), drawn at printed size in one visual style.
Uses the real BTS data and the result tables produced by the analysis scripts.
Run from the project root:  python analysis/poster_graphs.py
"""
import zipfile
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

OUT = "analysis/poster_"
GREY, RED, SLATE, BLUE = "#9aa5bd", "#a3111a", "#1f2937", "#2563eb"
SHADE = "#e9ebf0"
NYC = ["EWR", "JFK", "LGA"]
CORRIDOR = ["EWR", "JFK", "LGA", "BOS", "PHL", "DCA", "IAD", "BWI"]
COST_PER_MIN = 100.76
plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 23,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 23, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "legend.frameon": False, "legend.fontsize": 20,
})


def save(fig, name, bottom=0.0):
    fig.tight_layout(rect=(0, bottom, 1, 1))
    fig.savefig(f"{OUT}{name}.png", dpi=200)
    plt.close(fig)


def load(path, cols):
    with zipfile.ZipFile(path) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(name) as f:
            return pd.read_csv(f, usecols=cols, low_memory=False)


cols = ["FlightDate", "Origin", "CRSDepTime", "DepDelayMinutes", "Cancelled"]
base = "data/01_delay_ontime/BTS_OnTime_"
years = {}
for y in (2024, 2025):
    df = pd.concat([load(f"{base}{y}_{m}.zip", cols) for m in (10, 11)])
    df = df[df["Origin"].isin(CORRIDOR) & (df["Cancelled"] == 0)]
    df = df.dropna(subset=["DepDelayMinutes", "CRSDepTime"])
    hr = (df["CRSDepTime"].astype(int) // 100).clip(0, 23)
    df["FlightDate"] = pd.to_datetime(df["FlightDate"])
    df["ts"] = df["FlightDate"] + pd.to_timedelta(hr, unit="h")
    years[y] = df

# ---------------------------------------------------------- 1. delay timeline
def daily(df):
    s = df[df["Origin"].isin(NYC)].groupby("FlightDate")["DepDelayMinutes"].mean()
    s.index = s.index.map(lambda d: pd.Timestamp(2025, d.month, d.day))
    return s


s24, s25 = daily(years[2024]), daily(years[2025])
fig, ax = plt.subplots(figsize=(9.0, 3.45))
ax.axvspan(pd.Timestamp("2025-10-01"), pd.Timestamp("2025-11-12"), color=SHADE,
           lw=0, label="Shutdown")
ax.axvline(pd.Timestamp("2025-11-07"), color=SLATE, ls="--", lw=1.6)
ax.text(pd.Timestamp("2025-11-07"), 92, " FAA cuts", fontsize=19, va="top")
ax.plot(s24.index, s24.values, color=GREY, lw=3, label="2024 (normal)")
ax.plot(s25.index, s25.values, color=RED, lw=3.4, label="2025 (shutdown)")
ax.set_ylabel("Avg delay (min)")
ax.set_ylim(0, 95); ax.set_yticks([0, 40, 80])
ax.set_xticks([pd.Timestamp(d) for d in ("2025-10-01", "2025-10-15",
                                         "2025-11-01", "2025-11-15", "2025-12-01")])
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, columnspacing=1.2,
          handlelength=1.5, borderaxespad=0.1)
save(fig, "g_timeline")

# ------------------------------------------------- 2. delay + cancellations
raw = pd.read_csv("analysis/shutdown_raw_compare.csv").set_index("airport").loc[NYC]
pvals = {"EWR": 0.069, "JFK": 1.4e-5, "LGA": 7.3e-6}
cancel = {"EWR": (0.37, 4.85), "JFK": (0.01, 3.34), "LGA": (0.11, 4.28)}
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.0, 3.45))
x, w = np.arange(3), 0.38
a1.bar(x - w / 2, raw["mean_delay_2024"], w, color=GREY, label="2024")
a1.bar(x + w / 2, raw["mean_delay_2025"], w, color=RED, label="2025")
for i, a in enumerate(NYC):
    tag = f"+{raw.loc[a, 'mean_delay_change_pct']:.0f}%"
    sig = pvals[a] < 0.05
    a1.text(i + w / 2, raw.loc[a, "mean_delay_2025"] + 0.5,
            tag + ("" if sig else "\n(n.s.)"), ha="center", va="bottom",
            fontsize=19, fontweight="bold" if sig else "normal",
            color=RED if sig else SLATE)
a1.set_xticks(x); a1.set_xticklabels(NYC)
a1.set_ylim(0, 27); a1.set_title("Avg delay (min)")
fig.legend(*a1.get_legend_handles_labels(), loc="lower center", ncol=2,
           bbox_to_anchor=(0.5, 0), fontsize=19)
a2.bar(x - w / 2, [cancel[a][0] for a in NYC], w, color=GREY)
a2.bar(x + w / 2, [cancel[a][1] for a in NYC], w, color=RED)
for i, a in enumerate(NYC):
    a2.text(i + w / 2, cancel[a][1] + 0.1, f"{cancel[a][1]:.1f}%", ha="center",
            va="bottom", fontsize=19, fontweight="bold", color=RED)
a2.set_xticks(x); a2.set_xticklabels(NYC)
a2.set_ylim(0, 6); a2.set_title("Cancelled after cuts (%)")
save(fig, "g_airports", bottom=0.1)

# --------------------------------------------------------------- 3. cost
c24 = raw["total_delaymin_2024"] * COST_PER_MIN / 1e6
c25 = raw["total_delaymin_2025"] * COST_PER_MIN / 1e6
est = [("Prior year", 40.5), ("ML model", 41.3), ("ML + weather", 42.4)]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.0, 3.45),
                             gridspec_kw={"width_ratios": [1.15, 1]})
a1.bar(x - w / 2, c24, w, color=GREY, label="2024")
a1.bar(x + w / 2, c25, w, color=RED, label="2025")
for i, a in enumerate(NYC):
    a1.text(i + w / 2, c25[a] + 1, f"+${c25[a] - c24[a]:.1f}M", ha="center",
            va="bottom", fontsize=18, fontweight="bold", color=RED)
a1.set_xticks(x); a1.set_xticklabels(NYC)
a1.set_ylim(0, 56); a1.set_title("Delay cost ($M)")
fig.legend(*a1.get_legend_handles_labels(), loc="lower center", ncol=2,
           bbox_to_anchor=(0.5, 0), fontsize=19)
yy = np.arange(len(est))[::-1]
a2.barh(yy, [v for _, v in est], color=[GREY, GREY, SLATE], height=0.55)
for yi, (lab, v) in zip(yy, est):
    a2.text(v - 1, yi, f"${v}M", va="center", ha="right", color="white",
            fontsize=20, fontweight="bold")
a2.set_yticks(yy); a2.set_yticklabels([l for l, _ in est])
a2.set_xlim(0, 46); a2.set_xticks([0, 20, 40])
a2.set_title("Extra cost ($M)")
save(fig, "g_cost", bottom=0.1)

# ------------------------------------------------------------ 4. forecast
def panels(df):
    m = df.groupby(["ts", "Origin"])["DepDelayMinutes"].mean().unstack("Origin")
    c = df.groupby(["ts", "Origin"])["DepDelayMinutes"].size().unstack("Origin")
    idx = pd.date_range(m.index.min(), m.index.max(), freq="h")
    return m.reindex(idx).fillna(0.0), c.reindex(idx).fillna(0.0)


def feats(m, c, a, shut):
    f = pd.DataFrame(index=m.index)
    f["hour"], f["dow"] = f.index.hour, f.index.dayofweek
    f["sched_flights"] = c[a]
    f["shutdown"] = (((f.index >= "2025-10-01") & (f.index <= "2025-11-13"))
                     .astype(int) if shut else 0)
    f["y"] = m[a]
    return f


m24, k24 = panels(years[2024])
m25, k25 = panels(years[2025])
X = ["hour", "dow", "sched_flights", "shutdown"]
act, fc, bl = [], [], []
for a in NYC:
    f24, f25 = feats(m24, k24, a, False), feats(m25, k25, a, True)
    both = pd.concat([f24, f25]).dropna()
    is25 = both.index.year == 2025
    tr = both[~is25 | (is25 & (both.index.month == 10))]
    te = both[is25 & (both.index.month == 11)]
    mdl = HistGradientBoostingRegressor(max_depth=4, learning_rate=0.05,
                                        max_iter=400, l2_regularization=1.0,
                                        random_state=0).fit(tr[X], tr["y"])
    clim = f24.dropna().groupby(["hour", "dow"])["y"].mean()
    b = [clim.get((h, d), f24["y"].mean()) for h, d in zip(te["hour"], te["dow"])]
    act.append(te["y"].resample("D").mean())
    fc.append(pd.Series(mdl.predict(te[X]), index=te.index).resample("D").mean())
    bl.append(pd.Series(b, index=te.index).resample("D").mean())
act, fc, bl = (pd.concat(s, axis=1).mean(axis=1) for s in (act, fc, bl))
act, fc, bl = (s[s.index.month == 11] for s in (act, fc, bl))
fig, ax = plt.subplots(figsize=(9.0, 3.45))
ax.axvline(pd.Timestamp("2025-11-07"), color=SLATE, ls="--", lw=1.6)
ax.text(pd.Timestamp("2025-11-07"), 59, " FAA cuts", fontsize=19, va="top")
ax.plot(act.index, act.values, color=RED, lw=3.4, label="Actual")
ax.plot(fc.index, fc.values, color=SLATE, lw=3, ls="--", label="Our forecast")
ax.plot(bl.index, bl.values, color=GREY, lw=3, ls=":", label="Normal-year baseline")
ax.set_ylabel("Avg delay (min)")
ax.set_ylim(0, 60)
ax.set_xlim(pd.Timestamp("2025-11-01"), pd.Timestamp("2025-11-30"))
ax.xaxis.set_major_locator(mdates.DayLocator(bymonthday=[1, 8, 15, 22, 29]))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
ax.legend(loc="upper right", labelspacing=0.3)
save(fig, "g_forecast")

# ------------------------------------------------------------ 5. coupling
regimes = ["Jan 2023\nNOTAM outage", "Oct–Nov 2024\nnormal", "Oct–Nov 2025\nshutdown"]
jfk, lga = [0.573, 0.193, 0.547], [0.565, 0.134, 0.445]
fig, ax = plt.subplots(figsize=(6.9, 4.0))
x3 = np.arange(3)
ax.bar(x3 - w / 2, jfk, w, color=SLATE, label="Newark → JFK")
ax.bar(x3 + w / 2, lga, w, color=GREY, label="Newark → LGA")
for i in range(3):
    ax.text(i - w / 2, jfk[i] + 0.015, f"{jfk[i]:.2f}", ha="center", fontsize=18,
            fontweight="bold", color=RED if i != 1 else SLATE)
ax.set_xticks(x3); ax.set_xticklabels(regimes, fontsize=18)
ax.set_ylim(0, 0.72); ax.set_yticks([0, 0.2, 0.4, 0.6])
ax.set_ylabel("Correlation, 1 hr later")
ax.legend(loc="upper center", ncol=2, fontsize=18, bbox_to_anchor=(0.5, 1.12))
save(fig, "g_coupling")
print("saved poster graphs")
