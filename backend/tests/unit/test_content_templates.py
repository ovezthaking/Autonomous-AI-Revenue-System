from app.agents.content.templates import render_blog, render_social

LINK = "https://aff.test/ref?id=1&src=blog"


def test_render_blog_includes_the_exact_link():
    rendered = render_blog("A short review.", "Example CRM", LINK)

    assert f"Affiliate link: Example CRM - {LINK}" in rendered


def test_render_social_truncates_long_body_without_cutting_the_link():
    rendered = render_social("x" * 300, LINK)

    text, _, link = rendered.rpartition("\n\n")
    assert link == LINK
    assert len(text) <= 240
    assert text.endswith("...")
    assert "x" * 300 not in rendered


def test_render_blog_keeps_short_body():
    rendered = render_blog("  Short review.  ", "Example CRM", LINK)

    assert rendered.startswith("Short review.")
    assert LINK in rendered


def test_render_social_keeps_short_body():
    rendered = render_social("  Short post.  ", LINK)

    assert rendered == f"Short post.\n\n{LINK}"
