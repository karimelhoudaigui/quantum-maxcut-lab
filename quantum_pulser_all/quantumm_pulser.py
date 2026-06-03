import numpy as np

from pulser import Register, Sequence, Pulse
from pulser.devices import MockDevice
from pulser.waveforms import (
    RampWaveform,
    ConstantWaveform,
    BlackmanWaveform,
    CustomWaveform,
)
from pulser_simulation import QutipEmulator

from quantum_utils import *


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
    result = sim.run()
    return result


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

def grid_search_adiabatic_parameters(
    n,
    positions,
    target_edges,
    omega_prep,
    prep_duration,
    hold_durations,
    ramp_up_durations,
    omega_max_values,
    T_values,
    sampling_rate=0.05,
    scale=15.5,
):
    """
    Teste toutes les combinaisons :
    - hold_duration
    - ramp_up_duration
    - omega_max
    - T

    Retourne :
    - tous les résultats
    - le meilleur résultat selon ratio_pulser
    """
    all_results = []

    best_result = None
    best_ratio = -np.inf

    total = (
        len(hold_durations)
        * len(ramp_up_durations)
        * len(omega_max_values)
        * len(T_values)
    )
    counter = 0

    for hold_duration in hold_durations:
        for ramp_up_duration in ramp_up_durations:
            for omega_max in omega_max_values:
                for T in T_values:
                    counter += 1
                    print(
                        f"[{counter}/{total}] "
                        f"hold={hold_duration}, "
                        f"ramp_up={ramp_up_duration}, "
                        f"omega_max={omega_max:.6f}, "
                        f"T={T}"
                    )

                    try:
                        out = evaluate_pulser_final_state(
                            n=n,
                            positions=positions,
                            target_edges=target_edges,
                            omega_prep=omega_prep,
                            prep_duration=prep_duration,
                            omega_hold=omega_max,
                            hold_duration=hold_duration,
                            omega_max=omega_max,
                            ramp_up_duration=ramp_up_duration,
                            T=T,
                            sampling_rate=sampling_rate,
                            scale=scale,
                        )

                        overlap_proxy = state_overlap_pure(out["psi_r"], out["psi_T"])

                        row = {
                            "hold_duration": int(hold_duration),
                            "ramp_up_duration": int(ramp_up_duration),
                            "omega_max": float(omega_max),
                            "T": int(T),
                            "E0_qmc": float(out["E0_qmc"]),
                            "E0_r": float(out["E0_r"]),
                            "E_proxy_exact_in_qmc": float(out["E_proxy_exact_in_qmc"]),
                            "E_pulser_in_qmc": float(out["E_pulser_in_qmc"]),
                            "E_pulser_in_proxy": float(out["E_pulser_in_proxy"]),
                            "ratio_proxy_exact": float(out["ratio_proxy_exact"]),
                            "ratio_pulser": float(out["ratio_pulser"]),
                            "overlap_proxy": float(overlap_proxy),
                        }

                        all_results.append(row)

                        if row["ratio_pulser"] > best_ratio:
                            best_ratio = row["ratio_pulser"]
                            best_result = row.copy()

                    except Exception as e:
                        print(
                            f"Erreur pour "
                            f"hold={hold_duration}, ramp_up={ramp_up_duration}, "
                            f"omega_max={omega_max}, T={T} -> {e}"
                        )

    # Tri décroissant par ratio
    all_results = sorted(all_results, key=lambda x: x["ratio_pulser"], reverse=True)

    return {
        "best_result": best_result,
        "all_results": all_results,
    }
# =========================================================
# 1) Séquence adiabatique corrigée
# =========================================================
def build_xy_adiabatic_sequence(
    positions,
    omega_prep,
    prep_duration,
    omega_hold,
    hold_duration,
    omega_max,
    ramp_up_duration,
    anneal_duration,
    scale=15.5,
):
    """
    Séquence XY en 4 morceaux :
    1) pulse de préparation
    2) rampe montante 0 -> omega_max
    3) palier à omega_hold
    4) rampe descendante omega_max -> 0

    Remarque :
    - omega_hold peut être pris égal à omega_max pour un vrai palier haut
    - si on veut simplifier, on peut mettre ramp_up_duration = 0 plus tard
    """
    reg = build_xy_register(positions, scale=scale)

    seq = Sequence(reg, MockDevice)
    seq.declare_channel("mw", "mw_global")

    # 1) Préparation de |−x>^n
    prep_pulse = Pulse.ConstantPulse(
        duration=int(prep_duration),
        amplitude=float(omega_prep),
        detuning=0.0,
        phase=np.pi / 2,
    )
    seq.add(prep_pulse, "mw")

    # 2) Rampe montante
    if ramp_up_duration > 0:
        amp_up = RampWaveform(int(ramp_up_duration), 0.0, float(omega_max))
        det_up = ConstantWaveform(int(ramp_up_duration), 0.0)
        seq.add(Pulse(amp_up, det_up, phase=0.0), "mw")

    # 3) Palier haut
    if hold_duration > 0:
        hold_pulse = Pulse.ConstantPulse(
            duration=int(hold_duration),
            amplitude=float(omega_hold),
            detuning=0.0,
            phase=0.0,
        )
        seq.add(hold_pulse, "mw")

    # 4) Rampe descendante lente
    if anneal_duration > 0:
        amp_down = RampWaveform(int(anneal_duration), float(omega_max), 0.0)
        det_down = ConstantWaveform(int(anneal_duration), 0.0)
        seq.add(Pulse(amp_down, det_down, phase=0.0), "mw")

    seq.measure("XY")
    return seq


# =========================================================
# 2) Ancienne séquence simple conservée si besoin
# =========================================================
def build_xy_annealing_sequence(positions, omega_max, T):
    reg = build_xy_register(positions)

    seq = Sequence(reg, MockDevice)
    seq.declare_channel("mw", "mw_global")

    half_T = int(T // 2)

    amp_up = RampWaveform(half_T, 0.0, omega_max)
    amp_down = RampWaveform(T - half_T, omega_max, 0.0)

    det_up = ConstantWaveform(half_T, 0.0)
    det_down = ConstantWaveform(T - half_T, 0.0)

    seq.add(Pulse(amp_up, det_up, phase=0.0), "mw")
    seq.add(Pulse(amp_down, det_down, phase=0.0), "mw")

    seq.measure("XY")
    return seq


# =========================================================
# 3) Séquence paramétrée par morceaux
# =========================================================
def build_xy_piecewise_sequence(positions, pulse_params, pulse_duration=250):
    """
    pulse_params = [amp_0, det_0, phase_0, amp_1, det_1, phase_1, ...]
    """
    reg = build_xy_register(positions)

    seq = Sequence(reg, MockDevice)
    seq.declare_channel("mw", "mw_global")

    pulse_params = np.asarray(pulse_params, dtype=float)
    assert len(pulse_params) % 3 == 0

    n_pulses = len(pulse_params) // 3

    for k in range(n_pulses):
        amp = float(pulse_params[3 * k + 0])
        det = float(pulse_params[3 * k + 1])
        phase = float(pulse_params[3 * k + 2])

        pulse = Pulse.ConstantPulse(
            duration=int(pulse_duration),
            amplitude=amp,
            detuning=det,
            phase=phase,
        )
        seq.add(pulse, "mw")

    seq.measure("XY")
    return seq


# =========================================================
# 4) Évaluation de l'expérience adiabatique
# =========================================================
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

    # 1) Préparation |−x>^n
    prep_pulse = Pulse.ConstantPulse(
        duration=int(prep_duration),
        amplitude=float(omega_prep),
        detuning=0.0,
        phase=np.pi / 2,
    )
    seq.add(prep_pulse, "mw")

    # 2) Montée lisse vers omega_peak
    if rise_duration > 0:
        rise_samples = np.linspace(0.0, float(omega_peak), int(rise_duration))
        rise_det_samples = np.linspace(
            float(delta_start),
            float(delta_hold),
            int(rise_duration),
        )

        rise_amp = CustomWaveform(rise_samples)
        rise_det = CustomWaveform(rise_det_samples)

        seq.add(Pulse(rise_amp, rise_det, phase=0.0), "mw")

    # 3) Palier
    if hold_duration > 0:
        hold_pulse = Pulse.ConstantPulse(
            duration=int(hold_duration),
            amplitude=float(omega_peak),
            detuning=float(delta_hold),
            phase=0.0,
        )
        seq.add(hold_pulse, "mw")

    # 4) Descente lisse
    if fall_duration > 0:
        fall_samples = np.linspace(float(omega_peak), 0.0, int(fall_duration))
        fall_det_samples = np.linspace(
            float(delta_hold),
            float(delta_end),
            int(fall_duration),
        )

        fall_amp = CustomWaveform(fall_samples)
        fall_det = CustomWaveform(fall_det_samples)

        seq.add(Pulse(fall_amp, fall_det, phase=0.0), "mw")

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


# =========================================================
# 5) Recherche aléatoire sur séquence paramétrée
# =========================================================
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
        pulse_duration=pulse_duration
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


def random_search_xy_pulses(
    n,
    positions,
    target_edges,
    n_pulses=6,
    pulse_duration=200,
    n_trials=100,
    sampling_rate=0.05,
    amp_min=0.0,
    amp_max=2 * np.pi * 4.0,
    det_min=-2 * np.pi * 2.0,
    det_max=2 * np.pi * 2.0,
):
    best_E_qmc = np.inf
    best_ratio_qmc = np.nan
    best_overlap_proxy = 0.0
    best_params = None
    best_seq = None

    for trial in range(n_trials):
        params = []

        for _ in range(n_pulses):
            amp = np.random.uniform(amp_min, amp_max)
            det = np.random.uniform(det_min, det_max)
            phase = np.random.uniform(-np.pi, np.pi)

            params.extend([amp, det, phase])

        params = np.array(params, dtype=float)

        try:
            out = evaluate_piecewise_pulse_sequence(
                n=n,
                positions=positions,
                target_edges=target_edges,
                pulse_params=params,
                pulse_duration=pulse_duration,
                sampling_rate=sampling_rate,
            )

            E_qmc = out["E_qmc"]

            if E_qmc < best_E_qmc:
                best_E_qmc = E_qmc
                best_ratio_qmc = out["ratio_qmc"]
                best_overlap_proxy = out["overlap_proxy"]
                best_params = params.copy()
                best_seq = out["seq"]

        except Exception as e:
            print(f"[trial {trial}] erreur : {e}")

    return {
        "best_E_qmc": best_E_qmc,
        "best_ratio_qmc": best_ratio_qmc,
        "best_overlap_proxy": best_overlap_proxy,
        "best_params": best_params,
        "best_seq": best_seq,
    }
    
