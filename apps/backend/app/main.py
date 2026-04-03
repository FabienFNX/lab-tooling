from contextlib import asynccontextmanager
import os
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.gitlab import router as gitlab_router
from app.api.recordings import router as recordings_router
from app.api.routes import router
from app.api.training import router as training_router
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Lab Tooling API", lifespan=lifespan)

# Allow configuring CORS origins via env var `CORS_ALLOWED_ORIGINS` (comma-separated)
# or allow all origins when `CORS_ALLOW_ALL` is set to true.
allow_all = os.getenv("CORS_ALLOW_ALL", "").lower() in ("1", "true", "yes")
if allow_all:
    origins: List[str] | str = ["*"]
else:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200")
    origins = [o.strip() for o in raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(gitlab_router)
app.include_router(training_router)
app.include_router(recordings_router)


@app.get("/health")
def health():
    return {"status": "ok"}
