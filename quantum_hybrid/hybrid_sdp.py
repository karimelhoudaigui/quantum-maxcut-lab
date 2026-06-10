import numpy as np

from proxy_hamiltonians import DEFAULT_PROXY_HAMILTONIAN, proxy_metadata

try:
    import cvxpy as cp
except ImportError:
    cp = None


def operator_index_map(n):
    """
    Indices de la base P = {I, X1, Y1, X2, Y2, ..., Xn, Yn}.
    """
    index = {"I": 0}
    for i in range(n):
        index[("X", i)] = 1 + 2 * i
        index[("Y", i)] = 1 + 2 * i + 1
    return index


def build_proxy_cost_matrix(n, target_edges, operator_index=None):
    """
    Construit la matrice de cout C pour la base
    P = {I, X1, Y1, X2, Y2, ..., Xn, Yn}.

    Avec la convention :
    - idx(I) = 0
    - idx_X(i) = 2*i + 1
    - idx_Y(i) = 2*i + 2

    On encode ici l'objectif proxy
        H_r = sum_{(i,j) in E} w_ij (X_i X_j + Y_i Y_j)
    via trace(C Delta). Comme on veut minimiser cette energie proxy,
    l'objectif SDP est Minimize(trace(C @ Delta)) avec cette meme convention
    de signe.
    """
    if operator_index is None:
        operator_index = operator_index_map(n)

    dim = 2 * n + 1
    C = np.zeros((dim, dim), dtype=float)

    for i, j, w in target_edges:
        i = int(i)
        j = int(j)
        w = float(w)

        idx_x_i = operator_index[("X", i)]
        idx_x_j = operator_index[("X", j)]
        idx_y_i = operator_index[("Y", i)]
        idx_y_j = operator_index[("Y", j)]

        # On repartit sur les deux entrees symetriques pour que
        # trace(C Delta) = sum w_ij (Delta[Xi,Xj] + Delta[Yi,Yj])
        # lorsque Delta est symetrique.
        C[idx_x_i, idx_x_j] += 0.5 * w
        C[idx_x_j, idx_x_i] += 0.5 * w
        C[idx_y_i, idx_y_j] += 0.5 * w
        C[idx_y_j, idx_y_i] += 0.5 * w

    return C


def build_edge_correlation_dict(corrs):
    """
    Convertit la sortie de compute_edge_correlators en dictionnaires pratiques.
    """
    xx = {}
    yy = {}
    zz = {}
    tt = {}

    for item in corrs:
        i, j = item["edge"]
        key = (min(i, j), max(i, j))
        xx[key] = float(item["xx"])
        yy[key] = float(item["yy"])
        zz[key] = float(item["zz"])
        tt[key] = 0.5 * (float(item["xx"]) + float(item["yy"]))

    return {
        "xx": xx,
        "yy": yy,
        "zz": zz,
        "tt": tt,
    }


def solve_proxy_sdp_from_correlators(
    n,
    corrs,
    target_edges,
    proxy_hamiltonian=DEFAULT_PROXY_HAMILTONIAN,
):
    """
    V2 :
    construit une pseudo-moment matrix Delta de taille (2n+1) x (2n+1)
    indexée par P = {I, X1, Y1, X2, Y2, ..., Xn, Yn}.

    On impose :
    - Delta >> 0
    - Delta[I, I] = 1
    - Delta[Xi, Xi] = 1
    - Delta[Yi, Yi] = 1
    - Delta[Xi, Xj] = <XiXj>
    - Delta[Yi, Yj] = <YiYj>
    - symétrie réelle

    Cette version reste volontairement simple : elle n'impose pas encore les
    relations algébriques plus fines entre opérateurs.

    Important : la formulation reste la relaxation historique XX/YY. Les
    autres Hamiltoniens proxy peuvent fournir des corrélateurs additionnels
    (notamment ZZ), mais ceux-ci ne changent pas encore l'objectif SDP.
    """
    if cp is None:
        raise ImportError("cvxpy n'est pas installé. Installe-le pour utiliser l'étape SDP.")

    proxy_info = proxy_metadata(proxy_hamiltonian)
    corr_dict = build_edge_correlation_dict(corrs)
    xx = corr_dict["xx"]
    yy = corr_dict["yy"]

    dim = 2 * n + 1
    Delta = cp.Variable((dim, dim), symmetric=True)
    index = operator_index_map(n)
    C = build_proxy_cost_matrix(
        n=n,
        target_edges=target_edges,
        operator_index=index,
    )

    constraints = [Delta >> 0]
    constraints.append(Delta[index["I"], index["I"]] == 1.0)

    for k in range(n):
        constraints.append(Delta[index[("X", k)], index[("X", k)]] == 1.0)
        constraints.append(Delta[index[("Y", k)], index[("Y", k)]] == 1.0)

    for (i, j), val in xx.items():
        constraints.append(Delta[index[("X", i)], index[("X", j)]] == val)

    for (i, j), val in yy.items():
        constraints.append(Delta[index[("Y", i)], index[("Y", j)]] == val)

    objective = cp.Minimize(cp.trace(C @ Delta))

    problem = cp.Problem(objective, constraints)
    problem.solve(solver=cp.SCS, verbose=False)

    if Delta.value is None:
        raise RuntimeError("Le SDP n'a pas trouvé de solution faisable.")

    return {
        "Delta": np.array(Delta.value, dtype=float),
        "C": C,
        "status": problem.status,
        "objective_value": problem.value,
        "operator_index": index,
        "correlators": corr_dict,
        "proxy_hamiltonian": proxy_info["proxy_hamiltonian"],
        "proxy_required_correlators": proxy_info["proxy_required_correlators"],
        "proxy_sdp_note": proxy_info["proxy_sdp_note"],
        "sdp_formulation": "legacy_xy",
    }


def spectral_sdp_relaxation(n, edges, rank=None):
    """
    Relaxation spectrale simple conservée comme baseline classique.

    Elle sert à evaluate_hybrid_maxcut(), qui est indépendant du pipeline
    Pulser -> corrélations -> SDP. Le pipeline hybride principal utilise plutôt
    solve_proxy_sdp_from_correlators().
    """
    from .hybrid_core import graph_laplacian

    if n <= 0:
        return {
            "vectors": np.zeros((0, 0), dtype=float),
            "gram": np.zeros((0, 0), dtype=float),
            "eigenvalues": np.array([], dtype=float),
            "relaxation_value": 0.0,
        }

    if rank is None:
        rank = min(max(2, int(np.ceil(np.sqrt(n)))), n)

    L = graph_laplacian(n, edges)
    evals, evecs = np.linalg.eigh(L)
    order = np.argsort(evals)[::-1]
    selected = order[:rank]

    vectors = evecs[:, selected]
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / np.maximum(norms, 1e-12)

    gram = vectors @ vectors.T
    relaxation_value = 0.25 * float(np.sum(L * (1.0 - gram)))

    return {
        "vectors": vectors,
        "gram": gram,
        "eigenvalues": evals[selected],
        "relaxation_value": relaxation_value,
    }
