"""
LexiNews Content Generator - NewsData.io Fetcher

NewsData.io API'sinden haberleri çeker.
Free tier: 200 istek/gün, tam makale içeriği.
"""

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import urllib.request
import urllib.parse
import json


@dataclass
class RawArticle:
    id: str
    title: str
    summary: str
    url: str
    category: str
    published: Optional[str]
    source: str


def generate_article_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


NEWSDATA_CATEGORIES = {
    "world":      "top",
    "technology": "technology",
    "science":    "science",
    "sports":     "sports",
    "culture":    "entertainment",
}


def fetch_newsdata(category: str, api_key: str, limit: int = 3) -> list[RawArticle]:
    nd_category = NEWSDATA_CATEGORIES.get(category, "top")

    params = urllib.parse.urlencode({
        "apikey":   api_key,
        "language": "en",
        "category": nd_category,
    })
    url = f"https://newsdata.io/api/1/news?{params}"

    print(f"  Fetching NewsData.io [{nd_category}]...")
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        print(f"  ⚠️  NewsData error: {e}")
        return []

    if data.get("status") != "success":
        print(f"  ⚠️  NewsData API error: {data.get('results', data)}")
        return []

    articles = []
    for item in data.get("results", []):
        # Full content varsa kullan, yoksa description
        content = item.get("content") or item.get("description") or ""
        if not content or len(content) < 100:
            continue

        # Tarih parse
        published_iso = None
        pub = item.get("pubDate")
        if pub:
            try:
                published_iso = datetime.strptime(pub, "%Y-%m-%d %H:%M:%S").isoformat()
            except ValueError:
                published_iso = pub

        article = RawArticle(
            id=generate_article_id(item.get("link", item.get("article_id", ""))),
            title=item.get("title", ""),
            summary=content,
            url=item.get("link", ""),
            category=category,
            published=published_iso,
            source=item.get("source_name", "NewsData.io"),
        )
        articles.append(article)
        if len(articles) >= limit:
            break

    print(f"    ✓ Got {len(articles)} articles")
    return articles


def fetch_all(categories: list, per_category: int, api_key: str) -> list[RawArticle]:
    all_articles = []
    seen_ids = set()

    for category in categories:
        print(f"\n📡 Category: {category}")
        articles = fetch_newsdata(category, api_key, limit=per_category * 2)
        for article in articles:
            if article.id not in seen_ids:
                all_articles.append(article)
                seen_ids.add(article.id)
            if len([a for a in all_articles if a.category == category]) >= per_category:
                break

    print(f"\n✅ Total articles fetched: {len(all_articles)}")
    return all_articles
