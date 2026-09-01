from fastapi import FastAPI

from app.api.content import router as content_router
from app.api.recommendations import router as recommendations_router
from app.api.tasks import router as tasks_router

app = FastAPI(title="Revenue Swarm API", version="0.1.0")
app.include_router(tasks_router)
app.include_router(recommendations_router)
app.include_router(content_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
