import csv
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("MPLCONFIGDIR", "/tmp")


ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"

EXPERIMENTS = {
    "benchmark": {
        "label": "Benchmark proxy",
        "files": ["benchmark_summary.csv", "benchmark_full.json"],
    },
    "smooth_grid": {
        "label": "Grid search smooth",
        "files": ["pulser_smooth_grid_search.json", "pulser_smooth_grid_search_best.json"],
    },
    "smooth_graph": {
        "label": "Étude smooth multi-graphes",
        "files": [
            "pulser_smooth_graph_study_n4.json",
            "pulser_smooth_graph_study_n4_summary.json",
        ],
    },
}


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        for key, value in list(row.items()):
            if value is None or value == "":
                continue
            try:
                if "." in value or "e" in value.lower():
                    row[key] = float(value)
                else:
                    row[key] = int(value)
            except ValueError:
                pass
    return rows


def experiment_status():
    payload = {}
    for key, meta in EXPERIMENTS.items():
        files = []
        for filename in meta["files"]:
            path = ROOT / filename
            files.append({
                "name": filename,
                "exists": path.exists(),
                "size": path.stat().st_size if path.exists() else 0,
            })
        payload[key] = {
            "label": meta["label"],
            "ready": any(item["exists"] for item in files),
            "files": files,
        }
    return payload


def load_experiment(kind):
    if kind == "benchmark":
        csv_path = ROOT / "benchmark_summary.csv"
        json_path = ROOT / "benchmark_full.json"
        rows = read_csv(csv_path) if csv_path.exists() else []
        full = read_json(json_path) if json_path.exists() else []
        return {"kind": kind, "rows": rows, "full": full}

    if kind == "smooth_grid":
        rows_path = ROOT / "pulser_smooth_grid_search.json"
        best_path = ROOT / "pulser_smooth_grid_search_best.json"
        return {
            "kind": kind,
            "rows": read_json(rows_path) if rows_path.exists() else [],
            "best": read_json(best_path) if best_path.exists() else None,
        }

    if kind == "smooth_graph":
        rows_path = ROOT / "pulser_smooth_graph_study_n4.json"
        summary_path = ROOT / "pulser_smooth_graph_study_n4_summary.json"
        return {
            "kind": kind,
            "rows": read_json(rows_path) if rows_path.exists() else [],
            "summary": read_json(summary_path) if summary_path.exists() else None,
        }

    raise ValueError(f"Expérience inconnue: {kind}")


def generate_png(kind):
    import matplotlib

    matplotlib.use("Agg")

    if kind == "benchmark":
        from quantum_plot import (
            plot_mapping_error_vs_n,
            plot_ratio_vs_mapping_error,
            plot_ratio_vs_n,
        )

        data = load_experiment(kind)
        rows = data["full"] or data["rows"]
        if not rows:
            raise ValueError("Aucun résultat benchmark trouvé.")

        outputs = [
            "figure1_mapping_error_vs_n.png",
            "figure2_ratio_vs_n.png",
            "figure3_ratio_vs_mapping_error.png",
        ]
        plot_mapping_error_vs_n(rows, save_path=outputs[0], show=False)
        plot_ratio_vs_n(rows, save_path=outputs[1], show=False)
        plot_ratio_vs_mapping_error(rows, save_path=outputs[2], show=False)
        return outputs

    if kind == "smooth_graph":
        from quantum_plot import plot_smooth_graph_study_article

        data = load_experiment(kind)
        rows = data["rows"]
        if not rows:
            raise ValueError("Aucun résultat smooth multi-graphes trouvé.")

        output = "figure_smooth_graph_study_n4.png"
        plot_smooth_graph_study_article(
            rows,
            summary=data["summary"],
            save_paths=output,
            show=False,
        )
        return [output]

    if kind == "smooth_grid":
        data = load_experiment(kind)
        rows = data["rows"]
        if not rows:
            raise ValueError("Aucun résultat smooth grid search trouvé.")

        from quantum_frontend_plots import plot_smooth_grid_search_png

        output = "figure_smooth_grid_search.png"
        plot_smooth_grid_search_png(rows, data["best"], output)
        return [output]

    raise ValueError(f"PNG non supporté pour: {kind}")


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/api/status":
                self.send_json(experiment_status())
                return

            if path == "/api/data":
                query = parse_qs(parsed.query)
                kind = query.get("kind", [""])[0]
                self.send_json(load_experiment(kind))
                return

            if path == "/api/plot":
                query = parse_qs(parsed.query)
                kind = query.get("kind", [""])[0]
                outputs = generate_png(kind)
                self.send_json({"outputs": outputs})
                return

            if path == "/":
                path = "/index.html"

            candidate = (FRONTEND / path.lstrip("/")).resolve()
            if not str(candidate).startswith(str(FRONTEND.resolve())):
                self.send_error(403)
                return

            if not candidate.exists():
                root_candidate = (ROOT / path.lstrip("/")).resolve()
                if root_candidate.exists() and root_candidate.suffix.lower() == ".png":
                    candidate = root_candidate
                else:
                    self.send_error(404)
                    return

            content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            body = candidate.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def log_message(self, format, *args):
        print(f"[frontend] {format % args}")


def main():
    host = "127.0.0.1"
    port = int(os.environ.get("QUANTUM_FRONTEND_PORT", "8765"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Frontend Quantum MaxCut: http://{host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
