import httpx

from revenue_swarm import config
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.networks.base import (
    PermanentNetworkError,
    TrackingLink,
    make_client,
    require,
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
