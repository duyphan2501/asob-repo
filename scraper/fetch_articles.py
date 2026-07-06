import os
import time
from utils.retry import fetch_with_retry
BASE_URL = os.environ.get("ZENDESK_BASE_URL", "https://support.optisigns.com")
PER_PAGE = 100
MAX_ARTICLES = int(os.environ.get("MAX_ARTICLES", "0"))  # 0 = no limit (production)

def fetch_all_articles():
    """Fetch all published articles from Zendesk Help Center API.
    Handles pagination via `next_page` and basic 429 backoff.
    If MAX_ARTICLES env var is set (>0), stops early once that many
    articles are collected — useful for testing without hammering the
    Zendesk API or, downstream, the OpenAI vector store API.
    Returns list of dicts: id, title, html_url, body, updated_at, section_id
    """
    articles = []
    url = f"{BASE_URL}/api/v2/help_center/en-us/articles.json?per_page={PER_PAGE}&page=1"

    while url:
        data = fetch_with_retry(url)
        for a in data["articles"]:
            if a.get("draft"):
                continue
            articles.append({
                "id": a["id"],
                "title": a["title"],
                "html_url": a["html_url"],
                "body": a.get("body") or "",
                "updated_at": a["updated_at"],
                "section_id": a.get("section_id"),
            })
            if MAX_ARTICLES and len(articles) >= MAX_ARTICLES:
                print(f"MAX_ARTICLES={MAX_ARTICLES} reached, stopping fetch early (test mode).")
                return articles

        url = data.get("next_page")
        if url:
            time.sleep(0.3)

    return articles
