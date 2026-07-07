import os
import sys
from datetime import datetime, UTC
from time import perf_counter
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

from scraper.convert_to_markdown import article_to_markdown, slugify
from scraper.fetch_articles import fetch_all_articles
from scraper.hashing import hash_article
from vectorstore.remote_manifest import get_remote_manifest
from vectorstore.upload import upload_changed_docs


DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def scrape(client: OpenAI, vector_store_id: str) -> tuple[list[dict], dict]:
    os.makedirs(DOCS_DIR, exist_ok=True)

    print(f"[{now()}] Starting Zendesk synchronization...")

    articles = fetch_all_articles()

    print(f"[{now()}] Fetched {len(articles)} published articles.")

    remote_manifest = get_remote_manifest(client, vector_store_id)

    changed_items = []

    added = 0
    updated = 0
    skipped = 0

    for article in articles:
        article_id = str(article["id"])
        article_hash = hash_article(article)
        slug = slugify(article["title"]) or f"article-{article['id']}"

        existing = remote_manifest.get(article_id)

        if existing and existing.get("hash") == article_hash:
            skipped += 1
            continue

        markdown = article_to_markdown(article)

        with open(
            os.path.join(DOCS_DIR, f"{slug}.md"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(markdown)

        changed_items.append(
            {
                "article_id": article["id"],
                "slug": slug,
                "hash": article_hash,
                "source_url": article["html_url"],
            }
        )

        if existing:
            updated += 1
        else:
            added += 1

    print(
        f"[{now()}] Sync summary | "
        f"fetched={len(articles)} "
        f"added={added} "
        f"updated={updated} "
        f"skipped={skipped}"
    )

    return changed_items, remote_manifest


def run():
    started = perf_counter()

    vector_store_id = os.environ.get("VECTOR_STORE_ID")

    if not vector_store_id:
        raise RuntimeError("VECTOR_STORE_ID environment variable is required")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    changed_items, remote_manifest = scrape(client, vector_store_id)

    if not changed_items:
        duration = perf_counter() - started

        print(
            f"[{now()}] No changes detected. "
            f"Upload skipped. "
            f"duration={duration:.2f}s"
        )
        return

    print(
        f"[{now()}] Uploading {len(changed_items)} changed article(s) "
        f"to OpenAI Vector Store..."
    )

    result = upload_changed_docs(
        client,
        vector_store_id,
        changed_items,
        remote_manifest,
    )

    duration = perf_counter() - started

    print(
        f"[{now()}] Upload completed | "
        f"files_embedded={result['uploaded']} "
        f"estimated_chunks={result['estimated_chunks']} "
        f"files_replaced={result['replaced']} "
        f"vector_store_files={result['total_files_in_store']} "
        f"duration={duration:.2f}s"
    )

    print(f"[{now()}] Daily synchronization completed successfully.")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"[{now()}] Job failed | error={e}", file=sys.stderr)
        sys.exit(1)