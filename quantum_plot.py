import os

os.environ.setdefault("MPLCONFIGDIR", "/tmp")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


def plot_atom_geometry(positions, target_edges=None):
    """
    Visualise la géométrie des atomes.

    positions : array (n,2)
    target_edges : liste [(i,j,w)] (optionnel)
    """
    positions = np.array(positions)
    n = len(positions)

    plt.figure(figsize=(6,6))

    # Points (atomes)
    x = positions[:,0]
    y = positions[:,1]
    plt.scatter(x, y, s=100)

    # Labels des atomes
    for i, (xi, yi) in enumerate(positions):
        plt.text(xi + 0.02, yi + 0.02, f"{i}", fontsize=12)

    # Dessiner les arêtes cibles
    if target_edges is not None:
        for (i, j, w) in target_edges:
            xi, yi = positions[i]
            xj, yj = positions[j]

            plt.plot([xi, xj], [yi, yj], linestyle='--')

            # poids au milieu
            xm, ym = (xi + xj)/2, (yi + yj)/2
            plt.text(xm, ym, f"{w:.2f}", fontsize=9)

    plt.title("Géométrie des atomes (Rydberg)")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.axis("equal")
    plt.grid(True)
    plt.show()


from collections import defaultdict


import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

def plot_atom_geometry(positions, target_edges=None, title=None):
    """Visualisation claire de la géométrie des atomes"""
    positions = np.array(positions)
    n = len(positions)

    plt.figure(figsize=(7, 7))
    plt.scatter(positions[:,0], positions[:,1], s=180, c='blue', edgecolors='black', zorder=3)

    # Labels des atomes
    for i, (x, y) in enumerate(positions):
        plt.text(x + 0.05, y + 0.05, f"{i}", fontsize=14, fontweight='bold')

    # Arêtes cibles
    if target_edges is not None:
        for (i, j, w) in target_edges:
            x1, y1 = positions[i]
            x2, y2 = positions[j]
            plt.plot([x1, x2], [y1, y2], 'r--', alpha=0.7, linewidth=2)
            # Poids
            xm, ym = (x1 + x2)/2, (y1 + y2)/2
            plt.text(xm, ym, f"{w:.2f}", fontsize=11, color='red', 
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    plt.title(title or "Géométrie des atomes Rydberg", fontsize=14)
    plt.xlabel("Position x", fontsize=12)
    plt.ylabel("Position y", fontsize=12)
    plt.axis("equal")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_mapping_error_vs_n(results, save_path=None, show=True):
    """Figure 1 améliorée"""
    grouped = defaultdict(list)
    for r in results:
        grouped[r["n"]].append(r["mapping_error"])

    ns = sorted(grouped.keys())
    means = [np.mean(grouped[n]) for n in ns]
    stds = [np.std(grouped[n]) for n in ns]          # on passe à l'écart-type (plus clair)

    plt.figure(figsize=(8, 5.5))
    plt.errorbar(ns, means, yerr=stds, fmt='o-', capsize=6, linewidth=2, markersize=8, color='darkblue')
    plt.xlabel("Nombre de qubits (n)", fontsize=12)
    plt.ylabel("Erreur de mapping moyenne", fontsize=12)
    plt.title("Erreur de mapping en fonction de la taille du système", fontsize=14, pad=15)
    plt.grid(True, alpha=0.3)

    if save_path:
        plt.savefig(save_path, dpi=250, bbox_inches='tight')
    if show:
        plt.show()
    else:
        plt.close()


def plot_ratio_vs_n(results, save_path=None, show=True):
    """Figure 2 améliorée"""
    grouped = defaultdict(list)
    for r in results:
        grouped[r["n"]].append(r["ratio"])

    ns = sorted(grouped.keys())
    means = [np.mean(grouped[n]) for n in ns]
    stds  = [np.std(grouped[n]) for n in ns]

    plt.figure(figsize=(8, 5.5))
    plt.errorbar(ns, means, yerr=stds, fmt='o-', capsize=6, linewidth=2, markersize=8, color='darkred')
    plt.xlabel("Nombre de qubits (n)", fontsize=12)
    plt.ylabel("Ratio (E_proxy / E0_QMC)", fontsize=12)
    plt.title("Qualité du proxy Rydberg en fonction de n", fontsize=14, pad=15)
    plt.grid(True, alpha=0.3)
    plt.ylim(0, 1.05)

    if save_path:
        plt.savefig(save_path, dpi=250, bbox_inches='tight')
    if show:
        plt.show()
    else:
        plt.close()


def plot_ratio_vs_mapping_error(results, save_path=None, show=True):
    """Figure 3 améliorée : beaucoup plus lisible"""
    plt.figure(figsize=(9, 6))

    colors = {4: 'blue', 5: 'green', 6: 'orange', 7: 'red'}
    markers = {4: 'o', 5: 's', 6: '^', 7: 'D'}

    for n in [4, 5, 6, 7]:
        subset = [r for r in results if r["n"] == n]
        errors = [r["mapping_error"] for r in subset]
        ratios = [r["ratio"] for r in subset]
        
        plt.scatter(errors, ratios, 
                    label=f'n = {n}', 
                    marker=markers[n], 
                    color=colors[n], 
                    s=70, 
                    alpha=0.85,
                    edgecolors='black')

    plt.xlabel("Erreur de mapping", fontsize=12)
    plt.ylabel("Ratio proxy / optimum (E_proxy / E0_QMC)", fontsize=12)
    plt.title("Relation entre qualité du mapping et performance du proxy", fontsize=14, pad=15)
    plt.grid(True, alpha=0.3)
    plt.legend(title="Taille du système", fontsize=11)
    plt.xscale('log')          # très utile car les erreurs varient beaucoup
    plt.ylim(0, 1.05)

    if save_path:
        plt.savefig(save_path, dpi=250, bbox_inches='tight')
    if show:
        plt.show()
    else:
        plt.close()


def plot_smooth_graph_study_article(results, summary=None, save_paths=None, show=True):
    """
    Figure compacte pour l'article :
    - ratio Pulser par graphe
    - ratio proxy exact pour distinguer embedding et préparation dynamique
    - erreur de mapping sur un second panneau
    """
    if not results:
        raise ValueError("La liste results est vide.")

    x = np.arange(len(results))

    ratio_pulser = np.array([r["ratio_pulser"] for r in results], dtype=float)
    ratio_proxy = np.array([r["ratio_proxy_exact"] for r in results], dtype=float)
    mapping_error = np.array([r["mapping_error"] for r in results], dtype=float)

    mean_ratio = (
        float(summary["ratio_pulser_mean"])
        if summary and "ratio_pulser_mean" in summary
        else float(np.mean(ratio_pulser))
    )
    min_ratio = (
        float(summary["ratio_pulser_min"])
        if summary and "ratio_pulser_min" in summary
        else float(np.min(ratio_pulser))
    )
    max_ratio = (
        float(summary["ratio_pulser_max"])
        if summary and "ratio_pulser_max" in summary
        else float(np.max(ratio_pulser))
    )

    fig, (ax_ratio, ax_map) = plt.subplots(
        2,
        1,
        figsize=(8.2, 6.2),
        sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1.0], "hspace": 0.08},
    )
    fig.subplots_adjust(bottom=0.13)

    colors = plt.cm.viridis(np.linspace(0.18, 0.82, len(results)))
    ax_ratio.bar(
        x,
        ratio_pulser,
        color=colors,
        edgecolor="black",
        linewidth=0.7,
        alpha=0.88,
        label="Séquence smooth Pulser",
    )
    ax_ratio.plot(
        x,
        ratio_proxy,
        color="black",
        marker="o",
        markersize=5,
        linewidth=1.8,
        label="Proxy exact après embedding",
    )
    ax_ratio.axhline(
        mean_ratio,
        color="#b3261e",
        linestyle="--",
        linewidth=1.6,
        label=f"Moyenne Pulser = {mean_ratio:.2f}",
    )
    ax_ratio.fill_between(
        [-0.5, len(results) - 0.5],
        min_ratio,
        max_ratio,
        color="#b3261e",
        alpha=0.08,
        label=f"Intervalle Pulser [{min_ratio:.2f}, {max_ratio:.2f}]",
    )
    ax_ratio.set_ylabel("Ratio d'approximation", fontsize=11)
    ax_ratio.set_ylim(0.0, max(1.05, float(np.max(ratio_proxy)) * 1.08))
    ax_ratio.grid(True, axis="y", alpha=0.25)
    ax_ratio.legend(loc="upper right", fontsize=9, frameon=True)
    ax_ratio.set_title(
        "Robustesse d'une séquence smooth fixée sur 10 graphes aléatoires (n=4)",
        fontsize=12,
        pad=10,
    )

    ax_map.plot(
        x,
        mapping_error,
        color="#1f6f8b",
        marker="s",
        markersize=5,
        linewidth=1.7,
    )
    ax_map.set_yscale("log")
    ax_map.set_ylabel("Erreur de mapping", fontsize=11)
    ax_map.set_xlabel("Instance de graphe aléatoire", fontsize=11)
    ax_map.set_xticks(x)
    ax_map.set_xticklabels([])
    ax_map.tick_params(axis="x", length=0)
    ax_map.grid(True, axis="y", alpha=0.25)

    note = (
        "La variabilité du ratio Pulser contraste avec une erreur de mapping faible, "
        "ce qui pointe vers une limitation dynamique."
    )
    fig.text(0.5, 0.012, note, ha="center", va="bottom", fontsize=9)

    if save_paths:
        if isinstance(save_paths, (str, bytes)):
            save_paths = [save_paths]
        for save_path in save_paths:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")

    if show:
        plt.show()
    else:
        plt.close(fig)
