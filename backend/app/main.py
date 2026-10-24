from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.affiliate import router as affiliate_router
from app.api.checkout import router as checkout_router
from app.api.content import router as content_router
from app.api.downloads import router as downloads_router
from app.api.links import router as links_router
from app.api.metrics import router as metrics_router
from app.api.orders import router as orders_router
from app.api.products import router as products_router
from app.api.publications import router as publications_router
from app.api.recommendations import router as recommendations_router
from app.api.research import router as research_router
from app.api.tasks import router as tasks_router
from app.api.webhooks import router as webhooks_router
from app.core.config import CORS_ORIGINS

app = FastAPI(title="Revenue Swarm API", version="0.1.0")
app.include_router(tasks_router)
app.include_router(recommendations_router)
app.include_router(content_router)
app.include_router(research_router)
app.include_router(publications_router)
app.include_router(products_router)
app.include_router(checkout_router)
app.include_router(webhooks_router)
app.include_router(downloads_router)
app.include_router(orders_router)
app.include_router(affiliate_router)
app.include_router(links_router)
app.include_router(metrics_router)


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
