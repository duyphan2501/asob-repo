import os
import time
from utils.retry import fetch_with_retry

BASE_URL = os.environ.get("ZENDESK_BASE_URL", "https://support.optisigns.com")
PER_PAGE = 100
MAX_ARTICLES = int(os.environ.get("MAX_ARTICLES", "0")) 
SEARCH_QUERY = os.environ.get("SEARCH_QUERY", "").strip() 


def fetch_all_articles():
    """Fetch articles from Zendesk Help Center.
    
    1. First prioritizes articles matching SEARCH_QUERY via Search API.
    2. If MAX_ARTICLES is not reached (or is 0), fetches remaining articles
       via standard List API, skipping duplicates.
    """
    articles = []
    seen_ids = set()

    if SEARCH_QUERY:
        url = f"{BASE_URL}/api/v2/help_center/articles/search.json?query={SEARCH_QUERY}&per_page={PER_PAGE}&page=1"
        
        while url:
            data = fetch_with_retry(url)
            for a in data.get("results", []):
                if a.get("draft") or a["id"] in seen_ids:
                    continue
                
                articles.append({
                    "id": a["id"],
                    "title": a["title"],
                    "html_url": a["html_url"],
                    "body": a.get("body") or "",
                    "updated_at": a["updated_at"],
                    "section_id": a.get("section_id"),
                })
                seen_ids.add(a["id"])

                if MAX_ARTICLES and len(articles) >= MAX_ARTICLES:
                    return articles

            url = data.get("next_page")
            if url:
                time.sleep(0.3)

    if not MAX_ARTICLES or len(articles) < MAX_ARTICLES:
        url = f"{BASE_URL}/api/v2/help_center/en-us/articles.json?per_page={PER_PAGE}&page=1"
        
        while url:
            data = fetch_with_retry(url)
            for a in data.get("articles", []):
                if a.get("draft") or a["id"] in seen_ids:
                    continue  
                
                articles.append({
                    "id": a["id"],
                    "title": a["title"],
                    "html_url": a["html_url"],
                    "body": a.get("body") or "",
                    "updated_at": a["updated_at"],
                    "section_id": a.get("section_id"),
                })
                seen_ids.add(a["id"])

                if MAX_ARTICLES and len(articles) >= MAX_ARTICLES:
                    return articles

            url = data.get("next_page")
            if url:
                time.sleep(0.3)

    return articles
