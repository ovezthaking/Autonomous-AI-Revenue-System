from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from revenue_swarm import config
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.networks.base import (
    PerformanceRow,
    TrackingLink,
    require,
)


def with_params(url: str, params: dict[str, str]) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(params)
    return urlunsplit(parts._replace(query=urlencode(query)))


class ManualNetwork:
    """Programs without an API: the operator pastes the base link once."""

    name = "manual"
    allow_redirect = True

    def create_link(
        self, program: AffiliateProgram, destination: str, subid: str
    ) -> TrackingLink:
        base = require(program.affiliate_link or "", "affiliate_link")
        param = str((program.extras or {}).get("subid_param") or "subid")
        url = with_params(base, {param: subid})
        return TrackingLink(url=url, raw={"url": url})

    def fetch_performance(
        self, since: date, until: date
    ) -> list[PerformanceRow]:
        return []


class AmazonNetwork:
    """Direct links only: Amazon pays nothing on redirected clicks."""

    name = "amazon"
    allow_redirect = False

    def create_link(
        self, program: AffiliateProgram, destination: str, subid: str
    ) -> TrackingLink:
        tag = require(config.AMAZON_PARTNER_TAG, "AMAZON_PARTNER_TAG")
        url = with_params(destination, {"tag": tag, "ascsubtag": subid})
        return TrackingLink(url=url, raw={"url": url})

    def fetch_performance(
        self, since: date, until: date
    ) -> list[PerformanceRow]:
        return []
