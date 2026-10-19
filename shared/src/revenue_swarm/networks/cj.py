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


class CjNetwork:
    name = "cj"
    allow_redirect = True

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def create_link(
        self, program: AffiliateProgram, destination: str, subid: str
    ) -> TrackingLink:
        key = require(config.CJ_API_KEY, "CJ_API_KEY")
        if not program.network_program_id:
            raise PermanentNetworkError("network_program_id missing")
        pace(self.name)
        with make_client(self._transport) as client:
            response = client.get(
                "https://publishertracking.api.cj.com/trackinglink",
                headers={"Authorization": f"Bearer {key}"},
                params={
                    "programId": program.network_program_id,
                    "destinationUrl": destination,
                    "sid": subid,
                },
            )
        if response.status_code in (400, 401, 403, 404):
            raise PermanentNetworkError(f"cj {response.status_code}")
        response.raise_for_status()
        data = response.json()
        return TrackingLink(
            url=data["trackingUrl"],
            network_link_id=data.get("linkId"),
            raw=data,
        )
