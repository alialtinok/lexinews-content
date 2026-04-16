"""
LexiNews Content Generator - RSS Fetcher

RSS feed'lerinden haberleri çeker ve yapılandırılmış bir format döndürür.
feedparser kütüphanesi hem RSS hem Atom formatlarını otomatik handle eder.
"""

from dataclasses import dataclass
from typing import Optional
import feedparser
import hashlib
from datetime import datetime


@dataclass
class RawArticle:
    """RSS'den çekilen ham makale. Henüz basitleştirilmemiş."""
    id: str              # Stabil hash - aynı URL için her zaman aynı
    title: str
    summary: str         # RSS'deki kısa özet
    url: str             # Orijinal habere link (kredi için)
    category: str        # Bizim kategorilendirmemiz (feed'e göre)
    published: Optional[str]  # ISO timestamp, yoksa None


def generate_article_id(url: str) -> str:
    """
    URL'den stabil bir ID üret. Aynı URL her zaman aynı ID'yi verir.
    Bu sayede aynı haberi iki kere işlemeyiz.
    """
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def clean_html(text: str) -> str:
    """
    RSS summary'leri bazen HTML tag'leri içerir. Basit temizlik.
    Production'da BeautifulSoup kullanabiliriz ama bu MVP için yeterli.
    """
    import re
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_from_feed(feed_url: str, category: str, limit: int = 5) -> list[RawArticle]:
    """
    Tek bir RSS feed'inden haberleri çeker.

    Args:
        feed_url: RSS feed URL'i
        category: Bu feed'in kategorisi (config'den geliyor)
        limit: Kaç makale alınacak

    Returns:
        RawArticle listesi
    """
    print(f"  Fetching: {feed_url}")

    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        print(f"  ⚠️  Failed to parse feed: {e}")
        return []

    if feed.bozo and feed.bozo_exception:
        # bozo = feedparser'ın "bu feed'de bir sorun var" flag'i
        # Genelde yine de çalışır, sadece uyarı verir
        print(f"  ⚠️  Feed warning: {feed.bozo_exception}")

    articles = []
    for entry in feed.entries[:limit]:
        # Bazı feed'lerde 'summary' yok, 'description' var
        summary = entry.get("summary") or entry.get("description") or ""
        summary = clean_html(summary)

        # Özet çok kısaysa veya yoksa atla - Claude'a verecek içerik lazım
        if len(summary) < 100:
            continue

        # published_parsed bir struct_time, ISO string'e çeviriyoruz
        published_iso = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published_iso = datetime(*entry.published_parsed[:6]).isoformat()
            except (TypeError, ValueError):
                pass

        article = RawArticle(
            id=generate_article_id(entry.link),
            title=entry.title,
            summary=summary,
            url=entry.link,
            category=category,
            published=published_iso,
        )
        articles.append(article)

    print(f"    ✓ Got {len(articles)} articles")
    return articles


def fetch_all(feeds_config: dict, per_category: int) -> list[RawArticle]:
    """
    Tüm kategorilerden haberleri çeker.

    Args:
        feeds_config: {"world": [url1, url2], "tech": [url3], ...}
        per_category: Her kategoriden kaç haber

    Returns:
        Tüm kategorilerden toplanmış RawArticle listesi
    """
    all_articles = []
    seen_ids = set()  # Duplicate engelleme

    for category, feed_urls in feeds_config.items():
        print(f"\n📡 Category: {category}")
        category_articles = []

        for feed_url in feed_urls:
            articles = fetch_from_feed(feed_url, category, limit=per_category * 2)
            for article in articles:
                if article.id not in seen_ids:
                    category_articles.append(article)
                    seen_ids.add(article.id)
                if len(category_articles) >= per_category:
                    break
            if len(category_articles) >= per_category:
                break

        all_articles.extend(category_articles[:per_category])

    print(f"\n✅ Total articles fetched: {len(all_articles)}")
    return all_articles
