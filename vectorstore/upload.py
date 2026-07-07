import math
import os
import tiktoken
from openai import OpenAI

from utils.retry import openai_with_retry

VECTOR_STORE_NAME = "optibot-support-docs"
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")

ENCODING = tiktoken.get_encoding("cl100k_base")

# CHUNK_SIZE_TOKENS / CHUNK_OVERLAP_TOKENS: set both to override OpenAI's
# "auto" strategy (800/400) with a custom "static" one. Leave unset to
# keep auto. Kept as the single source of truth for both the actual
# upload request AND the local chunk-count estimate below, so the two
# never drift out of sync with each other.
CUSTOM_CHUNK_SIZE = os.environ.get("CHUNK_SIZE_TOKENS")
CUSTOM_CHUNK_OVERLAP = os.environ.get("CHUNK_OVERLAP_TOKENS")

if CUSTOM_CHUNK_SIZE and CUSTOM_CHUNK_OVERLAP:
    ESTIMATE_CHUNK_SIZE = int(CUSTOM_CHUNK_SIZE)
    ESTIMATE_CHUNK_OVERLAP = int(CUSTOM_CHUNK_OVERLAP)
    if ESTIMATE_CHUNK_OVERLAP > ESTIMATE_CHUNK_SIZE // 2:
        raise ValueError("CHUNK_OVERLAP_TOKENS must not exceed half of CHUNK_SIZE_TOKENS")
    CHUNKING_STRATEGY = {
        "type": "static",
        "static": {
            "max_chunk_size_tokens": ESTIMATE_CHUNK_SIZE,
            "chunk_overlap_tokens": ESTIMATE_CHUNK_OVERLAP,
        },
    }
else:
   # Approximation based on OpenAI's current automatic chunking behavior.
    # The API does not expose the actual chunk count when using auto chunking.
    ESTIMATE_CHUNK_SIZE = 800
    ESTIMATE_CHUNK_OVERLAP = 400
    CHUNKING_STRATEGY = None  # omit the field entirely -> OpenAI uses auto

STEP = ESTIMATE_CHUNK_SIZE - ESTIMATE_CHUNK_OVERLAP


def estimate_chunks(file_path: str) -> int:
    """Estimate chunk count for reporting purposes only — OpenAI does not
    return an exact chunk count via the API, so this approximates what
    the configured chunking strategy (auto or custom static) would
    produce, using the same token encoding OpenAI's models use (cl100k_base)."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    tokens = len(ENCODING.encode(text))

    if tokens <= ESTIMATE_CHUNK_SIZE:
        return 1

    return math.ceil((tokens - ESTIMATE_CHUNK_SIZE) / STEP) + 1


def get_client() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def upload_changed_docs(
    client,
    vector_store_id: str,
    changed_items: list[dict],
    remote_manifest: dict,
) -> dict:
    """Upload changed Markdown files to the vector store.

    Note: OpenAI performs the actual chunking server-side. `estimated_chunks`
    below is a local approximation for logging/reporting only, not the
    real count.
    """
    replaced = 0
    estimated_chunks = 0

    # Delete stale files for anything being updated (not new).
    for item in changed_items:
        existing = remote_manifest.get(str(item["article_id"]))
        if not existing:
            continue
        try:
            openai_with_retry(lambda fid=existing["file_id"]: client.vector_stores.files.delete(
                vector_store_id=vector_store_id, file_id=fid,
            ))
            openai_with_retry(lambda fid=existing["file_id"]: client.files.delete(fid))
            replaced += 1
        except Exception as e:
            print(f"Warning: could not delete stale file for article {item['article_id']}: {e}")

    # Upload changed files, collect batch entries with attributes.
    batch_entries = []
    for item in changed_items:
        file_path = os.path.join(DOCS_DIR, f"{item['slug']}.md")
        if not os.path.exists(file_path):
            continue

        estimated_chunks += estimate_chunks(file_path)

        with open(file_path, "rb") as f:
            raw_file = openai_with_retry(lambda fh=f: client.files.create(file=fh, purpose="assistants"))

        entry = {
            "file_id": raw_file.id,
            "attributes": {
                "article_id": str(item["article_id"]),
                "hash": item["hash"],
                "slug": item["slug"],
                "source_url": item["source_url"],
            },
        }
        if CHUNKING_STRATEGY:
            entry["chunking_strategy"] = CHUNKING_STRATEGY
        batch_entries.append(entry)

    if batch_entries:
        openai_with_retry(lambda: client.vector_stores.file_batches.create_and_poll(
            vector_store_id=vector_store_id,
            files=batch_entries,
        ))

    vs = openai_with_retry(lambda: client.vector_stores.retrieve(vector_store_id))

    return {
        "uploaded": len(batch_entries),  
        "replaced": replaced,                       
        "estimated_chunks": estimated_chunks,
        "total_files_in_store": vs.file_counts.completed,
    }