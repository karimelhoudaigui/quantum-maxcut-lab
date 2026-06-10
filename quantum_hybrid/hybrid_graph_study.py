"""
Study helpers for the full hybrid pipeline on random weighted graphs.

This module mirrors the existing Pulser-only graph study:
- generate random connected weighted graphs
- optimize atom positions
- run the fixed smooth Pulser sequence
- run the hybrid post-processing SDP + multiple roundings
- summarize and optionally plot the results
"""

import os

os.environ.setdefault("MPLCONFIGDIR", "/tmp")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from quantum_optmization import optimize_atom_positions
from quantum_pulser import compute_edge_correlators, evaluate_smooth_pulser_final_state

from .hybrid_core import run_hybrid_on_pulser_output


def _study_n_label(results=None, summary=None, scaling_summary=None):
    """
    Récupère la taille n depuis les sorties disponibles pour garder des titres
    et fichiers cohérents quelle que soit la taille étudiée.
    """
    if summary is not None and "n" in summary:
        return int(summary["n"])
    if results:
        first = results[0]
        if isinstance(first, dict) and "n" in first:
            return int(first["n"])
    if scaling_summary:
        first = scaling_summary[0]
        if isinstance(first, dict) and "n" in first:
            return int(first["n"])
    return None


def _is_connected(n, edges):
    if n == 0:
        return True

    adj = {i: set() for i in range(n)}
    for i, j, _ in edges:
        adj[i].add(j)
        adj[j].add(i)

    visited = set()
    stack = [0]
    while stack:
        u = stack.pop()
        if u in visited:
            continue
        visited.add(u)
        stack.extend(adj[u] - visited)

    return len(visited) == n


def generate_random_weighted_graph(
    n,
    edge_prob=0.6,
    w_min=0.5,
    w_max=1.5,
    seed=None,
    rng=None,
    require_connected=True,
):
    if rng is None:
        rng = np.random.default_rng(seed)

    while True:
        edges = []
        for i in range(n):
            for j in range(i + 1, n):
                if rng.random() < edge_prob:
                    w = rng.uniform(w_min, w_max)
                    edges.append((i, j, float(w)))

        if not edges:
            continue

        if require_connected and not _is_connected(n, edges):
            continue

        return edges


def evaluate_fixed_hybrid_sequence_on_graph(
    n,
    target_edges,
    omega_prep,
    prep_duration,
    omega_peak,
    rise_duration,
    hold_duration,
    fall_duration,
    delta_start,
    delta_hold,
    delta_end,
    sampling_rate=0.05,
    scale=15.5,
    n_roundings=64,
    seed=1234,
    max_iter=500,
    tol=1e-5,
    proxy_hamiltonian="rydberg_xy",
):
    positions, couplings, mapping_error = optimize_atom_positions(
        target_edges,
        n=n,
        max_iter=max_iter,
        tol=tol,
    )

    pulser_out = evaluate_smooth_pulser_final_state(
        n=n,
        positions=positions,
        target_edges=target_edges,
        omega_prep=omega_prep,
        prep_duration=prep_duration,
        omega_peak=omega_peak,
        rise_duration=rise_duration,
        hold_duration=hold_duration,
        fall_duration=fall_duration,
        delta_start=delta_start,
        delta_hold=delta_hold,
        delta_end=delta_end,
        sampling_rate=sampling_rate,
        scale=scale,
        proxy_hamiltonian=proxy_hamiltonian,
    )

    corrs = compute_edge_correlators(pulser_out["rho_T"], n, target_edges)

    hybrid_out = run_hybrid_on_pulser_output(
        n=n,
        target_edges=target_edges,
        pulser_out=pulser_out,
        corrs=corrs,
        seed=seed,
        n_roundings=n_roundings,
        proxy_hamiltonian=proxy_hamiltonian,
    )

    return {
        "n": int(n),
        "target_edges": [
            {"i": int(i), "j": int(j), "w": float(w)}
            for i, j, w in target_edges
        ],
        "positions": np.asarray(positions, dtype=float).tolist(),
        "couplings": [(int(i), int(j), float(J)) for i, j, J in couplings],
        "mapping_error": float(mapping_error),
        "ratio_proxy_exact": float(pulser_out["ratio_proxy_exact"]),
        "ratio_pulser": float(pulser_out["ratio_pulser"]),
        "ratio_product_best": float(hybrid_out["ratio_product"]),
        "ratio_hybrid": float(hybrid_out["ratio_hybrid"]),
        "winner": str(hybrid_out["winner"]),
        "best_seed": int(hybrid_out["best_rounding_seed"]),
        "n_roundings": int(hybrid_out["n_roundings"]),
        "sdp_status": str(hybrid_out["sdp_status"]),
        "E_pulser_in_qmc": float(pulser_out["E_pulser_in_qmc"]),
        "E_product_best_in_qmc": float(hybrid_out["E_product_in_qmc"]),
        "E_hybrid_in_qmc": float(hybrid_out["E_hybrid_in_qmc"]),
        "proxy_hamiltonian": str(pulser_out["proxy_hamiltonian"]),
        "proxy_label": str(pulser_out["proxy_label"]),
        "proxy_required_correlators": list(pulser_out["proxy_required_correlators"]),
        "proxy_experimental": bool(pulser_out["proxy_experimental"]),
        "proxy_sdp_note": str(hybrid_out["proxy_sdp_note"]),
        "sdp_formulation": str(hybrid_out["sdp_formulation"]),
        "preparation_mode": str(pulser_out["preparation_mode"]),
    }


def study_fixed_hybrid_sequence_on_random_graphs(
    n,
    omega_prep,
    prep_duration,
    omega_peak,
    rise_duration,
    hold_duration,
    fall_duration,
    delta_start,
    delta_hold,
    delta_end,
    edge_prob=0.6,
    w_min=0.5,
    w_max=1.5,
    seed=42,
    sampling_rate=0.05,
    scale=15.5,
    n_roundings=64,
    max_iter=500,
    tol=1e-5,
    n_instances=None,
    n_graphs=None,
    require_connected=True,
    proxy_hamiltonian="rydberg_xy",
):
    if n < 1:
        raise ValueError("n doit être un entier strictement positif.")

    if n_instances is None:
        n_instances = n_graphs
    if n_instances is None:
        raise ValueError("Il faut fournir n_instances ou n_graphs.")

    all_results = []
    rng = np.random.default_rng(seed)

    for instance in range(n_instances):
        print(f"\n--- Graphe hybride {instance + 1}/{n_instances} ---")

        target_edges = generate_random_weighted_graph(
            n=n,
            edge_prob=edge_prob,
            w_min=w_min,
            w_max=w_max,
            rng=rng,
            require_connected=require_connected,
        )

        print("Arêtes :")
        for i, j, w in target_edges:
            print(f"  ({i},{j}) -> w = {w:.6f}")

        result = evaluate_fixed_hybrid_sequence_on_graph(
            n=n,
            target_edges=target_edges,
            omega_prep=omega_prep,
            prep_duration=prep_duration,
            omega_peak=omega_peak,
            rise_duration=rise_duration,
            hold_duration=hold_duration,
            fall_duration=fall_duration,
            delta_start=delta_start,
            delta_hold=delta_hold,
            delta_end=delta_end,
            sampling_rate=sampling_rate,
            scale=scale,
            n_roundings=n_roundings,
            seed=seed + instance,
            max_iter=max_iter,
            tol=tol,
            proxy_hamiltonian=proxy_hamiltonian,
        )

        result["graph_id"] = int(instance)
        all_results.append(result)

        print(f"Erreur mapping     = {result['mapping_error']:.6f}")
        print(f"Ratio proxy exact  = {result['ratio_proxy_exact']:.6f}")
        print(f"Ratio Pulser       = {result['ratio_pulser']:.6f}")
        print(f"Ratio Product best = {result['ratio_product_best']:.6f}")
        print(f"Ratio Hybrid       = {result['ratio_hybrid']:.6f}")
        print(f"Winner             = {result['winner']}")
        print(f"Proxy Hamiltonian  = {result['proxy_hamiltonian']}")

    ratios_pulser = np.array([r["ratio_pulser"] for r in all_results], dtype=float)
    ratios_product = np.array([r["ratio_product_best"] for r in all_results], dtype=float)
    ratios_hybrid = np.array([r["ratio_hybrid"] for r in all_results], dtype=float)
    mapping_errors = np.array([r["mapping_error"] for r in all_results], dtype=float)
    proxy_ratios = np.array([r["ratio_proxy_exact"] for r in all_results], dtype=float)

    rounding_win_count = sum(1 for r in all_results if r["winner"] == "rounding")
    pulser_win_count = sum(1 for r in all_results if r["winner"] == "pulser")

    summary = {
        "n": int(n),
        "n_graphs": int(n_instances),
        "edge_prob": float(edge_prob),
        "w_min": float(w_min),
        "w_max": float(w_max),
        "ratio_pulser_mean": float(np.mean(ratios_pulser)),
        "ratio_pulser_min": float(np.min(ratios_pulser)),
        "ratio_pulser_max": float(np.max(ratios_pulser)),
        "ratio_product_mean": float(np.mean(ratios_product)),
        "ratio_product_min": float(np.min(ratios_product)),
        "ratio_product_max": float(np.max(ratios_product)),
        "ratio_hybrid_mean": float(np.mean(ratios_hybrid)),
        "ratio_hybrid_min": float(np.min(ratios_hybrid)),
        "ratio_hybrid_max": float(np.max(ratios_hybrid)),
        "mapping_error_mean": float(np.mean(mapping_errors)),
        "mapping_error_max": float(np.max(mapping_errors)),
        "ratio_proxy_exact_mean": float(np.mean(proxy_ratios)),
        "rounding_win_count": int(rounding_win_count),
        "pulser_win_count": int(pulser_win_count),
    }

    return {
        "summary": summary,
        "results": all_results,
    }


def plot_hybrid_graph_study(results, summary=None, save_path=None, show=True):
    """
    Plot simple comparant ratio Pulser, meilleur ratio produit, et ratio hybride
    pour chaque graphe.
    """
    graph_ids = [int(r["graph_id"]) for r in results]
    ratio_pulser = [float(r["ratio_pulser"]) for r in results]
    ratio_product = [float(r["ratio_product_best"]) for r in results]
    ratio_hybrid = [float(r["ratio_hybrid"]) for r in results]

    x = np.arange(len(graph_ids), dtype=float)
    width = 0.24

    plt.figure(figsize=(12, 5.8))
    plt.bar(x - width, ratio_pulser, width=width, label="Pulser", color="#4C78A8")
    plt.bar(x, ratio_product, width=width, label="SDP + rounding", color="#F58518")
    plt.bar(x + width, ratio_hybrid, width=width, label="Hybrid final", color="#54A24B")

    study_n = _study_n_label(results=results, summary=summary)
    title = "Hybrid graph study"
    if study_n is not None:
        title += f" at n={study_n}"

    plt.xlabel("Graph instances", fontsize=12)
    plt.ylabel("Approximation ratio", fontsize=12)
    plt.title(title, fontsize=14, pad=12)
    plt.xticks(x, [str(g + 1) for g in graph_ids], fontsize=9)
    plt.grid(axis="y", alpha=0.25)
    plt.legend(frameon=False)

    if summary is not None:
        text = (
            f"mean Pulser={summary['ratio_pulser_mean']:.3f}   "
            f"mean Product={summary['ratio_product_mean']:.3f}   "
            f"mean Hybrid={summary['ratio_hybrid_mean']:.3f}"
        )
        plt.suptitle(text, y=0.98, fontsize=10)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=250, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()


def plot_hybrid_vs_pulser_scatter(results, save_path=None, show=True):
    """
    Scatter plot : x = ratio Pulser, y = ratio Hybrid, avec diagonale y = x.
    """
    ratio_pulser = np.array([float(r["ratio_pulser"]) for r in results], dtype=float)
    ratio_hybrid = np.array([float(r["ratio_hybrid"]) for r in results], dtype=float)

    low = float(min(np.min(ratio_pulser), np.min(ratio_hybrid)))
    high = float(max(np.max(ratio_pulser), np.max(ratio_hybrid)))
    pad = 0.03 * max(high - low, 1e-6)

    plt.figure(figsize=(6.8, 6.0))
    plt.scatter(ratio_pulser, ratio_hybrid, s=52, color="#4C78A8", alpha=0.8, edgecolors="white", linewidths=0.5)
    plt.plot([low - pad, high + pad], [low - pad, high + pad], linestyle="--", color="#777777", linewidth=1.5)
    plt.xlabel("Pulser ratio", fontsize=12)
    plt.ylabel("Hybrid ratio", fontsize=12)
    plt.title("Hybrid vs Pulser", fontsize=14, pad=10)
    plt.xlim(low - pad, high + pad)
    plt.ylim(low - pad, high + pad)
    plt.grid(alpha=0.25)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=250, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()


def plot_hybrid_distribution(results, save_path=None, show=True):
    """
    Histogrammes comparant les distributions des ratios Pulser et Hybrid.
    """
    ratio_pulser = np.array([float(r["ratio_pulser"]) for r in results], dtype=float)
    ratio_hybrid = np.array([float(r["ratio_hybrid"]) for r in results], dtype=float)

    low = float(min(np.min(ratio_pulser), np.min(ratio_hybrid)))
    high = float(max(np.max(ratio_pulser), np.max(ratio_hybrid)))
    if abs(high - low) < 1e-12:
        high = low + 1e-3
    bins = np.linspace(low, high, 14)

    plt.figure(figsize=(7.4, 5.2))
    plt.hist(ratio_pulser, bins=bins, alpha=0.6, label="Pulser", color="#4C78A8", edgecolor="white")
    plt.hist(ratio_hybrid, bins=bins, alpha=0.6, label="Hybrid", color="#54A24B", edgecolor="white")
    plt.xlabel("Approximation ratio", fontsize=12)
    plt.ylabel("Count", fontsize=12)
    plt.title("Ratio distributions", fontsize=14, pad=10)
    plt.legend(frameon=False)
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=250, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()


def plot_hybrid_scaling_summary(scaling_summary, save_path=None, show=True):
    """
    Figure globale des moyennes en fonction de la taille d'échantillon.
    """
    x = [int(row["n_graphs"]) for row in scaling_summary]
    y_pulser = [float(row["ratio_pulser_mean"]) for row in scaling_summary]
    y_product = [float(row["ratio_product_mean"]) for row in scaling_summary]
    y_hybrid = [float(row["ratio_hybrid_mean"]) for row in scaling_summary]

    plt.figure(figsize=(7.8, 5.0))
    plt.plot(x, y_pulser, marker="o", linewidth=2, markersize=7, color="#4C78A8", label="Pulser")
    plt.plot(x, y_product, marker="s", linewidth=2, markersize=7, color="#F58518", label="Product / rounding")
    plt.plot(x, y_hybrid, marker="^", linewidth=2, markersize=7, color="#54A24B", label="Hybrid final")
    study_n = _study_n_label(scaling_summary=scaling_summary)
    title = "Hybrid scaling"
    if study_n is not None:
        title += f" at n={study_n}"
    plt.xlabel("Number of graphs", fontsize=12)
    plt.ylabel("Mean approximation ratio", fontsize=12)
    plt.title(title, fontsize=14, pad=10)
    plt.xticks(x, [str(v) for v in x])
    plt.grid(alpha=0.25)
    plt.legend(frameon=False)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=250, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()
