from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from quantum_utils import Z, build_qmc_hamiltonian, build_xy_hamiltonian, two_body_operator


ProxyHamiltonianName = Literal["rydberg_xy", "ising_zz", "heisenberg_qmc"]

DEFAULT_PROXY_HAMILTONIAN: ProxyHamiltonianName = "rydberg_xy"


@dataclass(frozen=True)
class ProxyHamiltonian:
    name: ProxyHamiltonianName
    label: str
    required_correlators: tuple[str, ...]
    experimental: bool
    sdp_note: str


PROXY_HAMILTONIANS: dict[ProxyHamiltonianName, ProxyHamiltonian] = {
    "rydberg_xy": ProxyHamiltonian(
        name="rydberg_xy",
        label="Rydberg XY",
        required_correlators=("xx", "yy"),
        experimental=False,
        sdp_note="Stable default. The existing SDP relaxation is built for XX/YY proxy correlators.",
    ),
    "ising_zz": ProxyHamiltonian(
        name="ising_zz",
        label="Ising ZZ",
        required_correlators=("zz",),
        experimental=True,
        sdp_note=(
            "Experimental. ZZ correlators are computed and reported, but the current SDP relaxation "
            "still uses its legacy XX/YY pseudo-moment formulation."
        ),
    ),
    "heisenberg_qmc": ProxyHamiltonian(
        name="heisenberg_qmc",
        label="Heisenberg QMC-like",
        required_correlators=("xx", "yy", "zz"),
        experimental=True,
        sdp_note=(
            "Experimental. XX/YY/ZZ correlators are computed, but the target-like proxy does not "
            "change the legacy SDP objective unless that relaxation is extended explicitly."
        ),
    ),
}


def normalize_proxy_hamiltonian(name: str | None = None) -> ProxyHamiltonianName:
    if name is None:
        return DEFAULT_PROXY_HAMILTONIAN
    normalized = str(name).strip().lower()
    if normalized not in PROXY_HAMILTONIANS:
        supported = ", ".join(sorted(PROXY_HAMILTONIANS))
        raise ValueError(f"Unsupported proxy_hamiltonian={name!r}. Supported values: {supported}.")
    return normalized  # type: ignore[return-value]


def get_proxy_hamiltonian(name: str | None = None) -> ProxyHamiltonian:
    return PROXY_HAMILTONIANS[normalize_proxy_hamiltonian(name)]


def build_ising_zz_hamiltonian(n: int, edges) -> np.ndarray:
    dim = 2**n
    H = np.zeros((dim, dim), dtype=complex)
    for i, j, w in edges:
        H += float(w) * two_body_operator(n, int(i), int(j), Z, Z)
    return H


def build_heisenberg_qmc_proxy_hamiltonian(n: int, edges) -> np.ndarray:
    return build_qmc_hamiltonian(n, edges)


def build_proxy_hamiltonian(
    n: int,
    target_edges,
    proxy_hamiltonian: str | None = None,
    couplings=None,
) -> np.ndarray:
    name = normalize_proxy_hamiltonian(proxy_hamiltonian)
    if name == "rydberg_xy":
        if couplings is None:
            raise ValueError("Rydberg XY proxy requires geometric couplings.")
        return build_xy_hamiltonian(n, couplings)
    if name == "ising_zz":
        return build_ising_zz_hamiltonian(n, target_edges)
    if name == "heisenberg_qmc":
        return build_heisenberg_qmc_proxy_hamiltonian(n, target_edges)
    raise AssertionError(f"Unhandled proxy Hamiltonian: {name}")


def proxy_metadata(name: str | None = None) -> dict[str, object]:
    proxy = get_proxy_hamiltonian(name)
    return {
        "proxy_hamiltonian": proxy.name,
        "proxy_label": proxy.label,
        "proxy_required_correlators": list(proxy.required_correlators),
        "proxy_experimental": proxy.experimental,
        "proxy_sdp_note": proxy.sdp_note,
    }
