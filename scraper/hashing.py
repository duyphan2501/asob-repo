import hashlib

def hash_article(article: dict) -> str:
    return hashlib.sha256(article["body"].encode("utf-8")).hexdigest()