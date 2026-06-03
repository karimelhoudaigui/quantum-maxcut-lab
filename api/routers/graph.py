from fastapi import APIRouter

from api.schemas import GraphGenerateRequest, GraphResponse
from api.services.pipeline_service import generate_graph


router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.post("/generate", response_model=GraphResponse)
def generate_graph_endpoint(payload: GraphGenerateRequest) -> GraphResponse:
    return generate_graph(payload)
