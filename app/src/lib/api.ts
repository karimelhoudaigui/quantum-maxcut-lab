import type {
  AnnealingConfig,
  FamilyResultRow,
  GraphGenerateRequest,
  GraphResponse,
  PipelineJob,
} from "../types";

const API_BASE = import.meta.env.DEV ? "" : import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function generateGraph(payload: GraphGenerateRequest): Promise<GraphResponse> {
  return request<GraphResponse>("/api/graph/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function runPipeline(graph: GraphResponse, annealing: AnnealingConfig): Promise<PipelineJob> {
  return request<PipelineJob>("/api/pipeline/run", {
    method: "POST",
    body: JSON.stringify({
      graph,
      annealing,
      n_roundings: annealing.n_roundings,
      seed: 1234,
    }),
  });
}

export function getPipelineStatus(jobId: string): Promise<PipelineJob> {
  return request<PipelineJob>(`/api/pipeline/${jobId}/status`);
}

export function getFamilyResults(family = "all"): Promise<FamilyResultRow[]> {
  return request<FamilyResultRow[]>(`/api/results/${family}`);
}
