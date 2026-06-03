import numpy as np

from pulser import Pulse, Sequence
from pulser.devices import MockDevice
from pulser.waveforms import CustomWaveform

from quantum_utils import build_qmc_hamiltonian, build_xy_hamiltonian, couplings_from_positions, ground_state

from .pulser_core import (
    build_xy_register,
    expectation_value,
    extract_final_statevector_from_result,
    run_pulser_sequence,
    state_overlap_pure,
    statevector_to_density,
)


def build_xy_smooth_sequence(
    positions,
    omega_prep,
    prep_duration,
    omega_peak,
    rise_duration,
    hold_duration,
    fall_duration,
    delta_start,
    delta_hold,
    delta_end,
    scale=15.5,
):
    reg = build_xy_register(positions, scale=scale)

    seq = Sequence(reg, MockDevice)
    seq.declare_channel("mw", "mw_global")

    prep_pulse = Pulse.ConstantPulse(
        duration=int(prep_duration),
        amplitude=float(omega_prep),
        detuning=0.0,
        phase=np.pi / 2,
    )
    seq.add(prep_pulse, "mw")

    if rise_duration > 0:
        rise_samples = np.linspace(0.0, float(omega_peak), int(rise_duration))
        rise_det_samples = np.linspace(float(delta_start), float(delta_hold), int(rise_duration))
        seq.add(Pulse(CustomWaveform(rise_samples), CustomWaveform(rise_det_samples), phase=0.0), "mw")

    if hold_duration > 0:
        hold_pulse = Pulse.ConstantPulse(
            duration=int(hold_duration),
            amplitude=float(omega_peak),
            detuning=float(delta_hold),
            phase=0.0,
        )
        seq.add(hold_pulse, "mw")

    if fall_duration > 0:
        fall_samples = np.linspace(float(omega_peak), 0.0, int(fall_duration))
        fall_det_samples = np.linspace(float(delta_hold), float(delta_end), int(fall_duration))
        seq.add(Pulse(CustomWaveform(fall_samples), CustomWaveform(fall_det_samples), phase=0.0), "mw")

    seq.measure("XY")
    return seq


def evaluate_smooth_pulser_final_state(
    n,
    positions,
    target_edges,
    omega_prep,
    prep_duration,
    omega_peak,
    rise_duration,
    hold_duration,
    fall_duration,
    delta_start,
    delta_hold,
    delta_end,
    sampling_rate=0.05,
    scale=15.5,
):
    H_qmc = build_qmc_hamiltonian(n, target_edges)
    E0_qmc, psi_qmc = ground_state(H_qmc)

    couplings = couplings_from_positions(positions, c3=1.0)
    H_r = build_xy_hamiltonian(n, couplings)
    E0_r, psi_r = ground_state(H_r)

    seq = build_xy_smooth_sequence(
        positions=positions,
        omega_prep=omega_prep,
        prep_duration=prep_duration,
        omega_peak=omega_peak,
        rise_duration=rise_duration,
        hold_duration=hold_duration,
        fall_duration=fall_duration,
        delta_start=delta_start,
        delta_hold=delta_hold,
        delta_end=delta_end,
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
    overlap_proxy = state_overlap_pure(psi_r, psi_T)

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
        "overlap_proxy": overlap_proxy,
    }


def grid_search_smooth_parameters(
    n,
    positions,
    target_edges,
    omega_prep,
    prep_duration,
    omega_peak_values,
    rise_durations,
    hold_durations,
    fall_durations,
    delta_start_values,
    delta_hold_values,
    delta_end_values,
    sampling_rate=0.05,
    scale=15.5,
):
    all_results = []
    best_result = None
    best_ratio = -np.inf

    total = (
        len(omega_peak_values)
        * len(rise_durations)
        * len(hold_durations)
        * len(fall_durations)
        * len(delta_start_values)
        * len(delta_hold_values)
        * len(delta_end_values)
    )
    counter = 0

    for omega_peak in omega_peak_values:
        for rise_duration in rise_durations:
            for hold_duration in hold_durations:
                for fall_duration in fall_durations:
                    for delta_start in delta_start_values:
                        for delta_hold in delta_hold_values:
                            for delta_end in delta_end_values:
                                counter += 1
                                print(
                                    f"[{counter}/{total}] "
                                    f"omega_peak={omega_peak:.6f}, "
                                    f"rise={rise_duration}, "
                                    f"hold={hold_duration}, "
                                    f"fall={fall_duration}, "
                                    f"dstart={delta_start:.6f}, "
                                    f"dhold={delta_hold:.6f}, "
                                    f"dend={delta_end:.6f}"
                                )

                                try:
                                    out = evaluate_smooth_pulser_final_state(
                                        n=n,
                                        positions=positions,
                                        target_edges=target_edges,
                                        omega_prep=omega_prep,
                                        prep_duration=prep_duration,
                                        omega_peak=omega_peak,
                                        rise_duration=rise_duration,
                                        hold_duration=hold_duration,
                                        fall_duration=fall_duration,
                                        delta_start=delta_start,
                                        delta_hold=delta_hold,
                                        delta_end=delta_end,
                                        sampling_rate=sampling_rate,
                                        scale=scale,
                                    )

                                    row = {
                                        "omega_peak": float(omega_peak),
                                        "rise_duration": int(rise_duration),
                                        "hold_duration": int(hold_duration),
                                        "fall_duration": int(fall_duration),
                                        "delta_start": float(delta_start),
                                        "delta_hold": float(delta_hold),
                                        "delta_end": float(delta_end),
                                        "E0_qmc": float(out["E0_qmc"]),
                                        "E0_r": float(out["E0_r"]),
                                        "E_proxy_exact_in_qmc": float(out["E_proxy_exact_in_qmc"]),
                                        "E_pulser_in_qmc": float(out["E_pulser_in_qmc"]),
                                        "E_pulser_in_proxy": float(out["E_pulser_in_proxy"]),
                                        "ratio_proxy_exact": float(out["ratio_proxy_exact"]),
                                        "ratio_pulser": float(out["ratio_pulser"]),
                                        "overlap_proxy": float(out["overlap_proxy"]),
                                    }

                                    all_results.append(row)
                                    if row["ratio_pulser"] > best_ratio:
                                        best_ratio = row["ratio_pulser"]
                                        best_result = row.copy()

                                except Exception as e:
                                    print(f"Erreur : {e}")

    all_results = sorted(all_results, key=lambda x: x["ratio_pulser"], reverse=True)
    return {
        "best_result": best_result,
        "all_results": all_results,
    }
