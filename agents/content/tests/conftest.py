from datetime import UTC, datetime, timedelta

import pytest
from revenue_swarm.models.publication import Publication

pytest_plugins = ["revenue_swarm.testing.fixtures"]


@pytest.fixture
def db(db_session):
    return db_session


@pytest.fixture
def item(make_content_item):
    return make_content_item(
        status="scheduled",
        scheduled_for=datetime.now(UTC) - timedelta(minutes=5),
    )


@pytest.fixture
def publication(db, item):
    row = Publication(
        content_item_id=item.id,
        target="dryrun",
        status="in_flight",
        attempts=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
