import numpy as np

from quantum_hybrid import hybrid_graph_study


def _fake_pulser_out(proxy_hamiltonian):
    return {
        "rho_T": np.eye(4, dtype=complex) / 4,
        "ratio_proxy_exact": 0.5,
        "ratio_pulser": 0.4,
        "E_pulser_in_qmc": -1.0,
        "proxy_hamiltonian": proxy_hamiltonian,
        "proxy_label": "Rydberg XY",
        "proxy_required_correlators": ["xx", "yy"],
        "proxy_experimental": False,
        "proxy_sdp_note": "stable",
        "preparation_mode": "pulser_sequence",
    }


def _install_lightweight_pipeline(monkeypatch):
    calls = {"proxy_hamiltonian": []}

    def fake_optimize_atom_positions(target_edges, n, max_iter, tol):
        return np.zeros((n, 2), dtype=float), [(0, 1, 1.0)], 0.123

    def fake_evaluate_smooth_pulser_final_state(**kwargs):
        calls["proxy_hamiltonian"].append(kwargs.get("proxy_hamiltonian"))
        return _fake_pulser_out(kwargs.get("proxy_hamiltonian", "rydberg_xy"))

    def fake_compute_edge_correlators(rho, n, target_edges):
        return [
            {
                "edge": (0, 1),
                "w": 1.0,
                "xx": 0.1,
                "yy": 0.2,
                "zz": -0.3,
                "t": 0.15,
            }
        ]

    def fake_run_hybrid_on_pulser_output(**kwargs):
        return {
            "ratio_product": 0.45,
            "ratio_hybrid": 0.45,
            "winner": "rounding",
            "best_rounding_seed": kwargs["seed"],
            "n_roundings": kwargs["n_roundings"],
            "sdp_status": "optimal",
            "E_product_in_qmc": -1.2,
            "E_hybrid_in_qmc": -1.2,
            "proxy_sdp_note": "stable",
            "sdp_formulation": "legacy_xy",
        }

    monkeypatch.setattr(hybrid_graph_study, "optimize_atom_positions", fake_optimize_atom_positions)
    monkeypatch.setattr(hybrid_graph_study, "evaluate_smooth_pulser_final_state", fake_evaluate_smooth_pulser_final_state)
    monkeypatch.setattr(hybrid_graph_study, "compute_edge_correlators", fake_compute_edge_correlators)
    monkeypatch.setattr(hybrid_graph_study, "run_hybrid_on_pulser_output", fake_run_hybrid_on_pulser_output)
    return calls


def _run_lightweight_pipeline(**kwargs):
    params = {
        "n": 2,
        "target_edges": [(0, 1, 1.0)],
        "omega_prep": 1.0,
        "prep_duration": 10,
        "omega_peak": 1.0,
        "rise_duration": 10,
        "hold_duration": 10,
        "fall_duration": 10,
        "delta_start": 1.0,
        "delta_hold": 0.0,
        "delta_end": -1.0,
        "sampling_rate": 0.05,
        "scale": 1.0,
        "n_roundings": 4,
        "seed": 123,
    }
    params.update(kwargs)
    return hybrid_graph_study.evaluate_fixed_hybrid_sequence_on_graph(**params)


def test_old_pipeline_works_without_proxy_parameter(monkeypatch):
    calls = _install_lightweight_pipeline(monkeypatch)
    result = _run_lightweight_pipeline()

    assert calls["proxy_hamiltonian"] == ["rydberg_xy"]
    assert result["proxy_hamiltonian"] == "rydberg_xy"
    assert result["ratio_hybrid"] == 0.45
    assert result["sdp_formulation"] == "legacy_xy"


def test_explicit_rydberg_xy_matches_default_pipeline(monkeypatch):
    _install_lightweight_pipeline(monkeypatch)
    default_result = _run_lightweight_pipeline()
    explicit_result = _run_lightweight_pipeline(proxy_hamiltonian="rydberg_xy")

    comparable_keys = [
        "mapping_error",
        "ratio_proxy_exact",
        "ratio_pulser",
        "ratio_hybrid",
        "proxy_hamiltonian",
        "sdp_formulation",
        "preparation_mode",
    ]
    for key in comparable_keys:
        assert explicit_result[key] == default_result[key]
