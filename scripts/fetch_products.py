"""Download lipstick, blush and eyeshadow products from the Makeup API.

2026-10 현재 API가 503을 반환해 사용하지 않음. 원본은 Kaggle 사본
(data/raw/products.json, "Herokuapp Makeup Products")이며
scripts/clean_products.py가 그 파일을 읽는다.

Each product type is saved as-is to data/raw/<product_type>.json.
If a request fails, nothing is written for that type and the script
exits with status 1. It never writes placeholder data.

Run from the repository root:
    python scripts/fetch_products.py
"""
import json
import sys
import time
from pathlib import Path

import requests

API_URL = "https://makeup-api.herokuapp.com/api/v1/products.json"
PRODUCT_TYPES = ["lipstick", "blush", "eyeshadow"]
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5


def get_with_retry(product_type):
    for attempt in range(1, ATTEMPTS + 1):
        try:
            response = requests.get(API_URL, params={"product_type": product_type}, timeout=60)
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            if attempt == ATTEMPTS:
                raise
            print(f"{product_type}: attempt {attempt} failed ({error}), retrying", file=sys.stderr)
            time.sleep(RETRY_DELAY_SECONDS * attempt)


def fetch(product_type):
    response = get_with_retry(product_type)
    products = response.json()
    if not isinstance(products, list):
        raise ValueError(f"expected a JSON list, got {type(products).__name__}")
    return products


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    failed = []
    for product_type in PRODUCT_TYPES:
        try:
            products = fetch(product_type)
        except (requests.RequestException, ValueError) as error:
            print(f"FAILED {product_type}: {error}", file=sys.stderr)
            failed.append(product_type)
            continue
        path = RAW_DIR / f"{product_type}.json"
        path.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{product_type}: {len(products)} products -> {path}")
    if failed:
        print(f"Collection failed for: {', '.join(failed)}. No data was invented.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
