"""Shopify GraphQL Admin API client with error handling and cost pacing."""

import time
from typing import Any

import httpx
from revenue_swarm import config

from shop_agent.redaction import (
    PermanentError,
    TransientError,
    UnknownOutcomeError,
    redact,
)
from shop_agent.shopify.auth import access_token, invalidate_token


def execute(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    response = _post(query, variables)
    if response.status_code == 401:
        raise PermanentError("shopify unauthorized")
    if response.status_code >= 500:
        raise TransientError(f"shopify http {response.status_code}")
    body = response.json()
    if body.get("errors"):
        if _is_throttled(body):
            raise TransientError("throttled")
        raise PermanentError(redact(str(body["errors"])))
    _respect_cost((body.get("extensions") or {}).get("cost"))
    return body["data"]


def mutation_result(data: dict[str, Any], field: str) -> dict[str, Any]:
    result = data[field]
    if result.get("userErrors"):
        raise PermanentError(redact(str(result["userErrors"])))
    return result


def _post(query: str, variables: dict[str, Any]) -> httpx.Response:
    response = _send(query, variables, access_token())
    if response.status_code != 401:
        return response
    invalidate_token()
    return _send(query, variables, access_token())


def _send(query: str, variables: dict[str, Any], token: str) -> httpx.Response:
    try:
        return httpx.post(
            f"https://{config.SHOPIFY_SHOP}.myshopify.com/admin/api/"
            f"{config.SHOPIFY_API_VERSION}/graphql.json",
            json={"query": query, "variables": variables},
            headers={"X-Shopify-Access-Token": token},
            timeout=20.0,
        )
    except httpx.ReadTimeout as exc:
        raise UnknownOutcomeError("shopify timeout") from exc


def _is_throttled(body: dict[str, Any]) -> bool:
    for err in body.get("errors") or []:
        code = (err.get("extensions") or {}).get("code")
        if code == "THROTTLED":
            return True
    return False


def _respect_cost(cost: dict[str, Any] | None) -> None:
    if not cost:
        return
    available = (cost.get("throttleStatus") or {}).get("currentlyAvailable")
    if isinstance(available, int) and available < 100:
        time.sleep(1)
