import { Download } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { usePipelineStore } from "../stores/pipelineStore";

const metricKeys = [
  ["ratio_proxy_exact", "Ratio Proxy"],
  ["cut_value", "Cut Value"],
  ["mapping_error", "Mapping Error"],
  ["gain_hybrid_vs_pulser", "Gain Hybrid"],
] as const;

export function ResultsDashboard() {
  const job = usePipelineStore((state) => state.job);
  const result = job?.result;

  const chartData = result
    ? [
        { name: "Pulser", ratio: Number(result.ratio_pulser ?? 0) },
        { name: "Hybrid", ratio: Number(result.ratio_hybrid ?? 0) },
      ]
    : [];

  return (
    <aside className="flex h-full flex-col gap-4 border-l border-border bg-muted/30 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium uppercase text-foreground/50">Results</p>
          <h2 className="text-xl font-semibold">Live metrics</h2>
        </div>
        <button
          type="button"
          disabled={!result}
          onClick={() => exportJson(result)}
          className="rounded-md border border-border p-2 text-foreground/75 transition hover:bg-background disabled:opacity-40"
          title="Export JSON"
        >
          <Download size={16} />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {metricKeys.map(([key, label]) => (
          <MetricCard key={key} label={label} value={result?.[key]} />
        ))}
      </div>

      <div className="min-h-64 rounded-md border border-border bg-background/70 p-4">
        <p className="mb-4 text-sm font-semibold">Pulser vs Hybrid</p>
        <ResponsiveContainer width="100%" height={210}>
          <BarChart data={chartData}>
            <XAxis dataKey="name" stroke="currentColor" fontSize={12} />
            <YAxis stroke="currentColor" fontSize={12} />
            <Tooltip cursor={{ fill: "rgba(255,255,255,0.06)" }} />
            <Bar dataKey="ratio" fill="#43d9b8" radius={[5, 5, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </aside>
  );
}

function MetricCard({ label, value }: { label: string; value: unknown }) {
  const display = typeof value === "number" ? value.toFixed(5) : "—";
  return (
    <article className="rounded-md border border-border bg-background/70 p-3">
      <p className="text-xs text-foreground/55">{label}</p>
      <p className="mt-2 font-mono text-lg font-semibold text-primary">{display}</p>
      <div className="mt-3 h-8 rounded-sm bg-[linear-gradient(90deg,rgba(67,217,184,.1),rgba(67,217,184,.45),rgba(67,217,184,.08))]" />
    </article>
  );
}

function exportJson(result: Record<string, unknown> | null | undefined) {
  if (!result) {
    return;
  }
  const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "quantum-maxcut-result.json";
  anchor.click();
  URL.revokeObjectURL(url);
}
