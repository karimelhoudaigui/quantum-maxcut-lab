import argparse
import csv
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("MPLCONFIGDIR", "/tmp")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from graph_structure_study import classify_graph_structure, compute_graph_descriptors
from quantum_hybrid.hybrid_graph_study import (
    evaluate_fixed_hybrid_sequence_on_graph,
    generate_random_weighted_graph,
)


DEFAULT_FAMILIES = [
    "path",
    "cycle",
    "star",
    "complete",
    "generic_random",
    "dense_random",
]


def _all_pairs(n):
    return [(i, j) for i in range(n) for j in range(i + 1, n)]


def _weighted_edges_from_pairs(pairs, rng, w_min, w_max):
    return [
        (int(i), int(j), float(rng.uniform(w_min, w_max)))
        for i, j in pairs
    ]


def generate_family_graph(family, n, rng, w_min=0.5, w_max=1.5):
    family = str(family).lower()

    if family == "path":
        pairs = [(i, i + 1) for i in range(n - 1)]
        return _weighted_edges_from_pairs(pairs, rng, w_min, w_max)

    if family == "cycle":
        if n < 3:
            raise ValueError("cycle nécessite n >= 3.")
        pairs = [(i, i + 1) for i in range(n - 1)] + [(0, n - 1)]
        return _weighted_edges_from_pairs(pairs, rng, w_min, w_max)

    if family == "star":
        if n < 4:
            raise ValueError("star nécessite n >= 4.")
        pairs = [(0, i) for i in range(1, n)]
        return _weighted_edges_from_pairs(pairs, rng, w_min, w_max)

    if family == "complete":
        pairs = _all_pairs(n)
        return _weighted_edges_from_pairs(pairs, rng, w_min, w_max)

    if family == "generic_random":
        return generate_random_weighted_graph(
            n=n,
            edge_prob=0.6,
            w_min=w_min,
            w_max=w_max,
            rng=rng,
            require_connected=True,
        )

    if family == "dense_random":
        return generate_random_weighted_graph(
            n=n,
            edge_prob=0.85,
            w_min=w_min,
            w_max=w_max,
            rng=rng,
            require_connected=True,
        )

    raise ValueError(f"Famille inconnue : {family}")


def run_full_hybrid_pipeline_on_graph(target_edges, family, n, instance_id, config):
    out = evaluate_fixed_hybrid_sequence_on_graph(
        n=n,
        target_edges=target_edges,
        omega_prep=config["omega_prep"],
        prep_duration=config["prep_duration"],
        omega_peak=config["omega_peak"],
        rise_duration=config["rise_duration"],
        hold_duration=config["hold_duration"],
        fall_duration=config["fall_duration"],
        delta_start=config["delta_start"],
        delta_hold=config["delta_hold"],
        delta_end=config["delta_end"],
        sampling_rate=config["sampling_rate"],
        scale=config["scale"],
        n_roundings=config["n_roundings"],
        seed=config["seed"] + instance_id,
        max_iter=config["max_iter"],
        tol=config["tol"],
    )

    descriptors = compute_graph_descriptors(n, target_edges)
    structure = classify_graph_structure(n, target_edges, descriptors=descriptors)

    ratio_pulser = float(out["ratio_pulser"])
    ratio_product = float(out["ratio_product_best"])
    ratio_hybrid = float(out["ratio_hybrid"])

    return {
        "family": family,
        "n": int(n),
        "instance_id": int(instance_id),
        "n_edges": int(descriptors["n_edges"]),
        "density": float(descriptors["density"]),
        "avg_degree": float(descriptors["avg_degree"]),
        "max_degree": int(descriptors["max_degree"]),
        "degree_variance": float(descriptors["degree_variance"]),
        "hub_count": int(descriptors["hub_count"]),
        "sparsity": float(descriptors["sparsity"]),
        "clustering_coeff_mean": float(descriptors["clustering_coeff_mean"]),
        "degree_centralization": float(descriptors["degree_centralization"]),
        "structure_bucket": structure["structure_bucket"],
        "hub_bucket": structure["hub_bucket"],
        "graph_family": structure["graph_family"],
        "mapping_error": float(out["mapping_error"]),
        "ratio_proxy_exact": float(out["ratio_proxy_exact"]),
        "ratio_pulser": ratio_pulser,
        "ratio_product": ratio_product,
        "ratio_hybrid": ratio_hybrid,
        "hybrid_gain": float(ratio_hybrid - ratio_pulser),
        "product_beats_pulser": bool(ratio_product > ratio_pulser),
        "winner": str(out["winner"]),
        "n_roundings": int(out["n_roundings"]),
        "sdp_status": str(out["sdp_status"]),
    }


def _summary_stats(values):
    values = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
    }


def summarize_by_family(results):
    grouped = {}
    for row in results:
        grouped.setdefault(row["family"], []).append(row)

    summary_rows = []
    for family, group in grouped.items():
        mapping_error = np.array([r["mapping_error"] for r in group], dtype=float)
        ratio_pulser = np.array([r["ratio_pulser"] for r in group], dtype=float)
        ratio_product = np.array([r["ratio_product"] for r in group], dtype=float)
        ratio_hybrid = np.array([r["ratio_hybrid"] for r in group], dtype=float)
        gains = np.array([r["hybrid_gain"] for r in group], dtype=float)
        wins = np.array([bool(r["product_beats_pulser"]) for r in group], dtype=bool)

        row = {
            "family": family,
            "N": int(len(group)),
            "map_err_mean": _summary_stats(mapping_error)["mean"],
            "map_err_min": _summary_stats(mapping_error)["min"],
            "map_err_max": _summary_stats(mapping_error)["max"],
            "pulser_mean": _summary_stats(ratio_pulser)["mean"],
            "product_mean": _summary_stats(ratio_product)["mean"],
            "hybrid_mean": _summary_stats(ratio_hybrid)["mean"],
            "gain_mean": _summary_stats(gains)["mean"],
            "hybrid_min": _summary_stats(ratio_hybrid)["min"],
            "hybrid_max": _summary_stats(ratio_hybrid)["max"],
            "win_rate": float(np.mean(wins)),
        }
        summary_rows.append(row)

    return sorted(summary_rows, key=lambda x: x["family"])


def save_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _family_color_map(families):
    palette = plt.cm.tab10(np.linspace(0, 1, max(len(families), 3)))
    return {family: palette[idx] for idx, family in enumerate(families)}


def plot_metric_by_family(results, metric_key, save_path, title, ylabel):
    grouped = {}
    for row in results:
        grouped.setdefault(row["family"], []).append(float(row[metric_key]))

    labels = list(grouped.keys())
    values = [grouped[label] for label in labels]

    plt.figure(figsize=(8.2, 5.2))
    plt.boxplot(values, tick_labels=labels, patch_artist=True)
    plt.ylabel(ylabel, fontsize=12)
    plt.title(title, fontsize=14, pad=10)
    plt.grid(True, axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(save_path, dpi=250, bbox_inches="tight")
    plt.close()


def plot_pulser_vs_hybrid_by_family(results, save_path):
    families = sorted({row["family"] for row in results})
    colors = _family_color_map(families)

    plt.figure(figsize=(6.8, 6.0))
    for family in families:
        subset = [row for row in results if row["family"] == family]
        x = np.array([row["ratio_pulser"] for row in subset], dtype=float)
        y = np.array([row["ratio_hybrid"] for row in subset], dtype=float)
        plt.scatter(
            x,
            y,
            label=family,
            s=55,
            alpha=0.82,
            color=colors[family],
            edgecolors="black",
            linewidths=0.4,
        )

    all_x = np.array([row["ratio_pulser"] for row in results], dtype=float)
    all_y = np.array([row["ratio_hybrid"] for row in results], dtype=float)
    low = float(min(np.min(all_x), np.min(all_y)))
    high = float(max(np.max(all_x), np.max(all_y)))
    pad = 0.03 * max(high - low, 1e-6)
    plt.plot([low - pad, high + pad], [low - pad, high + pad], "--", color="#666666", linewidth=1.4)
    plt.xlabel("Ratio Pulser", fontsize=12)
    plt.ylabel("Ratio hybride", fontsize=12)
    plt.title("Pulser vs hybride par famille", fontsize=14, pad=10)
    plt.legend(frameon=False)
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(save_path, dpi=250, bbox_inches="tight")
    plt.close()


def plot_ratio_vs_mapping_error_by_family(results, save_path):
    families = sorted({row["family"] for row in results})
    colors = _family_color_map(families)

    plt.figure(figsize=(7.2, 5.6))
    for family in families:
        subset = [row for row in results if row["family"] == family]
        x = np.array([row["mapping_error"] for row in subset], dtype=float)
        y = np.array([row["ratio_hybrid"] for row in subset], dtype=float)
        plt.scatter(
            x,
            y,
            label=family,
            s=55,
            alpha=0.82,
            color=colors[family],
            edgecolors="black",
            linewidths=0.4,
        )

    plt.xscale("log")
    plt.xlabel("Erreur de mapping", fontsize=12)
    plt.ylabel("Ratio hybride", fontsize=12)
    plt.title("Ratio hybride vs erreur de mapping", fontsize=14, pad=10)
    plt.legend(frameon=False)
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(save_path, dpi=250, bbox_inches="tight")
    plt.close()


def print_summary_table(summary_rows):
    print("\n===== Summary by graph family =====")
    print(
        f"{'family':<15} {'N':>4} {'map_err_mean':>14} {'pulser_mean':>14} "
        f"{'product_mean':>14} {'hybrid_mean':>14} {'gain_mean':>12} {'win_rate':>10}"
    )
    for row in summary_rows:
        print(
            f"{row['family']:<15} {row['N']:>4d} "
            f"{row['map_err_mean']:>14.6f} {row['pulser_mean']:>14.6f} "
            f"{row['product_mean']:>14.6f} {row['hybrid_mean']:>14.6f} "
            f"{row['gain_mean']:>12.6f} {row['win_rate']:>10.3f}"
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the full Pulser + SDP + rounding pipeline by graph family."
    )
    parser.add_argument("--n", type=int, required=True, help="Graph size.")
    parser.add_argument("--num-instances", type=int, default=20, help="Instances per family.")
    parser.add_argument("--seed", type=int, default=123, help="Random seed.")
    parser.add_argument(
        "--families",
        type=str,
        nargs="+",
        default=DEFAULT_FAMILIES,
        choices=DEFAULT_FAMILIES,
        help="Families to evaluate.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results_graph_families_full_pipeline",
        help="Directory where CSV and figures will be saved.",
    )
    parser.add_argument("--w-min", type=float, default=0.5, help="Minimum edge weight.")
    parser.add_argument("--w-max", type=float, default=1.5, help="Maximum edge weight.")
    parser.add_argument("--n-roundings", type=int, default=64, help="Number of rounding trials.")
    parser.add_argument("--sampling-rate", type=float, default=0.05, help="Pulser sampling rate.")
    parser.add_argument("--scale", type=float, default=15.5, help="Position scaling before Pulser.")
    parser.add_argument("--max-iter", type=int, default=500, help="Max iterations for geometry optimization.")
    parser.add_argument("--tol", type=float, default=1e-5, help="Tolerance for geometry optimization.")
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    config = {
        "omega_prep": 2 * np.pi * 2.0,
        "prep_duration": 125,
        "omega_peak": 2 * np.pi * 2.0,
        "rise_duration": 1000,
        "hold_duration": 1000,
        "fall_duration": 26000,
        "delta_start": np.pi,
        "delta_hold": -np.pi / 2,
        "delta_end": -np.pi,
        "sampling_rate": args.sampling_rate,
        "scale": args.scale,
        "n_roundings": args.n_roundings,
        "seed": args.seed,
        "max_iter": args.max_iter,
        "tol": args.tol,
    }

    results = []
    global_instance_id = 0

    for family in args.families:
        for local_idx in range(args.num_instances):
            target_edges = generate_family_graph(
                family=family,
                n=args.n,
                rng=rng,
                w_min=args.w_min,
                w_max=args.w_max,
            )
            row = run_full_hybrid_pipeline_on_graph(
                target_edges=target_edges,
                family=family,
                n=args.n,
                instance_id=global_instance_id,
                config=config,
            )
            results.append(row)
            global_instance_id += 1

            print(
                f"[family={family}] instance {local_idx + 1}/{args.num_instances} done | "
                f"pulser={row['ratio_pulser']:.6f} | "
                f"product={row['ratio_product']:.6f} | "
                f"hybrid={row['ratio_hybrid']:.6f} | "
                f"gain={row['hybrid_gain']:.6f}"
            )

    summary_rows = summarize_by_family(results)

    instance_fieldnames = [
        "family",
        "n",
        "instance_id",
        "n_edges",
        "density",
        "avg_degree",
        "max_degree",
        "degree_variance",
        "hub_count",
        "sparsity",
        "clustering_coeff_mean",
        "degree_centralization",
        "structure_bucket",
        "hub_bucket",
        "graph_family",
        "mapping_error",
        "ratio_proxy_exact",
        "ratio_pulser",
        "ratio_product",
        "ratio_hybrid",
        "hybrid_gain",
        "product_beats_pulser",
        "winner",
        "n_roundings",
        "sdp_status",
    ]
    summary_fieldnames = [
        "family",
        "N",
        "map_err_mean",
        "map_err_min",
        "map_err_max",
        "pulser_mean",
        "product_mean",
        "hybrid_mean",
        "gain_mean",
        "hybrid_min",
        "hybrid_max",
        "win_rate",
    ]

    save_csv(output_dir / "all_instances_results.csv", results, instance_fieldnames)
    save_csv(output_dir / "summary_by_family.csv", summary_rows, summary_fieldnames)

    plot_metric_by_family(
        results,
        metric_key="ratio_hybrid",
        save_path=output_dir / "ratio_hybrid_by_graph_family.png",
        title="Ratio hybride par famille de graphe",
        ylabel="Ratio hybride",
    )
    plot_metric_by_family(
        results,
        metric_key="hybrid_gain",
        save_path=output_dir / "gain_by_graph_family.png",
        title="Gain hybride par famille de graphe",
        ylabel="Gain hybride",
    )
    plot_pulser_vs_hybrid_by_family(
        results,
        save_path=output_dir / "pulser_vs_hybrid_by_family.png",
    )
    plot_metric_by_family(
        results,
        metric_key="mapping_error",
        save_path=output_dir / "mapping_error_by_family_full_pipeline.png",
        title="Erreur de mapping par famille",
        ylabel="Erreur de mapping",
    )
    plot_ratio_vs_mapping_error_by_family(
        results,
        save_path=output_dir / "ratio_vs_mapping_error_by_family.png",
    )

    print_summary_table(summary_rows)
    print(f"\nSaved outputs to: {output_dir}")


if __name__ == "__main__":
    main()
