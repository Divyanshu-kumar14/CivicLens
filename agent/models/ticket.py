"""Ticket/Cluster pydantic model — one deduped defect."""
from pydantic import BaseModel, Field


class TicketModel(BaseModel):
    ticket_id: str
    hole_label: str = ""
    det_ids: list[str] = Field(default_factory=list)
    centroid: list[float] = Field(description="[lat, lon]")
    repeat_count: int = 0
    severity: float = Field(ge=0.0, le=100.0)
    status: str = Field(description="filed | pending | dismissed")
    signals: dict = Field(default_factory=dict)
    trace: list[dict] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
