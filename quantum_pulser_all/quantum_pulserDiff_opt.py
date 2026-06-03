# ========================================================
# quantum_pulser_opt.py -  NOUVELLE VERSION avec PulserDiff
# ========================================================

import numpy as np
import torch
from pulser import Register, Sequence, Pulse
from pulser.devices import MockDevice
from pulser.waveforms import ConstantWaveform
from pulser_simulation import QutipEmulator

# PulserDiff
from pulser_diff.model import QuantumModel

from quantum_utils import *   # tes fonctions existantes (build_xy_hamiltonian, ground_state, etc.)

def build_parametrized_xy_sequence(positions, params, pulse_duration=250):
    qubits = {f"q{i}": pos.tolist() for i, pos in enumerate(positions)}
    reg = Register(qubits)

    seq = Sequence(reg, MockDevice)
    seq.declare_channel("mw", "mw_global")

    params = np.asarray(params, dtype=float)
    assert len(params) % 3 == 0, "Il faut 3 paramètres par pulse : amp, det, phase."

    n_pulses = len(params) // 3
    for k in range(n_pulses):
        amp = float(params[3 * k + 0])
        det = float(params[3 * k + 1])
        phase = float(params[3 * k + 2])

        amp_wf = ConstantWaveform(int(pulse_duration), amp)
        det_wf = ConstantWaveform(int(pulse_duration), det)
        pulse = Pulse(amp_wf, det_wf, phase=phase)
        seq.add(pulse, "mw")

    seq.measure("XY")
    return seq

def optimize_xy_pulses_for_2atoms(
    positions,
    target_edges,
    n_pulses=4,
    pulse_duration=250,
    sampling_rate=0.05,
    maxiter=300,
    lr=0.05,
):
    n = len(positions)
    assert n == 2, "Cette fonction est pour l'instant optimisée pour 2 atomes"

    # 1) Registre avec tenseurs torch explicites
    qubits = {
        f"q{i}": torch.tensor(np.asarray(pos, dtype=float), dtype=torch.float64)
        for i, pos in enumerate(positions)
    }
    reg = Register(qubits)

    # 2) Séquence XY
    seq = Sequence(reg, MockDevice)
    seq.declare_channel("mw", "mw_global")

    for k in range(n_pulses):
        amp_var = seq.declare_variable(f"amp_{k}")
        det_var = seq.declare_variable(f"det_{k}")
        phase_var = seq.declare_variable(f"phase_{k}")

        pulse = Pulse.ConstantPulse(
            duration=int(pulse_duration),
            amplitude=amp_var,
            detuning=det_var,
            phase=phase_var,
        )
        seq.add(pulse, "mw")

    seq.measure("XY")

    # 3) Cible = fondamental de H_r
    pos_np = np.array([np.asarray(p, dtype=float) for p in positions], dtype=float)
    couplings = couplings_from_positions(pos_np, c3=1.0)
    H_r = build_xy_hamiltonian(n, couplings)
    _, target_psi_np = ground_state(H_r)
    target_psi = torch.tensor(target_psi_np, dtype=torch.complex128)

    # 4) Paramètres entraînables
    trainable_params = {}
    constraints = {}

    for k in range(n_pulses):
        trainable_params[f"amp_{k}"] = torch.tensor(2 * np.pi * 1.0, dtype=torch.float64, requires_grad=True)
        trainable_params[f"det_{k}"] = torch.tensor(0.0, dtype=torch.float64, requires_grad=True)
        trainable_params[f"phase_{k}"] = torch.tensor(0.0, dtype=torch.float64, requires_grad=True)

        constraints[f"amp_{k}"] = {"min": 0.0, "max": 4 * np.pi}
        constraints[f"det_{k}"] = {"min": -4 * np.pi, "max": 4 * np.pi}
        # phase libre

    model = QuantumModel(
        seq=seq,
        trainable_param_values=trainable_params,
        constraints=constraints,
        sampling_rate=sampling_rate,
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    best_loss = float("inf")
    best_overlap = 0.0
    best_params_dict = None

    for epoch in range(maxiter):
        optimizer.zero_grad()

        eval_times, states = model.forward()
        final_psi = states[-1]

        target_psi_t = target_psi.to(device=final_psi.device, dtype=final_psi.dtype)
        overlap = torch.abs(torch.vdot(target_psi_t, final_psi)) ** 2
        loss = 1.0 - overlap.real

        loss.backward()
        optimizer.step()
        model.check_constraints()
        model.update_sequence()

        current_overlap = float(overlap.detach().cpu())

        if current_overlap > best_overlap:
            best_overlap = current_overlap
            best_loss = float(loss.detach().cpu())
            best_params_dict = {
                name: param.detach().clone()
                for name, param in model.named_parameters()
            }

        if epoch % 20 == 0 or epoch == maxiter - 1:
            print(f"Epoch {epoch:3d} | Loss: {float(loss.detach().cpu()):.6f} | Overlap: {current_overlap:.6f}")

    if best_params_dict is None:
        best_params_dict = {
            name: param.detach().clone()
            for name, param in model.named_parameters()
        }

    best_params = []
    for k in range(n_pulses):
        best_params.extend([
            float(best_params_dict[f"amp_{k}"]),
            float(best_params_dict[f"det_{k}"]),
            float(best_params_dict[f"phase_{k}"]),
        ])

    return {
        "success": True,
        "message": "Optimisation PulserDiff terminée",
        "best_params": np.array(best_params),
        "best_loss": best_loss,
        "best_overlap": best_overlap,
    }


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


def evaluate_optimized_pulses(n, positions, target_edges, best_params, pulse_duration=250, sampling_rate=0.05):
    """
    Évalue la séquence optimisée :
    - overlap avec le fondamental du proxy
    - énergie QMC
    - ratio QMC
    """
    H_qmc = build_qmc_hamiltonian(n, target_edges)
    E0_qmc, _ = ground_state(H_qmc)

    couplings = couplings_from_positions(positions, c3=1.0)
    H_r = build_xy_hamiltonian(n, couplings)
    E0_r, psi_r = ground_state(H_r)

    seq = build_parametrized_xy_sequence(positions, best_params, pulse_duration=pulse_duration)
    sim = QutipEmulator.from_sequence(seq, sampling_rate=sampling_rate)
    result = sim.run()

    psi_T = extract_final_statevector_from_result(result)
    rho_T = statevector_to_density(psi_T)

    overlap = state_overlap_pure(psi_r, psi_T)
    E_qmc = expectation_value(rho_T, H_qmc)
    ratio_qmc = E_qmc / E0_qmc if abs(E0_qmc) > 1e-12 else np.nan

    corrs = compute_edge_correlators(rho_T, n, target_edges)

    return {
        "seq": seq,
        "result": result,
        "psi_T": psi_T,
        "rho_T": rho_T,
        "E0_qmc": E0_qmc,
        "E0_r": E0_r,
        "E_qmc": E_qmc,
        "ratio_qmc": ratio_qmc,
        "overlap": overlap,
        "corrs": corrs,
    }
