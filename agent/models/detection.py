"""Detection pydantic model — one raw vision hit."""
from pydantic import BaseModel, Field


class DetectionModel(BaseModel):
    det_id: str
    job_id: str
    t: float = Field(description="timestamp in video, seconds")
    lat: float
    lon: float
    cls: str = Field(description="pothole | crack")
    conf: float = Field(ge=0.0, le=1.0)
    box: list[int] = Field(description="[x, y, w, h] in pixels")
    emb_url: str = ""
    crop_url: str = ""
