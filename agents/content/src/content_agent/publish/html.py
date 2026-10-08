import html

DISCLOSURE = (
    "Disclosure: this article contains affiliate links. If you buy "
    "through them, we may earn a commission at no extra cost to you."
)

SOCIAL_DISCLOSURE = "#ad affiliate link"


def ensure_disclosure(body: str) -> str:
    if "affiliate link" in body.lower():
        return body
    return f"{DISCLOSURE}\n\n{body}"


def ensure_social_disclosure(body: str, limit: int) -> str:
    lowered = body.lower()
    if "#ad" in lowered or "affiliate link" in lowered:
        return body[:limit]
    suffix = f"\n{SOCIAL_DISCLOSURE}"
    trimmed = body[: limit - len(suffix)].rstrip()
    return f"{trimmed}{suffix}"


def affiliate_anchor(link: str, name: str) -> str:
    safe_link = html.escape(link, quote=True)
    safe_name = html.escape(name)
    return (
        f'<a href="{safe_link}" rel="sponsored nofollow" '
        f'target="_blank">{safe_name}</a>'
    )


def to_html(body: str, link: str, name: str) -> str:
    paragraphs: list[str] = []
    for block in ensure_disclosure(body).split("\n\n"):
        escaped = html.escape(block.strip())
        if link:
            escaped = escaped.replace(
                html.escape(link), affiliate_anchor(link, name)
            )
        if escaped:
            paragraphs.append(f"<p>{escaped}</p>")
    return "\n".join(paragraphs)
