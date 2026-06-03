"""
Evaluation layer for hybrid MaxCut states.

Role of this module:
- evaluate candidate states/assignments in the target QMC objective
- compute energies, approximation ratios, and exact references when possible
- select the best rounded state returned by the hybrid pipeline
- summarize the final comparison between relaxation, rounding, and exact MaxCut

It supports both the new Pulser -> SDP -> product-state pipeline and the older
classical spectral-relaxation baseline.
"""

import numpy as np

from quantum_utils import build_qmc_hamiltonian

from .hybrid_core import exact_maxcut_bruteforce, infer_n_from_edges
from .hybrid_rounding import random_hyperplane_rounding
from .hybrid_sdp import spectral_sdp_relaxation


def evaluate_product_state_in_qmc(n, target_edges, rho_product):
    H_qmc = build_qmc_hamiltonian(n, target_edges)
    evals, _ = np.linalg.eigh(H_qmc)
    E0_qmc = float(np.min(evals))

    E_product = float(np.real(np.trace(rho_product @ H_qmc)))
    ratio_product = E_product / E0_qmc if abs(E0_qmc) > 1e-12 else np.nan

    return {
        "E0_qmc": E0_qmc,
        "E_product_in_qmc": E_product,
        "ratio_product": ratio_product,
    }


def evaluate_multiple_product_states_in_qmc(n, target_edges, candidates):
    """
    Evalue plusieurs etats produits et garde le meilleur selon le ratio.
    """
    evaluated = []
    best = None

    for candidate in candidates:
        eval_out = evaluate_product_state_in_qmc(
            n=n,
            target_edges=target_edges,
            rho_product=candidate["rho_product"],
        )
        row = {
            **candidate,
            **eval_out,
        }
        evaluated.append(row)

        if best is None or row["ratio_product"] > best["ratio_product"]:
            best = row

    return {
        "best": best,
        "all_results": evaluated,
    }


def choose_best_hybrid_result(
    ratio_pulser,
    ratio_product,
    E_pulser_in_qmc,
    E_product_in_qmc,
):
    """
    Comme on minimise un Hamiltonien négatif, le meilleur ratio est le plus grand
    si E0 < 0 et E/E0 > 0. On compare donc les ratios.
    """
    if ratio_product > ratio_pulser:
        winner = "rounding"
        ratio_hybrid = ratio_product
        E_hybrid = E_product_in_qmc
    else:
        winner = "pulser"
        ratio_hybrid = ratio_pulser
        E_hybrid = E_pulser_in_qmc

    return {
        "winner": winner,
        "ratio_hybrid": ratio_hybrid,
        "E_hybrid_in_qmc": E_hybrid,
    }


def evaluate_hybrid_maxcut(
    edges,
    n=None,
    rank=None,
    n_rounds=256,
    seed=42,
    compute_exact=True,
):
    if n is None:
        n = infer_n_from_edges(edges)

    relaxation = spectral_sdp_relaxation(n=n, edges=edges, rank=rank)
    rounding = random_hyperplane_rounding(
        vectors=relaxation["vectors"],
        edges=edges,
        n_rounds=n_rounds,
        seed=seed,
    )

    out = {
        "n": int(n),
        "relaxation_value": float(relaxation["relaxation_value"]),
        "rounded_value": float(rounding["best_value"]),
        "rounded_assignment": rounding["best_assignment"],
        "rounding_mean_value": float(rounding["mean_value"]),
        "vectors": relaxation["vectors"],
        "gram": relaxation["gram"],
    }

    if compute_exact:
        exact = exact_maxcut_bruteforce(n, edges)
        optimum = float(exact["best_value"])
        out.update({
            "exact_value": optimum,
            "exact_assignment": exact["best_assignment"],
            "approx_ratio": float(rounding["best_value"] / optimum) if abs(optimum) > 1e-12 else np.nan,
        })

    return out
