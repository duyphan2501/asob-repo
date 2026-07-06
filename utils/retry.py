import os
import time
import requests

MAX_RETRY_ATTEMPTS = int(os.environ.get("MAX_RETRY_ATTEMPTS", "5"))
    
def fetch_with_retry(url, attempt=1):
    res = requests.get(url, timeout=30)
    if res.status_code == 429 and attempt <= MAX_RETRY_ATTEMPTS:
        retry_after = int(res.headers.get("Retry-After", attempt * 2))
        print(f"Rate limited, retrying in {retry_after}s (attempt {attempt})")
        time.sleep(retry_after)
        return fetch_with_retry(url, attempt + 1)
    res.raise_for_status()
    return res.json()