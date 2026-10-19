"""Clean the raw Makeup API data and classify each shade.

Reads data/raw/products.json, a copy of the full Makeup API data from the
Kaggle dataset "Herokuapp Makeup Products", keeps lipstick, blush and
eyeshadow, writes data/products.json for the site, and prints a summary.

Run from the repository root:
    python scripts/clean_products.py
"""
import html
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path

import color_rules as rules

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_FILE = DATA_DIR / "raw" / "products.json"
OUTPUT_FILE = DATA_DIR / "products.json"
PRODUCT_TYPES = ["lipstick", "blush", "eyeshadow"]
NO_BRAND = "브랜드 정보 없음"
NO_SHADE_NAME = "이름 없음"
EXAMPLES_PER_SEASON = 5
EXAMPLE_SEED = 42

# D65 reference white (CIE 1931 2-degree observer).
WHITE_X, WHITE_Y, WHITE_Z = 0.95047, 1.00000, 1.08883

IMAGE_WIDTH_SUFFIX = re.compile(r"\s+\d+w$")


# Text cleanup -------------------------------------------------------------

def clean_text(value):
    if value is None:
        return None
    text = str(value)
    # Some values are escaped twice, e.g. "&amp;trade;".
    for _ in range(3):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped
    return text.strip()


def clean_image_link(value):
    if value is None:
        return None
    return IMAGE_WIDTH_SUFFIX.sub("", value.strip())


def clean_hex(value):
    return (value or "").strip().upper()


# Color conversion ---------------------------------------------------------

def srgb_to_linear(channel):
    c = channel / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lab_f(t):
    delta = 6 / 29
    return t ** (1 / 3) if t > delta ** 3 else t / (3 * delta ** 2) + 4 / 29


def hex_to_lab(hex_value):
    r, g, b = (srgb_to_linear(int(hex_value[i:i + 2], 16)) for i in (1, 3, 5))
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    fx, fy, fz = lab_f(x / WHITE_X), lab_f(y / WHITE_Y), lab_f(z / WHITE_Z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


# Classification -----------------------------------------------------------

def classify(hex_value):
    """Return (shade_info, None) or (None, exclusion_reason)."""
    # 1. hex validity
    if not rules.HEX_PATTERN.match(hex_value):
        return None, rules.REASON_INVALID_HEX

    lightness, a, b = hex_to_lab(hex_value)
    chroma = math.hypot(a, b)

    # 2. low chroma, checked before the hue angle exists
    if chroma < rules.MIN_CHROMA:
        return None, rules.REASON_LOW_CHROMA

    hue = math.degrees(math.atan2(b, a)) % 360

    # 3. hue range
    if rules.EXCLUDED_HUE_MIN <= hue < rules.EXCLUDED_HUE_MAX:
        return None, rules.REASON_OUT_OF_HUE

    # 4. warm/cool and season
    if rules.WARM_HUE_MIN <= hue < rules.WARM_HUE_MAX:
        tone = rules.WARM
        season = rules.SPRING if lightness >= rules.LIGHTNESS_SPLIT else rules.AUTUMN
    else:
        tone = rules.COOL
        if lightness >= rules.LIGHTNESS_SPLIT and chroma < rules.CHROMA_SPLIT:
            season = rules.SUMMER
        else:
            season = rules.WINTER

    return {
        "lab_l": round(lightness, 2),
        "lab_c": round(chroma, 2),
        "lab_h": round(hue, 2),
        "tone": tone,
        "season": season,
    }, None


# Pipeline -----------------------------------------------------------------

def pick_examples(candidates, rng):
    """Pick a fixed-seed random sample that mixes product types and brands.

    Shuffle, then take shades whose product type and brand are both new,
    then shades with either one new, then any shade from a new product.
    """
    pool = candidates[:]
    rng.shuffle(pool)
    picked, types, brands, products = [], set(), set(), set()
    tests = [
        lambda c: c["product_type"] not in types and c["brand"] not in brands,
        lambda c: c["product_type"] not in types or c["brand"] not in brands,
        lambda c: True,
    ]
    for test in tests:
        for candidate in pool:
            if len(picked) == EXAMPLES_PER_SEASON:
                return picked
            if candidate["product_id"] in products or not test(candidate):
                continue
            picked.append(candidate)
            types.add(candidate["product_type"])
            brands.add(candidate["brand"])
            products.add(candidate["product_id"])
    return picked


def load_raw():
    if not RAW_FILE.exists():
        raise ValueError(f"{RAW_FILE} is missing.")
    try:
        products = json.loads(RAW_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{RAW_FILE} is not valid JSON: {error}")
    if not isinstance(products, list):
        raise ValueError(f"{RAW_FILE} should hold a JSON list, got {type(products).__name__}.")
    raw = {product_type: [] for product_type in PRODUCT_TYPES}
    for product in products:
        if isinstance(product, dict) and product.get("product_type") in raw:
            raw[product["product_type"]].append(product)
    return raw


def main():
    try:
        raw = load_raw()
    except ValueError as error:
        print(f"FAILED: {error}", file=sys.stderr)
        sys.exit(1)

    output = []
    stats = {}
    reasons = Counter()
    seasons = {product_type: Counter() for product_type in PRODUCT_TYPES}
    candidates = {season: [] for season in rules.SEASONS}

    for product_type, products in raw.items():
        stat = stats[product_type] = Counter()
        stat["raw_products"] = len(products)
        for product in products:
            colors = product.get("product_colors") or []
            if not colors:
                stat["no_colors"] += 1
                continue
            stat["products"] += 1

            brand = clean_text(product.get("brand")) or NO_BRAND
            shades = []
            for color in colors:
                stat["shades"] += 1
                hex_value = clean_hex(color.get("hex_value"))
                info, reason = classify(hex_value)
                if reason != rules.REASON_INVALID_HEX:
                    stat["valid_hex"] += 1
                if reason:
                    reasons[reason] += 1
                    continue
                seasons[product_type][info["season"]] += 1
                shade = {
                    "hex_value": hex_value,
                    "colour_name": clean_text(color.get("colour_name")) or NO_SHADE_NAME,
                    **info,
                }
                shades.append(shade)
                candidates[info["season"]].append({
                    "product_type": product_type,
                    "brand": brand,
                    "product_id": product.get("id"),
                    "name": clean_text(product.get("name")),
                    "shade": shade,
                })

            if shades:
                output.append({
                    "id": product.get("id"),
                    "brand": brand,
                    "name": clean_text(product.get("name")),
                    "product_type": product_type,
                    "image_link": clean_image_link(product.get("image_link")),
                    "product_link": clean_text(product.get("product_link")),
                    "shades": shades,
                })

    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("== 제품군별 제품 수 / 셰이드 수 / 유효한 hex 수 ==")
    print("(제품 수는 product_colors가 있는 제품 기준, 괄호는 원본 수와 셰이드 없어 제외된 수)")
    for product_type in PRODUCT_TYPES:
        stat = stats[product_type]
        print(f"{product_type:10} 제품 {stat['products']:4} (원본 {stat['raw_products']}, 셰이드 없음 {stat['no_colors']})"
              f"  셰이드 {stat['shades']:5}  유효 hex {stat['valid_hex']:5}")

    print("\n== 셰이드 제외 사유별 개수 ==")
    for reason in (rules.REASON_INVALID_HEX, rules.REASON_LOW_CHROMA, rules.REASON_OUT_OF_HUE):
        print(f"{reason}: {reasons[reason]}")

    print("\n== 제품군별·계절별 셰이드 개수 ==")
    print(f"{'':10} " + " ".join(f"{season:>12}" for season in rules.SEASONS) + f" {'합계':>6}")
    for product_type in PRODUCT_TYPES:
        counts = seasons[product_type]
        print(f"{product_type:10} " + " ".join(f"{counts[season]:12}" for season in rules.SEASONS)
              + f" {sum(counts.values()):6}")

    print(f"\n== 계절별 예시 셰이드 (seed {EXAMPLE_SEED} 무작위 {EXAMPLES_PER_SEASON}개) ==")
    rng = random.Random(EXAMPLE_SEED)
    for season in rules.SEASONS:
        pool = candidates[season]
        picked = pick_examples(pool, rng)
        print(season)
        for c in picked:
            shade = c["shade"]
            print(f"  {c['product_type']:9} | {c['brand']} | {c['name']} | {shade['colour_name']} | {shade['hex_value']}")
        types_available = len({c["product_type"] for c in pool})
        brands_available = len({c["brand"] for c in pool})
        types_picked = len({c["product_type"] for c in picked})
        brands_picked = len({c["brand"] for c in picked})
        if (len(picked) < EXAMPLES_PER_SEASON
                or types_picked < min(types_available, len(PRODUCT_TYPES))
                or brands_picked < min(brands_available, EXAMPLES_PER_SEASON)):
            print(f"  ! 다양성 부족: {len(picked)}개, 제품군 {types_picked}/{types_available}, "
                  f"브랜드 {brands_picked}/{brands_available}")

    print(f"\n{len(output)} products written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
