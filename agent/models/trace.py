"""Trace entry pydantic model — every state transition, logged."""
from pydantic import BaseModel, Field


class TraceEntry(BaseModel):
    ts: str = Field(description="ISO timestamp")
    actor: str = Field(description='"agent" | "human"')
    from_status: str
    to_status: str
    reasons: list[str] = Field(default_factory=list)
    signals: dict = Field(default_factory=dict)
