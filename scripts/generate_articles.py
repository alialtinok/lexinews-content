"""
LexiNews Content Generator - Main Script

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
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

# dotenv opsiyonel - GitHub Actions'da environment variable direkt inject edilir
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import ARTICLES_PER_CATEGORY, OUTPUT_PATH, NEWSDATA_CATEGORIES
from newsdata_fetcher import fetch_all
from ai_simplifier import create_simplifier


def main() -> int:
    """Ana pipeline. Başarıda 0, hatada 1 döner (exit code)."""
    print("=" * 60)
    print("LexiNews Content Generator")
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
    raw_articles = fetch_all(list(NEWSDATA_CATEGORIES.keys()), ARTICLES_PER_CATEGORY, newsdata_key)

    if not raw_articles:
        print("❌ No articles fetched. Exiting.")
        return 1

    # ─── 3. Her makaleyi AI ile basitleştir ──────────────
    print(f"\n🤖 Step 2: Simplifying {len(raw_articles)} articles")
    simplifier = create_simplifier()

    processed = []
    for article in raw_articles:
        result = simplifier.process_article(article)
        if result:
            processed.append(result)

    if not processed:
        print("\n❌ No articles were successfully processed. Exiting.")
        return 1

    print(f"\n✅ Successfully processed {len(processed)}/{len(raw_articles)} articles")

    # ─── 4. JSON çıktısını oluştur ───────────────────────
    print(f"\n💾 Step 3: Writing output to {OUTPUT_PATH}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
        "article_count": len(processed),
        "articles": [asdict(a) for a in processed],
    }

    output_path = Path(OUTPUT_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    file_size = output_path.stat().st_size / 1024
    print(f"   ✓ Wrote {file_size:.1f} KB")
    print(f"   ✓ {len(processed)} articles × ~6 levels = ~{len(processed) * 6} versions")

    print("\n" + "=" * 60)
    print("✅ Done!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
