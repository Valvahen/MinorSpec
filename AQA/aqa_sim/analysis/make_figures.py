"""Generate the two publication figures for the Results section."""
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUT = Path("results/figures")
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.size": 12,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "figure.dpi": 300,
})

# ----------------------------------------------------------------------
# FIGURE 1: Communication reduction (bar chart) — the WIN
# ----------------------------------------------------------------------
nodes = ["n=20", "n=50", "n=100"]
split_msgs = [7660, 49060, 198060]
part_msgs = [3898, 26118, 106026]        # <-- UPDATED (was 102695)

x = np.arange(len(nodes))
w = 0.38

fig1, ax1 = plt.subplots(figsize=(6.5, 4.2))
ax1.bar(x - w/2, split_msgs, w, label="Static SplitBFT",
        color="#4c72b0", edgecolor="black", linewidth=0.5)
ax1.bar(x + w/2, part_msgs, w, label="Participation-AQA",
        color="#dd8452", edgecolor="black", linewidth=0.5)

ax1.set_ylabel("Total protocol messages")
ax1.set_xlabel("Network size")
ax1.set_title("Communication Overhead: Participation-AQA vs SplitBFT\n(benign, lossless conditions)")
ax1.set_xticks(x)
ax1.set_xticklabels(nodes)
ax1.set_yscale("log")
ax1.legend()

reductions = [49.1, 46.8, 46.5]          # <-- UPDATED (was 48.2 for n=100)
for i, red in enumerate(reductions):
    top = max(split_msgs[i], part_msgs[i])
    ax1.text(x[i], top * 1.35, f"-{red:.0f}%", ha="center",
             fontweight="bold", color="#c44e52")

fig1.tight_layout()
fig1.savefig(OUT / "fig1_message_reduction.pdf")
fig1.savefig(OUT / "fig1_message_reduction.png")
print(f"Saved: {OUT/'fig1_message_reduction.pdf'}")

# ----------------------------------------------------------------------
# FIGURE 2: Communication-liveness trade-off — now showing ALL THREE SIZES
# ----------------------------------------------------------------------
loss = [0, 1, 2, 3, 5, 8, 10]

split_20  = [20.0, 19.4, 18.6, 18.0, 16.4, 15.0, 12.7]
part_20   = [20.0,  9.6, 10.0,  9.8,  7.3,  2.7,  1.2]
split_50  = [20.0, 19.0, 18.4, 17.9, 16.7, 14.7, 13.5]
part_50   = [20.0, 13.1,  9.8,  9.9,  3.2,  1.9,  0.8]
split_100 = [20.0, 19.0, 18.5, 17.7, 16.9, 14.8, 13.5]
part_100  = [20.0, 19.0, 17.6, 14.6,  7.2,  2.8,  1.1]

fig2, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)

datasets = [
    ("n = 20",  split_20,  part_20,  1),
    ("n = 50",  split_50,  part_50,  1),
    ("n = 100", split_100, part_100, 3),
]

for ax, (title, sblk, pblk, crossover) in zip(axes, datasets):
    ax.plot(loss, sblk, marker="o", linewidth=2, markersize=6,
            label="Static SplitBFT", color="#4c72b0")
    ax.plot(loss, pblk, marker="s", linewidth=2, markersize=6,
            label="Participation-AQA", color="#dd8452")
    # shade from 0 up to the crossover point
    ax.axvspan(0, crossover, alpha=0.12, color="green")
    ax.text(crossover / 2 if crossover > 1 else 0.5, 2.0,
            f"Part-AQA\nfavoured\n(≤{crossover}%)",
            ha="center", fontsize=8, color="#2e7d32", fontweight="bold")
    ax.set_title(title)
    ax.set_xlabel("Packet loss (%)")
    ax.set_ylim(0, 21)

axes[0].set_ylabel("Blocks finalized (liveness)")
axes[0].legend(loc="upper right", fontsize=9)
fig2.suptitle("Communication–Liveness Trade-off: the crossover is size-dependent", y=1.02)

fig2.tight_layout()
fig2.savefig(OUT / "fig2_tradeoff.pdf", bbox_inches="tight")
fig2.savefig(OUT / "fig2_tradeoff.png", bbox_inches="tight")
print(f"Saved: {OUT/'fig2_tradeoff.pdf'}")

print("Both figures generated.")