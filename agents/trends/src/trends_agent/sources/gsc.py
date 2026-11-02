"""Google Search Console signal source (queries and clicks)."""

from revenue_swarm import config
from revenue_swarm.models.trend_signal import TrendSignal
from sqlalchemy.orm import Session


class GscSource:
    name = "gsc"

    def collect(self, db: Session) -> list[TrendSignal]:
        if not config.GSC_SITE_URL or not config.GSC_CREDENTIALS_JSON:
            return []
        return []
