import re
from datetime import date

import httpx

from revenue_swarm import config
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.networks.base import (
    PerformanceRow,
    PermanentNetworkError,
    TrackingLink,
    make_client,
    redact_secrets,
    require,
    to_cents,
)
from revenue_swarm.networks.pacing import pace

# clickref: max 50 chars, lowercase, no # + " & | '
_CLICKREF = re.compile(r"^[a-z0-9][a-z0-9._-]{0,49}$")
_BATCH_LIMIT = 100


class AwinNetwork:
    name = "awin"
    allow_redirect = True

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def _endpoint(self) -> str:
        publisher = require(config.AWIN_PUBLISHER_ID, "AWIN_PUBLISHER_ID")
        return (
            f"https://api.awin.com/publishers/{publisher}/linkbuilder/generate"
        )

    def _post(self, payload: object, timeout: float) -> httpx.Response:
        token = require(config.AWIN_API_TOKEN, "AWIN_API_TOKEN")
        pace(self.name)
        with make_client(self._transport, timeout) as client:
            response = client.post(
                self._endpoint(),
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
        # Advertisers with link builder disabled return this misleading
        # message. It is not transient; fall back to a manual link.
        if "Unknown error" in response.text:
            raise PermanentNetworkError("link builder disabled")
        if response.status_code in (400, 401, 403, 404):
            raise PermanentNetworkError(
                redact_secrets(f"awin {response.status_code}")
            )
        response.raise_for_status()
        return response

    @staticmethod
    def _item(program: AffiliateProgram, destination: str, subid: str):
        if _CLICKREF.fullmatch(subid) is None:
            raise PermanentNetworkError("clickref rejected")
        if not program.network_program_id:
            raise PermanentNetworkError("network_program_id missing")
        return {
            "advertiserId": program.network_program_id,
            "destinationUrl": destination,
            "parameters": {"clickref": subid},
        }

    def create_link(
        self, program: AffiliateProgram, destination: str, subid: str
    ) -> TrackingLink:
        payload = self._item(program, destination, subid)
        data = self._post(payload, timeout=20).json()
        row = data[0] if isinstance(data, list) else data
        return TrackingLink(
            url=row["url"], network_link_id=row.get("id"), raw=row
        )

    def create_links(
        self, items: list[tuple[AffiliateProgram, str, str]]
    ) -> list[TrackingLink]:
        if len(items) > _BATCH_LIMIT:
            raise PermanentNetworkError("batch larger than 100")
        payload = [self._item(p, d, s) for p, d, s in items]
        data = self._post(payload, timeout=30).json()
        return [TrackingLink(url=row["url"], raw=row) for row in data]

    def fetch_performance(
        self, since: date, until: date
    ) -> list[PerformanceRow]:
        publisher = require(config.AWIN_PUBLISHER_ID, "AWIN_PUBLISHER_ID")
        token = require(config.AWIN_API_TOKEN, "AWIN_API_TOKEN")
        pace(self.name)
        with make_client(self._transport, timeout=30) as client:
            response = client.get(
                f"https://api.awin.com/publishers/{publisher}/reports/advertiser",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "startDate": since.isoformat(),
                    "endDate": until.isoformat(),
                },
            )
        if response.status_code in (400, 401, 403, 404):
            raise PermanentNetworkError(
                redact_secrets(f"awin {response.status_code}")
            )
        response.raise_for_status()
        rows: list[PerformanceRow] = []
        for item in response.json():
            raw_date = str(item.get("date") or since.isoformat())[:10]
            rows.append(
                PerformanceRow(
                    day=date.fromisoformat(raw_date),
                    program_id=str(item.get("advertiserId") or "") or None,
                    subid=item.get("clickRef"),
                    clicks=int(item.get("clicks") or 0),
                    conversions_pending=int(item.get("pendingNo") or 0),
                    conversions_approved=int(item.get("approvedNo") or 0),
                    conversions_declined=int(item.get("declinedNo") or 0),
                    revenue_pending_cents=to_cents(item.get("pendingValue")),
                    revenue_approved_cents=to_cents(item.get("approvedValue")),
                    currency=str(item.get("currency") or "USD"),
                )
            )
        return rows
