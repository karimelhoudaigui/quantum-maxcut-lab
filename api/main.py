from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.graph import router as graph_router
from api.routers.pipeline import router as pipeline_router


app = FastAPI(
    title="Quantum MaxCut API",
    description="Production-oriented API for graph generation and hybrid Pulser-SDP-rounding jobs.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graph_router)
app.include_router(pipeline_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
