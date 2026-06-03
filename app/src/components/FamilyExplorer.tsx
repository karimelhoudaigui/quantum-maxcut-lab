import { useQuery } from "@tanstack/react-query";

import { getFamilyResults } from "../lib/api";

export function FamilyExplorer() {
  const { data } = useQuery({
    queryKey: ["family-results"],
    queryFn: () => getFamilyResults("all"),
  });

  return (
    <section className="rounded-md border border-border bg-muted/25 p-4">
      <div className="mb-4 flex items-end justify-between">
        <div>
          <p className="text-xs font-medium uppercase text-foreground/50">Families</p>
          <h2 className="text-lg font-semibold">Structure explorer</h2>
        </div>
        <span className="text-xs text-foreground/50">{data?.length ?? 0} cohorts</span>
      </div>
      <div className="max-h-56 overflow-auto">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 bg-muted text-xs uppercase text-foreground/50">
            <tr>
              <th className="px-2 py-2">Family</th>
              <th className="px-2 py-2">Hybrid</th>
              <th className="px-2 py-2">Pulser</th>
              <th className="px-2 py-2">Gain</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((row) => (
              <tr key={row.family} className="border-t border-border">
                <td className="px-2 py-2 font-medium">{row.family}</td>
                <td className="px-2 py-2 font-mono">{formatMetric(row.metrics.hybrid_mean)}</td>
                <td className="px-2 py-2 font-mono">{formatMetric(row.metrics.pulser_mean)}</td>
                <td className="px-2 py-2 font-mono text-primary">{formatMetric(row.metrics.gain_mean)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatMetric(value: number | string | undefined) {
  return typeof value === "number" ? value.toFixed(4) : "—";
}
