BLOG_PROMPT = (
    "Write a short blog article (3 paragraphs, plain text, no headings, "
    "no markdown links) reviewing {name}, a {category} product. "
    "Commission model: {commission}. Audience: small business owners "
    "comparing tools. Be specific and avoid hype."
)

SOCIAL_PROMPT = (
    "Write one social media post (max 3 sentences, plain text, no "
    "hashtags, no links) recommending {name}, a {category} product, "
    "to small business owners."
)

STUB_BLOG = (
    "Stub article (LLM_STUB=1). Paragraph one describes the product. "
    "Paragraph two covers pricing and who it fits. Paragraph three "
    "closes with a recommendation."
)

STUB_SOCIAL = "Stub social post (LLM_STUB=1). Short, plain, no hashtags."

BLOG_BODY = "{body}\n\n---\n\nAffiliate link: {name} - {link}"
SOCIAL_BODY = "{body}\n\n{link}"


def render_blog(body: str, name: str, link: str) -> str:
    return BLOG_BODY.format(body=body.strip(), name=name, link=link)


def render_social(body: str, link: str) -> str:
    trimmed = body.strip()
    if len(trimmed) > 240:
        trimmed = trimmed[:237].rstrip() + "..."
    return SOCIAL_BODY.format(body=trimmed, link=link)
