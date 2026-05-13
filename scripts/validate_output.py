"""
Validate an existing WislyNews output/articles.json file.

This is useful after a local or GitHub Actions run: it checks that every article
contains all configured CEFR levels and that each version passes the same quality
rules used during generation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from config import CEFR_LEVELS
from quality_check import (
    dedupe_articles_by_identity,
    missing_level_codes,
    validate_simplified_version,
)


def default_output_path() -> Path:
    return Path(__file__).resolve().parents[1] / "output" / "articles.json"


def main() -> int:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_output_path()

    if not output_path.exists():
        print(f"Output file not found: {output_path}")
        return 1

    data = json.loads(output_path.read_text(encoding="utf-8"))
    articles = data.get("articles", [])
    level_by_code = {level.code: level for level in CEFR_LEVELS}

    issue_count = 0
    deduped_articles = dedupe_articles_by_identity(articles, "output article")
    if len(deduped_articles) != len(articles):
        issue_count += len(articles) - len(deduped_articles)

    for index, article in enumerate(articles, start=1):
        title = article.get("original_title", f"article #{index}")
        versions = article.get("versions", {})

        missing = missing_level_codes(versions)
        if missing:
            issue_count += 1
            print(f"[{index}] {title}: missing levels {', '.join(missing)}")

        for code, level in level_by_code.items():
            version = versions.get(code)
            if not version:
                continue

            issues = validate_simplified_version(version, level)
            if issues:
                issue_count += len(issues)
                print(f"[{index}] {title} / {code}: " + "; ".join(issues))

    if issue_count:
        print(f"\nValidation failed with {issue_count} issue(s).")
        return 1

    print(f"Validation passed for {len(articles)} article(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
