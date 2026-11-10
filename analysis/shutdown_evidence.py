"""
Real shutdown evidence: compare NYC-metro delays in the 2025 shutdown window
(Oct-Nov 2025) against the same months in the normal prior year (2024).
Uses the actual BTS on-time zips in data/01_delay_ontime/.
Produces graphs that show real spread and a clear shutdown effect.
"""
import zipfile, glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NYC = ["EWR", "JFK", "LGA"]
COLS = ["FlightDate", "Origin", "DepDelayMinutes", "Cancelled"]

def load(zippath):
    with zipfile.ZipFile(zippath) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(name) as f:
            df = pd.read_csv(f, usecols=COLS, low_memory=False)
    df = df[df["Origin"].isin(NYC)]
    df = df[df["Cancelled"] == 0].dropna(subset=["DepDelayMinutes"])
    df["FlightDate"] = pd.to_datetime(df["FlightDate"])
    return df

base = "data/01_delay_ontime/"
normal = pd.concat([load(base+"BTS_OnTime_2024_10.zip"), load(base+"BTS_OnTime_2024_11.zip")])
shut   = pd.concat([load(base+"BTS_OnTime_2025_10.zip"), load(base+"BTS_OnTime_2025_11.zip")])
print(f"normal 2024 flights: {len(normal):,}   shutdown 2025 flights: {len(shut):,}")

# ---- summary stats (real spread, counters 'too close') ----
def stats(df, label):
    d = df["DepDelayMinutes"]
    print(f"{label:16s} mean={d.mean():5.1f}  median={d.median():4.1f}  "
          f"std={d.std():5.1f}  p90={d.quantile(.9):5.1f}  %delayed(>15)={100*(d>15).mean():4.1f}%")
print()
stats(normal, "2024 normal"); stats(shut, "2025 shutdown")
for a in NYC:
    m24 = normal.loc[normal.Origin==a,"DepDelayMinutes"].mean()
    m25 = shut.loc[shut.Origin==a,"DepDelayMinutes"].mean()
    print(f"  {a}: 2024={m24:5.1f} min  2025={m25:5.1f} min  (+{m25-m24:4.1f})")

# ---- Figure 1: daily average delay, 2024 vs 2025 (aligned by month-day) ----
def daily(df):
    s = df.groupby("FlightDate")["DepDelayMinutes"].mean()
    s.index = [(d.month, d.day) for d in s.index]
    return s
d24, d25 = daily(normal), daily(shut)
order = sorted(set(d24.index) | set(d25.index))
x = range(len(order))
y24 = [d24.get(k, np.nan) for k in order]
y25 = [d25.get(k, np.nan) for k in order]
labels = [f"{m}/{dd}" for (m, dd) in order]

fig, ax = plt.subplots(figsize=(11, 4.6))
ax.plot(x, y24, color="#94a3c4", lw=2, label="2024 (normal year)")
ax.plot(x, y25, color="#f43f5e", lw=2.2, label="2025 (shutdown year)")
ax.axvspan(0, len(order)-1, color="#fee2e2", alpha=0.25)
ax.set_title("NYC-metro average departure delay: shutdown year vs normal year\n(Oct 1 - Nov 30, real BTS data)")
ax.set_ylabel("avg departure delay (min)")
ax.set_xticks(list(x)[::5]); ax.set_xticklabels(labels[::5], rotation=45, fontsize=8)
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig("analysis/fig_shutdown_daily.png", dpi=140)
print("\nsaved analysis/fig_shutdown_daily.png")

# ---- Figure 2: distribution of per-flight delays (shows real spread) ----
fig, ax = plt.subplots(figsize=(8, 4.6))
bins = np.linspace(-20, 180, 60)
ax.hist(normal["DepDelayMinutes"].clip(-20,180), bins=bins, density=True,
        alpha=0.55, color="#94a3c4", label="2024 normal")
ax.hist(shut["DepDelayMinutes"].clip(-20,180), bins=bins, density=True,
        alpha=0.55, color="#f43f5e", label="2025 shutdown")
ax.set_yscale("log")
ax.set_title("Distribution of individual flight departure delays (NYC metro)")
ax.set_xlabel("departure delay (min)"); ax.set_ylabel("density (log)")
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig("analysis/fig_delay_distribution.png", dpi=140)
print("saved analysis/fig_delay_distribution.png")

# ---- Figure 3: per-airport mean, 2024 vs 2025 ----
m24 = [normal.loc[normal.Origin==a,"DepDelayMinutes"].mean() for a in NYC]
m25 = [shut.loc[shut.Origin==a,"DepDelayMinutes"].mean() for a in NYC]
fig, ax = plt.subplots(figsize=(6.5, 4.4))
xi = np.arange(len(NYC)); w=0.38
ax.bar(xi-w/2, m24, w, color="#94a3c4", label="2024 normal")
ax.bar(xi+w/2, m25, w, color="#f43f5e", label="2025 shutdown")
ax.set_xticks(xi); ax.set_xticklabels(NYC)
ax.set_ylabel("avg departure delay (min)")
ax.set_title("Shutdown effect by airport (Oct-Nov)")
for i,(a,b) in enumerate(zip(m24,m25)):
    ax.text(i+w/2, b+0.3, f"+{b-a:.0f}", ha="center", color="#b91c1c", fontsize=9)
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig("analysis/fig_airport_compare.png", dpi=140)
print("saved analysis/fig_airport_compare.png")
