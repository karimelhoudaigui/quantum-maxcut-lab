import { Network, Play, RefreshCw, RotateCcw, SlidersHorizontal, Waves } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";

import { useGraphGeneration } from "../hooks/usePipeline";
import { usePipelineStore } from "../stores/pipelineStore";
import type { GraphFamily, ProxyHamiltonianName } from "../types";

const families: GraphFamily[] = ["path", "cycle", "star", "complete", "random"];
const proxyOptions: Array<{ value: ProxyHamiltonianName; label: string; hint: string }> = [
  { value: "rydberg_xy", label: "Rydberg XY", hint: "stable default" },
  { value: "ising_zz", label: "Ising ZZ", hint: "experimental" },
  { value: "heisenberg_qmc", label: "Heisenberg QMC-like", hint: "experimental" },
];

export function GraphConfigurator() {
  const config = usePipelineStore((state) => state.config);
  const annealing = usePipelineStore((state) => state.annealing);
  const proxyHamiltonian = usePipelineStore((state) => state.proxyHamiltonian);
  const setConfig = usePipelineStore((state) => state.setConfig);
  const setAnnealing = usePipelineStore((state) => state.setAnnealing);
  const setProxyHamiltonian = usePipelineStore((state) => state.setProxyHamiltonian);
  const generation = useGraphGeneration();

  return (
    <aside className="flex h-screen flex-col overflow-y-auto border-r border-border bg-muted/30 p-5">
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

        <label className="block rounded-md border border-border bg-background/70 p-3">
          <span className="text-sm font-medium text-foreground/80">Proxy Hamiltonian</span>
          <select
            value={proxyHamiltonian}
            onChange={(event) => setProxyHamiltonian(event.target.value as ProxyHamiltonianName)}
            className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
          >
            {proxyOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label} - {option.hint}
              </option>
            ))}
          </select>
          <p className="mt-2 text-xs leading-relaxed text-foreground/50">
            Rydberg XY preserves the current pipeline. Ising ZZ and Heisenberg QMC-like are experimental proxy-state modes.
          </p>
        </label>

        <div className="rounded-md border border-border bg-background/55 p-3">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <SlidersHorizontal size={17} className="text-primary" />
              <div>
                <h2 className="text-sm font-semibold">Annealing controls</h2>
                <p className="text-xs text-foreground/50">Dynamic pulse schedule</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() =>
                setAnnealing({
                  omega_peak_mhz: 2,
                  rise_duration: 1000,
                  hold_duration: 1000,
                  fall_duration: 26000,
                  delta_start_pi: 1,
                  delta_hold_pi: -0.5,
                  delta_end_pi: -1,
                  sampling_rate: 0.05,
                  n_roundings: 32,
                })
              }
              className="rounded-md border border-border p-2 text-foreground/65 transition hover:bg-muted hover:text-foreground"
              title="Reset annealing controls"
            >
              <RotateCcw size={15} />
            </button>
          </div>

          <div className="space-y-4">
            <Slider
              label="Omega peak"
              value={annealing.omega_peak_mhz}
              min={0.5}
              max={5}
              step={0.1}
              unit="MHz"
              onChange={(omega_peak_mhz) => setAnnealing({ omega_peak_mhz })}
            />
            <Slider
              label="Rise"
              value={annealing.rise_duration}
              min={100}
              max={5000}
              step={100}
              unit="ns"
              onChange={(rise_duration) => setAnnealing({ rise_duration })}
            />
            <Slider
              label="Hold"
              value={annealing.hold_duration}
              min={0}
              max={6000}
              step={100}
              unit="ns"
              onChange={(hold_duration) => setAnnealing({ hold_duration })}
            />
            <Slider
              label="Fall"
              value={annealing.fall_duration}
              min={1000}
              max={40000}
              step={500}
              unit="ns"
              onChange={(fall_duration) => setAnnealing({ fall_duration })}
            />
            <Slider
              label="Delta start"
              value={annealing.delta_start_pi}
              min={-2}
              max={2}
              step={0.05}
              unit="pi"
              onChange={(delta_start_pi) => setAnnealing({ delta_start_pi })}
            />
            <Slider
              label="Delta hold"
              value={annealing.delta_hold_pi}
              min={-2}
              max={2}
              step={0.05}
              unit="pi"
              onChange={(delta_hold_pi) => setAnnealing({ delta_hold_pi })}
            />
            <Slider
              label="Delta end"
              value={annealing.delta_end_pi}
              min={-2}
              max={2}
              step={0.05}
              unit="pi"
              onChange={(delta_end_pi) => setAnnealing({ delta_end_pi })}
            />
            <Slider
              label="Sampling"
              value={annealing.sampling_rate}
              min={0.01}
              max={0.2}
              step={0.01}
              onChange={(sampling_rate) => setAnnealing({ sampling_rate })}
            />
            <Slider
              label="Roundings"
              value={annealing.n_roundings}
              min={8}
              max={128}
              step={8}
              onChange={(n_roundings) => setAnnealing({ n_roundings })}
            />
          </div>

          <div className="mt-4 grid grid-cols-3 gap-2 rounded-md border border-border bg-muted/35 p-2">
            <MiniMetric label="Total" value={`${formatNumber(annealing.rise_duration + annealing.hold_duration + annealing.fall_duration, 0)} ns`} />
            <MiniMetric label="Sweep" value={`${formatNumber(annealing.delta_start_pi, 2)}→${formatNumber(annealing.delta_end_pi, 2)} pi`} />
            <MiniMetric label="Mode" value={<Waves size={15} />} />
          </div>
        </div>

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
  unit?: string;
  disabled?: boolean;
  onChange: (value: number) => void;
}

function Slider({ label, value, min, max, step, unit, disabled = false, onChange }: SliderProps) {
  const progress = ((value - min) / (max - min)) * 100;

  return (
    <label className={disabled ? "block opacity-45" : "block"}>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-foreground/80">{label}</span>
        <span className="font-mono text-foreground/60">
          {formatNumber(value, step < 1 ? 2 : 0)}
          {unit ? <span className="ml-1 text-foreground/40">{unit}</span> : null}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(Number(event.target.value))}
        className="modern-slider mt-3 w-full"
        style={{ "--slider-progress": `${progress}%` } as CSSProperties}
      />
    </label>
  );
}

function MiniMetric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0">
      <p className="text-[10px] font-medium uppercase text-foreground/45">{label}</p>
      <div className="mt-1 flex min-h-5 items-center truncate font-mono text-xs text-primary">{value}</div>
    </div>
  );
}

function formatNumber(value: number, digits: number) {
  return value.toFixed(digits);
}
