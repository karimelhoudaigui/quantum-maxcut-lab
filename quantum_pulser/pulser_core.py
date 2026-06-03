import numpy as np

from pulser import Register
from pulser_simulation import QutipEmulator

from quantum_utils import I2, X, Y, Z, two_body_correlator


def build_xy_register(positions, scale=15.5):
    scaled_positions = scale * np.asarray(positions, dtype=float)
    qubits = {f"q{i}": scaled_positions[i] for i in range(len(scaled_positions))}
    return Register(qubits)


def extract_final_statevector_from_result(result):
    final_state = result.states[-1]
    if hasattr(final_state, "full"):
        return final_state.full().flatten()
    return np.asarray(final_state).flatten()


def statevector_to_density(psi):
    psi = np.asarray(psi).reshape(-1, 1)
    return psi @ psi.conj().T


def expectation_value(rho, H):
    return np.real(np.trace(rho @ H))


def state_overlap_pure(psi, phi):
    return np.abs(np.vdot(psi, phi)) ** 2


def run_pulser_sequence(seq, sampling_rate=0.05):
    sim = QutipEmulator.from_sequence(seq, sampling_rate=sampling_rate)
    return sim.run()


def compute_edge_correlators(rho, n, edges):
    corrs = []
    for i, j, w in edges:
        xx = two_body_correlator(rho, n, i, j, X, X)
        yy = two_body_correlator(rho, n, i, j, Y, Y)
        zz = two_body_correlator(rho, n, i, j, Z, Z)
        t = 0.5 * (xx + yy)

        corrs.append({
            "edge": (i, j),
            "w": w,
            "xx": xx,
            "yy": yy,
            "zz": zz,
            "t": t,
        })
    return corrs
