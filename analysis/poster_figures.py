"""
Poster versions of the two headline figures (no titles; the poster supplies
captions). Each figure is drawn at its printed size so fonts print at the
intended point size. Run from the project root.
"""
import zipfile
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

NYC = ["EWR", "JFK", "LGA"]
COST_PER_MIN = 100.76
GREY, RED = "#94a3c4", "#b01e2d"


def load(path):
    with zipfile.ZipFile(path) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(name) as f:
            df = pd.read_csv(f, usecols=["FlightDate", "Origin",
                                         "DepDelayMinutes", "Cancelled"],
                             low_memory=False)
    df = df[df["Origin"].isin(NYC) & (df["Cancelled"] == 0)]
    df = df.dropna(subset=["DepDelayMinutes"])
    df["FlightDate"] = pd.to_datetime(df["FlightDate"])
    return df


def daily(df):
    s = df.groupby("FlightDate")["DepDelayMinutes"].mean()
    s.index = s.index.map(lambda d: pd.Timestamp(2025, d.month, d.day))
    return s


base = "data/01_delay_ontime/BTS_OnTime_"
s24 = daily(pd.concat([load(base + "2024_10.zip"), load(base + "2024_11.zip")]))
s25 = daily(pd.concat([load(base + "2025_10.zip"), load(base + "2025_11.zip")]))
raw = pd.read_csv("analysis/shutdown_raw_compare.csv").set_index("airport")
c24 = raw.loc[NYC, "total_delaymin_2024"] * COST_PER_MIN / 1e6
c25 = raw.loc[NYC, "total_delaymin_2025"] * COST_PER_MIN / 1e6


def draw(suffix, daily_size, cost_size, font, small, lw):
    plt.rcParams.update({"font.size": font, "axes.spines.top": False,
                         "axes.spines.right": False})

    fig, ax = plt.subplots(figsize=daily_size)
    ax.axvspan(pd.Timestamp("2025-10-01"), pd.Timestamp("2025-11-12"),
               color="#fde2e2", alpha=0.7, lw=0, label="Shutdown period")
    ax.axvline(pd.Timestamp("2025-11-07"), color="#444", ls="--", lw=lw / 2)
    ax.text(pd.Timestamp("2025-11-07"), 84, " FAA cuts", fontsize=small,
            va="top", color="#333")
    ax.plot(s24.index, s24.values, color=GREY, lw=lw, label="2024 (normal)")
    ax.plot(s25.index, s25.values, color=RED, lw=lw * 1.1,
            label="2025 (shutdown)")
    ax.set_ylabel("Avg delay (min)")
    ax.set_ylim(0, 95)
    ax.set_yticks([0, 25, 50, 75])
    ax.set_xticks([pd.Timestamp(d) for d in
                   ("2025-10-01", "2025-10-15", "2025-11-01", "2025-11-15",
                    "2025-12-01")])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.legend(frameon=False, loc="upper left", fontsize=small,
              handlelength=1.4, labelspacing=0.3)
    fig.tight_layout()
    fig.savefig(f"analysis/poster_fig_daily{suffix}.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=cost_size)
    x = range(len(NYC))
    w = 0.38
    ax.bar([i - w / 2 for i in x], c24, w, color=GREY, label="2024 (normal)")
    ax.bar([i + w / 2 for i in x], c25, w, color=RED, label="2025 (shutdown)")
    for i, a in enumerate(NYC):
        ax.text(i + w / 2, c25[a] + 1, f"+${c25[a] - c24[a]:.1f}M",
                ha="center", fontsize=small, color=RED, fontweight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(NYC)
    ax.set_ylabel("Delay cost ($M)")
    ax.set_ylim(0, 54)
    ax.legend(frameon=False, loc="upper left", fontsize=small)
    fig.tight_layout()
    fig.savefig(f"analysis/poster_fig_cost{suffix}.png", dpi=200)
    plt.close(fig)


draw("", (10, 3.6), (6.4, 3.6), 13, 11, 2)
draw("_36x24", (7.7, 3.6), (7.2, 4.3), 20, 17, 3)
print("excess by airport ($M):", (c25 - c24).round(1).to_dict(),
      "total", round((c25 - c24).sum(), 1))
