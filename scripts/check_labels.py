"""Compare the warm/cool rule with manufacturer labels in shade names.

A small reference check, not a validation. The labels are the
manufacturer's own words in the shade name (Blue-Toned, Yellow-Toned,
Blue-Red, Warm, Cool, Warm Tones, Cool Tones) and only say warm or cool,
so only warm/cool is scored. Pure Anada eyeshadow names carry (C), (W)
and (N); since the same brand spells out Cool and Warm on its blushes,
(C) is read as Cool and (W) as Warm, and the table says so. The season
is shown for reference. Shades whose name only might describe the
undertone, neutral shades and pearl descriptions are listed in EXCLUDED
with the reason and are not scored. Shades the rules exclude from
classification (e.g. yellow hues) are marked "분류 제외" and not scored.
Every lipstick, blush and eyeshadow shade in the raw data whose name
contains a label word, a Pure Anada abbreviation, Neutral or (N), or
"Blue Pearl" must be in TARGETS or EXCLUDED; any other is reported.
Shades are classified with clean_products.classify(), which reads every
threshold from color_rules.py; nothing here changes those rules or
data/products.json.

Run from the repository root:
    python scripts/check_labels.py
"""
import json
import math
import re
import sys

import color_rules as rules
from clean_products import (PRODUCT_TYPES, RAW_FILE, OUTPUT_FILE, classify, clean_hex,
                            clean_text, hex_to_lab)

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
    ("Pure Anada", "Hibiscus", "#8B2D46", rules.COOL),
    ("Pure Anada", "Mango Ice", "#F69476", rules.WARM),
    ("Pure Anada", "Berry Blush", "#A25156", rules.COOL),
    ("Pure Anada", "Apricot Blush", "#AC564D", rules.WARM),
    ("NYX", "Boho Chic", "#E4878D", rules.COOL),
    ("NYX", "S.O.S", "#B99D87", rules.COOL),
    ("Cargo Cosmetics", "Oz", "#E3AF50", rules.WARM),
    ("Pure Anada", "Lavender Grey", "#A5A1A2", rules.COOL),
    ("Pure Anada", "Moonstone", "#656D78", rules.COOL),
    ("Pure Anada", "Ocean Mist", "#274A65", rules.COOL),
    ("Pure Anada", "Purple Pride", "#69577F", rules.COOL),
    ("Pure Anada", "Close to Cocoa", "#865945", rules.WARM),
    ("Pure Anada", "Copper", "#702A1A", rules.WARM),
]

# (brand, shade name, hex, reason) for names that may not describe the
# undertone. Not scored.
AMBIGUOUS = "언더톤 설명인지 애매함"
NEUTRAL = "뉴트럴: 웜/쿨 라벨이 아님"
EXCLUDED = [
    ("NYX", "Cool Intentions", "#864B45", f"{AMBIGUOUS}: 'Cool'이 이름의 일부"),
    ("Maybelline", "Warm Me Up", "#CA6E6B", f"{AMBIGUOUS}: 'Warm'이 이름의 일부"),
    ("Maybelline", "Too Cool", "#D3CFCC", f"{AMBIGUOUS}: 'Cool'이 이름의 일부"),
    ("Clinique", "Golden Brandy", "#BE453E", f"{AMBIGUOUS}: 'Golden'은 기준 표현 아님"),
    ("Dr. Hauschka", "Golden Earth", "#F8C4AA", f"{AMBIGUOUS}: 'Golden'은 기준 표현 아님"),
    ("Dr. Hauschka", "Golden Sand", "#F7DBB6", f"{AMBIGUOUS}: 'Golden'은 기준 표현 아님"),
    ("NYX", "Summer Love", "#DDA1A1", f"{AMBIGUOUS}: 'Pink Undertones'는 웜/쿨이 아님"),
    ("Pure Anada", "Black Tie", "#373030", f"{NEUTRAL}: (N)"),
    ("Pure Anada", "Champagne", "#D7AE7A", f"{NEUTRAL}: (N)"),
    ("Pure Anada", "Cornflower", "#6D8B93", f"{NEUTRAL}: (N)"),
    ("Pure Anada", "Deep Plum", "#4E3E3E", f"{NEUTRAL}: (N)"),
    ("Pure Anada", "Grenada Green", "#377A3C", f"{NEUTRAL}: (N)"),
    ("Pure Anada", "Peach Freeze", "#EBC8B4", f"{NEUTRAL}: (N)"),
    ("Pure Anada", "Autum", "#B5665F", f"{NEUTRAL}: Neutral"),
    ("Pure Anada", "Twig Blush", "#9B593E", f"{NEUTRAL}: Neutral Tones"),
    ("NYX", "Fig", "#E46A79", f"{NEUTRAL}: Neutral Pink"),
    ("NYX", "Pure Nude", "#E6A28E", f"{NEUTRAL}: Neutral Baby Pink"),
    ("Clinique", "Neutral Territory", "#E0C4AB,#5F574F", f"{NEUTRAL}: Neutral이 이름의 일부"),
    ("Wet n Wild", "Fuchsia with Blue Pearl", "#BF1790", "펄 색 설명: 'Blue Pearl'은 언더톤이 아님"),
]

# Manufacturer wording that carries the warm/cool label.
LABEL_WORDS = re.compile(r"Blue-Toned|Yellow-Toned|Blue-Red|(?:Warm|Cool)(?: Tones)?", re.IGNORECASE)

# Pure Anada abbreviations, read as Cool and Warm (see the module docstring).
ABBREVIATION_BRAND = "pure anada"
ABBREVIATIONS = re.compile(r"\((C|W)\)")
ABBREVIATION_WORDS = {"C": "Cool", "W": "Warm"}

# Other wording checked so every such shade is in TARGETS or EXCLUDED.
NEUTRAL_OR_PEARL_WORDS = re.compile(r"\bNeutral\b|\(N\)|Blue Pearl", re.IGNORECASE)

TONE_LABELS = {rules.WARM: "웜", rules.COOL: "쿨"}
NOT_CLASSIFIED = "분류 제외"


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


def label_words(brand, colour_name):
    """Manufacturer label wording in the shade name, abbreviations marked as interpreted."""
    words = LABEL_WORDS.findall(colour_name)
    if brand.lower() == ABBREVIATION_BRAND:
        words += [f"({letter})→{ABBREVIATION_WORDS[letter]} 해석"
                  for letter in ABBREVIATIONS.findall(colour_name)]
    return ", ".join(words) or "-"


def is_candidate(brand, colour_name):
    if LABEL_WORDS.search(colour_name) or NEUTRAL_OR_PEARL_WORDS.search(colour_name):
        return True
    return brand.lower() == ABBREVIATION_BRAND and bool(ABBREVIATIONS.search(colour_name))


def unlisted_candidates(products, found):
    """Candidate shade names that are in neither TARGETS nor EXCLUDED."""
    missing = []
    for product in products:
        if not isinstance(product, dict) or product.get("product_type") not in PRODUCT_TYPES:
            continue
        for color in product.get("product_colors") or []:
            colour_name = clean_text(color.get("colour_name")) or ""
            brand = clean_text(product.get("brand")) or ""
            if is_candidate(brand, colour_name) and (product.get("id"), colour_name) not in found:
                missing.append(f"id {product.get('id')} {clean_text(product.get('brand'))} | "
                               f"{colour_name} | {clean_hex(color.get('hex_value'))}")
    return missing


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

    scored = matched = compared = not_classified = 0
    mismatches = []
    found = set()
    for brand, name, hex_value, label_tone in TARGETS:
        source = find_source(products, brand, name, hex_value)
        if source:
            product, colour_name = source
            found.add((product.get("id"), colour_name))
            origin = f"id {product.get('id')} {clean_text(product.get('name'))}"
            words = label_words(brand, colour_name)
        else:
            colour_name, origin, words = None, NOT_FOUND, "-"

        info, reason = classify(hex_value)
        if reason:
            if source:
                not_classified += 1
            lab = ["-", "-", "-"]
            if reason != rules.REASON_INVALID_HEX:
                lightness, a, b = hex_to_lab(hex_value)
                lab = [f"{lightness:.2f}", f"{math.hypot(a, b):.2f}",
                       f"{math.degrees(math.atan2(b, a)) % 360:.2f}"]
            values = lab + [f"제외({reason})", NOT_CLASSIFIED, "-"]
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

    print(f"\n웜/쿨 일치: {matched}/{scored} (출처가 확인되고 분류된 셰이드만 채점)")
    print(f"{NOT_CLASSIFIED}: {not_classified}개 (규칙상 분류 대상이 아니어서 채점하지 않음)")
    print("계절은 제조사 라벨에 없으므로 채점하지 않음.")
    if mismatches:
        print("! data/products.json에 저장된 계절과 재계산 결과가 다름:")
        for line in mismatches:
            print(f"  {line}")
    else:
        print(f"data/products.json에 저장된 계절과 재계산 결과 비교: {compared}개 모두 같음.")

    print("\n== 비교에서 제외한 셰이드 (채점하지 않음) ==")
    print("| 셰이드 | hex | 출처 | 제외 이유 |")
    print("|---|---|---|---|")
    for brand, name, hex_value, reason in EXCLUDED:
        source = find_source(products, brand, name, hex_value)
        if source:
            product, colour_name = source
            found.add((product.get("id"), colour_name))
            origin = f"id {product.get('id')} {clean_text(product.get('name'))} ({colour_name})"
        else:
            origin = NOT_FOUND
        print(f"| {brand} {name} | {hex_value} | {origin} | {reason} |")

    missing = unlisted_candidates(products, found)
    if missing:
        print("\n! 이름에 라벨·약어·뉴트럴·펄 표현이 있지만 비교 대상에도 제외 목록에도 없는 셰이드:")
        for line in missing:
            print(f"  {line}")
    else:
        print("\n이름에 라벨·약어·뉴트럴·펄 표현이 있는 립스틱·블러셔·아이섀도 셰이드는 "
              "모두 비교 대상 또는 제외 목록에 있음.")


if __name__ == "__main__":
    main()
