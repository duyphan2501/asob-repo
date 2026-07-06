import os
import time
from openai import RateLimitError
import requests

MAX_RETRY_ATTEMPTS = int(os.environ.get("MAX_RETRY_ATTEMPTS", "5"))

def openai_with_retry(fn, attempt=1):
    """Retry a zero-arg callable on OpenAI 429s with linear backoff.
    Shared by upload.py and ask.py so both survive rate limiting during
    testing without duplicating the same retry loop in each file.
    """
    try:
        return fn()
    except RateLimitError:
        if attempt > MAX_RETRY_ATTEMPTS:
            raise
        wait = attempt * 2
        print(f"Rate limited by OpenAI, retrying in {wait}s (attempt {attempt}/{MAX_RETRY_ATTEMPTS})")
        time.sleep(wait)
        return openai_with_retry(fn, attempt + 1)
    
def fetch_with_retry(url, attempt=1):
    res = requests.get(url, timeout=30)
    if res.status_code == 429 and attempt <= MAX_RETRY_ATTEMPTS:
        retry_after = int(res.headers.get("Retry-After", attempt * 2))
        print(f"Rate limited, retrying in {retry_after}s (attempt {attempt})")
        time.sleep(retry_after)
        return fetch_with_retry(url, attempt + 1)
    res.raise_for_status()
    return res.json()