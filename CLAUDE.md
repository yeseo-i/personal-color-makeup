# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Makeup shade data for a site. Lipstick, blush and eyeshadow shades are classified into four seasons (spring warm, autumn warm, summer cool, winter cool) from their CIELAB (D65) values.

## Layout

- `scripts/clean_products.py`: reads the raw data, cleans it, classifies each shade, writes `data/products.json`, and prints the summary statistics.
- `scripts/color_rules.py`: every classification threshold (hex format, minimum chroma, excluded hue range, warm/cool hue range, lightness and chroma splits). These are provisional project rules, not validated. Do not change any threshold without the user's explicit approval. If a change is approved, change it here only.
- `scripts/fetch_products.py`: downloads from the Makeup API. Not used: the API has returned 503 since 2026-10.
- `data/raw/products.json`: the raw source, a copy of the Kaggle dataset "Herokuapp Makeup Products". Ignored by git. Never edit it.
- `data/products.json`: the cleaned output for the site, produced by `clean_products.py`. Committed.

## Python environment

Use the `.venv` at the repository root (Python 3.14).

```sh
python3 -m venv .venv          # only if .venv does not exist
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` lists `requests`, which only `fetch_products.py` uses. `clean_products.py` uses only the standard library.

## Raw data

The raw data is not in git. To get it:

1. Sign in to Kaggle and download the dataset "Herokuapp Makeup Products", a copy of the full Makeup API product list.
2. Save its JSON file as `data/raw/products.json`. The file is a JSON list of products with `product_type` and `product_colors` fields.
3. The copy used for the committed `data/products.json` has sha256 `ebb0dca2095302dab9a9f8726b5e3fbdaae677afbce8f5ec72c89d2ad56b057a`. Check with `sha256sum data/raw/products.json`.

Never commit `data/raw/`. `.gitignore` excludes it. The committed `data/products.json` is the cleaned result, not raw data.

## Run

From the repository root:

1. Use `data/raw/products.json` as the raw source. Do not call the Makeup API. Do not edit the raw file, and never invent data that is not in it. If the raw file is missing or cannot be read, tell the user before doing anything else.
2. `python scripts/clean_products.py`

The script exits with status 1 and writes no output if the raw file is missing or is not valid JSON. After a run, compare its statistics with the previous run. If any number changes, report the old and new values and the cause. Do not adjust code to make numbers match.

## Git

- Never use `git add .` or `git add -A`. Add each file by path.
- Before committing, check `git diff --cached --name-only` and confirm that only the intended files are staged.
- Commit only after the user has reviewed the results and approved.
- Add or change a remote, and push, only after the user has approved. Never use `--force`.
