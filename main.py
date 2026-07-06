import os
import sys

from dotenv import load_dotenv
load_dotenv()   

from scraper.fetch_articles import fetch_all_articles
from scraper.convert_to_markdown import article_to_markdown, slugify
from scraper.manifest import load_manifest, save_manifest, hash_article

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")

def scrape() -> list[str]:
    """Returns list of slugs that were added or updated this run."""
    os.makedirs(DOCS_DIR, exist_ok=True)

    print("Fetching articles from Zendesk...")
    articles = fetch_all_articles()
    print(f"Fetched {len(articles)} published articles.")

    manifest = load_manifest()
    new_manifest = {}
    changed_slugs = []
    added = updated = skipped = 0

    for article in articles:
        h = hash_article(article)
        slug = slugify(article["title"]) or f'article-{article["id"]}'
        existing = manifest.get(str(article["id"]))

        new_manifest[str(article["id"])] = {
            "slug": slug,
            "hash": h,
            "source_url": article["html_url"],
            "updated_at": article["updated_at"],
        }

        if existing and existing["hash"] == h:
            skipped += 1
            continue

        markdown = article_to_markdown(article)
        with open(os.path.join(DOCS_DIR, f"{slug}.md"), "w", encoding="utf-8") as f:
            f.write(markdown)

        changed_slugs.append(slug)
        if existing:
            updated += 1
        else:
            added += 1

    save_manifest(new_manifest)
    print(f"Scrape done. added={added} updated={updated} skipped={skipped}")
    return changed_slugs

def run():
    changed_slugs = scrape()

    if not changed_slugs:
        print("No new/updated articles")
        return

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"Job failed: {e}", file=sys.stderr)
        sys.exit(1)