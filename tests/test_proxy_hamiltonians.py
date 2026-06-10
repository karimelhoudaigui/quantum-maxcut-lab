import numpy as np

from proxy_hamiltonians import (
    DEFAULT_PROXY_HAMILTONIAN,
    build_proxy_hamiltonian,
    get_proxy_hamiltonian,
)


def test_default_proxy_hamiltonian_is_rydberg_xy():
    assert DEFAULT_PROXY_HAMILTONIAN == "rydberg_xy"
    proxy = get_proxy_hamiltonian()
    assert proxy.name == "rydberg_xy"
    assert proxy.required_correlators == ("xx", "yy")
    assert proxy.experimental is False


def test_rydberg_xy_proxy_can_be_instantiated():
    H = build_proxy_hamiltonian(
        n=2,
        target_edges=[(0, 1, 1.0)],
        proxy_hamiltonian="rydberg_xy",
        couplings=[(0, 1, 0.7)],
    )
    assert H.shape == (4, 4)
    assert np.allclose(H, H.conj().T)


def test_experimental_proxy_hamiltonians_can_be_instantiated():
    edges = [(0, 1, 1.0)]
    for name in ("ising_zz", "heisenberg_qmc"):
        proxy = get_proxy_hamiltonian(name)
        H = build_proxy_hamiltonian(n=2, target_edges=edges, proxy_hamiltonian=name)
        assert proxy.experimental is True
        assert H.shape == (4, 4)
        assert np.allclose(H, H.conj().T)
