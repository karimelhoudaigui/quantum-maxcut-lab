# ================================================
# MAIN QUANTUM FILE - Version propre et organisée
# ================================================

import json
import numpy as np

from quantum_utils import *
from quantum_optmization import optimize_atom_positions
from quantum_plot import *
from quantum_benchmark import *
from quantum_io import *
from quantum_pulser import (
    build_xy_adiabatic_sequence,
    build_xy_smooth_sequence,
    compute_edge_correlators,
    evaluate_pulser_final_state,
    evaluate_smooth_pulser_final_state,
    grid_search_adiabatic_parameters,
    grid_search_smooth_parameters,
    random_search_xy_pulses,
    scan_annealing_times,
    state_overlap_pure,
    study_fixed_smooth_sequence_on_random_graphs,
)
from quantum_hybrid import run_hybrid_on_pulser_output
from quantum_hybrid import (
    plot_hybrid_distribution,
    plot_hybrid_scaling_summary,
    plot_hybrid_vs_pulser_scatter,
    study_fixed_hybrid_sequence_on_random_graphs,
)
from graph_structure_study import (
    plot_hybrid_by_graph_type,
    plot_hybrid_vs_density,
    plot_mapping_by_graph_family,
    plot_mapping_by_graph_type,
    plot_mapping_error_by_connectivity_bucket,
    plot_mapping_vs_avg_degree,
    plot_mapping_vs_density,
    plot_mapping_vs_max_degree,
    plot_proxy_by_graph_type,
    plot_proxy_vs_avg_degree,
    plot_proxy_vs_density,
    study_graph_structure_on_random_graphs,
)


if __name__ == "__main__":

    print("=" * 80)
    print("               QUANTUM MAX-CUT - RYDBERG PROXY")
    print("=" * 80)

    # ==================== CONFIGURATION ====================
    RUN_BENCHMARK = False
    RUN_SINGLE_TEST = False

    RUN_PULSER_EXPERIMENT = False
    RUN_PULSER_PARAM_SEARCH = False
    RUN_PULSER_GRID_SEARCH = False

    RUN_PULSER_SMOOTH_EXPERIMENT = False
    RUN_PULSER_SMOOTH_GRID_SEARCH = False
    RUN_PULSER_SMOOTH_GRAPH_STUDY = False

    RUN_HYBRID_SINGLE_EXPERIMENT = False
    RUN_HYBRID_GRAPH_STUDY = False

    RUN_GRAPH_STRUCTURE_STUDY = True
    SAVE_RESULTS = True

    active_modes = [
        RUN_BENCHMARK,
        RUN_SINGLE_TEST,
        RUN_PULSER_EXPERIMENT,
        RUN_PULSER_PARAM_SEARCH,
        RUN_PULSER_GRID_SEARCH,
        RUN_PULSER_SMOOTH_EXPERIMENT,
        RUN_PULSER_SMOOTH_GRID_SEARCH,
        RUN_PULSER_SMOOTH_GRAPH_STUDY,
        RUN_HYBRID_SINGLE_EXPERIMENT,
        RUN_HYBRID_GRAPH_STUDY,
        RUN_GRAPH_STRUCTURE_STUDY,
    ]

    if sum(active_modes) > 1:
        raise ValueError("Un seul mode doit être activé à la fois.")

    print("Modes actifs :")
    print(f"  RUN_BENCHMARK                = {RUN_BENCHMARK}")
    print(f"  RUN_SINGLE_TEST              = {RUN_SINGLE_TEST}")
    print(f"  RUN_PULSER_EXPERIMENT        = {RUN_PULSER_EXPERIMENT}")
    print(f"  RUN_PULSER_PARAM_SEARCH      = {RUN_PULSER_PARAM_SEARCH}")
    print(f"  RUN_PULSER_GRID_SEARCH       = {RUN_PULSER_GRID_SEARCH}")
    print(f"  RUN_PULSER_SMOOTH_EXPERIMENT = {RUN_PULSER_SMOOTH_EXPERIMENT}")
    print(f"  RUN_PULSER_SMOOTH_GRID_SEARCH= {RUN_PULSER_SMOOTH_GRID_SEARCH}")
    print(f"  RUN_PULSER_SMOOTH_GRAPH_STUDY = {RUN_PULSER_SMOOTH_GRAPH_STUDY}")
    print(f"  RUN_HYBRID_SINGLE_EXPERIMENT = {RUN_HYBRID_SINGLE_EXPERIMENT}")
    print(f"  RUN_HYBRID_GRAPH_STUDY       = {RUN_HYBRID_GRAPH_STUDY}")
    print(f"  RUN_GRAPH_STRUCTURE_STUDY    = {RUN_GRAPH_STRUCTURE_STUDY}")
    print()
    output_dirs = ensure_results_dirs()
    n_values = [4, 5, 6, 7, 8]
    n_instances = 60

    # ====================== BENCHMARK ======================
    if RUN_BENCHMARK:
        print(f"\nLancement du benchmark : {n_instances} instances pour n = {n_values}\n")

        results = benchmark_over_n(
            n_values=n_values,
            n_instances_per_n=n_instances,
            edge_prob=0.6,
            w_min=0.5,
            w_max=1.5,
            seed=42
        )

        summarize_results(results)

        if SAVE_RESULTS:
            csv_path = table_output_path("benchmark_summary.csv")
            json_path = json_output_path("benchmark_full.json")
            save_results_csv(results, filename=csv_path)
            save_results_json(results, filename=json_path)
            print("✅ Résultats sauvegardés (CSV + JSON)")

        plot_mapping_error_vs_n(results, save_path=figure_output_path("figure1_mapping_error_vs_n.png"))
        plot_ratio_vs_n(results, save_path=figure_output_path("figure2_ratio_vs_n.png"))
        plot_ratio_vs_mapping_error(results, save_path=figure_output_path("figure3_ratio_vs_mapping_error.png"))
        print("✅ Plots sauvegardés")

    # ====================== TEST EXACT / DEBUG ======================
    elif RUN_SINGLE_TEST:
        print("\nMode TEST SINGLE INSTANCE activé\n")

        n = 4
        target_edges = [
            (0, 1, 1.0),
            (1, 2, 0.8),
            (2, 3, 1.2),
            (0, 3, 0.6),
        ]

        best_positions, best_couplings, best_error = optimize_atom_positions(target_edges, n=n)

        print("=== POSITIONS OPTIMISÉES ===")
        for i, pos in enumerate(best_positions):
            print(f"Atome {i}: ({pos[0]:.6f}, {pos[1]:.6f})")

        print("\n=== COUPLAGES GÉOMÉTRIQUES ===")
        for i, j, J in sorted(best_couplings):
            print(f"({i},{j}) -> J = {J:.6f}")

        print(f"\nErreur de mapping = {best_error:.6f}")

    # ====================== EXPÉRIENCE PULSER SIMPLE ======================
    elif RUN_PULSER_EXPERIMENT:
        print("\nMode EXPÉRIENCE PULSER activé\n")

        n = 4
        target_edges = [
            (0, 1, 1.0),
            (1, 2, 0.8),
            (2, 3, 1.2),
            (0, 3, 0.6),
        ]

        best_positions, best_couplings, best_error = optimize_atom_positions(target_edges, n=n)

        print("=== POSITIONS OPTIMISÉES ===")
        for i, pos in enumerate(best_positions):
            print(f"Atome {i}: ({pos[0]:.6f}, {pos[1]:.6f})")

        print(f"\nErreur de mapping = {best_error:.6f}")
        omega_prep = 2 * np.pi * 2.0
        prep_duration = 125

        omega_max = 2 * np.pi * 4.0
        omega_hold = omega_max

        ramp_up_duration = 1000
        hold_duration = 4000

        T0 = 12000
        sampling_rate = 0.05
        scale = 15.5

        T_values = [4000, 8000, 12000, 16000, 20000]

        
        print("\n=== SÉQUENCE PULSER ===")
        seq_test = build_xy_adiabatic_sequence(
        positions=best_positions,
        omega_prep=omega_prep,
        prep_duration=prep_duration,
        omega_hold=omega_hold,
        hold_duration=hold_duration,
        omega_max=omega_max,
        ramp_up_duration=ramp_up_duration,
        anneal_duration=T0,
        scale=scale,
        )   
        seq_test.draw()
        print("Durée totale :", seq_test.get_duration())
        print("Base de mesure :", seq_test.get_measurement_basis())

        print("\n=== ÉVALUATION PULSER ===")
        out = evaluate_pulser_final_state(
            n=n,
            positions=best_positions,
            target_edges=target_edges,
            omega_prep=omega_prep,
            prep_duration=prep_duration,
            omega_hold=omega_hold,
            hold_duration=hold_duration,
            omega_max=omega_max,
            ramp_up_duration=ramp_up_duration,
            T=T0,
            sampling_rate=sampling_rate,
            scale=scale,
        )

        print(f"E0(H_qmc)                 = {out['E0_qmc']:.6f}")
        print(f"E0(H_r)                   = {out['E0_r']:.6f}")
        print(f"E(proxy exact dans QMC)   = {out['E_proxy_exact_in_qmc']:.6f}")
        print(f"E(Pulser final dans QMC)  = {out['E_pulser_in_qmc']:.6f}")
        print(f"Ratio proxy exact         = {out['ratio_proxy_exact']:.6f}")
        print(f"Ratio Pulser              = {out['ratio_pulser']:.6f}")

        overlap_proxy = state_overlap_pure(out["psi_r"], out["psi_T"])
        print(f"Overlap avec le fondamental exact de H_r = {overlap_proxy:.6f}")

        print("\n=== CORRÉLATIONS FINALES SUR LES ARÊTES ===")
        corrs = compute_edge_correlators(out["rho_T"], n, target_edges)
        for item in corrs:
            print(
                f"edge={item['edge']} | "
                f"XX={item['xx']:.6f}, "
                f"YY={item['yy']:.6f}, "
                f"ZZ={item['zz']:.6f}, "
                f"t={item['t']:.6f}"
            )

        print("\n=== SCAN EN TEMPS D'ANNEALING ===")
        scan_results = scan_annealing_times(
            n=n,
            positions=best_positions,
            target_edges=target_edges,
            omega_prep=omega_prep,
            prep_duration=prep_duration,
            omega_hold=omega_hold,
            hold_duration=hold_duration,
            omega_max=omega_max,
            ramp_up_duration=ramp_up_duration,
            T_values=T_values,
            sampling_rate=sampling_rate,
            scale=scale,
        )
        for row in scan_results:
            print(
                f"T={row['T']:7.1f} | "
                f"ratio_pulser={row['ratio_pulser']:.6f} | "
                f"ratio_proxy_exact={row['ratio_proxy_exact']:.6f} | "
                f"overlap_proxy={row['overlap_proxy']:.6f}"
            )

        if SAVE_RESULTS:
            out_path = save_json_data(scan_results, "pulser_adiabatic_scan.json")
            print(f"\n✅ Résultats sauvegardés dans {out_path}")

    # ====================== RECHERCHE DE PARAMÈTRES SUR PULSES ======================
    elif RUN_PULSER_PARAM_SEARCH:
        print("\nMode RECHERCHE PARAMÉTRIQUE PULSER activé\n")

        n = 4
        target_edges = [
            (0, 1, 1.0),
            (1, 2, 0.8),
            (2, 3, 1.2),
            (0, 3, 0.6),
        ]

        best_positions, best_couplings, best_error = optimize_atom_positions(target_edges, n=n)

        print("=== POSITIONS OPTIMISÉES ===")
        for i, pos in enumerate(best_positions):
            print(f"Atome {i}: ({pos[0]:.6f}, {pos[1]:.6f})")

        print(f"\nErreur de mapping = {best_error:.6f}")

        search_out = random_search_xy_pulses(
            n=n,
            positions=best_positions,
            target_edges=target_edges,
            n_pulses=6,
            pulse_duration=200,
            n_trials=100,
            sampling_rate=0.05,
            amp_min=0.0,
            amp_max=2 * np.pi * 4.0,
            det_min=-2 * np.pi * 2.0,
            det_max=2 * np.pi * 2.0,
        )

        print("\n=== MEILLEUR RÉSULTAT TROUVÉ ===")
        print(f"Best energy in QMC  = {search_out['best_E_qmc']:.6f}")
        print(f"Best ratio          = {search_out['best_ratio_qmc']:.6f}")
        print(f"Best overlap proxy  = {search_out['best_overlap_proxy']:.6f}")
        print(f"Best params         = {search_out['best_params']}")

        print("\n=== SÉQUENCE GAGNANTE ===")
        search_out["best_seq"].draw()

        if SAVE_RESULTS:
            serializable = {
                "best_E_qmc": float(search_out["best_E_qmc"]),
                "best_ratio_qmc": float(search_out["best_ratio_qmc"]),
                "best_overlap_proxy": float(search_out["best_overlap_proxy"]),
                "best_params": [float(x) for x in search_out["best_params"]],
            }
            out_path = save_json_data(serializable, "pulser_param_search_best.json")

            print(f"\n✅ Résultats sauvegardés dans {out_path}")
        # ====================== GRID SEARCH ADIABATIQUE ======================
    elif RUN_PULSER_GRID_SEARCH:
        print("\nMode GRID SEARCH ADIABATIQUE PULSER activé\n")

        n = 4
        target_edges = [
            (0, 1, 1.0),
            (1, 2, 0.8),
            (2, 3, 1.2),
            (0, 3, 0.6),
        ]

        best_positions, best_couplings, best_error = optimize_atom_positions(target_edges, n=n)

        print("=== POSITIONS OPTIMISÉES ===")
        for i, pos in enumerate(best_positions):
            print(f"Atome {i}: ({pos[0]:.6f}, {pos[1]:.6f})")

        print(f"\nErreur de mapping = {best_error:.6f}")

        omega_prep = 2 * np.pi * 2.0
        prep_duration = 125
        sampling_rate = 0.05
        scale = 15.5

        hold_durations = [1000, 2000, 3000, 4000]

        ramp_up_durations = [1500, 2000, 2500, 3000]

        omega_max_values = [
            2 * np.pi * 2.5,
            2 * np.pi * 3.0,
            2 * np.pi * 3.5,
        ]

        T_values = [18000, 20000, 22000, 24000] 

        search_out = grid_search_adiabatic_parameters(
            n=n,
            positions=best_positions,
            target_edges=target_edges,
            omega_prep=omega_prep,
            prep_duration=prep_duration,
            hold_durations=hold_durations,
            ramp_up_durations=ramp_up_durations,
            omega_max_values=omega_max_values,
            T_values=T_values,
            sampling_rate=sampling_rate,
            scale=scale,
        )

        best_result = search_out["best_result"]
        all_results = search_out["all_results"]

        print("\n=== MEILLEUR RÉSULTAT TROUVÉ ===")
        print(f"hold_duration     = {best_result['hold_duration']}")
        print(f"ramp_up_duration  = {best_result['ramp_up_duration']}")
        print(f"omega_max         = {best_result['omega_max']:.6f}")
        print(f"T                 = {best_result['T']}")
        print(f"E_pulser_in_qmc   = {best_result['E_pulser_in_qmc']:.6f}")
        print(f"E_pulser_in_proxy = {best_result['E_pulser_in_proxy']:.6f}")
        print(f"ratio_pulser      = {best_result['ratio_pulser']:.6f}")
        print(f"overlap_proxy     = {best_result['overlap_proxy']:.6f}")

        print("\n=== TOP 10 ===")
        for i, row in enumerate(all_results[:10], start=1):
            print(
                f"{i:2d} | "
                f"hold={row['hold_duration']:5d} | "
                f"ramp_up={row['ramp_up_duration']:5d} | "
                f"omega_max={row['omega_max']:.6f} | "
                f"T={row['T']:6d} | "
                f"ratio={row['ratio_pulser']:.6f} | "
                f"overlap={row['overlap_proxy']:.6f}"
            )

        if SAVE_RESULTS:
            all_path = save_json_data(all_results, "pulser_adiabatic_grid_search.json")
            best_path = save_json_data(best_result, "pulser_adiabatic_grid_search_best.json")

            print("\n✅ Résultats sauvegardés dans :")
            print(f"   - {all_path}")
            print(f"   - {best_path}")
    # ====================== EXPÉRIENCE PULSER SMOOTH ======================
    elif RUN_PULSER_SMOOTH_EXPERIMENT:
        print("\nMode EXPÉRIENCE PULSER SMOOTH activé\n")

        n = 4
        target_edges = [
            (0, 1, 1.0),
            (1, 2, 0.8),
            (2, 3, 1.2),
            (0, 3, 0.6),
        ]

        best_positions, best_couplings, best_error = optimize_atom_positions(target_edges, n=n)

        print("=== POSITIONS OPTIMISÉES ===")
        for i, pos in enumerate(best_positions):
            print(f"Atome {i}: ({pos[0]:.6f}, {pos[1]:.6f})")

        print(f"\nErreur de mapping = {best_error:.6f}")

        omega_prep = 2 * np.pi * 2.0
        prep_duration = 125

        omega_peak = 2 * np.pi * 2.0
        rise_duration = 1000
        hold_duration = 1000
        fall_duration = 26000

        delta_start = np.pi
        delta_hold = -np.pi / 2
        delta_end = -np.pi

        sampling_rate = 0.05
        scale = 15.5

        print("\n=== SÉQUENCE PULSER SMOOTH ===")
        seq_test = build_xy_smooth_sequence(
            positions=best_positions,
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
        seq_test.draw()
        print("Durée totale :", seq_test.get_duration())
        print("Base de mesure :", seq_test.get_measurement_basis())

        print("\n=== ÉVALUATION PULSER SMOOTH ===")
        out = evaluate_smooth_pulser_final_state(
            n=n,
            positions=best_positions,
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

        print(f"E0(H_qmc)                 = {out['E0_qmc']:.6f}")
        print(f"E0(H_r)                   = {out['E0_r']:.6f}")
        print(f"E(proxy exact dans QMC)   = {out['E_proxy_exact_in_qmc']:.6f}")
        print(f"E(Pulser final dans QMC)  = {out['E_pulser_in_qmc']:.6f}")
        print(f"E(Pulser final dans proxy)= {out['E_pulser_in_proxy']:.6f}")
        print(f"Ratio proxy exact         = {out['ratio_proxy_exact']:.6f}")
        print(f"Ratio Pulser              = {out['ratio_pulser']:.6f}")

        overlap_proxy = state_overlap_pure(out["psi_r"], out["psi_T"])
        print(f"Overlap avec le fondamental exact de H_r = {overlap_proxy:.6f}")

        print("\n=== CORRÉLATIONS FINALES SUR LES ARÊTES ===")
        corrs = compute_edge_correlators(out["rho_T"], n, target_edges)
        for item in corrs:
            print(
                f"edge={item['edge']} | "
                f"XX={item['xx']:.6f}, "
                f"YY={item['yy']:.6f}, "
                f"ZZ={item['zz']:.6f}, "
                f"t={item['t']:.6f}"
            )

        if SAVE_RESULTS:
            serializable_out = {
                "E0_qmc": float(out["E0_qmc"]),
                "E0_r": float(out["E0_r"]),
                "E_proxy_exact_in_qmc": float(out["E_proxy_exact_in_qmc"]),
                "E_pulser_in_qmc": float(out["E_pulser_in_qmc"]),
                "E_pulser_in_proxy": float(out["E_pulser_in_proxy"]),
                "ratio_proxy_exact": float(out["ratio_proxy_exact"]),
                "ratio_pulser": float(out["ratio_pulser"]),
                "overlap_proxy": float(overlap_proxy),
                "omega_peak": float(omega_peak),
                "rise_duration": int(rise_duration),
                "hold_duration": int(hold_duration),
                "fall_duration": int(fall_duration),
                "delta_start": float(delta_start),
                "delta_hold": float(delta_hold),
                "delta_end": float(delta_end),
            }

            out_path = save_json_data(serializable_out, "pulser_smooth_experiment.json")
            print(f"\n✅ Résultats sauvegardés dans {out_path}")
    elif RUN_PULSER_SMOOTH_GRID_SEARCH:
        print("\nMode GRID SEARCH PULSER SMOOTH activé\n")

        n = 4
        target_edges = [
            (0, 1, 1.0),
            (1, 2, 0.8),
            (2, 3, 1.2),
            (0, 3, 0.6),
        ]

        best_positions, best_couplings, best_error = optimize_atom_positions(target_edges, n=n)

        print("=== POSITIONS OPTIMISÉES ===")
        for i, pos in enumerate(best_positions):
            print(f"Atome {i}: ({pos[0]:.6f}, {pos[1]:.6f})")

        print(f"\nErreur de mapping = {best_error:.6f}")

        omega_prep = 2 * np.pi * 2.0
        prep_duration = 125
        sampling_rate = 0.05
        scale = 15.5

        omega_peak_values = [
            2 * np.pi * 2.0,
            2 * np.pi * 2.5,
            2 * np.pi * 3.0,
        ]

        rise_durations = [1000, 2000, 3000]
        hold_durations = [1000, 2000, 3000]
        fall_durations = [18000, 22000, 26000]

        delta_start_values = [
            0.0,
            2 * np.pi * 0.5,
            2 * np.pi * 1.0,
        ]

        delta_hold_values = [
            0.0,
            2 * np.pi * 0.25,
            -2 * np.pi * 0.25,
        ]

        delta_end_values = [
            0.0,
            -2 * np.pi * 0.5,
            -2 * np.pi * 1.0,
        ]

        search_out = grid_search_smooth_parameters(
            n=n,
            positions=best_positions,
            target_edges=target_edges,
            omega_prep=omega_prep,
            prep_duration=prep_duration,
            omega_peak_values=omega_peak_values,
            rise_durations=rise_durations,
            hold_durations=hold_durations,
            fall_durations=fall_durations,
            delta_start_values=delta_start_values,
            delta_hold_values=delta_hold_values,
            delta_end_values=delta_end_values,
            sampling_rate=sampling_rate,
            scale=scale,
        )

        best_result = search_out["best_result"]
        all_results = search_out["all_results"]

        print("\n=== MEILLEUR RÉSULTAT TROUVÉ ===")
        print(f"omega_peak        = {best_result['omega_peak']:.6f}")
        print(f"rise_duration     = {best_result['rise_duration']}")
        print(f"hold_duration     = {best_result['hold_duration']}")
        print(f"fall_duration     = {best_result['fall_duration']}")
        print(f"delta_start       = {best_result['delta_start']:.6f}")
        print(f"delta_hold        = {best_result['delta_hold']:.6f}")
        print(f"delta_end         = {best_result['delta_end']:.6f}")
        print(f"E_pulser_in_qmc   = {best_result['E_pulser_in_qmc']:.6f}")
        print(f"E_pulser_in_proxy = {best_result['E_pulser_in_proxy']:.6f}")
        print(f"ratio_pulser      = {best_result['ratio_pulser']:.6f}")
        print(f"overlap_proxy     = {best_result['overlap_proxy']:.6f}")

        print("\n=== TOP 10 ===")
        for i, row in enumerate(all_results[:10], start=1):
            print(
                f"{i:2d} | "
                f"omega_peak={row['omega_peak']:.6f} | "
                f"rise={row['rise_duration']:5d} | "
                f"hold={row['hold_duration']:5d} | "
                f"fall={row['fall_duration']:6d} | "
                f"dstart={row['delta_start']:.6f} | "
                f"dhold={row['delta_hold']:.6f} | "
                f"dend={row['delta_end']:.6f} | "
                f"ratio={row['ratio_pulser']:.6f} | "
                f"overlap={row['overlap_proxy']:.6f}"
            )

        if SAVE_RESULTS:
            all_path = save_json_data(all_results, "pulser_smooth_grid_search.json")
            best_path = save_json_data(best_result, "pulser_smooth_grid_search_best.json")

            print("\n✅ Résultats sauvegardés dans :")
            print(f"   - {all_path}")
            print(f"   - {best_path}")
    # ====================== EXPÉRIENCE HYBRIDE PULSER + SDP ======================
    elif RUN_HYBRID_SINGLE_EXPERIMENT:
        print("\nMode EXPÉRIENCE HYBRIDE activé\n")

        n = 4
        target_edges = [
            (0, 1, 1.0),
            (1, 2, 0.8),
            (2, 3, 1.2),
            (0, 3, 0.6),
        ]

        best_positions, best_couplings, best_error = optimize_atom_positions(target_edges, n=n)

        print("=== POSITIONS OPTIMISÉES ===")
        for i, pos in enumerate(best_positions):
            print(f"Atome {i}: ({pos[0]:.6f}, {pos[1]:.6f})")
        print(f"\nErreur de mapping = {best_error:.6f}")

        omega_prep = 2 * np.pi * 2.0
        prep_duration = 125

        omega_peak = 2 * np.pi * 2.0
        rise_duration = 1000
        hold_duration = 1000
        fall_duration = 26000

        delta_start = np.pi
        delta_hold = -np.pi / 2
        delta_end = -np.pi

        sampling_rate = 0.05
        scale = 15.5

        pulser_out = evaluate_smooth_pulser_final_state(
            n=n,
            positions=best_positions,
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

        corrs = compute_edge_correlators(pulser_out["rho_T"], n, target_edges)

        try:
            hybrid_out = run_hybrid_on_pulser_output(
                n=n,
                target_edges=target_edges,
                pulser_out=pulser_out,
                corrs=corrs,
                seed=1234,
                n_roundings=64,
            )
        except ImportError as e:
            print("\nImpossible de lancer l'étape SDP hybride.")
            print(e)
            print("Installe cvxpy dans l'environnement actif, puis relance ce mode.")
        else:
            print("=== RÉSULTAT PULSER ===")
            print(f"Ratio Pulser      = {pulser_out['ratio_pulser']:.6f}")
            print(f"E Pulser in QMC   = {pulser_out['E_pulser_in_qmc']:.6f}")

            print("\n=== RÉSULTAT ROUNDING ===")
            print(f"SDP status        = {hybrid_out['sdp_status']}")
            print(f"Best seed         = {hybrid_out['best_rounding_seed']}")
            print(f"N roundings       = {hybrid_out['n_roundings']}")
            print(f"Ratio Product     = {hybrid_out['ratio_product']:.6f}")
            print(f"E Product in QMC  = {hybrid_out['E_product_in_qmc']:.6f}")

            print("\n=== RÉSULTAT HYBRIDE FINAL ===")
            print(f"Winner            = {hybrid_out['winner']}")
            print(f"Ratio Hybrid      = {hybrid_out['ratio_hybrid']:.6f}")
            print(f"E Hybrid in QMC   = {hybrid_out['E_hybrid_in_qmc']:.6f}")

    # ====================== ÉTUDE MULTI-GRAPHES HYBRIDE ======================
    elif RUN_HYBRID_GRAPH_STUDY:
        print("\nMode ÉTUDE MULTI-GRAPHES HYBRIDE activé\n")

        n = 6
        graph_sample_sizes = [20, 50, 100]
        edge_prob = 0.6
        w_min = 0.5
        w_max = 1.5
        seed = 42
        require_connected = True

        omega_prep = 2 * np.pi * 2.0
        prep_duration = 125
        omega_peak = 2 * np.pi * 2.0
        rise_duration = 1000
        hold_duration = 1000
        fall_duration = 26000
        delta_start = np.pi
        delta_hold = -np.pi / 2
        delta_end = -np.pi
        sampling_rate = 0.05
        scale = 15.5
        n_roundings = 64

        scaling_summary = []
        run_tag = f"n{n}"

        try:
            for n_graphs in graph_sample_sizes:
                print("\n" + "-" * 80)
                print(f"Campagne hybride : n_graphs = {n_graphs}")
                print("-" * 80)

                study_out = study_fixed_hybrid_sequence_on_random_graphs(
                    n=n,
                    n_graphs=n_graphs,
                    edge_prob=edge_prob,
                    w_min=w_min,
                    w_max=w_max,
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
                    n_roundings=n_roundings,
                    seed=seed,
                    require_connected=require_connected,
                )

                summary = study_out["summary"]
                results = study_out["results"]
                scaling_summary.append(summary)

                print("\n=== RÉSUMÉ COMPACT ===")
                print(f"ratio_pulser_mean      = {summary['ratio_pulser_mean']:.6f}")
                print(f"ratio_product_mean     = {summary['ratio_product_mean']:.6f}")
                print(f"ratio_hybrid_mean      = {summary['ratio_hybrid_mean']:.6f}")
                print(f"rounding_win_count     = {summary['rounding_win_count']}")
                print(f"pulser_win_count       = {summary['pulser_win_count']}")
                print(f"mapping_error_mean     = {summary['mapping_error_mean']:.6f}")

                if SAVE_RESULTS:
                    results_path = save_json_data(results, f"hybrid_graph_study_{run_tag}_{n_graphs}.json")
                    summary_path = save_json_data(summary, f"hybrid_graph_study_{run_tag}_{n_graphs}_summary.json")
                    scatter_path = figure_output_path(f"figure_hybrid_vs_pulser_{run_tag}_{n_graphs}.png")
                    dist_path = figure_output_path(f"figure_hybrid_distribution_{run_tag}_{n_graphs}.png")

                    plot_hybrid_vs_pulser_scatter(
                        results,
                        save_path=scatter_path,
                        show=False,
                    )
                    plot_hybrid_distribution(
                        results,
                        save_path=dist_path,
                        show=False,
                    )

                    print("\n✅ Fichiers sauvegardés :")
                    print(f"   - {results_path}")
                    print(f"   - {summary_path}")
                    print(f"   - {scatter_path}")
                    print(f"   - {dist_path}")

        except ImportError as e:
            print("\nImpossible de lancer l'étude hybride complète.")
            print(e)
            print("Installe cvxpy dans l'environnement actif, puis relance ce mode.")
        else:
            print("\n" + "=" * 80)
            print("RÉSUMÉ GLOBAL FINAL")
            print("=" * 80)
            for row in scaling_summary:
                print(
                    f"n_graphs={row['n_graphs']:3d} | "
                    f"pulser_mean={row['ratio_pulser_mean']:.6f} | "
                    f"product_mean={row['ratio_product_mean']:.6f} | "
                    f"hybrid_mean={row['ratio_hybrid_mean']:.6f} | "
                    f"rounding_wins={row['rounding_win_count']:3d} | "
                    f"pulser_wins={row['pulser_win_count']:3d} | "
                    f"mapping_mean={row['mapping_error_mean']:.6f}"
                )

            if SAVE_RESULTS:
                scaling_path = save_json_data(scaling_summary, f"hybrid_graph_study_{run_tag}_scaling_summary.json")

                plot_hybrid_scaling_summary(
                    scaling_summary,
                    save_path=figure_output_path(f"figure_hybrid_scaling_{run_tag}.png"),
                    show=False,
                )

                print("\n✅ Fichiers globaux sauvegardés :")
                print(f"   - {scaling_path}")
                print(f"   - {figure_output_path(f'figure_hybrid_scaling_{run_tag}.png')}")

    # ====================== ÉTUDE STRUCTURE DU GRAPHE ======================
    elif RUN_GRAPH_STRUCTURE_STUDY:
        print("\nMode ÉTUDE STRUCTURE DU GRAPHE activé\n")

        n = 4
        n_graphs = 200
        study_level = "proxy_exact"
        edge_prob = 0.6
        w_min = 0.5
        w_max = 1.5
        seed = 42
        require_connected = True

        omega_prep = 2 * np.pi * 2.0
        prep_duration = 125
        omega_peak = 2 * np.pi * 2.0
        rise_duration = 1000
        hold_duration = 1000
        fall_duration = 26000
        delta_start = np.pi
        delta_hold = -np.pi / 2
        delta_end = -np.pi
        sampling_rate = 0.05
        scale = 15.5
        n_roundings = 64

        study_out = study_graph_structure_on_random_graphs(
            n=n,
            n_graphs=n_graphs,
            level=study_level,
            edge_prob=edge_prob,
            w_min=w_min,
            w_max=w_max,
            seed=seed,
            require_connected=require_connected,
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
            n_roundings=n_roundings,
        )

        results = study_out["results"]
        summary = study_out["summary"]
        category_summary = study_out["category_summary"]
        top_flop = study_out["top_flop"]
        conclusion_lines = study_out["conclusion_lines"]

        print("\n=== RÉSUMÉ STRUCTUREL ===")
        print(f"n_graphs                  = {summary['n_graphs']}")
        print(f"mapping_error_mean        = {summary['metrics']['mapping_error']['mean']:.6f}")
        print(f"ratio_proxy_exact_mean    = {summary['metrics']['ratio_proxy_exact']['mean']:.6f}")
        print(f"density_mean              = {summary['metrics']['density']['mean']:.6f}")
        print(f"avg_degree_mean           = {summary['metrics']['avg_degree']['mean']:.6f}")
        print(f"corr(density, error)      = {summary['correlations']['mapping_error']['density']:.6f}")
        print(f"corr(avg_degree, error)   = {summary['correlations']['mapping_error']['avg_degree']:.6f}")
        print(
            f"corr(density, proxy)      = "
            f"{summary['correlations']['ratio_proxy_exact']['density']:.6f}"
        )
        print("\n=== CONCLUSION PAR TYPES ===")
        for line in conclusion_lines:
            print(f"- {line}")

        if SAVE_RESULTS:
            level_tag = "" if study_level == "proxy_exact" else f"_{study_level}"
            results_path = save_json_data(results, f"graph_structure_study{level_tag}_n{n}.json")
            summary_path = save_json_data(summary, f"graph_structure_study{level_tag}_n{n}_summary.json")
            category_summary_path = save_json_data(
                category_summary,
                f"graph_structure_categories{level_tag}_n{n}_summary.json",
            )
            top_flop_path = save_json_data(
                top_flop,
                f"graph_structure_top_flop{level_tag}_n{n}.json",
            )

            map_density_path = figure_output_path(f"figure_mapping_vs_density{level_tag}_n{n}.png")
            map_avg_degree_path = figure_output_path(f"figure_mapping_vs_avg_degree{level_tag}_n{n}.png")
            map_max_degree_path = figure_output_path(f"figure_mapping_vs_max_degree{level_tag}_n{n}.png")
            proxy_density_path = figure_output_path(f"figure_proxy_vs_density{level_tag}_n{n}.png")
            proxy_degree_path = figure_output_path(f"figure_proxy_vs_degree{level_tag}_n{n}.png")
            connectivity_path = figure_output_path(
                f"figure_mapping_by_connectivity{level_tag}_n{n}.png"
            )
            graph_type_mapping_path = figure_output_path(
                f"figure_mapping_by_graph_type{level_tag}_n{n}.png"
            )
            graph_type_proxy_path = figure_output_path(
                f"figure_proxy_by_graph_type{level_tag}_n{n}.png"
            )
            graph_family_mapping_path = figure_output_path(
                f"figure_mapping_by_graph_family{level_tag}_n{n}.png"
            )

            plot_mapping_vs_density(results, save_path=map_density_path, show=False)
            plot_mapping_vs_avg_degree(results, save_path=map_avg_degree_path, show=False)
            plot_mapping_vs_max_degree(results, save_path=map_max_degree_path, show=False)
            plot_proxy_vs_density(results, save_path=proxy_density_path, show=False)
            plot_proxy_vs_avg_degree(results, save_path=proxy_degree_path, show=False)
            plot_mapping_error_by_connectivity_bucket(
                results,
                save_path=connectivity_path,
                show=False,
            )
            plot_mapping_by_graph_type(results, save_path=graph_type_mapping_path, show=False)
            plot_proxy_by_graph_type(results, save_path=graph_type_proxy_path, show=False)
            plot_mapping_by_graph_family(results, save_path=graph_family_mapping_path, show=False)

            saved_paths = [
                results_path,
                summary_path,
                category_summary_path,
                top_flop_path,
                map_density_path,
                map_avg_degree_path,
                map_max_degree_path,
                proxy_density_path,
                proxy_degree_path,
                connectivity_path,
                graph_type_mapping_path,
                graph_type_proxy_path,
                graph_family_mapping_path,
            ]

            if study_level == "hybrid":
                hybrid_density_path = figure_output_path(
                    f"figure_hybrid_vs_density{level_tag}_n{n}.png"
                )
                hybrid_graph_type_path = figure_output_path(
                    f"figure_hybrid_by_graph_type{level_tag}_n{n}.png"
                )
                plot_hybrid_vs_density(results, save_path=hybrid_density_path, show=False)
                plot_hybrid_by_graph_type(results, save_path=hybrid_graph_type_path, show=False)
                saved_paths.extend([hybrid_density_path, hybrid_graph_type_path])

            print("\n✅ Fichiers sauvegardés :")
            for path in saved_paths:
                print(f"   - {path}")

    # ====================== ÉTUDE MULTI-GRAPHES SMOOTH (n=4) ======================
    elif RUN_PULSER_SMOOTH_GRAPH_STUDY:
        print("\nMode ÉTUDE MULTI-GRAPHES SMOOTH activé\n")

        # Taille fixée
        n = 4

        # Paramètres des graphes aléatoires
        n_graphs = 100
        edge_prob = 0.6
        w_min = 0.5
        w_max = 1.5
        seed = 42

        # Meilleure séquence smooth trouvée
        omega_prep = 2 * np.pi * 2.0
        prep_duration = 125

        omega_peak = 2 * np.pi * 2.0
        rise_duration = 1000
        hold_duration = 1000
        fall_duration = 26000

        delta_start = np.pi
        delta_hold = -np.pi / 2
        delta_end = -np.pi

        sampling_rate = 0.05
        scale = 15.5

        study_out = study_fixed_smooth_sequence_on_random_graphs(
            n=n,
            n_graphs=n_graphs,
            edge_prob=edge_prob,
            w_min=w_min,
            w_max=w_max,
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
            seed=seed,
            require_connected=True,
        )

        summary = study_out["summary"]
        results = study_out["results"]

        print("\n=== RÉSUMÉ GLOBAL ===")
        print(f"n                         = {summary['n']}")
        print(f"nombre de graphes         = {summary['n_graphs']}")
        print(f"edge_prob                 = {summary['edge_prob']}")
        print(f"poids                     = [{summary['w_min']}, {summary['w_max']}]")
        print()
        print(f"ratio_pulser_mean         = {summary['ratio_pulser_mean']:.6f}")
        print(f"ratio_pulser_min          = {summary['ratio_pulser_min']:.6f}")
        print(f"ratio_pulser_max          = {summary['ratio_pulser_max']:.6f}")
        print()
        print(f"overlap_mean              = {summary['overlap_mean']:.6f}")
        print(f"overlap_min               = {summary['overlap_min']:.6f}")
        print(f"overlap_max               = {summary['overlap_max']:.6f}")
        print()
        print(f"mapping_error_mean        = {summary['mapping_error_mean']:.6f}")
        print(f"mapping_error_max         = {summary['mapping_error_max']:.6f}")
        print()
        print(f"ratio_proxy_exact_mean    = {summary['ratio_proxy_exact_mean']:.6f}")
        print(f"ratio_proxy_exact_min     = {summary['ratio_proxy_exact_min']:.6f}")
        print(f"ratio_proxy_exact_max     = {summary['ratio_proxy_exact_max']:.6f}")

        print("\n=== DÉTAIL PAR GRAPHE ===")
        for r in results:
            print(
                f"Graphe {r['graph_id']:2d} | "
                f"ratio_pulser={r['ratio_pulser']:.6f} | "
                f"overlap={r['overlap_proxy']:.6f} | "
                f"ratio_proxy_exact={r['ratio_proxy_exact']:.6f} | "
                f"mapping_error={r['mapping_error']:.6f}"
            )

        if SAVE_RESULTS:
            plot_smooth_graph_study_article(
                results,
                summary=summary,
                save_paths=figure_output_path("figure_smooth_graph_study_n4.png"),
                show=False,
            )

            results_path = save_json_data(results, "pulser_smooth_graph_study_n4.json")
            summary_path = save_json_data(summary, "pulser_smooth_graph_study_n4_summary.json")

            print("\n✅ Résultats sauvegardés dans :")
            print(f"   - {results_path}")
            print(f"   - {summary_path}")
            print(f"   - {figure_output_path('figure_smooth_graph_study_n4.png')}")
    
    else:
        print("Aucun mode activé.")
    
    print("\n" + "=" * 80)
    print("Exécution terminée.")
