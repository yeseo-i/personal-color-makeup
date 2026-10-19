"""Project-only provisional rules for classifying shades.

WARNING: every threshold in this file is a temporary value chosen for this
project. None of them has been validated against research, expert
judgement, or user testing. Do not treat the warm/cool or season labels
as established color science. Change the values here and rerun
scripts/clean_products.py; no other file holds these numbers.

Classification order:
  1. hex validity  2. low chroma  3. hue range  4. warm/cool and season
"""
import re

# 1. Hex validity: only #RRGGBB is accepted (after strip and uppercase).
HEX_PATTERN = re.compile(r"^#[0-9A-F]{6}$")

# 2. Low chroma: shades with C* below this are excluded before the hue
#    angle is computed. (Provisional, unvalidated.)
MIN_CHROMA = 10

# 3. Hue range to exclude (yellow, green, blue families):
#    EXCLUDED_HUE_MIN <= h < EXCLUDED_HUE_MAX. (Provisional, unvalidated.)
EXCLUDED_HUE_MIN = 75
EXCLUDED_HUE_MAX = 290

# 4. Warm: WARM_HUE_MIN <= h < WARM_HUE_MAX.
#    Cool: h < WARM_HUE_MIN or h >= EXCLUDED_HUE_MAX. (Provisional, unvalidated.)
WARM_HUE_MIN = 30
WARM_HUE_MAX = 75

#    Season split by lightness and chroma. (Provisional, unvalidated.)
#    Spring warm: warm and L* >= LIGHTNESS_SPLIT
#    Autumn warm: warm and L* <  LIGHTNESS_SPLIT
#    Summer cool: cool and L* >= LIGHTNESS_SPLIT and C* < CHROMA_SPLIT
#    Winter cool: cool and (L* < LIGHTNESS_SPLIT or C* >= CHROMA_SPLIT)
LIGHTNESS_SPLIT = 55
CHROMA_SPLIT = 50

# Exclusion reason labels used in the report.
REASON_INVALID_HEX = "잘못된 hex"
REASON_LOW_CHROMA = "저채도"
REASON_OUT_OF_HUE = "노랑·초록·파랑 계열"

WARM = "warm"
COOL = "cool"
SPRING = "spring_warm"
AUTUMN = "autumn_warm"
SUMMER = "summer_cool"
WINTER = "winter_cool"
SEASONS = [SPRING, AUTUMN, SUMMER, WINTER]
