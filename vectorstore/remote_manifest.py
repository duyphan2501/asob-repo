from utils.retry import openai_with_retry


def get_remote_manifest(client, vector_store_id: str) -> dict:
    """Rebuild the in-memory manifest from file attributes stored in the vector store."""
    manifest = {}
    after = None

    while True:
        page = openai_with_retry(lambda a=after: client.vector_stores.files.list(
            vector_store_id=vector_store_id,
            limit=100,
            after=a,
        ))
        for item in page.data:
            attrs = item.attributes or {}
            article_id = attrs.get("article_id")
            if article_id:
                manifest[str(article_id)] = {
                    "file_id": item.id,
                    "hash": attrs.get("hash"),
                    "slug": attrs.get("slug"),
                    "source_url": attrs.get("source_url"),
                }
        if not getattr(page, "has_more", False):
            break
        after = page.data[-1].id

    return manifest