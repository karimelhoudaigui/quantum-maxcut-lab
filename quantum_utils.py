# Utility functions for quantum operations


import numpy as np

# Matrices de base
I2 = np.eye(2, dtype=complex)

X = np.array([[0, 1],
              [1, 0]], dtype=complex)

Y = np.array([[0, -1j],
              [1j,  0]], dtype=complex)

Z = np.array([[1,  0],
              [0, -1]], dtype=complex)


def kron_n(ops):
    """
    Produit tensoriel d'une liste d'opérateurs.
    Exemple: [X, I2, Z] -> X ⊗ I ⊗ Z
    """
    result = ops[0]
    for op in ops[1:]:
        result = np.kron(result, op)
    return result


def one_body_operator(n, site, op):
    """
    Construit un opérateur agissant comme 'op' sur le qubit 'site'
    et comme l'identité sur tous les autres.
    """
    ops = [I2] * n
    ops[site] = op
    return kron_n(ops)


def two_body_operator(n, i, j, op_i, op_j):
    """
    Construit un opérateur à deux corps:
    op_i sur le site i, op_j sur le site j, identité ailleurs.
    """
    ops = [I2] * n
    ops[i] = op_i
    ops[j] = op_j
    return kron_n(ops)


def build_qmc_hamiltonian(n, edges):
    """Version correcte et claire du Quantum Max-Cut"""
    dim = 2**n
    H = np.zeros((dim, dim), dtype=complex)
    
    for i, j, w in edges:
        XX = two_body_operator(n, i, j, X, X)
        YY = two_body_operator(n, i, j, Y, Y)
        ZZ = two_body_operator(n, i, j, Z, Z)
        
        # Terme important : identité seulement sur les deux qubits concernés
        I_ij = two_body_operator(n, i, j, I2, I2)
        
        # Formule exacte de l'article :
        # H += -w * (I_ij - XX - YY - ZZ)
        H += -w * (I_ij - XX - YY - ZZ)

    return H


def build_xy_hamiltonian(n, couplings):
    """Version correcte du proxy XY (Rydberg)"""
    dim = 2**n
    H = np.zeros((dim, dim), dtype=complex)
    
    for i, j, J in couplings:
        XX = two_body_operator(n, i, j, X, X)
        YY = two_body_operator(n, i, j, Y, Y)
        H += J * (XX + YY)          # Pas de terme I ici

    return H
def exact_diagonalization(H):
    """
    Retourne toutes les valeurs propres et vecteurs propres.
    """
    eigvals, eigvecs = np.linalg.eigh(H)
    return eigvals, eigvecs


def ground_state(H):
    """
    Retourne l'énergie fondamentale et le vecteur propre associé.
    """
    eigvals, eigvecs = exact_diagonalization(H)
    return np.real(eigvals[0]), eigvecs[:, 0]


def state_to_density_matrix(psi):
    """
    Convertit un vecteur d'état |psi> en matrice densité rho = |psi><psi|.
    """
    psi = np.asarray(psi).reshape(-1, 1)
    return psi @ psi.conj().T


def expectation_value(rho, O):
    """
    Calcule Tr(rho O).
    """
    return np.real(np.trace(rho @ O))


def two_body_correlator(rho, n, i, j, op1, op2):
    """
    Calcule <op1_i op2_j>.
    """
    O = two_body_operator(n, i, j, op1, op2)
    return expectation_value(rho, O)


import numpy as np


def distance(p1, p2):
    """Distance euclidienne entre deux points 2D."""
    return np.linalg.norm(np.array(p1) - np.array(p2))


def couplings_from_positions(positions, c3=1.0, min_dist=1e-9):
    """
    Construit les couplages géométriques J_ij = c3 / R_ij^3
    à partir des positions atomiques.

    positions : array/list de taille n, chaque élément est [x, y]
    retourne : liste de tuples (i, j, J_ij)
    """
    n = len(positions)
    couplings = []

    for i in range(n):
        for j in range(i + 1, n):
            r_ij = distance(positions[i], positions[j])
            r_ij = max(r_ij, min_dist)  # sécurité numérique
            J_ij = c3 / (r_ij ** 3)
            couplings.append((i, j, J_ij))

    return couplings

"""Fonction,Rôle
edge_dict(),Convertit la liste d’arêtes en dictionnaire facile à utiliser
mapping_error(),Calcule l’erreur globale entre tes poids cibles et la géométrie
print_edge_comparison(),Affiche un tableau détaillé pour voir les écarts arête par arête"""
def edge_dict(edge_list):
    """
    Convertit une liste [(i,j,val), ...] en dictionnaire {(i,j): val}
    avec i < j. exemple: [(0,1,1.0), (0,2,0.8)] -> {(0,1): 1.0, (0,2): 0.8}
    """
    d = {}
    for i, j, val in edge_list:
        key = (min(i, j), max(i, j))
        d[key] = val
    return d


def mapping_error(target_edges, model_couplings):
    """
    Erreur relative quadratique entre les poids cibles omega_ij
    et les couplages géométriques J_ij, sur les arêtes communes.
    """
    target = edge_dict(target_edges)
    model = edge_dict(model_couplings)

    common_edges = sorted(set(target.keys()) & set(model.keys()))
    if not common_edges:
        return np.inf

    num = 0.0
    den = 0.0
    for e in common_edges:
        num += (model[e] - target[e]) ** 2
        den += target[e] ** 2

    return np.sqrt(num / max(den, 1e-12))


def print_edge_comparison(target_edges, model_couplings):
    """
    Affiche comparaison arête par arête.
    """
    target = edge_dict(target_edges)
    model = edge_dict(model_couplings)

    common_edges = sorted(set(target.keys()) & set(model.keys()))
    print("\nComparaison des poids cible / géométrie")
    print("-" * 50)
    for e in common_edges:
        print(f"Arête {e} : omega = {target[e]:.6f}, J = {model[e]:.6f}, "
              f"écart = {model[e] - target[e]:.6f}")