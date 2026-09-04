from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.content import router as content_router
from app.api.recommendations import router as recommendations_router
from app.api.tasks import router as tasks_router
from app.core.config import CORS_ORIGINS

app = FastAPI(title="Revenue Swarm API", version="0.1.0")
app.include_router(tasks_router)
app.include_router(recommendations_router)
app.include_router(content_router)

origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
