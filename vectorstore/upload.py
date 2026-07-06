import os
from openai import OpenAI

from utils.retry import openai_with_retry

VECTOR_STORE_NAME = "optibot-support-docs"
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")


def get_client() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def upload_changed_docs(client, vector_store_id: str, changed_items: list[dict], remote_manifest: dict) -> dict:
    """Upload changed docs and attach article metadata as file attributes."""
    replaced = 0

    for item in changed_items:
        existing = remote_manifest.get(str(item["article_id"]))
        if not existing:
            continue
        try:
            openai_with_retry(lambda fid=existing["file_id"]: client.vector_stores.files.delete(
                vector_store_id=vector_store_id,
                file_id=fid,
            ))
            openai_with_retry(lambda fid=existing["file_id"]: client.files.delete(fid))
            replaced += 1
        except Exception as e:
            print(f"Warning: could not delete stale file for article {item['article_id']}: {e}")

    batch_entries = []
    for item in changed_items:
        file_path = os.path.join(DOCS_DIR, f"{item['slug']}.md")
        if not os.path.exists(file_path):
            continue

        with open(file_path, "rb") as f:
            raw_file = openai_with_retry(lambda fh=f: client.files.create(file=fh, purpose="assistants"))

        batch_entries.append({
            "file_id": raw_file.id,
            "attributes": {
                "article_id": str(item["article_id"]),
                "hash": item["hash"],
                "slug": item["slug"],
                "source_url": item["source_url"],
            },
        })

    if batch_entries:
        openai_with_retry(lambda: client.vector_stores.file_batches.create_and_poll(
            vector_store_id=vector_store_id,
            files=batch_entries,
        ))

    vs = openai_with_retry(lambda: client.vector_stores.retrieve(vector_store_id))
    return {
        "uploaded": len(batch_entries),
        "replaced": replaced,
        "total_files_in_store": vs.file_counts.completed,
    }