import numpy as np

from quantum_optmization import optimize_atom_positions

from .pulser_core import compute_edge_correlators
from .pulser_smooth import evaluate_smooth_pulser_final_state


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


def evaluate_fixed_smooth_sequence_on_graph(
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
    max_iter=500,
    tol=1e-5,
):
    positions, couplings, mapping_error = optimize_atom_positions(
        target_edges,
        n=n,
        max_iter=max_iter,
        tol=tol,
    )

    out = evaluate_smooth_pulser_final_state(
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
    )
    corrs = compute_edge_correlators(out["rho_T"], n, target_edges)

    return {
        "n": int(n),
        "target_edges": [
            {"i": int(i), "j": int(j), "w": float(w)}
            for i, j, w in target_edges
        ],
        "positions": np.asarray(positions, dtype=float).tolist(),
        "couplings": [(int(i), int(j), float(J)) for i, j, J in couplings],
        "mapping_error": float(mapping_error),
        "E0_qmc": float(out["E0_qmc"]),
        "E0_r": float(out["E0_r"]),
        "E_proxy_exact_in_qmc": float(out["E_proxy_exact_in_qmc"]),
        "E_pulser_in_qmc": float(out["E_pulser_in_qmc"]),
        "E_pulser_in_proxy": float(out["E_pulser_in_proxy"]),
        "ratio_proxy_exact": float(out["ratio_proxy_exact"]),
        "ratio_pulser": float(out["ratio_pulser"]),
        "overlap_proxy": float(out["overlap_proxy"]),
        "correlators": [
            {
                "edge": [int(item["edge"][0]), int(item["edge"][1])],
                "w": float(item["w"]),
                "xx": float(item["xx"]),
                "yy": float(item["yy"]),
                "zz": float(item["zz"]),
                "t": float(item["t"]),
            }
            for item in corrs
        ],
    }


def study_fixed_smooth_sequence_on_random_graphs(
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
    max_iter=500,
    tol=1e-5,
    n_instances=None,
    n_graphs=None,
    require_connected=True,
):
    if n_instances is None:
        n_instances = n_graphs
    if n_instances is None:
        raise ValueError("Il faut fournir n_instances ou n_graphs.")

    all_results = []
    rng = np.random.default_rng(seed)

    for instance in range(n_instances):
        print(f"\n--- Graphe aléatoire {instance + 1}/{n_instances} ---")

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

        result = evaluate_fixed_smooth_sequence_on_graph(
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
            max_iter=max_iter,
            tol=tol,
        )

        result["graph_id"] = int(instance)
        all_results.append(result)

        print(f"Erreur mapping     = {result['mapping_error']:.6f}")
        print(f"Ratio proxy exact  = {result['ratio_proxy_exact']:.6f}")
        print(f"Ratio Pulser       = {result['ratio_pulser']:.6f}")
        print(f"Overlap proxy      = {result['overlap_proxy']:.6f}")

    ratios = np.array([r["ratio_pulser"] for r in all_results], dtype=float)
    overlaps = np.array([r["overlap_proxy"] for r in all_results], dtype=float)
    mapping_errors = np.array([r["mapping_error"] for r in all_results], dtype=float)
    proxy_ratios = np.array([r["ratio_proxy_exact"] for r in all_results], dtype=float)

    summary = {
        "n": int(n),
        "n_graphs": int(n_instances),
        "edge_prob": float(edge_prob),
        "w_min": float(w_min),
        "w_max": float(w_max),
        "ratio_pulser_mean": float(np.mean(ratios)),
        "ratio_pulser_min": float(np.min(ratios)),
        "ratio_pulser_max": float(np.max(ratios)),
        "overlap_mean": float(np.mean(overlaps)),
        "overlap_min": float(np.min(overlaps)),
        "overlap_max": float(np.max(overlaps)),
        "mapping_error_mean": float(np.mean(mapping_errors)),
        "mapping_error_max": float(np.max(mapping_errors)),
        "ratio_proxy_exact_mean": float(np.mean(proxy_ratios)),
        "ratio_proxy_exact_min": float(np.min(proxy_ratios)),
        "ratio_proxy_exact_max": float(np.max(proxy_ratios)),
    }

    return {
        "summary": summary,
        "results": all_results,
    }
