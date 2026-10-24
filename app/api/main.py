"""
FastAPI application entry point.

This file's only job is wiring — it creates the app instance, adds
middleware, and mounts the router. No business logic lives here.

Uvicorn target (see Dockerfile + docker-compose.yml):
    uvicorn app.api.main:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(
    title="RAG Pipeline",
    description="Hybrid search RAG with grounded generation and LLM-as-judge citation verification.",
    version="1.0.0",
)

# Allow requests from any origin — fine for local dev / internal tooling.
# Tighten allow_origins to specific domains before any public deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
