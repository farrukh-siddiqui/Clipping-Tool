"""FastAPI application — Clipping Engine API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import create_tables
from api.routers.auth_router import router as auth_router
from api.routers.jobs_router import router as jobs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="Clipping Engine API",
    version="1.0.0",
    description="AI-powered viral clip extraction from long-form videos",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(jobs_router)


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}
