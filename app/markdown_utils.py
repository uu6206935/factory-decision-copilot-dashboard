from __future__ import annotations

import re
from markupsafe import Markup
import mistune
import bleach

_MD = mistune.create_markdown(escape=True, hard_wrap=False, plugins=["table", "strikethrough"])

_ALLOWED_TAGS = [
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "em", "del", "ul", "ol", "li", "blockquote", "code", "pre",
    "table", "thead", "tbody", "tr", "th", "td", "a",
]
_ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "th": ["align"],
    "td": ["align"],
}


def _normalize_markdown(text: str) -> str:
    value = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    # Unescape only Markdown control characters that sometimes arrive from LLM/API
    # serialization. Ordinary path backslashes remain untouched.
    value = re.sub(r"\\(?=#{1,6}(?:\s|$))", "", value, flags=re.MULTILINE)
    value = re.sub(r"\\([*_`~|\[\]()>])", r"\1", value)
    stripped = value.strip()
    m = re.fullmatch(r"```(?:markdown|md)\s*\n(.*)\n```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if m:
        value = m.group(1)
    return value.strip()


def render_markdown(text: str | None) -> Markup:
    if not text:
        return Markup("")
    html = _MD(_normalize_markdown(text))
    clean = bleach.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        protocols=["http", "https", "mailto"],
        strip=True,
    )
    return Markup(f'<div class="md-rendered">{clean}</div>')
