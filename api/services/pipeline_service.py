from __future__ import annotations

import csv
import math
import threading
import time
import uuid
from pathlib import Path
from typing import Iterable

import numpy as np

from api.schemas import (
    AnnealingConfig,
    Edge,
    FamilyResultRow,
    GraphFamily,
    GraphGenerateRequest,
    GraphResponse,
    PipelineJobResponse,
    PipelineRunRequest,
    PipelineStep,
    Position,
)
from graph_structure_study import compute_graph_descriptors
from quantum_optmization import optimize_atom_positions


ROOT_DIR = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT_DIR / "results_graph_families_full_pipeline"


DEFAULT_PULSE = {
    "omega_prep": 2 * np.pi * 2.0,
    "prep_duration": 125,
    "omega_peak": 2 * np.pi * 2.0,
    "rise_duration": 1000,
    "hold_duration": 1000,
    "fall_duration": 26000,
    "delta_start": np.pi,
    "delta_hold": -np.pi / 2,
    "delta_end": -np.pi,
    "sampling_rate": 0.05,
    "scale": 15.5,
}


def _pulse_from_annealing(config: AnnealingConfig) -> dict[str, float | int]:
    return {
        **DEFAULT_PULSE,
        "omega_peak": 2 * np.pi * config.omega_peak_mhz,
        "rise_duration": int(config.rise_duration),
        "hold_duration": int(config.hold_duration),
        "fall_duration": int(config.fall_duration),
        "delta_start": np.pi * config.delta_start_pi,
        "delta_hold": np.pi * config.delta_hold_pi,
        "delta_end": np.pi * config.delta_end_pi,
        "sampling_rate": float(config.sampling_rate),
    }


STEP_TEMPLATE = [
    PipelineStep(id="geometry", label="Geometry embedding", status="pending", metric_label="Mapping error"),
    PipelineStep(id="pulser", label="Pulser", status="pending", metric_label="Ratio Pulser"),
    PipelineStep(id="sdp", label="SDP", status="pending", metric_label="Status"),
    PipelineStep(id="rounding", label="Rounding", status="pending", metric_label="Ratio hybrid"),
]


class PipelineRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, PipelineJobResponse] = {}
        self._lock = threading.Lock()

    def create(self) -> PipelineJobResponse:
        job = PipelineJobResponse(
            job_id=str(uuid.uuid4()),
            status="queued",
            progress=0,
            steps=[step.model_copy() for step in STEP_TEMPLATE],
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> PipelineJobResponse | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.model_copy(deep=True) if job else None

    def update(self, job_id: str, **changes: object) -> None:
        with self._lock:
            job = self._jobs[job_id]
            updated = job.model_copy(update=changes)
            self._jobs[job_id] = updated

    def update_step(
        self,
        job_id: str,
        step_id: str,
        status: str,
        metric_value: float | str | None = None,
        progress: int | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs[job_id]
            steps = []
            for step in job.steps:
                if step.id == step_id:
                    steps.append(step.model_copy(update={"status": status, "metric_value": metric_value}))
                else:
                    steps.append(step)
            payload: dict[str, object] = {"steps": steps}
            if progress is not None:
                payload["progress"] = progress
            self._jobs[job_id] = job.model_copy(update=payload)


registry = PipelineRegistry()


def _weighted_edges_for_family(request: GraphGenerateRequest) -> list[tuple[int, int, float]]:
    rng = np.random.default_rng(request.seed)
    n = request.n_nodes

    def weight() -> float:
        return float(rng.uniform(request.weight_min, request.weight_max))

    if request.family == GraphFamily.path:
        return [(i, i + 1, weight()) for i in range(n - 1)]
    if request.family == GraphFamily.cycle:
        return [(i, (i + 1) % n, weight()) for i in range(n)]
    if request.family == GraphFamily.star:
        return [(0, i, weight()) for i in range(1, n)]
    if request.family == GraphFamily.complete:
        return [(i, j, weight()) for i in range(n) for j in range(i + 1, n)]

    edges: list[tuple[int, int, float]] = []
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() <= request.density:
                edges.append((i, j, weight()))
    if not edges:
        edges.append((0, 1, weight()))
    return edges


def _fallback_positions(n: int) -> list[Position]:
    radius = 1.0 + 0.08 * n
    return [
        Position(
            id=i,
            x=float(radius * math.cos(2 * math.pi * i / n)),
            y=float(radius * math.sin(2 * math.pi * i / n)),
        )
        for i in range(n)
    ]


def _to_edge_models(edges: Iterable[tuple[int, int, float]]) -> list[Edge]:
    return [Edge(i=int(i), j=int(j), w=float(w)) for i, j, w in edges]


def generate_graph(request: GraphGenerateRequest) -> GraphResponse:
    edges = _weighted_edges_for_family(request)
    mapping_error: float | None = None
    positions = _fallback_positions(request.n_nodes)

    if request.optimize_geometry:
        try:
            optimized_positions, _, mapping_error = optimize_atom_positions(
                edges,
                n=request.n_nodes,
                max_iter=200,
                tol=1e-5,
            )
            positions = [
                Position(id=index, x=float(pos[0]), y=float(pos[1]))
                for index, pos in enumerate(np.asarray(optimized_positions, dtype=float))
            ]
        except Exception:
            mapping_error = None

    descriptors = compute_graph_descriptors(request.n_nodes, edges)
    return GraphResponse(
        family=request.family,
        n_nodes=request.n_nodes,
        edges=_to_edge_models(edges),
        positions=positions,
        mapping_error=mapping_error,
        descriptors=descriptors,
    )


def start_pipeline(request: PipelineRunRequest) -> PipelineJobResponse:
    job = registry.create()
    thread = threading.Thread(target=_run_pipeline_job, args=(job.job_id, request), daemon=True)
    thread.start()
    return registry.get(job.job_id) or job


def get_job(job_id: str) -> PipelineJobResponse | None:
    return registry.get(job_id)


def _edge_tuples(edges: list[Edge]) -> list[tuple[int, int, float]]:
    return [(edge.i, edge.j, edge.w) for edge in edges]


def _run_pipeline_job(job_id: str, request: PipelineRunRequest) -> None:
    from quantum_hybrid.hybrid_graph_study import evaluate_fixed_hybrid_sequence_on_graph

    edges = _edge_tuples(request.graph.edges)
    pulse = _pulse_from_annealing(request.annealing)
    n_roundings = request.annealing.n_roundings or request.n_roundings
    try:
        registry.update(job_id, status="running", progress=5)
        registry.update_step(job_id, "geometry", "running", progress=15)
        time.sleep(0.15)

        result = evaluate_fixed_hybrid_sequence_on_graph(
            n=request.graph.n_nodes,
            target_edges=edges,
            n_roundings=n_roundings,
            seed=request.seed,
            max_iter=500,
            tol=1e-5,
            **pulse,
        )

        registry.update_step(job_id, "geometry", "completed", result.get("mapping_error"), 35)
        registry.update_step(job_id, "pulser", "completed", result.get("ratio_pulser"), 60)
        registry.update_step(job_id, "sdp", "completed", result.get("sdp_status"), 80)
        registry.update_step(job_id, "rounding", "completed", result.get("ratio_hybrid"), 96)

        gain = float(result["ratio_hybrid"]) - float(result["ratio_pulser"])
        result_payload: dict[str, object] = {
            **result,
            "gain_hybrid_vs_pulser": gain,
            "cut_value": float(result["E_hybrid_in_qmc"]),
            "annealing": request.annealing.model_dump(),
        }
        registry.update(job_id, status="completed", progress=100, result=result_payload)
    except Exception as exc:
        current = registry.get(job_id)
        if current:
            for step in current.steps:
                if step.status == "running":
                    registry.update_step(job_id, step.id, "failed", "failed")
                    break
        registry.update(job_id, status="failed", error=str(exc), progress=100)


def load_family_results(family: str) -> list[FamilyResultRow]:
    csv_path = RESULTS_DIR / "summary_by_family.csv"
    if not csv_path.exists():
        return []

    rows: list[FamilyResultRow] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if family != "all" and row.get("family") != family:
                continue
            metrics: dict[str, float | int | str] = {}
            for key, value in row.items():
                if key == "family":
                    continue
                try:
                    numeric = float(value)
                    metrics[key] = int(numeric) if numeric.is_integer() else numeric
                except (TypeError, ValueError):
                    metrics[key] = value
            rows.append(FamilyResultRow(family=str(row["family"]), metrics=metrics))
    return rows
