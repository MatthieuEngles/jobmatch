"""Template filters for Markdown rendering."""

import bleach
import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Allowed HTML tags and attributes for sanitization
ALLOWED_TAGS = [
    "p",
    "br",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "s",
    "code",
    "pre",
    "ul",
    "ol",
    "li",
    "blockquote",
    "hr",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "a",
    "span",
    "div",
]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "th": ["align"],
    "td": ["align"],
}


@register.filter(name="markdown")
def markdown_format(text):
    """Convert Markdown text to sanitized HTML.

    Usage in templates:
        {% load markdown_extras %}
        {{ offer.description|markdown }}
    """
    if not text:
        return ""
    # Convert markdown to HTML
    html = markdown.markdown(
        text,
        extensions=["nl2br", "fenced_code", "tables", "sane_lists"],
    )
    # Sanitize HTML to prevent XSS
    clean_html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )
    # Safe because bleach.clean() sanitizes the HTML with a strict whitelist
    return mark_safe(clean_html)  # nosec B308 B703
