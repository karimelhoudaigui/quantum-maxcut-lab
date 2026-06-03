# Quantum MaxCut Lab

> A modern research console for neutral-atom MaxCut experiments, from graph generation to Rydberg proxy simulation, SDP relaxation and hybrid rounding.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Console-61DAFB?style=for-the-badge&logo=react&logoColor=111827)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-Frontend-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

![Quantum MaxCut Lab software preview](assets/software-preview.png)

## Overview

Quantum MaxCut Lab is a production-style software interface built on top of the research project [`karimelhoudaigui/quantum-maxcut`](https://github.com/karimelhoudaigui/quantum-maxcut).

The goal is to make the complete quantum optimization workflow visible, interactive and reproducible:

- generate weighted graph instances;
- optimize a neutral-atom geometry for the graph;
- evaluate a Rydberg XY proxy with Pulser-inspired simulation tools;
- reconstruct a hybrid classical/quantum relaxation with SDP;
- run rounding and compare Pulser proxy quality against hybrid recovery;
- inspect live metrics through a modern React console.

## What The Software Does

Quantum MaxCut Lab studies the MaxCut problem through a neutral-atom mapping. A weighted graph is transformed into atom positions, where distance-dependent couplings approximate graph edge weights. The software then compares several layers of the pipeline:

- **Geometry embedding**: maps graph weights into atom coordinates and reports the mapping error.
- **Rydberg proxy**: evaluates a proxy Hamiltonian based on neutral-atom interactions.
- **Pulser pipeline**: prepares and evaluates pulse-sequence inspired quantum states.
- **SDP relaxation**: reconstructs a pseudo-moment matrix from proxy correlators.
- **Hybrid rounding**: produces rounded candidate cuts and compares them to proxy-only behavior.
- **Dashboard analytics**: exposes ratio, cut value, mapping error and hybrid gain in a console UI.

The application is designed for small research instances where exact methods, simulation, SDP and visualization can be combined in the same loop.

## Product Surface

The repository contains two user-facing interfaces:

- **Modern Console**: React + TypeScript + Vite frontend in `app/`, connected to a FastAPI backend in `api/`.
- **Legacy Research Dashboard**: lightweight Python HTTP dashboard in `quantum_frontend.py`, useful when Node or Docker are not available.

The modern console is the main software surface. It provides graph controls, pipeline execution, live progress cards, graph visualization and metric panels.

## Architecture

```text
.
├── api/                         # FastAPI backend and pipeline endpoints
├── app/                         # React 18 + TypeScript + Vite console
├── frontend/                    # Lightweight static dashboard assets
├── quantum_hybrid/              # SDP relaxation and hybrid rounding
├── quantum_pulser/              # Pulser-style sequence simulation and evaluation
├── quantum_pulser_all/          # Legacy Pulser experiment helpers
├── scripts/                     # Reproducible experiment launchers
├── assets/software-preview.png  # README preview image
├── docker-compose.yml           # Full API + frontend stack
├── quantum_main.py              # Research runner
├── quantum_utils.py             # Hamiltonians, Pauli operators and exact utilities
└── requirements.txt             # Python dependencies
```

## Run With Docker

```bash
docker compose up
```

Then open:

```text
http://localhost:5173
```

The API is available at:

```text
http://localhost:8000
```

## Run Without Docker

Backend:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --port 8000
```

Frontend:

```bash
cd app
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Python-Only Dashboard

If Docker and Node.js are not installed, run the lightweight dashboard:

```bash
source .venv/bin/activate
python quantum_frontend.py
```

Open:

```text
http://127.0.0.1:8765
```

## API Endpoints

- `POST /api/graph/generate` creates a weighted graph instance.
- `POST /api/pipeline/run` starts the full Pulser to SDP to rounding pipeline.
- `GET /api/pipeline/{job_id}/status` polls a running pipeline job.
- `GET /api/results/{family}` reads available family-level experiment summaries.

## Research Core

The main quantum objective is the Quantum MaxCut Hamiltonian:

```math
H_{\mathrm{qmc}} = - \sum_{(i,j)\in E} w_{ij} \left(I - X_i X_j - Y_i Y_j - Z_i Z_j\right)
```

The neutral-atom proxy uses distance-dependent XY couplings:

```math
H_r = \sum_{(i,j)\in E} J_{ij} \left(X_i X_j + Y_i Y_j\right),
\qquad J_{ij} = \frac{C_3}{r_{ij}^3}
```

The software measures the geometry mismatch:

```math
f(\mathbf r) =
\sqrt{
  \frac{
    \sum_{(i,j)} \left(J_{ij}(\mathbf r) - w_{ij}\right)^2
  }{
    \sum_{(i,j)} w_{ij}^2
  }
}
```

and compares proxy/hybrid quality through energy and MaxCut-style metrics.

## Experiment Scripts

Run the selected research mode:

```bash
source .venv/bin/activate
python quantum_main.py
```

Run the graph-family hybrid pipeline:

```bash
python scripts/run_graph_family_full_pipeline.py --n 4 --num-instances 100 --seed 123
```

## Why This Repository Exists

The original repository documents the research pipeline in detail. This repository is positioned as the software showcase version: cleaner packaging, a stronger README, an application-first presentation, and a visible product preview for GitHub visitors.

## License

MIT License.
