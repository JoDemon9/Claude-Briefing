#!/usr/bin/env python3
"""
Ultra-fast (0.5s) pre-commit validation for LLM content generation.
Verifies edition JSON syntax, article references, and article content validity
without executing heavy builds, image downloads, Playwright, or network tests.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def validate_edition(edition_slug: str, root: Path = ROOT) -> int:
    root = Path(root)
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-(morning|midday|evening)', edition_slug):
        print('[ERROR] Invalid edition id')
        return 1
    edition_path = root / "content" / "editions" / f"{edition_slug}.json"
    articles_dir = root / "content" / "articles" / edition_slug

    if not edition_path.exists():
        print(f"[ERROR] Missing edition file: {edition_path}")
        return 1

    try:
        edition = json.loads(edition_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[ERROR] Invalid JSON in {edition_path}: {exc}")
        return 1

    # Check essential top-level fields
    for field in ("id", "date", "type", "articles", "sports"):
        if field not in edition:
            print(f"[ERROR] Edition is missing required field: '{field}'")
            return 1

    if not articles_dir.exists():
        print(f"[ERROR] Missing articles directory: {articles_dir}")
        return 1

    # Verify all declared articles exist and have content
    declared_articles = edition.get("articles", [])
    if not declared_articles:
        print("[ERROR] Edition declared no articles")
        return 1

    article_files = {p.stem: p for p in articles_dir.glob("*.json")}
    for rel_path in declared_articles:
        if not re.fullmatch(r'articles/'+re.escape(edition_slug)+r'/[a-z0-9-]+\.json', rel_path):
            print('[ERROR] Unsafe or cross-edition article path')
            return 1
        stem = Path(rel_path).stem
        if stem not in article_files:
            print(f"[ERROR] Declared article '{rel_path}' not found in {articles_dir}")
            return 1

        path = article_files[stem]
        try:
            art_data = json.loads(path.read_text(encoding="utf-8"))
            if not art_data.get("headline") and not art_data.get("title"):
                print(f"[ERROR] Article {stem} is missing 'headline'")
                return 1
            if not art_data.get("summary"):
                print(f"[ERROR] Article {stem} is missing 'summary'")
                return 1
        except Exception as exc:
            print(f"[ERROR] Invalid JSON in article {path}: {exc}")
            return 1

    print(f"[OK] JSON syntax/references only: {edition_slug}, {len(declared_articles)} articles. Editorial and release gates remain required.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/v2/quick_validate.py <edition-id>")
        sys.exit(1)
    sys.exit(validate_edition(sys.argv[1]))
