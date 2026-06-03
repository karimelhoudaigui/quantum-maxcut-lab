import numpy as np

from .pulser_core import state_overlap_pure
from .pulser_eval import evaluate_piecewise_pulse_sequence, evaluate_pulser_final_state


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

    all_results = sorted(all_results, key=lambda x: x["ratio_pulser"], reverse=True)
    return {
        "best_result": best_result,
        "all_results": all_results,
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
