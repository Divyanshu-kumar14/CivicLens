"""CivicLens API — agentic pothole triage service.

Plan ref: IMPLEMENTATION_PLAN.md Task 1.4.1.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.routes import export, health, jobs, tickets

app = FastAPI(
    title="CivicLens API",
    version="1.0.0",
    description="Agentic pothole detection triage API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # CORS allowlist
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
app.include_router(export.router, tags=["export"])
