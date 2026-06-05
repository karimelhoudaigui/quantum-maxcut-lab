import { Activity, TimerReset, Waves } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

import { usePipelineStore } from "../stores/pipelineStore";

interface SchedulePoint {
  t: number;
  omega: number;
  delta: number;
  phase: "rise" | "sweep" | "fall";
}

export function FamilyExplorer() {
  const annealing = usePipelineStore((state) => state.annealing);
  const [hovered, setHovered] = useState<SchedulePoint | null>(null);

  const schedule = useMemo(() => buildSchedule(annealing), [annealing]);
  const activePoint = hovered ?? schedule.points[Math.floor(schedule.points.length * 0.58)] ?? null;

  return (
    <section className="rounded-md border border-border bg-muted/25 p-4">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase text-foreground/50">Annealing schedule</p>
          <h2 className="text-lg font-semibold">Pulse evolution over time</h2>
        </div>
        <div className="grid grid-cols-3 gap-2 text-right">
          <CompactMetric label="Total" value={`${format(schedule.totalTime, 0)} ns`} />
          <CompactMetric label="Omega" value={`${format(annealing.omega_peak_mhz, 2)} MHz`} />
          <CompactMetric label="Samples" value={String(schedule.samples)} />
        </div>
      </div>

      <div className="grid gap-4">
        <div className="relative overflow-hidden rounded-md border border-border bg-background/70">
          <svg
            viewBox="0 0 920 330"
            className="h-[360px] w-full"
            role="img"
            onMouseLeave={() => setHovered(null)}
            onMouseMove={(event) => {
              const svg = event.currentTarget;
              const rect = svg.getBoundingClientRect();
              const x = ((event.clientX - rect.left) / rect.width) * 920;
              const t = schedule.xToTime(x);
              setHovered(nearestPoint(schedule.points, t));
            }}
          >
            <defs>
              <linearGradient id="omegaFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#6ee7cf" stopOpacity="0.36" />
                <stop offset="100%" stopColor="#6ee7cf" stopOpacity="0.03" />
              </linearGradient>
              <linearGradient id="deltaFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#8fb7ff" stopOpacity="0.24" />
                <stop offset="100%" stopColor="#8fb7ff" stopOpacity="0.02" />
              </linearGradient>
              <filter id="lineGlow">
                <feGaussianBlur stdDeviation="3.5" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <rect x="0" y="0" width="920" height="330" fill="transparent" />
            {schedule.gridY.map((line) => (
              <line key={line} x1="56" x2="884" y1={line} y2={line} stroke="currentColor" className="text-border" strokeOpacity="0.5" />
            ))}
            {schedule.boundaries.map((boundary) => (
              <g key={boundary.label}>
                <rect x={boundary.x0} y="52" width={boundary.x1 - boundary.x0} height="222" fill={boundary.fill} opacity="0.18" />
                <line x1={boundary.x1} x2={boundary.x1} y1="52" y2="274" stroke="#32423f" strokeDasharray="4 7" />
                {boundary.x1 - boundary.x0 > 72 ? (
                  <text x={(boundary.x0 + boundary.x1) / 2} y="298" textAnchor="middle" className="fill-foreground/50 text-[11px] font-semibold uppercase">
                    {boundary.label}
                  </text>
                ) : null}
              </g>
            ))}

            <text x="56" y="36" className="fill-primary text-[12px] font-semibold">
              Omega amplitude
            </text>
            <text x="884" y="36" textAnchor="end" className="fill-[#9bbcff] text-[12px] font-semibold">
              Detuning
            </text>
            <text x="56" y="315" className="fill-foreground/40 text-[11px]">
              time ns
            </text>

            <path d={schedule.omegaAreaPath} fill="url(#omegaFill)" />
            <path d={schedule.deltaAreaPath} fill="url(#deltaFill)" />
            <path d={schedule.omegaPath} fill="none" stroke="#6ee7cf" strokeWidth="4" filter="url(#lineGlow)" strokeLinecap="round" />
            <path d={schedule.deltaPath} fill="none" stroke="#9bbcff" strokeWidth="3" strokeLinecap="round" strokeDasharray="7 8" />

            {activePoint ? (
              <g>
                <line x1={schedule.x(activePoint.t)} x2={schedule.x(activePoint.t)} y1="50" y2="276" stroke="#d6fff4" strokeOpacity="0.48" />
                <circle cx={schedule.x(activePoint.t)} cy={schedule.yOmega(activePoint.omega)} r="7" fill="#6ee7cf" stroke="#09231e" strokeWidth="3" />
                <circle cx={schedule.x(activePoint.t)} cy={schedule.yDelta(activePoint.delta)} r="6" fill="#9bbcff" stroke="#091327" strokeWidth="3" />
              </g>
            ) : null}
          </svg>
        </div>

        <aside className="grid gap-3 xl:grid-cols-2">
          <PhaseCard
            icon={<Activity size={16} />}
            label="Rise"
            value={`${format(annealing.rise_duration, 0)} ns`}
            detail={`Omega 0 to ${format(annealing.omega_peak_mhz, 2)} MHz`}
          />
          <PhaseCard
            icon={<Waves size={16} />}
            label="Sweep"
            value={`${format(annealing.hold_duration, 0)} ns`}
            detail={`Delta ${format(annealing.delta_start_pi, 2)} to ${format(annealing.delta_end_pi, 2)} pi`}
          />
          <PhaseCard
            icon={<TimerReset size={16} />}
            label="Fall"
            value={`${format(annealing.fall_duration, 0)} ns`}
            detail={`Omega ${format(annealing.omega_peak_mhz, 2)} MHz to 0`}
          />

          <div className="rounded-md border border-border bg-background/70 p-3">
            <p className="text-xs font-medium uppercase text-foreground/45">Probe</p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <CompactMetric label="t" value={`${format(activePoint?.t ?? 0, 0)} ns`} />
              <CompactMetric label="Phase" value={activePoint?.phase ?? "—"} />
              <CompactMetric label="Omega" value={`${format(activePoint?.omega ?? 0, 2)} MHz`} />
              <CompactMetric label="Delta" value={`${format(activePoint?.delta ?? 0, 2)} pi`} />
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}

function buildSchedule(annealing: ReturnType<typeof usePipelineStore.getState>["annealing"]) {
  const margin = { left: 56, right: 36, top: 52, bottom: 56 };
  const width = 920 - margin.left - margin.right;
  const height = 330 - margin.top - margin.bottom;
  const totalTime = Math.max(1, annealing.rise_duration + annealing.hold_duration + annealing.fall_duration);
  const minDelta = Math.min(annealing.delta_start_pi, annealing.delta_hold_pi, annealing.delta_end_pi, -0.1);
  const maxDelta = Math.max(annealing.delta_start_pi, annealing.delta_hold_pi, annealing.delta_end_pi, 0.1);
  const deltaSpan = Math.max(maxDelta - minDelta, 0.1);

  const x = (t: number) => margin.left + (t / totalTime) * width;
  const xToTime = (xPosition: number) => clamp(((xPosition - margin.left) / width) * totalTime, 0, totalTime);
  const yOmega = (omega: number) => margin.top + height - (omega / Math.max(annealing.omega_peak_mhz, 0.1)) * height;
  const yDelta = (delta: number) => margin.top + height - ((delta - minDelta) / deltaSpan) * height;

  const points: SchedulePoint[] = [];
  const pushPhase = (phase: SchedulePoint["phase"], duration: number, startTime: number, count: number) => {
    for (let index = 0; index <= count; index += 1) {
      const ratio = count === 0 ? 0 : index / count;
      const t = startTime + duration * ratio;
      points.push({
        t,
        omega: omegaAt(annealing, t),
        delta: deltaAt(annealing, t),
        phase,
      });
    }
  };

  pushPhase("rise", annealing.rise_duration, 0, 24);
  pushPhase("sweep", annealing.hold_duration, annealing.rise_duration, 36);
  pushPhase("fall", annealing.fall_duration, annealing.rise_duration + annealing.hold_duration, 28);

  const omegaPath = linePath(points, (point) => x(point.t), (point) => yOmega(point.omega));
  const deltaPath = linePath(points, (point) => x(point.t), (point) => yDelta(point.delta));
  const omegaAreaPath = areaPath(points, (point) => x(point.t), (point) => yOmega(point.omega), margin.top + height);
  const deltaAreaPath = areaPath(points, (point) => x(point.t), (point) => yDelta(point.delta), margin.top + height);

  const riseEnd = annealing.rise_duration;
  const sweepEnd = annealing.rise_duration + annealing.hold_duration;
  const boundaries = [
    { label: "rise", x0: x(0), x1: x(riseEnd), fill: "#6ee7cf" },
    { label: "sweep", x0: x(riseEnd), x1: x(sweepEnd), fill: "#9bbcff" },
    { label: "fall", x0: x(sweepEnd), x1: x(totalTime), fill: "#6ee7cf" },
  ];

  return {
    totalTime,
    samples: Math.max(1, Math.round(totalTime * annealing.sampling_rate)),
    points,
    x,
    xToTime,
    yOmega,
    yDelta,
    omegaPath,
    deltaPath,
    omegaAreaPath,
    deltaAreaPath,
    boundaries,
    gridY: [margin.top, margin.top + height * 0.25, margin.top + height * 0.5, margin.top + height * 0.75, margin.top + height],
  };
}

function omegaAt(annealing: ReturnType<typeof usePipelineStore.getState>["annealing"], t: number) {
  const riseEnd = annealing.rise_duration;
  const sweepEnd = annealing.rise_duration + annealing.hold_duration;
  if (t <= riseEnd) {
    return annealing.omega_peak_mhz * ratio(t, 0, riseEnd);
  }
  if (t <= sweepEnd) {
    return annealing.omega_peak_mhz;
  }
  return annealing.omega_peak_mhz * (1 - ratio(t, sweepEnd, sweepEnd + annealing.fall_duration));
}

function deltaAt(annealing: ReturnType<typeof usePipelineStore.getState>["annealing"], t: number) {
  const riseEnd = annealing.rise_duration;
  const sweepEnd = annealing.rise_duration + annealing.hold_duration;
  if (t <= riseEnd) {
    return annealing.delta_start_pi;
  }
  if (t <= sweepEnd) {
    return lerp(annealing.delta_start_pi, annealing.delta_end_pi, ratio(t, riseEnd, sweepEnd));
  }
  return annealing.delta_end_pi;
}

function linePath(points: SchedulePoint[], x: (point: SchedulePoint) => number, y: (point: SchedulePoint) => number) {
  return points.map((point, index) => `${index === 0 ? "M" : "L"} ${x(point).toFixed(2)} ${y(point).toFixed(2)}`).join(" ");
}

function areaPath(points: SchedulePoint[], x: (point: SchedulePoint) => number, y: (point: SchedulePoint) => number, baseline: number) {
  if (points.length === 0) {
    return "";
  }
  const first = points[0];
  const last = points[points.length - 1];
  return `${linePath(points, x, y)} L ${x(last).toFixed(2)} ${baseline.toFixed(2)} L ${x(first).toFixed(2)} ${baseline.toFixed(2)} Z`;
}

function nearestPoint(points: SchedulePoint[], t: number) {
  return points.reduce((best, point) => (Math.abs(point.t - t) < Math.abs(best.t - t) ? point : best), points[0]);
}

function ratio(value: number, start: number, end: number) {
  if (end <= start) {
    return 1;
  }
  return clamp((value - start) / (end - start), 0, 1);
}

function lerp(start: number, end: number, amount: number) {
  return start + (end - start) * amount;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function PhaseCard({ icon, label, value, detail }: { icon: ReactNode; label: string; value: string; detail: string }) {
  return (
    <div className="rounded-md border border-border bg-background/70 p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-primary">
          {icon}
          <span className="text-sm font-semibold text-foreground">{label}</span>
        </div>
        <span className="font-mono text-xs text-foreground/60">{value}</span>
      </div>
      <p className="mt-2 text-xs text-foreground/50">{detail}</p>
    </div>
  );
}

function CompactMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border border-border bg-background/70 px-3 py-2">
      <p className="text-[10px] font-medium uppercase text-foreground/45">{label}</p>
      <p className="mt-1 truncate font-mono text-xs text-primary">{value}</p>
    </div>
  );
}

function format(value: number, digits: number) {
  return Number.isFinite(value) ? value.toFixed(digits) : "—";
}
