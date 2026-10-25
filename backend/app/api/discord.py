import json
import time

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from revenue_swarm.db import SessionLocal

from app.core.config import (
    DASHBOARD_URL,
    DISCORD_ALLOWED_USER_IDS,
    DISCORD_PUBLIC_KEY,
)
from app.services.discord_auth import verify_signature
from app.services.discord_interactions import handle_interaction

router = APIRouter(prefix="/discord", tags=["discord"])


def _handle(payload: dict) -> dict:
    db = SessionLocal()
    try:
        return handle_interaction(
            db,
            payload,
            allowed=DISCORD_ALLOWED_USER_IDS,
            dashboard_url=DASHBOARD_URL,
        )
    finally:
        db.close()


@router.post("/interactions")
async def discord_interactions(request: Request) -> JSONResponse:
    body = await request.body()
    signature = request.headers.get("X-Signature-Ed25519", "")
    timestamp = request.headers.get("X-Signature-Timestamp", "")
    if not verify_signature(
        body,
        signature,
        timestamp,
        DISCORD_PUBLIC_KEY,
        now=int(time.time()),
    ):
        return JSONResponse({"error": "invalid signature"}, status_code=401)
    try:
        payload = json.loads(body)
    except ValueError:
        return JSONResponse({"error": "invalid json"}, status_code=400)
    if not isinstance(payload, dict):
        return JSONResponse({"error": "invalid json"}, status_code=400)
    result = await run_in_threadpool(_handle, payload)
    return JSONResponse(result)
