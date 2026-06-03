import { create } from "zustand";

import type { GraphGenerateRequest, GraphResponse, PipelineJob } from "../types";

interface PipelineState {
  config: GraphGenerateRequest;
  graph: GraphResponse | null;
  job: PipelineJob | null;
  setConfig: (config: Partial<GraphGenerateRequest>) => void;
  setGraph: (graph: GraphResponse) => void;
  setJob: (job: PipelineJob | null) => void;
}

export const usePipelineStore = create<PipelineState>((set) => ({
  config: {
    family: "random",
    n_nodes: 6,
    density: 0.6,
    weight_min: 0.5,
    weight_max: 1.5,
    seed: 42,
    optimize_geometry: true,
  },
  graph: null,
  job: null,
  setConfig: (config) => set((state) => ({ config: { ...state.config, ...config } })),
  setGraph: (graph) => set({ graph }),
  setJob: (job) => set({ job }),
}));
