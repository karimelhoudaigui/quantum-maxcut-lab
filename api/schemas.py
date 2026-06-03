from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class GraphFamily(str, Enum):
    path = "path"
    cycle = "cycle"
    star = "star"
    complete = "complete"
    random = "random"


class Edge(BaseModel):
    i: int
    j: int
    w: float


class Position(BaseModel):
    id: int
    x: float
    y: float


class GraphGenerateRequest(BaseModel):
    family: GraphFamily = GraphFamily.random
    n_nodes: int = Field(default=6, ge=2, le=12)
    density: float = Field(default=0.6, ge=0.0, le=1.0)
    weight_min: float = Field(default=0.5, gt=0.0)
    weight_max: float = Field(default=1.5, gt=0.0)
    seed: Optional[int] = 42
    optimize_geometry: bool = True


class GraphResponse(BaseModel):
    family: GraphFamily
    n_nodes: int
    edges: List[Edge]
    positions: List[Position]
    mapping_error: Optional[float] = None
    descriptors: Dict[str, Union[float, int, str]]


class PipelineRunRequest(BaseModel):
    graph: GraphResponse
    n_roundings: int = Field(default=32, ge=1, le=256)
    seed: int = 1234


class PipelineStep(BaseModel):
    id: Literal["geometry", "pulser", "sdp", "rounding"]
    label: str
    status: Literal["pending", "running", "completed", "failed"]
    metric_label: Optional[str] = None
    metric_value: Optional[Union[float, str]] = None


class PipelineJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    progress: int
    steps: List[PipelineStep]
    result: Optional[Dict[str, object]] = None
    error: Optional[str] = None


class FamilyResultRow(BaseModel):
    family: str
    metrics: Dict[str, Union[float, int, str]]
