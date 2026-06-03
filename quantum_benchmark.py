import numpy as np

from quantum_utils import *
from quantum_optmization import *
from quantum_plot import *
from quantum_benchmark import *
from quantum_io import *

# ============================================================
# Génération de graphes aléatoires
# ============================================================

def generate_random_weighted_graph(n, edge_prob=0.6, w_min=0.5, w_max=1.5, seed=None):
    """
    Génère un graphe pondéré aléatoire.
    """
    rng = np.random.default_rng(seed)
    edges = []

    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < edge_prob:
                w = rng.uniform(w_min, w_max)
                edges.append((i, j, w))

    return edges


# ============================================================
# Analyse complète d'une instance
# ============================================================

def analyze_instance(n, target_edges, instance_id=None, do_plot=False):
    """
    Pipeline complet pour une instance :
    1. Optimisation des positions atomiques
    2. Construction des Hamiltoniens
    3. Diagonalisation exacte
    4. Calcul de la qualité du proxy
    """

    # Étape 3 : optimisation géométrique
    best_positions, best_couplings, best_error = optimize_atom_positions(target_edges, n=n)

    # Construction des Hamiltoniens
    H_qmc = build_qmc_hamiltonian(n, target_edges)
    H_r = build_xy_hamiltonian(n, best_couplings)

    # États fondamentaux
    E0_qmc, psi_qmc = ground_state(H_qmc)
    E0_r, psi_r = ground_state(H_r)

    # Énergie du proxy dans le problème cible
    rho_r = state_to_density_matrix(psi_r)
    E_proxy = np.real(np.trace(rho_r @ H_qmc))

    ratio = E_proxy / E0_qmc if abs(E0_qmc) > 1e-12 else np.nan
    num_edges = len(target_edges)
    density = 2 * num_edges / (n * (n - 1))
    if do_plot:
     plot_atom_geometry(best_positions, target_edges)
    return {
        "n": n,
        "instance_id": instance_id,
        "num_edges": num_edges,
        "density": density,
        "mapping_error": best_error,
        "E0_qmc": E0_qmc,
        "E0_r": E0_r,
        "E_proxy_in_qmc": E_proxy,
        "ratio": ratio,
        "target_edges": target_edges,
        "positions": best_positions,
        "couplings": best_couplings,
    }


# ============================================================
# Benchmark global
# ============================================================

def benchmark_over_n(
    n_values,
    n_instances_per_n=5,
    edge_prob=0.6,
    w_min=0.5,
    w_max=1.5,
    seed=0
):
    rng = np.random.default_rng(seed)
    results = []

    for n in n_values:
        print("\n" + "=" * 60)
        print(f"Benchmark pour n = {n}")
        print("=" * 60)

        for instance_id in range(n_instances_per_n):
            print(f"\nInstance {instance_id + 1}/{n_instances_per_n}")

            graph_seed = int(rng.integers(1_000_000))
            target_edges = generate_random_weighted_graph(
                n=n,
                edge_prob=edge_prob,
                w_min=w_min,
                w_max=w_max,
                seed=graph_seed
            )

            if len(target_edges) == 0:
                print("Graphe vide, instance ignorée.")
                continue

            try:
                result = analyze_instance(n, target_edges, do_plot=False)
                result["instance_id"] = instance_id
                results.append(result)

                print(f"Erreur mapping = {result['mapping_error']:.6f}")
                print(f"Ratio          = {result['ratio']:.6f}")

            except Exception as e:
                print(f"Erreur sur n={n}, instance={instance_id}: {e}")

    return results

# ============================================================
# Résumé statistique
# ============================================================

def summarize_results(results):
    """
    Affiche statistiques globales.
    """
    grouped = {}

    for r in results:
        grouped.setdefault(r["n"], []).append(r)

    print("\n" + "#" * 60)
    print("RÉSUMÉ")
    print("#" * 60)

    for n in sorted(grouped.keys()):
        group = grouped[n]

        errors = np.array([r["mapping_error"] for r in group], dtype=float)
        ratios = np.array([r["ratio"] for r in group], dtype=float)

        print(f"\nn = {n}")
        print(f"instances           : {len(group)}")
        print(f"error mean          : {errors.mean():.6f}")
        print(f"error max           : {errors.max():.6f}")
        print(f"ratio mean          : {ratios.mean():.6f}")
        print(f"ratio min           : {ratios.min():.6f}")