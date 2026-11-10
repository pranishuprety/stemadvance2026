"""Finance figure: dollar cost of delay, normal (2024) vs shutdown (2025),
per NYC-metro airport, using A4A CY2024 $100.76 per block-minute."""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COST = 100.76
raw = pd.read_csv("analysis/shutdown_raw_compare.csv")
raw["cost_2024_M"] = raw["total_delaymin_2024"] * COST / 1e6
raw["cost_2025_M"] = raw["total_delaymin_2025"] * COST / 1e6
raw["excess_M"] = raw["cost_2025_M"] - raw["cost_2024_M"]

fig, ax = plt.subplots(figsize=(7.5, 4.6))
x = np.arange(len(raw)); w = 0.38
ax.bar(x - w/2, raw["cost_2024_M"], w, label="2024 (normal year)", color="#94a3c4")
b = ax.bar(x + w/2, raw["cost_2025_M"], w, label="2025 (shutdown)", color="#ef4444")
# mark the shutdown-attributable excess on top of each 2025 bar
for i, r in raw.iterrows():
    ax.text(i + w/2, r["cost_2025_M"] + 0.6,
            f"+${r['excess_M']:.1f}M", ha="center", fontsize=9, color="#b91c1c")
    ax.text(i - w/2, r["cost_2024_M"] + 0.6,
            f"${r['cost_2024_M']:.1f}M", ha="center", fontsize=8, color="#475569")
ax.set_xticks(x); ax.set_xticklabels(raw["airport"])
ax.set_ylabel("delay cost (US$ millions)")
tot25 = raw["cost_2025_M"].sum(); exc = raw["excess_M"].sum()
ax.set_title(f"Cost of departure delay, NYC metro (Oct+Nov)\n"
             f"2025 shutdown total ${tot25:.0f}M  |  shutdown-attributable excess ${exc:.0f}M "
             f"(A4A ${COST}/min)")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig("analysis/fig_finance.png", dpi=140)
print(raw[["airport", "cost_2024_M", "cost_2025_M", "excess_M"]].round(1).to_string(index=False))
print(f"\nTotal 2025 cost ${tot25:.1f}M | total excess ${exc:.1f}M")
print("saved analysis/fig_finance.png")
