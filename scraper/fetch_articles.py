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

    # --- GIAI ĐOẠN 1: Ưu tiên lấy các bài theo QUERY ---
    if SEARCH_QUERY:
        print(f"Phase 1: Fetching articles matching query '{SEARCH_QUERY}'...")
        # Sử dụng API Search của Zendesk
        url = f"{BASE_URL}/api/v2/help_center/articles/search.json?query={SEARCH_QUERY}&per_page={PER_PAGE}&page=1"
        
        while url:
            data = fetch_with_retry(url)
            # API Search trả về mảng kết quả trong key 'results'
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

                # Dừng sớm nếu chế độ giới hạn số lượng đã thỏa mãn
                if MAX_ARTICLES and len(articles) >= MAX_ARTICLES:
                    print(f"Reached MAX_ARTICLES={MAX_ARTICLES} during Phase 1.")
                    return articles

            url = data.get("next_page")
            if url:
                time.sleep(0.3)
        print(f"Phase 1 finished. Collected {len(articles)} targeted articles.")

    # --- GIAI ĐOẠN 2: Lấy các bài còn lại nếu chưa đủ số lượng ---
    # Điều kiện chạy tiếp: Không giới hạn (MAX_ARTICLES=0) HOẶC số lượng hiện tại vẫn nhỏ hơn MAX_ARTICLES
    if not MAX_ARTICLES or len(articles) < MAX_ARTICLES:
        remaining_needed = MAX_ARTICLES - len(articles) if MAX_ARTICLES else "unlimited"
        print(f"Phase 2: Fetching remaining articles (Needs: {remaining_needed})...")
        
        url = f"{BASE_URL}/api/v2/help_center/en-us/articles.json?per_page={PER_PAGE}&page=1"
        
        while url:
            data = fetch_with_retry(url)
            # API List thông thường trả về mảng kết quả trong key 'articles'
            for a in data.get("articles", []):
                if a.get("draft") or a["id"] in seen_ids:
                    continue  # Bỏ qua nếu là bản nháp hoặc đã được lấy ở Phase 1
                
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
                    print(f"Reached MAX_ARTICLES={MAX_ARTICLES} during Phase 2.")
                    return articles

            url = data.get("next_page")
            if url:
                time.sleep(0.3)

    return articles
