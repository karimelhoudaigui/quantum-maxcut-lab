import { Network, Play, RefreshCw } from "lucide-react";

import { useGraphGeneration } from "../hooks/usePipeline";
import { usePipelineStore } from "../stores/pipelineStore";
import type { GraphFamily } from "../types";

const families: GraphFamily[] = ["path", "cycle", "star", "complete", "random"];

export function GraphConfigurator() {
  const config = usePipelineStore((state) => state.config);
  const setConfig = usePipelineStore((state) => state.setConfig);
  const generation = useGraphGeneration();

  return (
    <aside className="flex h-full flex-col border-r border-border bg-muted/30 p-5">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-background">
          <Network size={20} />
        </div>
        <div>
          <h1 className="text-lg font-semibold">Quantum MaxCut</h1>
          <p className="text-sm text-foreground/60">Hybrid pipeline console</p>
        </div>
      </div>

      <div className="space-y-5">
        <label className="block">
          <span className="text-sm font-medium text-foreground/80">Graph family</span>
          <select
            value={config.family}
            onChange={(event) => setConfig({ family: event.target.value as GraphFamily })}
            className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
          >
            {families.map((family) => (
              <option key={family} value={family}>
                {family}
              </option>
            ))}
          </select>
        </label>

        <Slider
          label="Nodes"
          value={config.n_nodes}
          min={2}
          max={12}
          step={1}
          onChange={(n_nodes) => setConfig({ n_nodes })}
        />
        <Slider
          label="Density"
          value={config.density}
          min={0.1}
          max={1}
          step={0.05}
          disabled={config.family !== "random"}
          onChange={(density) => setConfig({ density })}
        />
        <Slider
          label="Min weight"
          value={config.weight_min}
          min={0.1}
          max={3}
          step={0.1}
          onChange={(weight_min) => setConfig({ weight_min })}
        />
        <Slider
          label="Max weight"
          value={config.weight_max}
          min={0.2}
          max={4}
          step={0.1}
          onChange={(weight_max) => setConfig({ weight_max })}
        />

        <label className="flex items-center justify-between rounded-md border border-border bg-background/70 px-3 py-3 text-sm">
          <span>Optimize atom geometry</span>
          <input
            type="checkbox"
            checked={config.optimize_geometry}
            onChange={(event) => setConfig({ optimize_geometry: event.target.checked })}
            className="h-4 w-4 accent-primary"
          />
        </label>

        <button
          type="button"
          onClick={() => generation.mutate()}
          disabled={generation.isPending}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-3 text-sm font-semibold text-background transition hover:opacity-90 disabled:cursor-wait disabled:opacity-60"
        >
          {generation.isPending ? <RefreshCw className="animate-spin" size={16} /> : <Play size={16} />}
          Generate graph
        </button>

        {generation.error ? (
          <p className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {generation.error.message}
          </p>
        ) : null}
      </div>
    </aside>
  );
}

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  disabled?: boolean;
  onChange: (value: number) => void;
}

function Slider({ label, value, min, max, step, disabled = false, onChange }: SliderProps) {
  return (
    <label className={disabled ? "block opacity-45" : "block"}>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-foreground/80">{label}</span>
        <span className="font-mono text-foreground/60">{value.toFixed(step < 1 ? 2 : 0)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-3 w-full accent-primary"
      />
    </label>
  );
}
