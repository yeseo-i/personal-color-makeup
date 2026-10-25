"""Compare the warm/cool rule with manufacturer labels for a few shades.

A small reference check, not a validation. The labels are the
manufacturer's own words in the shade name (Blue-Toned, Yellow-Toned,
Warm, ...) and only say warm or cool, so only warm/cool is scored. The
season is shown for reference. Shades are classified with
clean_products.classify(), which reads every threshold from
color_rules.py; nothing here changes those rules or data/products.json.

Run from the repository root:
    python scripts/check_labels.py
"""
import json
import re
import sys

import color_rules as rules
from clean_products import RAW_FILE, OUTPUT_FILE, classify, clean_hex, clean_text

NOT_FOUND = "출처 확인 불가"

# (brand, shade name, hex, manufacturer label tone)
TARGETS = [
    ("NYX", "Chic", "#FF898F", rules.COOL),
    ("NYX", "Fire", "#DC002C", rules.COOL),
    ("NYX", "Flower", "#E96384", rules.COOL),
    ("NYX", "Power", "#CD859D", rules.COOL),
    ("NYX", "Hot Red", "#AA202E", rules.COOL),
    ("NYX", "Stella", "#F58E7C", rules.WARM),
    ("NYX", "Matte Warm Brown", "#512D2D", rules.WARM),
    ("Fenty", "Shawty", "#894134", rules.WARM),
]

# Manufacturer wording that carries the warm/cool label.
LABEL_WORDS = re.compile(r"Blue-Toned|Yellow-Toned|Blue-Red|Warm|Cool", re.IGNORECASE)

TONE_LABELS = {rules.WARM: "웜", rules.COOL: "쿨"}


def load_raw_products():
    if not RAW_FILE.exists():
        raise ValueError(f"{RAW_FILE} is missing.")
    try:
        products = json.loads(RAW_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{RAW_FILE} is not valid JSON: {error}")
    if not isinstance(products, list):
        raise ValueError(f"{RAW_FILE} should hold a JSON list, got {type(products).__name__}.")
    return products


def find_source(products, brand, name, hex_value):
    """Return (product, colour_name) whose brand, hex and shade name all match, or None."""
    for product in products:
        if not isinstance(product, dict):
            continue
        if (clean_text(product.get("brand")) or "").lower() != brand.lower():
            continue
        for color in product.get("product_colors") or []:
            colour_name = clean_text(color.get("colour_name")) or ""
            if clean_hex(color.get("hex_value")) == hex_value and \
                    colour_name.lower().startswith(name.lower()):
                return product, colour_name
    return None


def stored_season(output, hex_value, colour_name):
    """Season stored in data/products.json for this shade, or None."""
    for product in output:
        for shade in product["shades"]:
            if shade["hex_value"] == hex_value and shade["colour_name"] == colour_name:
                return shade["season"]
    return None


def main():
    try:
        products = load_raw_products()
    except ValueError as error:
        print(f"FAILED: {error}", file=sys.stderr)
        sys.exit(1)
    output = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))

    print("== 제조사 라벨 비교 (소규모 참고용, 규칙 검증 아님) ==")
    print("| 셰이드 | hex | 출처 | 제조사 표현 | 라벨 | L* | C* | h° | 규칙 판정 | 일치 | 계절(참고) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")

    scored = matched = compared = 0
    mismatches = []
    for brand, name, hex_value, label_tone in TARGETS:
        source = find_source(products, brand, name, hex_value)
        if source:
            product, colour_name = source
            origin = f"id {product.get('id')} {clean_text(product.get('name'))}"
            words = ", ".join(LABEL_WORDS.findall(colour_name)) or "-"
        else:
            colour_name, origin, words = None, NOT_FOUND, "-"

        info, reason = classify(hex_value)
        if reason:
            values = ["-", "-", "-", f"제외({reason})", "-", "-"]
        else:
            same = info["tone"] == label_tone
            if source:
                scored += 1
                matched += same
            mark = ("O" if same else "X") if source else "채점 제외"
            values = [f"{info['lab_l']:.2f}", f"{info['lab_c']:.2f}", f"{info['lab_h']:.2f}",
                      TONE_LABELS[info["tone"]], mark, info["season"]]
            if source:
                stored = stored_season(output, hex_value, colour_name)
                if stored is not None:
                    compared += 1
                if stored is not None and stored != info["season"]:
                    mismatches.append(f"{brand} {name}: products.json {stored}, 재계산 {info['season']}")

        print(f"| {brand} {name} | {hex_value} | {origin} | {words} | {TONE_LABELS[label_tone]} | "
              + " | ".join(values) + " |")

    print(f"\n웜/쿨 일치: {matched}/{scored} (출처가 확인된 셰이드만 채점)")
    print("계절은 제조사 라벨에 없으므로 채점하지 않음.")
    if mismatches:
        print("! data/products.json에 저장된 계절과 재계산 결과가 다름:")
        for line in mismatches:
            print(f"  {line}")
    else:
        print(f"data/products.json에 저장된 계절과 재계산 결과 비교: {compared}개 모두 같음.")


if __name__ == "__main__":
    main()
