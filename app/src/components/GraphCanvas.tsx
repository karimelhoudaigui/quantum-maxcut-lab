import { useMemo } from "react";

import { usePipelineStore } from "../stores/pipelineStore";

export function GraphCanvas() {
  const graph = usePipelineStore((state) => state.graph);
  const job = usePipelineStore((state) => state.job);

  const bounds = useMemo(() => {
    if (!graph || graph.positions.length === 0) {
      return { minX: -1, maxX: 1, minY: -1, maxY: 1 };
    }
    const xs = graph.positions.map((point) => point.x);
    const ys = graph.positions.map((point) => point.y);
    return {
      minX: Math.min(...xs),
      maxX: Math.max(...xs),
      minY: Math.min(...ys),
      maxY: Math.max(...ys),
    };
  }, [graph]);

  const project = (x: number, y: number) => {
    const width = Math.max(bounds.maxX - bounds.minX, 0.01);
    const height = Math.max(bounds.maxY - bounds.minY, 0.01);
    return {
      x: 70 + ((x - bounds.minX) / width) * 660,
      y: 70 + ((y - bounds.minY) / height) * 440,
    };
  };

  return (
    <section className="relative min-h-[560px] overflow-hidden rounded-md border border-border bg-background shadow-panel">
      <div className="absolute left-5 top-5 z-10">
        <p className="text-xs font-medium uppercase text-foreground/50">Graph canvas</p>
        <h2 className="text-2xl font-semibold">{graph ? `${graph.family} / ${graph.n_nodes} nodes` : "Generate a graph"}</h2>
      </div>

      <svg viewBox="0 0 800 580" className="h-full min-h-[560px] w-full">
        <defs>
          <radialGradient id="nodeGlow">
            <stop offset="0%" stopColor="#d6fff4" />
            <stop offset="100%" stopColor="#43d9b8" />
          </radialGradient>
        </defs>
        <rect width="800" height="580" fill="transparent" />
        {graph?.edges.map((edge) => {
          const source = graph.positions.find((position) => position.id === edge.i);
          const target = graph.positions.find((position) => position.id === edge.j);
          if (!source || !target) {
            return null;
          }
          const a = project(source.x, source.y);
          const b = project(target.x, target.y);
          const opacity = Math.min(0.95, 0.25 + edge.w / 4);
          return (
            <line
              key={`${edge.i}-${edge.j}`}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="#6ee7cf"
              strokeOpacity={opacity}
              strokeWidth={1.5 + edge.w}
            />
          );
        })}
        {graph?.positions.map((position) => {
          const point = project(position.x, position.y);
          const isRunning = job?.status === "running" || job?.status === "queued";
          return (
            <g key={position.id} className={isRunning ? "animate-pulse" : ""}>
              <circle cx={point.x} cy={point.y} r="15" fill="url(#nodeGlow)" opacity="0.95" />
              <text x={point.x} y={point.y + 4} textAnchor="middle" className="fill-background text-xs font-bold">
                {position.id}
              </text>
            </g>
          );
        })}
      </svg>
    </section>
  );
}
