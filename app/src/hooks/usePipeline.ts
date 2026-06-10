import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { generateGraph, getPipelineStatus, runPipeline } from "../lib/api";
import { usePipelineStore } from "../stores/pipelineStore";

export function useGraphGeneration() {
  const config = usePipelineStore((state) => state.config);
  const setGraph = usePipelineStore((state) => state.setGraph);

  return useMutation({
    mutationFn: () => generateGraph(config),
    onSuccess: setGraph,
  });
}

export function usePipelineRunner() {
  const graph = usePipelineStore((state) => state.graph);
  const job = usePipelineStore((state) => state.job);
  const annealing = usePipelineStore((state) => state.annealing);
  const proxyHamiltonian = usePipelineStore((state) => state.proxyHamiltonian);
  const setJob = usePipelineStore((state) => state.setJob);

  const run = useMutation({
    mutationFn: () => {
      if (!graph) {
        throw new Error("Generate a graph before running the pipeline.");
      }
      return runPipeline(graph, annealing, proxyHamiltonian);
    },
    onSuccess: setJob,
  });

  const status = useQuery({
    queryKey: ["pipeline-status", job?.job_id],
    queryFn: () => getPipelineStatus(job?.job_id ?? ""),
    enabled: Boolean(job?.job_id) && job?.status !== "completed" && job?.status !== "failed",
    refetchInterval: 1200,
  });

  useEffect(() => {
    if (status.data && status.data.job_id === job?.job_id) {
      setJob(status.data);
    }
  }, [job?.job_id, setJob, status.data]);

  return { run, status };
}
