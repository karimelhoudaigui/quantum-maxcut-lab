import numpy as np

from quantum_utils import build_qmc_hamiltonian, build_xy_hamiltonian, couplings_from_positions, ground_state

from .pulser_core import (
    expectation_value,
    extract_final_statevector_from_result,
    run_pulser_sequence,
    state_overlap_pure,
    statevector_to_density,
)
from .pulser_sequences import build_xy_adiabatic_sequence, build_xy_piecewise_sequence


def evaluate_pulser_final_state(
    n,
    positions,
    target_edges,
    omega_prep,
    prep_duration,
    omega_hold,
    hold_duration,
    omega_max,
    ramp_up_duration,
    T,
    sampling_rate=0.05,
    scale=15.5,
):
    H_qmc = build_qmc_hamiltonian(n, target_edges)
    E0_qmc, psi_qmc = ground_state(H_qmc)

    couplings = couplings_from_positions(positions, c3=1.0)
    H_r = build_xy_hamiltonian(n, couplings)
    E0_r, psi_r = ground_state(H_r)

    seq = build_xy_adiabatic_sequence(
        positions=positions,
        omega_prep=omega_prep,
        prep_duration=prep_duration,
        omega_hold=omega_hold,
        hold_duration=hold_duration,
        omega_max=omega_max,
        ramp_up_duration=ramp_up_duration,
        anneal_duration=T,
        scale=scale,
    )

    result = run_pulser_sequence(seq, sampling_rate=sampling_rate)
    psi_T = extract_final_statevector_from_result(result)
    rho_T = statevector_to_density(psi_T)

    E_proxy_exact_in_qmc = expectation_value(statevector_to_density(psi_r), H_qmc)
    E_pulser_in_qmc = expectation_value(rho_T, H_qmc)
    E_pulser_in_proxy = expectation_value(rho_T, H_r)

    ratio_proxy_exact = E_proxy_exact_in_qmc / E0_qmc if abs(E0_qmc) > 1e-12 else np.nan
    ratio_pulser = E_pulser_in_qmc / E0_qmc if abs(E0_qmc) > 1e-12 else np.nan

    return {
        "seq": seq,
        "sim_result": result,
        "psi_T": psi_T,
        "rho_T": rho_T,
        "psi_r": psi_r,
        "psi_qmc": psi_qmc,
        "E0_qmc": E0_qmc,
        "E0_r": E0_r,
        "E_proxy_exact_in_qmc": E_proxy_exact_in_qmc,
        "E_pulser_in_qmc": E_pulser_in_qmc,
        "E_pulser_in_proxy": E_pulser_in_proxy,
        "ratio_proxy_exact": ratio_proxy_exact,
        "ratio_pulser": ratio_pulser,
    }


def scan_annealing_times(
    n,
    positions,
    target_edges,
    omega_prep,
    prep_duration,
    omega_hold,
    hold_duration,
    omega_max,
    ramp_up_duration,
    T_values,
    sampling_rate=0.05,
    scale=15.5,
):
    rows = []
    for T in T_values:
        out = evaluate_pulser_final_state(
            n=n,
            positions=positions,
            target_edges=target_edges,
            omega_prep=omega_prep,
            prep_duration=prep_duration,
            omega_hold=omega_hold,
            hold_duration=hold_duration,
            omega_max=omega_max,
            ramp_up_duration=ramp_up_duration,
            T=T,
            sampling_rate=sampling_rate,
            scale=scale,
        )

        overlap_proxy = state_overlap_pure(out["psi_r"], out["psi_T"])
        rows.append({
            "T": float(T),
            "E_pulser_in_qmc": float(out["E_pulser_in_qmc"]),
            "E_proxy_exact_in_qmc": float(out["E_proxy_exact_in_qmc"]),
            "ratio_pulser": float(out["ratio_pulser"]),
            "ratio_proxy_exact": float(out["ratio_proxy_exact"]),
            "overlap_proxy": float(overlap_proxy),
        })

    return rows


def evaluate_piecewise_pulse_sequence(
    n,
    positions,
    target_edges,
    pulse_params,
    pulse_duration=250,
    sampling_rate=0.05,
):
    H_qmc = build_qmc_hamiltonian(n, target_edges)
    E0_qmc, _ = ground_state(H_qmc)

    couplings = couplings_from_positions(positions, c3=1.0)
    H_r = build_xy_hamiltonian(n, couplings)
    _, psi_r = ground_state(H_r)

    seq = build_xy_piecewise_sequence(
        positions=positions,
        pulse_params=pulse_params,
        pulse_duration=pulse_duration,
    )

    result = run_pulser_sequence(seq, sampling_rate=sampling_rate)
    psi_T = extract_final_statevector_from_result(result)
    rho_T = statevector_to_density(psi_T)

    E_qmc = expectation_value(rho_T, H_qmc)
    ratio_qmc = E_qmc / E0_qmc if abs(E0_qmc) > 1e-12 else np.nan
    overlap_proxy = state_overlap_pure(psi_r, psi_T)

    return {
        "seq": seq,
        "result": result,
        "psi_T": psi_T,
        "rho_T": rho_T,
        "E_qmc": E_qmc,
        "ratio_qmc": ratio_qmc,
        "overlap_proxy": overlap_proxy,
    }
