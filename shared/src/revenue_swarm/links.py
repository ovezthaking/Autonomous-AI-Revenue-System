"""Tracked affiliate links: SubID per content item, /go/{slug} indirection."""

import hashlib
import secrets
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from revenue_swarm import config
from revenue_swarm.enums import ApplicationStatus, LinkStatus
from revenue_swarm.models.affiliate_link import AffiliateLink
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.networks import PermanentNetworkError, network_for


def subid_for(item: ContentItem) -> str:
    """32 lowercase hex chars: fits Awin's 50-char clickref, no & + # '."""
    return item.id.hex


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _with_utm(url: str, subid: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["utm_content"] = subid
    return urlunsplit(parts._replace(query=urlencode(query)))


def tracking_enabled(program: AffiliateProgram) -> bool:
    return (
        config.AFFILIATE_LINKS_ENABLED
        and program.application_status == ApplicationStatus.ACTIVE.value
    )


def destination_for(program: AffiliateProgram) -> str:
    return program.url or program.affiliate_link or ""


def ensure_link(
    db: Session, program: AffiliateProgram, item: ContentItem
) -> AffiliateLink:
    """Returns the tracked link for (program, item), creating it once."""
    if not config.AFFILIATE_LINKS_ENABLED:
        raise RuntimeError("affiliate links disabled")
    if program.application_status != ApplicationStatus.ACTIVE.value:
        raise RuntimeError("program is not active")
    subid = subid_for(item)
    destination = destination_for(program)
    existing = db.scalar(
        select(AffiliateLink).where(
            AffiliateLink.program_id == program.id,
            AffiliateLink.destination_url == destination,
            AffiliateLink.subid == subid,
        )
    )
    if existing is not None:
        return existing
    network = network_for(program.network)
    target = (
        _with_utm(destination, subid)
        if config.SITE_URL and destination.startswith(config.SITE_URL)
        else destination
    )
    tracking = network.create_link(program, target, subid)
    row = AffiliateLink(
        program_id=program.id,
        content_item_id=item.id,
        destination_url=destination,
        tracking_url=tracking.url,
        slug=secrets.token_urlsafe(8),
        subid=subid,
        network=network.name,
        status=LinkStatus.ACTIVE.value,
    )
    row.program = program
    db.add(row)
    db.flush()
    return row


def public_url(link: AffiliateLink) -> str:
    """URL to embed in content. Amazon always gets the direct link."""
    if link.network == "amazon" or not link.program.allow_redirect:
        return link.tracking_url
    return f"{config.SITE_URL}/go/{link.slug}"


def link_for_content(
    db: Session, program: AffiliateProgram, item: ContentItem
) -> str:
    """Link for a new content item, falling back to the pasted link.

    `item` must already be flushed (the link row references it).
    Raises PermanentNetworkError when neither path yields a link.
    """
    if tracking_enabled(program):
        try:
            return public_url(ensure_link(db, program, item))
        except PermanentNetworkError as exc:
            if not program.affiliate_link:
                raise
            program.extras = {
                **(program.extras or {}),
                "link_error": str(exc)[:200],
            }
    if not program.affiliate_link:
        raise PermanentNetworkError("no affiliate link available")
    return program.affiliate_link
