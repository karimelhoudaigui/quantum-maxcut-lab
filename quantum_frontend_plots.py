import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


def plot_smooth_grid_search_png(rows, best, output):
    sorted_rows = sorted(rows, key=lambda row: row["ratio_pulser"], reverse=True)
    top = sorted_rows[: min(20, len(sorted_rows))]

    labels = [str(i + 1) for i in range(len(top))]
    ratios = np.array([row["ratio_pulser"] for row in top], dtype=float)
    overlaps = np.array([row["overlap_proxy"] for row in top], dtype=float)

    fig, ax = plt.subplots(figsize=(9, 5.2))
    x = np.arange(len(top))
    colors = plt.cm.magma(np.linspace(0.25, 0.82, len(top)))

    ax.bar(x, ratios, color=colors, edgecolor="black", linewidth=0.6, label="ratio Pulser")
    ax.plot(x, overlaps, color="black", marker="o", linewidth=1.7, label="overlap proxy")

    if best:
        ax.axhline(
            float(best["ratio_pulser"]),
            color="#147d64",
            linestyle="--",
            linewidth=1.5,
            label=f"meilleur ratio = {float(best['ratio_pulser']):.3f}",
        )

    ax.set_title("Top paramètres de la grid search smooth", fontsize=13, pad=10)
    ax.set_xlabel("Rang dans la recherche", fontsize=11)
    ax.set_ylabel("Score", fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0.0, max(1.05, float(max(np.max(ratios), np.max(overlaps))) * 1.08))
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(fig)
