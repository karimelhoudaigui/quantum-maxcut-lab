const state = {
  status: {},
  kind: "smooth_graph",
  data: null,
};

const experimentMeta = {
  benchmark: {
    title: "Benchmark proxy Rydberg",
    subtitle: "Ratios et erreurs de mapping en fonction de n",
    readout: "n-scan",
    accent: "#2057a8",
  },
  smooth_grid: {
    title: "Grid search smooth",
    subtitle: "Classement des paramètres de séquence",
    readout: "grid",
    accent: "#7c3aed",
  },
  smooth_graph: {
    title: "Étude smooth multi-graphes",
    subtitle: "Robustesse sur graphes aléatoires à n=4",
    readout: "n=4",
    accent: "#147d64",
  },
};

function fmt(value, digits = 3) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return "—";
  const number = Number(value);
  if (Math.abs(number) > 0 && Math.abs(number) < 0.001) return number.toExponential(2);
  return number.toFixed(digits);
}

async function api(path) {
  const response = await fetch(path);
  const payload = await response.json();
  if (!response.ok || payload.error) throw new Error(payload.error || response.statusText);
  return payload;
}

function setStatus(text) {
  document.getElementById("statusBadge").textContent = text;
}

function setHero(meta) {
  document.getElementById("title").textContent = meta.title;
  document.getElementById("subtitle").textContent = meta.subtitle;
  document.getElementById("readoutValue").textContent = meta.readout;
}

function renderExperiments() {
  const root = document.getElementById("experiments");
  root.innerHTML = "";

  for (const [kind, meta] of Object.entries(state.status)) {
    const ui = experimentMeta[kind] || {};
    const button = document.createElement("button");
    button.className = `experiment ${kind === state.kind ? "active" : ""} ${meta.ready ? "" : "missing"}`;
    button.innerHTML = `
      <strong>${meta.label}</strong>
      <small>${meta.ready ? ui.subtitle : "aucun résultat trouvé"}</small>
    `;
    button.addEventListener("click", () => selectExperiment(kind));
    root.appendChild(button);
  }
}

async function selectExperiment(kind) {
  state.kind = kind;
  renderExperiments();
  document.getElementById("outputList").innerHTML = "";
  await loadData();
}

async function loadData() {
  const meta = experimentMeta[state.kind];
  setHero(meta);
  setStatus("Chargement");

  try {
    state.data = await api(`/api/data?kind=${encodeURIComponent(state.kind)}`);
    setStatus(meta.subtitle);
    renderDashboard();
  } catch (error) {
    setStatus("Erreur");
    document.getElementById("primaryPlot").innerHTML = `<p>${error.message}</p>`;
  }
}

function renderDashboard() {
  if (state.kind === "benchmark") renderBenchmark();
  if (state.kind === "smooth_grid") renderSmoothGrid();
  if (state.kind === "smooth_graph") renderSmoothGraph();
}

function metric(label, value) {
  const [main, note] = Array.isArray(value) ? value : [value, ""];
  return `<div class="metric"><span>${label}</span><strong>${main}</strong>${note ? `<em>${note}</em>` : ""}</div>`;
}

function renderMetrics(items) {
  document.getElementById("metrics").innerHTML = items.map(([label, value]) => metric(label, value)).join("");
}

function renderLegend(items) {
  document.getElementById("primaryLegend").innerHTML = items
    .map((item) => `<span><i style="background:${item.color}"></i>${item.label}</span>`)
    .join("");
}

function svgBarLine({ rows, barKey, lineKey, xKey, target, title, barColor = "#2057a8", lineColor = "#111827" }) {
  if (!rows.length) return `<div class="empty">Aucune donnée disponible</div>`;

  const width = 760;
  const height = 330;
  const margin = { top: 22, right: 24, bottom: 42, left: 54 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;
  const barValues = rows.map((r) => Number(r[barKey]));
  const lineValues = lineKey ? rows.map((r) => Number(r[lineKey])) : [];
  const maxY = Math.max(1, ...barValues, ...lineValues) * 1.08;
  const minY = 0;
  const xStep = innerW / rows.length;
  const barW = Math.max(8, xStep * 0.62);
  const y = (v) => margin.top + innerH - ((v - minY) / (maxY - minY)) * innerH;
  const x = (i) => margin.left + i * xStep + xStep / 2;

  const gradientId = `grad-${Math.random().toString(36).slice(2)}`;
  const glowId = `glow-${Math.random().toString(36).slice(2)}`;

  const grid = [0, 0.25, 0.5, 0.75, 1].map((tick) => {
    const yy = y(tick * maxY);
    return `<line class="grid" x1="${margin.left}" y1="${yy}" x2="${width - margin.right}" y2="${yy}"/><text class="label" x="10" y="${yy + 4}">${fmt(tick * maxY, 2)}</text>`;
  }).join("");

  const bars = rows.map((row, i) => {
    const value = Number(row[barKey]);
    const h = margin.top + innerH - y(value);
    const label = value > 0.12 ? `<text class="value-label" x="${x(i)}" y="${y(value) - 7}" text-anchor="middle">${fmt(value, 2)}</text>` : "";
    return `
      <rect x="${x(i) - barW / 2}" y="${y(value)}" width="${barW}" height="${h}" rx="7" fill="url(#${gradientId})" filter="url(#${glowId})">
        <title>${barKey}: ${fmt(value)}</title>
      </rect>
      ${label}
    `;
  }).join("");

  const line = lineKey
    ? `<polyline points="${rows.map((row, i) => `${x(i)},${y(Number(row[lineKey]))}`).join(" ")}" fill="none" stroke="${lineColor}" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round"/>`
      + rows.map((row, i) => `<circle cx="${x(i)}" cy="${y(Number(row[lineKey]))}" r="4.5" fill="${lineColor}" stroke="white" stroke-width="2"><title>${lineKey}: ${fmt(row[lineKey])}</title></circle>`).join("")
    : "";

  const targetLine = target
    ? `<line x1="${margin.left}" y1="${y(target)}" x2="${width - margin.right}" y2="${y(target)}" stroke="#b3261e" stroke-dasharray="6 5" stroke-width="2"><title>moyenne: ${fmt(target)}</title></line>`
    : "";

  const labels = rows.map((row, i) => {
    const label = row[xKey] ?? i;
    return `<text class="label" x="${x(i)}" y="${height - 14}" text-anchor="middle">${label}</text>`;
  }).join("");

  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${title}">
    <defs>
      <linearGradient id="${gradientId}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${barColor}"/>
        <stop offset="100%" stop-color="${barColor}" stop-opacity="0.48"/>
      </linearGradient>
      <filter id="${glowId}" x="-30%" y="-30%" width="160%" height="160%">
        <feDropShadow dx="0" dy="8" stdDeviation="7" flood-color="${barColor}" flood-opacity="0.18"/>
      </filter>
    </defs>
    ${grid}
    <line class="axis" x1="${margin.left}" y1="${margin.top + innerH}" x2="${width - margin.right}" y2="${margin.top + innerH}"/>
    <line class="axis" x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${margin.top + innerH}"/>
    ${targetLine}
    ${bars}
    ${line}
    ${labels}
  </svg>`;
}

function svgScatter({ rows, xKey, yKey, colorKey, color = "#2057a8" }) {
  if (!rows.length) return `<div class="empty">Aucune donnée disponible</div>`;

  const width = 500;
  const height = 260;
  const margin = { top: 18, right: 22, bottom: 42, left: 58 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;
  const xs = rows.map((r) => Number(r[xKey]));
  const ys = rows.map((r) => Number(r[yKey]));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const x = (v) => margin.left + ((v - minX) / Math.max(maxX - minX, 1e-12)) * innerW;
  const y = (v) => margin.top + innerH - ((v - minY) / Math.max(maxY - minY, 1e-12)) * innerH;

  const points = rows.map((row) => {
    const c = colorKey && Number(row[colorKey]) > 0.5 ? "#147d64" : color;
    return `<circle cx="${x(Number(row[xKey]))}" cy="${y(Number(row[yKey]))}" r="5.5" fill="${c}" opacity="0.82" stroke="white" stroke-width="1.8"><title>${xKey}: ${fmt(row[xKey])}, ${yKey}: ${fmt(row[yKey])}</title></circle>`;
  }).join("");

  return `<svg viewBox="0 0 ${width} ${height}">
    <line class="axis" x1="${margin.left}" y1="${margin.top + innerH}" x2="${width - margin.right}" y2="${margin.top + innerH}"/>
    <line class="axis" x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${margin.top + innerH}"/>
    <text class="label" x="${width / 2}" y="${height - 10}" text-anchor="middle">${xKey}</text>
    <text class="label" x="14" y="${height / 2}" transform="rotate(-90 14 ${height / 2})" text-anchor="middle">${yKey}</text>
    ${points}
  </svg>`;
}

function renderTable(rows, columns) {
  const head = `<thead><tr>${columns.map((c) => `<th>${c.label}</th>`).join("")}</tr></thead>`;
  const body = rows.slice(0, 80).map((row) => `<tr>${columns.map((c) => {
    const value = row[c.key];
    return `<td>${typeof value === "number" ? fmt(value, c.digits ?? 4) : value ?? "—"}</td>`;
  }).join("")}</tr>`).join("");
  document.getElementById("dataTable").innerHTML = `${head}<tbody>${body}</tbody>`;
  document.getElementById("tableHint").textContent = `${Math.min(rows.length, 80)} / ${rows.length} lignes`;
}

function renderBenchmark() {
  const rows = state.data.rows || [];
  const byN = {};
  rows.forEach((r) => {
    byN[r.n] ||= [];
    byN[r.n].push(r);
  });
  const grouped = Object.entries(byN).map(([n, vals]) => ({
    n,
    ratio: vals.reduce((s, r) => s + Number(r.ratio), 0) / vals.length,
    mapping_error: vals.reduce((s, r) => s + Number(r.mapping_error), 0) / vals.length,
  }));

  renderMetrics([
    ["Instances", [rows.length, "graphes benchmarkés"]],
    ["n min/max", [rows.length ? `${Math.min(...rows.map((r) => r.n))}–${Math.max(...rows.map((r) => r.n))}` : "—", "taille système"]],
    ["Ratio moyen", [fmt(rows.reduce((s, r) => s + Number(r.ratio || 0), 0) / Math.max(rows.length, 1)), "proxy / optimum"]],
    ["Mapping moyen", [fmt(rows.reduce((s, r) => s + Number(r.mapping_error || 0), 0) / Math.max(rows.length, 1)), "erreur relative"]],
  ]);
  renderLegend([
    { label: "ratio moyen", color: "#2057a8" },
  ]);
  document.getElementById("primaryPlotTitle").textContent = "Ratio moyen par taille";
  document.getElementById("primaryPlotHint").textContent = "benchmark_summary.csv";
  document.getElementById("primaryPlot").innerHTML = svgBarLine({ rows: grouped, barKey: "ratio", lineKey: null, xKey: "n", title: "benchmark", barColor: "#2057a8" });
  document.getElementById("secondaryPlotTitle").textContent = "Ratio vs mapping";
  document.getElementById("secondaryPlotHint").textContent = "chaque point = instance";
  document.getElementById("secondaryPlot").innerHTML = svgScatter({ rows, xKey: "mapping_error", yKey: "ratio", color: "#2057a8" });
  renderTable(rows, [
    { key: "n", label: "n" },
    { key: "instance_id", label: "instance" },
    { key: "mapping_error", label: "mapping" },
    { key: "ratio", label: "ratio" },
  ]);
}

function renderSmoothGrid() {
  const rows = (state.data.rows || []).slice().sort((a, b) => Number(b.ratio_pulser) - Number(a.ratio_pulser));
  const best = state.data.best || rows[0];
  const top = rows.slice(0, 20).map((r, i) => ({ ...r, rank: i + 1 }));
  renderMetrics([
    ["Essais", [rows.length, "combinaisons testées"]],
    ["Meilleur ratio", [fmt(best?.ratio_pulser), "objectif Pulser"]],
    ["Overlap best", [fmt(best?.overlap_proxy), "état proxy"]],
    ["Fall duration", [best?.fall_duration ?? "—", "ns"]],
  ]);
  renderLegend([
    { label: "ratio Pulser", color: "#7c3aed" },
    { label: "overlap proxy", color: "#111827" },
    { label: "meilleur ratio", color: "#b3261e" },
  ]);
  document.getElementById("primaryPlotTitle").textContent = "Top 20 ratios Pulser";
  document.getElementById("primaryPlotHint").textContent = "grid search smooth";
  document.getElementById("primaryPlot").innerHTML = svgBarLine({ rows: top, barKey: "ratio_pulser", lineKey: "overlap_proxy", xKey: "rank", target: best?.ratio_pulser, title: "smooth grid", barColor: "#7c3aed" });
  document.getElementById("secondaryPlotTitle").textContent = "Ratio vs overlap";
  document.getElementById("secondaryPlotHint").textContent = "tous les essais";
  document.getElementById("secondaryPlot").innerHTML = svgScatter({ rows, xKey: "overlap_proxy", yKey: "ratio_pulser", color: "#7c3aed" });
  renderTable(top, [
    { key: "rank", label: "#" },
    { key: "ratio_pulser", label: "ratio" },
    { key: "overlap_proxy", label: "overlap" },
    { key: "omega_peak", label: "omega" },
    { key: "rise_duration", label: "rise", digits: 0 },
    { key: "hold_duration", label: "hold", digits: 0 },
    { key: "fall_duration", label: "fall", digits: 0 },
  ]);
}

function renderSmoothGraph() {
  const rows = state.data.rows || [];
  const summary = state.data.summary || {};
  renderMetrics([
    ["Graphes", [rows.length, "instances aléatoires"]],
    ["Ratio moyen", [fmt(summary.ratio_pulser_mean), "séquence fixée"]],
    ["Min / max", [`${fmt(summary.ratio_pulser_min)} / ${fmt(summary.ratio_pulser_max)}`, "variabilité"]],
    ["Mapping max", [fmt(summary.mapping_error_max), "embedding stable"]],
  ]);
  renderLegend([
    { label: "ratio Pulser", color: "#147d64" },
    { label: "proxy exact", color: "#111827" },
    { label: "moyenne", color: "#b3261e" },
  ]);
  document.getElementById("primaryPlotTitle").textContent = "Robustesse par graphe";
  document.getElementById("primaryPlotHint").textContent = "barres: Pulser, ligne: proxy exact";
  document.getElementById("primaryPlot").innerHTML = svgBarLine({ rows, barKey: "ratio_pulser", lineKey: "ratio_proxy_exact", xKey: "graph_id", target: summary.ratio_pulser_mean, title: "smooth graph", barColor: "#147d64" });
  document.getElementById("secondaryPlotTitle").textContent = "Mapping vs ratio";
  document.getElementById("secondaryPlotHint").textContent = "limitation dynamique";
  document.getElementById("secondaryPlot").innerHTML = svgScatter({ rows, xKey: "mapping_error", yKey: "ratio_pulser", color: "#147d64" });
  renderTable(rows, [
    { key: "graph_id", label: "graphe" },
    { key: "ratio_pulser", label: "ratio" },
    { key: "overlap_proxy", label: "overlap" },
    { key: "ratio_proxy_exact", label: "proxy exact" },
    { key: "mapping_error", label: "mapping" },
  ]);
}

async function generatePng() {
  const root = document.getElementById("outputList");
  root.textContent = "Génération...";
  try {
    const payload = await api(`/api/plot?kind=${encodeURIComponent(state.kind)}`);
    root.innerHTML = payload.outputs.map((file) => `<div><a href="/${file}" target="_blank">${file}</a></div>`).join("");
  } catch (error) {
    root.textContent = error.message;
  }
}

async function init() {
  state.status = await api("/api/status");
  const firstReady = Object.entries(state.status).find(([, meta]) => meta.ready);
  if (firstReady) state.kind = firstReady[0];
  renderExperiments();
  document.getElementById("generatePng").addEventListener("click", generatePng);
  await loadData();
}

init().catch((error) => {
  setStatus("Erreur");
  document.getElementById("primaryPlot").innerHTML = `<p>${error.message}</p>`;
});
