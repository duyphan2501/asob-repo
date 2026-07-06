import os
import sys

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

from scraper.fetch_articles import fetch_all_articles
from scraper.convert_to_markdown import article_to_markdown, slugify
from scraper.manifest import hash_article
from vectorstore.remote_manifest import get_remote_manifest
from vectorstore.upload import upload_changed_docs

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")


def scrape(client: OpenAI, vector_store_id: str) -> tuple[list[dict], dict]:
    """Fetch docs, compare against the remote manifest rebuilt from vector-store attributes."""
    os.makedirs(DOCS_DIR, exist_ok=True)

    print("Fetching articles from Zendesk...")
    articles = fetch_all_articles()
    print(f"Fetched {len(articles)} published articles.")

    remote_manifest = get_remote_manifest(client, vector_store_id)
    changed_items = []
    added = updated = skipped = 0

    for article in articles:
        article_id = str(article["id"])
        h = hash_article(article)
        slug = slugify(article["title"]) or f"article-{article['id']}"
        existing = remote_manifest.get(article_id)

        if existing and existing.get("hash") == h:
            skipped += 1
            continue

        markdown = article_to_markdown(article)
        with open(os.path.join(DOCS_DIR, f"{slug}.md"), "w", encoding="utf-8") as f:
            f.write(markdown)

        changed_items.append({
            "article_id": article["id"],
            "slug": slug,
            "hash": h,
            "source_url": article["html_url"],
        })

        if existing:
            updated += 1
        else:
            added += 1

    print(f"Scrape done. added={added} updated={updated} skipped={skipped}")
    return changed_items, remote_manifest


def run():
    vector_store_id = os.environ.get("VECTOR_STORE_ID")
    if not vector_store_id:
        raise RuntimeError("VECTOR_STORE_ID environment variable is required")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    changed_items, remote_manifest = scrape(client, vector_store_id)

    if not changed_items:
        print("No new/updated articles — skipping vector store upload.")
        return

    print(f"Uploading {len(changed_items)} changed doc(s) to vector store...")
    result = upload_changed_docs(client, vector_store_id, changed_items, remote_manifest)
    print(
        f"Upload done. vector_store_id={vector_store_id} "
        f"uploaded={result['uploaded']} replaced={result['replaced']} "
        f"total_files_in_store={result['total_files_in_store']}"
    )


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"Job failed: {e}", file=sys.stderr)
        sys.exit(1)