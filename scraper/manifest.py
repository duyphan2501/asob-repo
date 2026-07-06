import json
import hashlib
import os

MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "..", "manifest.json")

def load_manifest() -> dict:
    if not os.path.exists(MANIFEST_PATH):
        return {}
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(manifest: dict) -> None:
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def hash_article(article: dict) -> str:
    # Hash the raw HTML body, NOT the post-processed markdown, so the hash
    # only changes when the source content actually changes.
    return hashlib.sha256(article["body"].encode("utf-8")).hexdigest()