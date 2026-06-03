"""
Rounding layer for the hybrid MaxCut pipeline.

Role of this module:
- transform the SDP/relaxation output into a product-state ansatz
- extract vectors from the relaxed Gram representation
- generate Bloch vectors and construct rho_p
- keep classical hyperplane/sign rounding helpers for MaxCut baselines
"""

import numpy as np

from quantum_utils import I2, X, Y, Z

from .hybrid_core import cut_value, spin_to_assignment


def nearest_psd(mat, eps=1e-10):
    """
    Corrige numériquement une matrice symétrique pour la rendre PSD.
    """
    mat = np.asarray(mat, dtype=float)
    mat = 0.5 * (mat + mat.T)
    vals, vecs = np.linalg.eigh(mat)
    vals = np.maximum(vals, eps)
    return vecs @ np.diag(vals) @ vecs.T


def factorize_pseudo_moment_matrix(Delta):
    """
    Factorisation spectrale numeriquement stable de Delta.
    """
    Delta_psd = nearest_psd(Delta)
    vals, vecs = np.linalg.eigh(Delta_psd)
    sqrt_vals = np.sqrt(np.maximum(vals, 0.0))
    return vecs @ np.diag(sqrt_vals)


def extract_xy_operator_vectors(n, Delta_factor):
    """
    Extrait les vecteurs u_i^X et u_i^Y depuis la factorisation de Delta,
    avec la convention P = {I, X1, Y1, ..., Xn, Yn}.
    """
    u_x = []
    u_y = []
    for i in range(n):
        u_x.append(np.asarray(Delta_factor[1 + 2 * i, :], dtype=float))
        u_y.append(np.asarray(Delta_factor[1 + 2 * i + 1, :], dtype=float))
    return {
        "u_x": u_x,
        "u_y": u_y,
    }


def build_proxy_rounding_vectors(n, Delta_factor):
    """
    Construit les vecteurs x_i a partir de u_i^X et u_i^Y afin que
    x_i^T x_j approche t_ij = 1/2(<XiXj> + <YiYj>).
    """
    xy = extract_xy_operator_vectors(n, Delta_factor)
    x_vectors = []

    for ux, uy in zip(xy["u_x"], xy["u_y"]):
        xi = np.concatenate([ux, uy]) / np.sqrt(2.0)
        norm = np.linalg.norm(xi)
        if norm > 1e-12:
            xi = xi / norm
        x_vectors.append(xi)

    return {
        "u_x": xy["u_x"],
        "u_y": xy["u_y"],
        "x_vectors": x_vectors,
    }


def bloch_vectors_from_x_vectors(x_vectors, seed=1234):
    """
    Rounding aleatoire de l'article :
    projection gaussienne R dans R^{3 x d}, puis normalisation.
    """
    rng = np.random.default_rng(seed)
    if not x_vectors:
        return []

    proj_dim = len(x_vectors[0])
    R = rng.normal(size=(3, proj_dim))

    bloch_vectors = []
    for x_vec in x_vectors:
        b = R @ x_vec
        norm = np.linalg.norm(b)
        if norm < 1e-12:
            b = np.array([0.0, 0.0, 1.0], dtype=float)
        else:
            b = b / norm
        bloch_vectors.append(b)

    return bloch_vectors


def build_product_state_from_bloch_vectors(bloch_vectors):
    """
    Construit rho_p = rho_1 \otimes ... \otimes rho_n.
    """
    single_qubit_states = []
    for b in bloch_vectors:
        ax, ay, az = b
        rho = 0.5 * (I2 + ax * X + ay * Y + az * Z)
        single_qubit_states.append(rho)

    if not single_qubit_states:
        return np.array([[1.0]], dtype=complex)

    rho_product = single_qubit_states[0]
    for k in range(1, len(single_qubit_states)):
        rho_product = np.kron(rho_product, single_qubit_states[k])
    return rho_product


def round_sdp_to_product_state(n, Delta, seed=1234):
    """
    Rounding plus fidele a l'article :
    - factorisation de Delta*
    - extraction de u_i^X et u_i^Y
    - construction des vecteurs concaténés x_i
    - projection gaussienne aleatoire vers R^3
    - construction de rho_p
    """
    Delta_factor = factorize_pseudo_moment_matrix(Delta)
    vec_out = build_proxy_rounding_vectors(n=n, Delta_factor=Delta_factor)
    bloch_vectors = bloch_vectors_from_x_vectors(vec_out["x_vectors"], seed=seed)
    rho_product = build_product_state_from_bloch_vectors(bloch_vectors)

    return {
        "rho_product": rho_product,
        "bloch_vectors": bloch_vectors,
        "u_x": vec_out["u_x"],
        "u_y": vec_out["u_y"],
        "x_vectors": vec_out["x_vectors"],
        "Delta_factor": Delta_factor,
    }


def random_hyperplane_rounding(vectors, edges, n_rounds=256, seed=42):
    vectors = np.asarray(vectors, dtype=float)
    if vectors.ndim != 2:
        raise ValueError("vectors must be a 2D array.")

    n, rank = vectors.shape
    rng = np.random.default_rng(seed)

    best_value = -np.inf
    best_assignment = None
    all_values = []

    for _ in range(int(n_rounds)):
        direction = rng.normal(size=rank)
        direction /= max(np.linalg.norm(direction), 1e-12)

        spins = np.sign(vectors @ direction)
        spins[spins == 0] = 1
        assignment = spin_to_assignment(spins)
        value = cut_value(edges, assignment)
        all_values.append(float(value))

        if value > best_value:
            best_value = value
            best_assignment = assignment

    return {
        "best_value": float(best_value),
        "best_assignment": best_assignment,
        "all_values": all_values,
        "mean_value": float(np.mean(all_values)) if all_values else 0.0,
    }


def deterministic_sign_rounding(vectors, edges, axis=0):
    vectors = np.asarray(vectors, dtype=float)
    if vectors.ndim != 2:
        raise ValueError("vectors must be a 2D array.")

    axis = int(axis)
    if axis < 0 or axis >= vectors.shape[1]:
        raise ValueError("axis is outside vector rank.")

    spins = np.sign(vectors[:, axis])
    spins[spins == 0] = 1
    assignment = spin_to_assignment(spins)

    return {
        "value": cut_value(edges, assignment),
        "assignment": assignment,
    }
