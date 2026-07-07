import re
from bs4 import BeautifulSoup
from markdownify import MarkdownConverter


class OptiSignsConverter(MarkdownConverter):
    """Custom markdownify converter with Zendesk-specific cleanup."""

    def convert_div(self, el, text, **kwargs):
        classes = " ".join(el.get("class", []))
        if re.search(r"callout|notice|warning|note", classes, re.I):
            quoted = "\n".join(f"> {line}" for line in text.strip().splitlines())
            return f"\n{quoted}\n\n"
        return text

    def convert_p(self, el, text, **kwargs):
        children = [c for c in el.children if getattr(c, "name", None) or str(c).strip()]
        if (
            len(children) == 1
            and getattr(children[0], "name", None) == "strong"
            and len(el.get_text(strip=True)) < 80
        ):
            heading_text = el.get_text(strip=True)
            return f"\n### {heading_text}\n\n"
        return super().convert_p(el, text, **kwargs)


def article_to_markdown(article: dict) -> str:
    cleaned_html = _strip_noise(article["body"])
    markdown = OptiSignsConverter(heading_style="ATX", code_language="").convert(cleaned_html).strip()

    frontmatter = "\n".join([
        "---",
        f'title: {_escape_yaml(article["title"])}',
        f'source_url: {article["html_url"]}',
        f'updated_at: {article["updated_at"]}',
        f'article_id: {article["id"]}',
        "---",
        "",
    ])

    return f'{frontmatter}## {article["title"]}\n\n{markdown}\n'


def _strip_noise(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = str(soup).replace("&nbsp;", " ")
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()


def _escape_yaml(value: str) -> str:
    return str(value).replace('"', '\\"')


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:80]