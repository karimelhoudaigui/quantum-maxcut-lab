from fastapi import APIRouter, HTTPException

from api.schemas import FamilyResultRow, PipelineJobResponse, PipelineRunRequest
from api.services.pipeline_service import get_job, load_family_results, start_pipeline


router = APIRouter(tags=["pipeline"])


@router.post("/api/pipeline/run", response_model=PipelineJobResponse)
def run_pipeline_endpoint(payload: PipelineRunRequest) -> PipelineJobResponse:
    return start_pipeline(payload)


@router.get("/api/pipeline/{job_id}/status", response_model=PipelineJobResponse)
def pipeline_status_endpoint(job_id: str) -> PipelineJobResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Pipeline job not found")
    return job


@router.get("/api/results/{family}", response_model=list[FamilyResultRow])
def family_results_endpoint(family: str) -> list[FamilyResultRow]:
    return load_family_results(family)
