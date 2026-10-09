"""Job pydantic models — video processing batch."""
from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    video_url: str
    gps_url: str
    ward: str = "ward-12-demo"


class JobModel(BaseModel):
    job_id: str
    status: str = Field(description="queued | processing | completed | failed")
    progress_pct: float = 0.0
    counts: dict = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
