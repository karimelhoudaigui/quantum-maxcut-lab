import os

os.environ.setdefault("MPLCONFIGDIR", "/tmp")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from quantum_benchmark import analyze_instance
from quantum_hybrid.hybrid_graph_study import (
    evaluate_fixed_hybrid_sequence_on_graph,
    generate_random_weighted_graph,
)


GRAPH_DESCRIPTOR_KEYS = [
    "n_edges",
    "density",
    "avg_degree",
    "max_degree",
    "degree_variance",
    "hub_count",
    "sparsity",
    "clustering_coeff_mean",
    "degree_centralization",
]


def _edge_list_to_adjacency(n, target_edges):
    adj = {i: set() for i in range(n)}
    for i, j, _ in target_edges:
        i = int(i)
        j = int(j)
        adj[i].add(j)
        adj[j].add(i)
    return adj


def _edge_key_set(target_edges):
    return {
        (min(int(i), int(j)), max(int(i), int(j)))
        for i, j, _ in target_edges
    }


def _mean_local_clustering(adjacency):
    coeffs = []
    for node, neighbors in adjacency.items():
        k = len(neighbors)
        if k < 2:
            coeffs.append(0.0)
            continue

        links = 0
        neighbors = list(neighbors)
        for idx, u in enumerate(neighbors):
            for v in neighbors[idx + 1 :]:
                if v in adjacency[u]:
                    links += 1

        coeffs.append(2.0 * links / (k * (k - 1)))

    return float(np.mean(coeffs)) if coeffs else 0.0


def compute_graph_descriptors(n, target_edges, hub_degree_threshold=None):
    """
    Descripteurs simples de structure de graphe, sans dépendance externe.
    """
    n = int(n)
    adjacency = _edge_list_to_adjacency(n, target_edges)
    degrees = np.array([len(adjacency[i]) for i in range(n)], dtype=float)

    n_edges = int(len(target_edges))
    density = 2.0 * n_edges / (n * (n - 1)) if n > 1 else 0.0
    avg_degree = float(np.mean(degrees)) if n > 0 else 0.0
    max_degree = int(np.max(degrees)) if n > 0 else 0
    degree_variance = float(np.var(degrees)) if n > 0 else 0.0

    if hub_degree_threshold is None:
        hub_degree_threshold = max(2, int(np.ceil(n / 2)))
    hub_count = int(np.sum(degrees >= hub_degree_threshold))

    sparsity = float(1.0 - density)
    clustering_coeff_mean = _mean_local_clustering(adjacency)

    if n <= 2:
        degree_centralization = 0.0
    else:
        degree_centralization = float(
            np.sum(max_degree - degrees) / ((n - 1) * (n - 2))
        )

    return {
        "n": n,
        "n_edges": n_edges,
        "density": float(density),
        "avg_degree": avg_degree,
        "max_degree": max_degree,
        "degree_variance": degree_variance,
        "hub_degree_threshold": int(hub_degree_threshold),
        "hub_count": hub_count,
        "sparsity": sparsity,
        "clustering_coeff_mean": clustering_coeff_mean,
        "degree_centralization": degree_centralization,
    }


def classify_graph_structure(n, target_edges, descriptors=None):
    """
    Classification interprétable des graphes pour l'analyse qualitative.
    """
    if descriptors is None:
        descriptors = compute_graph_descriptors(n, target_edges)

    density = float(descriptors["density"])
    max_degree = int(descriptors["max_degree"])
    hub_threshold = int(descriptors["hub_degree_threshold"])
    n_edges = int(descriptors["n_edges"])
    adjacency = _edge_list_to_adjacency(n, target_edges)
    degrees = [len(adjacency[i]) for i in range(n)]
    edge_keys = _edge_key_set(target_edges)

    if n_edges == n * (n - 1) // 2:
        structure_bucket = "complete"
    elif density <= 0.34:
        structure_bucket = "sparse"
    elif density <= 0.67:
        structure_bucket = "medium"
    else:
        structure_bucket = "dense"

    hub_bucket = "hub" if max_degree >= hub_threshold else "no_hub"

    graph_family = "generic_random"
    if n >= 2 and n_edges == n - 1 and sorted(degrees) == [1, 1] + [2] * max(0, n - 2):
        graph_family = "path"
    elif n >= 3 and all(d == 2 for d in degrees) and n_edges == n:
        graph_family = "cycle"
    elif n >= 4 and sorted(degrees) == [1] * (n - 1) + [n - 1]:
        graph_family = "star"
    elif n_edges == n * (n - 1) // 2:
        graph_family = "complete"
    elif n == 4 and edge_keys == {(0, 1), (1, 2), (2, 3), (0, 3)}:
        graph_family = "square"
    elif n == 4 and edge_keys == {(0, 1), (1, 2), (2, 3), (0, 3), (0, 2), (1, 3)}:
        graph_family = "complete"
    elif n == 4 and all(d == 2 for d in degrees) and n_edges == 4:
        graph_family = "square"

    return {
        "structure_bucket": structure_bucket,
        "hub_bucket": hub_bucket,
        "graph_family": graph_family,
    }


def _serialize_edges(target_edges):
    return [
        {"i": int(i), "j": int(j), "w": float(w)}
        for i, j, w in target_edges
    ]


def evaluate_graph_structure_proxy_instance(
    n,
    target_edges,
    graph_id=None,
):
    """
    Niveau A : mapping + proxy exact uniquement.
    """
    descriptors = compute_graph_descriptors(n, target_edges)
    out = analyze_instance(n=n, target_edges=target_edges, instance_id=graph_id, do_plot=False)

    categories = classify_graph_structure(n, target_edges, descriptors=descriptors)

    return {
        "graph_id": int(graph_id) if graph_id is not None else None,
        **descriptors,
        **categories,
        "mapping_error": float(out["mapping_error"]),
        "ratio_proxy_exact": float(out["ratio"]),
        "ratio_pulser": None,
        "ratio_hybrid": None,
        "winner": None,
        "target_edges": _serialize_edges(target_edges),
    }


def evaluate_graph_structure_hybrid_instance(
    n,
    target_edges,
    graph_id=None,
    omega_prep=2 * np.pi * 2.0,
    prep_duration=125,
    omega_peak=2 * np.pi * 2.0,
    rise_duration=1000,
    hold_duration=1000,
    fall_duration=26000,
    delta_start=np.pi,
    delta_hold=-np.pi / 2,
    delta_end=-np.pi,
    sampling_rate=0.05,
    scale=15.5,
    n_roundings=64,
    seed=1234,
    max_iter=500,
    tol=1e-5,
):
    """
    Niveau B : pipeline hybride complet réutilisé tel quel.
    """
    descriptors = compute_graph_descriptors(n, target_edges)
    out = evaluate_fixed_hybrid_sequence_on_graph(
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
        seed=seed,
        max_iter=max_iter,
        tol=tol,
    )

    categories = classify_graph_structure(n, target_edges, descriptors=descriptors)

    return {
        "graph_id": int(graph_id) if graph_id is not None else None,
        **descriptors,
        **categories,
        "mapping_error": float(out["mapping_error"]),
        "ratio_proxy_exact": float(out["ratio_proxy_exact"]),
        "ratio_pulser": float(out["ratio_pulser"]),
        "ratio_hybrid": float(out["ratio_hybrid"]),
        "winner": str(out["winner"]),
        "target_edges": out["target_edges"],
    }


def _summary_stats(values):
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"mean": np.nan, "min": np.nan, "max": np.nan}
    return {
        "mean": float(np.mean(finite)),
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
    }


def _safe_corr(x_values, y_values):
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if np.sum(mask) < 2:
        return np.nan
    x = x[mask]
    y = y[mask]
    if np.allclose(x, x[0]) or np.allclose(y, y[0]):
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def _coerce_metric_array(results, key):
    values = []
    for result in results:
        value = result.get(key, np.nan)
        if value is None:
            value = np.nan
        values.append(float(value))
    return np.asarray(values, dtype=float)


def summarize_graph_structure_results(results):
    if not results:
        raise ValueError("La liste results est vide.")

    metric_keys = ["mapping_error", "ratio_proxy_exact", "ratio_pulser", "ratio_hybrid"]

    summary = {
        "n": int(results[0]["n"]),
        "n_graphs": int(len(results)),
        "metrics": {},
        "correlations": {},
    }

    for key in GRAPH_DESCRIPTOR_KEYS + metric_keys:
        summary["metrics"][key] = _summary_stats([r.get(key, np.nan) for r in results])

    for target_key in metric_keys:
        target_values = _coerce_metric_array(results, target_key)
        if not np.any(np.isfinite(target_values)):
            continue
        summary["correlations"][target_key] = {
            descriptor: _safe_corr(
                [r.get(descriptor, np.nan) for r in results],
                target_values,
            )
            for descriptor in GRAPH_DESCRIPTOR_KEYS
        }

    winners = [r.get("winner") for r in results if r.get("winner") is not None]
    if winners:
        summary["winner_counts"] = {
            "pulser": int(sum(w == "pulser" for w in winners)),
            "rounding": int(sum(w == "rounding" for w in winners)),
        }

    return summary


def _summarize_metric_for_group(group, key):
    return _summary_stats([item.get(key, np.nan) for item in group])


def summarize_graph_categories(results):
    if not results:
        raise ValueError("La liste results est vide.")

    category_keys = ["structure_bucket", "hub_bucket", "graph_family"]
    metric_keys = ["mapping_error", "ratio_proxy_exact", "ratio_pulser", "ratio_hybrid"]
    summary = {
        "n": int(results[0]["n"]),
        "n_graphs": int(len(results)),
        "categories": {},
    }

    for category_key in category_keys:
        grouped = {}
        for result in results:
            label = result.get(category_key, "unknown")
            grouped.setdefault(label, []).append(result)

        summary["categories"][category_key] = {}
        for label, group in grouped.items():
            row = {
                "count": int(len(group)),
                "metrics": {
                    metric: _summarize_metric_for_group(group, metric)
                    for metric in metric_keys
                },
            }
            winners = [g.get("winner") for g in group if g.get("winner") is not None]
            if winners:
                row["winner_counts"] = {
                    "pulser": int(sum(w == "pulser" for w in winners)),
                    "rounding": int(sum(w == "rounding" for w in winners)),
                }
            summary["categories"][category_key][label] = row

    return summary


def build_top_flop_summary(results, top_k=10):
    if not results:
        raise ValueError("La liste results est vide.")

    display_keys = [
        "graph_id",
        "density",
        "avg_degree",
        "max_degree",
        "structure_bucket",
        "hub_bucket",
        "graph_family",
        "mapping_error",
        "ratio_proxy_exact",
        "ratio_hybrid",
    ]

    def project(items):
        projected = []
        for item in items:
            projected.append({key: item.get(key) for key in display_keys})
        return projected

    def finite_sorted(key, reverse=False):
        finite = [
            result for result in results
            if result.get(key) is not None and np.isfinite(float(result[key]))
        ]
        return sorted(finite, key=lambda x: float(x[key]), reverse=reverse)

    output = {
        "best_mapping_error": project(finite_sorted("mapping_error", reverse=False)[:top_k]),
        "worst_mapping_error": project(finite_sorted("mapping_error", reverse=True)[:top_k]),
        "best_ratio_proxy_exact": project(finite_sorted("ratio_proxy_exact", reverse=True)[:top_k]),
        "worst_ratio_proxy_exact": project(finite_sorted("ratio_proxy_exact", reverse=False)[:top_k]),
    }

    hybrid_sorted = finite_sorted("ratio_hybrid", reverse=True)
    if hybrid_sorted:
        output["best_ratio_hybrid"] = project(hybrid_sorted[:top_k])
        output["worst_ratio_hybrid"] = project(list(reversed(hybrid_sorted[-top_k:])))

    return output


def build_graph_structure_conclusion(results, category_summary, level="proxy_exact"):
    structure_groups = category_summary["categories"]["structure_bucket"]

    def best_label(metric, reverse=True):
        candidates = []
        for label, row in structure_groups.items():
            value = row["metrics"][metric]["mean"]
            if np.isfinite(value):
                candidates.append((label, float(value)))
        if not candidates:
            return None, np.nan
        candidates.sort(key=lambda x: x[1], reverse=reverse)
        return candidates[0]

    best_mapping, best_mapping_val = best_label("mapping_error", reverse=False)
    worst_mapping, worst_mapping_val = best_label("mapping_error", reverse=True)
    best_proxy, best_proxy_val = best_label("ratio_proxy_exact", reverse=True)
    worst_proxy, worst_proxy_val = best_label("ratio_proxy_exact", reverse=False)

    lines = [
        f"Type de graphe qui se mappe le mieux : {best_mapping} (mapping_error moyen = {best_mapping_val:.6f})"
        if best_mapping is not None else "Aucun groupe exploitable pour mapping_error.",
        f"Type de graphe qui se mappe le moins bien : {worst_mapping} (mapping_error moyen = {worst_mapping_val:.6f})"
        if worst_mapping is not None else "",
        f"Type de graphe avec le meilleur ratio proxy : {best_proxy} (ratio_proxy_exact moyen = {best_proxy_val:.6f})"
        if best_proxy is not None else "",
        f"Type de graphe avec le plus faible ratio proxy : {worst_proxy} (ratio_proxy_exact moyen = {worst_proxy_val:.6f})"
        if worst_proxy is not None else "",
    ]

    if level == "hybrid":
        best_hybrid, best_hybrid_val = best_label("ratio_hybrid", reverse=True)
        worst_hybrid, worst_hybrid_val = best_label("ratio_hybrid", reverse=False)
        if best_hybrid is not None:
            lines.append(
                f"Type de graphe avec le meilleur ratio hybride : {best_hybrid} "
                f"(ratio_hybrid moyen = {best_hybrid_val:.6f})"
            )
        if worst_hybrid is not None:
            lines.append(
                f"Type de graphe avec le plus faible ratio hybride : {worst_hybrid} "
                f"(ratio_hybrid moyen = {worst_hybrid_val:.6f})"
            )

    return [line for line in lines if line]


def study_graph_structure_on_random_graphs(
    n,
    n_graphs,
    level="proxy_exact",
    edge_prob=0.6,
    w_min=0.5,
    w_max=1.5,
    seed=42,
    require_connected=True,
    omega_prep=2 * np.pi * 2.0,
    prep_duration=125,
    omega_peak=2 * np.pi * 2.0,
    rise_duration=1000,
    hold_duration=1000,
    fall_duration=26000,
    delta_start=np.pi,
    delta_hold=-np.pi / 2,
    delta_end=-np.pi,
    sampling_rate=0.05,
    scale=15.5,
    n_roundings=64,
    max_iter=500,
    tol=1e-5,
):
    level = str(level).lower()
    if level not in {"proxy_exact", "hybrid"}:
        raise ValueError("level doit valoir 'proxy_exact' ou 'hybrid'.")

    rng = np.random.default_rng(seed)
    results = []

    for graph_id in range(int(n_graphs)):
        print(f"\n--- Graph structure study {graph_id + 1}/{n_graphs} | level={level} ---")
        target_edges = generate_random_weighted_graph(
            n=n,
            edge_prob=edge_prob,
            w_min=w_min,
            w_max=w_max,
            rng=rng,
            require_connected=require_connected,
        )

        if level == "proxy_exact":
            result = evaluate_graph_structure_proxy_instance(
                n=n,
                target_edges=target_edges,
                graph_id=graph_id,
            )
        else:
            result = evaluate_graph_structure_hybrid_instance(
                n=n,
                target_edges=target_edges,
                graph_id=graph_id,
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
                seed=seed + graph_id,
                max_iter=max_iter,
                tol=tol,
            )

        results.append(result)

        print(
            f"density={result['density']:.4f} | "
            f"avg_degree={result['avg_degree']:.4f} | "
            f"mapping_error={result['mapping_error']:.6f} | "
            f"ratio_proxy_exact={result['ratio_proxy_exact']:.6f}"
        )
        if result["ratio_pulser"] is not None:
            print(
                f"ratio_pulser={result['ratio_pulser']:.6f} | "
                f"ratio_hybrid={result['ratio_hybrid']:.6f} | "
                f"winner={result['winner']}"
            )

    summary = summarize_graph_structure_results(results)
    category_summary = summarize_graph_categories(results)
    top_flop = build_top_flop_summary(results)
    conclusion_lines = build_graph_structure_conclusion(results, category_summary, level=level)

    return {
        "results": results,
        "summary": summary,
        "category_summary": category_summary,
        "top_flop": top_flop,
        "conclusion_lines": conclusion_lines,
    }


def _scatter_from_results(
    results,
    x_key,
    y_key,
    save_path=None,
    show=True,
    xlabel=None,
    ylabel=None,
    title=None,
):
    pairs = [
        (float(r[x_key]), float(r[y_key]))
        for r in results
        if r.get(x_key) is not None and r.get(y_key) is not None
        and np.isfinite(float(r[x_key])) and np.isfinite(float(r[y_key]))
    ]
    if not pairs:
        raise ValueError(f"Aucune donnée exploitable pour {y_key} vs {x_key}.")

    x_values = np.array([p[0] for p in pairs], dtype=float)
    y_values = np.array([p[1] for p in pairs], dtype=float)

    plt.figure(figsize=(7.4, 5.2))
    plt.scatter(
        x_values,
        y_values,
        s=55,
        color="#2C7FB8",
        alpha=0.82,
        edgecolors="black",
        linewidths=0.45,
    )
    plt.xlabel(xlabel or x_key, fontsize=12)
    plt.ylabel(ylabel or y_key, fontsize=12)
    plt.title(title or f"{y_key} vs {x_key}", fontsize=14, pad=10)
    plt.grid(True, alpha=0.25)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=250, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()


def plot_mapping_vs_density(results, save_path=None, show=True):
    _scatter_from_results(
        results,
        x_key="density",
        y_key="mapping_error",
        save_path=save_path,
        show=show,
        xlabel="Densité du graphe",
        ylabel="Erreur de mapping",
        title="Erreur de mapping vs densité",
    )


def plot_mapping_vs_avg_degree(results, save_path=None, show=True):
    _scatter_from_results(
        results,
        x_key="avg_degree",
        y_key="mapping_error",
        save_path=save_path,
        show=show,
        xlabel="Degré moyen",
        ylabel="Erreur de mapping",
        title="Erreur de mapping vs degré moyen",
    )


def plot_mapping_vs_max_degree(results, save_path=None, show=True):
    _scatter_from_results(
        results,
        x_key="max_degree",
        y_key="mapping_error",
        save_path=save_path,
        show=show,
        xlabel="Degré maximal",
        ylabel="Erreur de mapping",
        title="Erreur de mapping vs degré maximal",
    )


def plot_proxy_vs_density(results, save_path=None, show=True):
    _scatter_from_results(
        results,
        x_key="density",
        y_key="ratio_proxy_exact",
        save_path=save_path,
        show=show,
        xlabel="Densité du graphe",
        ylabel="Ratio proxy exact",
        title="Ratio proxy exact vs densité",
    )


def plot_proxy_vs_avg_degree(results, save_path=None, show=True):
    _scatter_from_results(
        results,
        x_key="avg_degree",
        y_key="ratio_proxy_exact",
        save_path=save_path,
        show=show,
        xlabel="Degré moyen",
        ylabel="Ratio proxy exact",
        title="Ratio proxy exact vs degré moyen",
    )


def plot_hybrid_vs_density(results, save_path=None, show=True):
    _scatter_from_results(
        results,
        x_key="density",
        y_key="ratio_hybrid",
        save_path=save_path,
        show=show,
        xlabel="Densité du graphe",
        ylabel="Ratio hybride",
        title="Ratio hybride vs densité",
    )


def plot_mapping_error_by_connectivity_bucket(results, save_path=None, show=True):
    densities = np.array([float(r["density"]) for r in results], dtype=float)
    mapping_errors = np.array([float(r["mapping_error"]) for r in results], dtype=float)

    if densities.size == 0:
        raise ValueError("La liste results est vide.")

    q1, q2 = np.quantile(densities, [1.0 / 3.0, 2.0 / 3.0])
    buckets = {
        "densité faible": mapping_errors[densities <= q1],
        "densité moyenne": mapping_errors[(densities > q1) & (densities <= q2)],
        "densité élevée": mapping_errors[densities > q2],
    }

    labels = list(buckets.keys())
    values = [buckets[label] for label in labels]

    plt.figure(figsize=(7.4, 5.2))
    plt.boxplot(values, labels=labels, patch_artist=True)
    plt.ylabel("Erreur de mapping", fontsize=12)
    plt.title("Erreur de mapping par régime de connectivité", fontsize=14, pad=10)
    plt.grid(True, axis="y", alpha=0.25)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=250, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()


def _plot_metric_by_category(results, category_key, metric_key, save_path=None, show=True, title=None, ylabel=None):
    groups = {}
    for result in results:
        category = result.get(category_key)
        metric = result.get(metric_key)
        if category is None or metric is None:
            continue
        metric = float(metric)
        if not np.isfinite(metric):
            continue
        groups.setdefault(str(category), []).append(metric)

    if not groups:
        raise ValueError(f"Aucune donnée exploitable pour {metric_key} par {category_key}.")

    labels = list(groups.keys())
    values = [groups[label] for label in labels]

    plt.figure(figsize=(8.0, 5.2))
    plt.boxplot(values, tick_labels=labels, patch_artist=True)
    plt.ylabel(ylabel or metric_key, fontsize=12)
    plt.title(title or f"{metric_key} by {category_key}", fontsize=14, pad=10)
    plt.grid(True, axis="y", alpha=0.25)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=250, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()


def plot_mapping_by_graph_type(results, save_path=None, show=True):
    _plot_metric_by_category(
        results,
        category_key="structure_bucket",
        metric_key="mapping_error",
        save_path=save_path,
        show=show,
        title="Erreur de mapping par type de graphe",
        ylabel="Erreur de mapping",
    )


def plot_proxy_by_graph_type(results, save_path=None, show=True):
    _plot_metric_by_category(
        results,
        category_key="structure_bucket",
        metric_key="ratio_proxy_exact",
        save_path=save_path,
        show=show,
        title="Ratio proxy exact par type de graphe",
        ylabel="Ratio proxy exact",
    )


def plot_hybrid_by_graph_type(results, save_path=None, show=True):
    _plot_metric_by_category(
        results,
        category_key="structure_bucket",
        metric_key="ratio_hybrid",
        save_path=save_path,
        show=show,
        title="Ratio hybride par type de graphe",
        ylabel="Ratio hybride",
    )


def plot_mapping_by_graph_family(results, save_path=None, show=True):
    _plot_metric_by_category(
        results,
        category_key="graph_family",
        metric_key="mapping_error",
        save_path=save_path,
        show=show,
        title="Erreur de mapping par famille de graphe",
        ylabel="Erreur de mapping",
    )
