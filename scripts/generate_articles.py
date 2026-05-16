"""
WislyNews Content Generator - Main Script

Tüm pipeline'ı çalıştırır:
1. RSS feed'lerinden haberleri çek
2. Her birini Claude ile CEFR seviyelerine basitleştir
3. Sonucu output/articles.json'a yaz

Kullanım:
    python generate_articles.py

Environment variables:
    ANTHROPIC_API_KEY: Claude API anahtarı (zorunlu)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# dotenv opsiyonel - GitHub Actions'da environment variable direkt inject edilir
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import (
    ARTICLES_PER_CATEGORY,
    CEFR_LEVELS,
    MIN_OUTPUT_ARTICLES,
    NEWSDATA_CATEGORIES,
    OUTPUT_PATH,
    RAW_CANDIDATE_MULTIPLIER,
)
from newsdata_fetcher import fetch_all
from ai_simplifier import ProviderRateLimitError, create_simplifier
from quality_check import article_to_dict, dedupe_processed_articles, dedupe_raw_articles


def main() -> int:
    """Ana pipeline. Başarıda 0, hatada 1 döner (exit code)."""
    print("=" * 60)
    print("WislyNews Content Generator")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # ─── 1. API Key kontrolü ───────────────────────────────
    provider = os.environ.get("AI_PROVIDER", "groq").lower()
    key_map = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY", "claude": "ANTHROPIC_API_KEY"}
    required_key = key_map.get(provider, "GROQ_API_KEY")

    if not os.environ.get(required_key):
        print(f"❌ {required_key} not set!")
        url_map = {
            "groq": "https://console.groq.com/keys",
            "gemini": "https://aistudio.google.com/apikey",
            "claude": "https://console.anthropic.com/",
        }
        print(f"   Get free key: {url_map.get(provider, '')}")
        print(f"   Local: add {required_key}=... to .env file")
        return 1

    # ─── 2. NewsData.io'dan haberleri çek ────────────────
    newsdata_key = os.environ.get("NEWSDATA_API_KEY")
    if not newsdata_key:
        print("❌ NEWSDATA_API_KEY not set!")
        return 1

    print("\n🌐 Step 1: Fetching from NewsData.io")
    raw_articles = fetch_all(
        list(NEWSDATA_CATEGORIES.keys()),
        ARTICLES_PER_CATEGORY,
        newsdata_key,
        RAW_CANDIDATE_MULTIPLIER,
    )

    if not raw_articles:
        print("❌ No articles fetched. Exiting.")
        return 1

    raw_count = len(raw_articles)
    raw_articles = dedupe_raw_articles(raw_articles)
    if len(raw_articles) != raw_count:
        print(f"   ✓ Removed {raw_count - len(raw_articles)} duplicate raw article(s)")

    # ─── 3. Her makaleyi AI ile basitleştir ──────────────
    print(f"\n🤖 Step 2: Simplifying {len(raw_articles)} articles")
    simplifier = create_simplifier()

    target_total = len(NEWSDATA_CATEGORIES) * ARTICLES_PER_CATEGORY
    processed = []
    processed_by_category = {category: 0 for category in NEWSDATA_CATEGORIES}
    for article in raw_articles:
        if processed_by_category.get(article.category, 0) >= ARTICLES_PER_CATEGORY:
            continue

        try:
            result = simplifier.process_article(article)
        except ProviderRateLimitError as e:
            print(f"\n❌ AI provider rate limit reached. Keeping existing output.")
            print(f"   {e}")
            return 1

        if result:
            processed.append(result)
            processed_by_category[result.category] = processed_by_category.get(result.category, 0) + 1

        if len(processed) >= target_total:
            break

    if not processed:
        print("\n❌ No articles were successfully processed. Exiting.")
        return 1

    processed = dedupe_processed_articles(processed)

    if len(processed) < MIN_OUTPUT_ARTICLES:
        print(
            f"\n❌ Only {len(processed)} articles passed quality; "
            f"minimum is {MIN_OUTPUT_ARTICLES}. Keeping existing output."
        )
        return 1

    print(f"\n✅ Successfully processed {len(processed)}/{len(raw_articles)} articles")

    # ─── 4. JSON çıktısını oluştur ───────────────────────
    print(f"\n💾 Step 3: Writing output to {OUTPUT_PATH}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
        "article_count": len(processed),
        "articles": [article_to_dict(a) for a in processed],
    }

    output_path = Path(OUTPUT_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    file_size = output_path.stat().st_size / 1024
    print(f"   ✓ Wrote {file_size:.1f} KB")
    print(
        f"   ✓ {len(processed)} articles × {len(CEFR_LEVELS)} levels = "
        f"{len(processed) * len(CEFR_LEVELS)} versions"
    )

    print("\n" + "=" * 60)
    print("✅ Done!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
