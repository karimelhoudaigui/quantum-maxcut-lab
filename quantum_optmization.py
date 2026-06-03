import numpy as np
from scipy.optimize import minimize
from quantum_utils import * 

# ====================== OPTIMISATION DES POSITIONS ======================

def objective(pos_flat, target_edges, n, c3=1.0):
    """Fonction à minimiser : l'erreur de mapping"""
    positions = pos_flat.reshape((n, 2))
    couplings = couplings_from_positions(positions, c3=c3)
    return mapping_error(target_edges, couplings)


def optimize_atom_positions(target_edges, n=4, max_iter=500, tol=1e-5):
    """
    Optimise les positions des atomes pour minimiser l'erreur de mapping.
    """
    print("Début de l'optimisation des positions des atomes...\n")
    
    # Position initiale aléatoire (un peu étalée)
    np.random.seed(42)  # pour reproductibilité
    initial_pos = np.random.uniform(-1.5, 1.5, (n, 2))
    
    # On optimise
    result = minimize(
        fun=objective,
        x0=initial_pos.flatten(),
        args=(target_edges, n),
        method='L-BFGS-B',      # bonne méthode pour ce problème
        tol=tol,
        options={'maxiter': max_iter, 'disp': False}
    )
    
    final_positions = result.x.reshape((n, 2))
    final_couplings = couplings_from_positions(final_positions)
    final_error = mapping_error(target_edges, final_couplings)
    
    print(f"Optimisation terminée !")
    print(f"Erreur finale de mapping = {final_error:.6f}\n")
    
    return final_positions, final_couplings, final_error



