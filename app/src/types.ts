export type GraphFamily = "path" | "cycle" | "star" | "complete" | "random";
export type ProxyHamiltonianName = "rydberg_xy" | "ising_zz" | "heisenberg_qmc";

export interface Edge {
  i: number;
  j: number;
  w: number;
}

export interface Position {
  id: number;
  x: number;
  y: number;
}

export interface GraphResponse {
  family: GraphFamily;
  n_nodes: number;
  edges: Edge[];
  positions: Position[];
  mapping_error: number | null;
  descriptors: Record<string, number | string>;
}

export interface GraphGenerateRequest {
  family: GraphFamily;
  n_nodes: number;
  density: number;
  weight_min: number;
  weight_max: number;
  seed: number;
  optimize_geometry: boolean;
}

export interface AnnealingConfig {
  omega_peak_mhz: number;
  rise_duration: number;
  hold_duration: number;
  fall_duration: number;
  delta_start_pi: number;
  delta_hold_pi: number;
  delta_end_pi: number;
  sampling_rate: number;
  n_roundings: number;
}

export interface PipelineRunRequest {
  graph: GraphResponse;
  annealing: AnnealingConfig;
  proxy_hamiltonian: ProxyHamiltonianName;
  n_roundings: number;
  seed: number;
}

export type StepStatus = "pending" | "running" | "completed" | "failed";
export type JobStatus = "queued" | "running" | "completed" | "failed";

export interface PipelineStep {
  id: "geometry" | "pulser" | "sdp" | "rounding";
  label: string;
  status: StepStatus;
  metric_label: string | null;
  metric_value: number | string | null;
}

export interface PipelineJob {
  job_id: string;
  status: JobStatus;
  progress: number;
  steps: PipelineStep[];
  result: Record<string, unknown> | null;
  error: string | null;
}

export interface FamilyResultRow {
  family: string;
  metrics: Record<string, number | string>;
}
