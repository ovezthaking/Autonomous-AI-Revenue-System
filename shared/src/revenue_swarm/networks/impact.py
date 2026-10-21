from datetime import date

import httpx

from revenue_swarm import config
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.networks.base import (
    PerformanceRow,
    PermanentNetworkError,
    TrackingLink,
    make_client,
    require,
    to_cents,
)
from revenue_swarm.networks.pacing import pace


class ImpactNetwork:
    name = "impact"
    allow_redirect = True

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def create_link(
        self, program: AffiliateProgram, destination: str, subid: str
    ) -> TrackingLink:
        sid = require(config.IMPACT_ACCOUNT_SID, "IMPACT_ACCOUNT_SID")
        token = require(config.IMPACT_AUTH_TOKEN, "IMPACT_AUTH_TOKEN")
        if not program.network_program_id:
            raise PermanentNetworkError("network_program_id missing")
        pace(self.name)
        with make_client(self._transport) as client:
            response = client.post(
                f"https://api.impact.com/Mediapartners/{sid}"
                f"/Programs/{program.network_program_id}/TrackingLinks",
                auth=(sid, token),
                headers={"Accept": "application/json"},
                data={
                    # Regular, not Vanity: Vanity is capped at 5000/account.
                    "Type": "Regular",
                    "subId1": subid,
                    "DeepLink": destination,
                },
            )
        if response.status_code == 403:
            raise PermanentNetworkError("vanity limit or forbidden")
        if response.status_code in (400, 401, 404):
            raise PermanentNetworkError(f"impact {response.status_code}")
        response.raise_for_status()
        data = response.json()
        return TrackingLink(
            url=data["TrackingLink"],
            network_link_id=data.get("Id"),
            raw=data,
        )

    def fetch_performance(
        self, since: date, until: date
    ) -> list[PerformanceRow]:
        sid = require(config.IMPACT_ACCOUNT_SID, "IMPACT_ACCOUNT_SID")
        token = require(config.IMPACT_AUTH_TOKEN, "IMPACT_AUTH_TOKEN")
        pace(self.name)
        with make_client(self._transport, timeout=30) as client:
            response = client.get(
                f"https://api.impact.com/Mediapartners/{sid}/Reports/partner_performance_by_subid",
                auth=(sid, token),
                headers={"Accept": "application/json"},
                params={
                    "START_DATE": since.isoformat(),
                    "END_DATE": until.isoformat(),
                },
            )
        if response.status_code in (400, 401, 403, 404):
            raise PermanentNetworkError(f"impact {response.status_code}")
        response.raise_for_status()
        payload = response.json()
        items = (
            payload.get("Records", [])
            if isinstance(payload, dict)
            else payload
        )
        rows: list[PerformanceRow] = []
        for item in items:
            raw_date = str(
                item.get("date") or item.get("Date") or since.isoformat()
            )[:10]
            prog_id = (
                item.get("programId")
                or item.get("CampaignId")
                or item.get("advertiserId")
            )
            rows.append(
                PerformanceRow(
                    day=date.fromisoformat(raw_date),
                    program_id=str(prog_id) if prog_id else None,
                    subid=item.get("subId1") or item.get("subid"),
                    clicks=int(item.get("clicks") or item.get("Clicks") or 0),
                    conversions_pending=int(
                        item.get("pendingNo")
                        or item.get("PendingActions")
                        or 0
                    ),
                    conversions_approved=int(
                        item.get("approvedNo") or item.get("Actions") or 0
                    ),
                    conversions_declined=int(
                        item.get("declinedNo")
                        or item.get("ReversedActions")
                        or 0
                    ),
                    revenue_pending_cents=to_cents(
                        item.get("pendingValue") or item.get("PendingPayout")
                    ),
                    revenue_approved_cents=to_cents(
                        item.get("approvedValue") or item.get("Payout")
                    ),
                    currency=str(
                        item.get("currency") or item.get("Currency") or "USD"
                    ),
                )
            )
        return rows
