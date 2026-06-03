"""
High-level hybrid orchestration helpers and shared graph utilities.

Role of this module:
- provide the common graph/matrix tools used by the hybrid pipeline
- normalize weighted MaxCut edge lists
- build weight matrices and graph Laplacians
- evaluate classical cut values and exact small-instance optima

In the full hybrid workflow, this module also orchestrates the post-processing:
Pulser correlations -> SDP -> rounding -> product-state evaluation -> final
comparison against the raw Pulser state.
"""

import itertools

import numpy as np


def normalize_edges(edges):
    normalized = []
    for i, j, w in edges:
        i = int(i)
        j = int(j)
        if i == j:
            continue
        if j < i:
            i, j = j, i
        normalized.append((i, j, float(w)))
    return normalized


def infer_n_from_edges(edges):
    edges = normalize_edges(edges)
    if not edges:
        return 0
    return max(max(i, j) for i, j, _ in edges) + 1


def weight_matrix(n, edges):
    W = np.zeros((n, n), dtype=float)
    for i, j, w in normalize_edges(edges):
        W[i, j] += float(w)
        W[j, i] += float(w)
    return W


def graph_laplacian(n, edges):
    W = weight_matrix(n, edges)
    degrees = np.sum(W, axis=1)
    return np.diag(degrees) - W


def cut_value(edges, assignment):
    assignment = np.asarray(assignment, dtype=int)
    value = 0.0
    for i, j, w in normalize_edges(edges):
        if assignment[i] != assignment[j]:
            value += float(w)
    return float(value)


def spin_to_assignment(spins):
    spins = np.asarray(spins, dtype=float)
    return (spins < 0).astype(int)


def assignment_to_spins(assignment):
    assignment = np.asarray(assignment, dtype=int)
    return np.where(assignment > 0, -1, 1)


def exact_maxcut_bruteforce(n, edges):
    if n > 24:
        raise ValueError("Bruteforce exact MaxCut is only intended for small n.")

    best_value = -np.inf
    best_assignment = None

    for bits in itertools.product([0, 1], repeat=n):
        assignment = np.array(bits, dtype=int)
        value = cut_value(edges, assignment)
        if value > best_value:
            best_value = value
            best_assignment = assignment

    return {
        "best_value": float(best_value),
        "best_assignment": best_assignment,
    }


def run_hybrid_postprocessing(
    n,
    target_edges,
    corrs,
    ratio_pulser,
    E_pulser_in_qmc,
    seed=1234,
    n_roundings=32,
):
    """
    Pipeline complet :
    corrélations Pulser -> SDP -> plusieurs roundings -> meilleur état produit
    -> comparaison finale.
    """
    from .hybrid_eval import (
        choose_best_hybrid_result,
        evaluate_multiple_product_states_in_qmc,
    )
    from .hybrid_rounding import round_sdp_to_product_state
    from .hybrid_sdp import solve_proxy_sdp_from_correlators

    sdp_out = solve_proxy_sdp_from_correlators(
        n=n,
        corrs=corrs,
        target_edges=target_edges,
    )
    Delta = sdp_out["Delta"]

    rounding_candidates = []
    for trial in range(int(n_roundings)):
        trial_seed = int(seed) + trial
        rounding_out = round_sdp_to_product_state(n=n, Delta=Delta, seed=trial_seed)
        rounding_candidates.append({
            **rounding_out,
            "seed": trial_seed,
        })

    eval_summary = evaluate_multiple_product_states_in_qmc(
        n=n,
        target_edges=target_edges,
        candidates=rounding_candidates,
    )
    best_rounding = eval_summary["best"]

    final_out = choose_best_hybrid_result(
        ratio_pulser=ratio_pulser,
        ratio_product=best_rounding["ratio_product"],
        E_pulser_in_qmc=E_pulser_in_qmc,
        E_product_in_qmc=best_rounding["E_product_in_qmc"],
    )

    return {
        "sdp_status": sdp_out["status"],
        "Delta": Delta,
        "C": sdp_out["C"],
        "operator_index": sdp_out.get("operator_index"),
        "correlators": sdp_out.get("correlators"),
        "rho_product": best_rounding["rho_product"],
        "bloch_vectors": best_rounding["bloch_vectors"],
        "u_x": best_rounding["u_x"],
        "u_y": best_rounding["u_y"],
        "x_vectors": best_rounding["x_vectors"],
        "best_rounding_seed": best_rounding["seed"],
        "n_roundings": int(n_roundings),
        "rounding_trials": eval_summary["all_results"],
        "E0_qmc": best_rounding["E0_qmc"],
        "E_product_in_qmc": best_rounding["E_product_in_qmc"],
        "ratio_product": best_rounding["ratio_product"],
        "ratio_pulser": float(ratio_pulser),
        "E_pulser_in_qmc": float(E_pulser_in_qmc),
        "winner": final_out["winner"],
        "ratio_hybrid": final_out["ratio_hybrid"],
        "E_hybrid_in_qmc": final_out["E_hybrid_in_qmc"],
    }


def run_hybrid_on_pulser_output(
    n,
    target_edges,
    pulser_out,
    corrs,
    seed=1234,
    n_roundings=32,
):
    """
    Wrapper pratique quand evaluate_smooth_pulser_final_state a déjà tourné.
    """
    return run_hybrid_postprocessing(
        n=n,
        target_edges=target_edges,
        corrs=corrs,
        ratio_pulser=float(pulser_out["ratio_pulser"]),
        E_pulser_in_qmc=float(pulser_out["E_pulser_in_qmc"]),
        seed=seed,
        n_roundings=n_roundings,
    )
