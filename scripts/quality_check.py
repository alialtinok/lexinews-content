"""
Quality checks for generated WislyNews articles.

The content pipeline should only publish articles that are complete enough for
the app: every CEFR level must exist, each version must hit its word-count
target, and vocabulary data must be usable by the reader UI.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from difflib import SequenceMatcher
from typing import Iterable

from config import CEFR_LEVELS, CEFRLevel, WORD_COUNT_MAX_TOLERANCE


WORD_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)?")
TITLE_SIMILARITY_THRESHOLD = 0.92


def count_words(text: str) -> int:
    """Count English-like words in generated article text."""
    return len(WORD_RE.findall(text or ""))


def max_allowed_words(level: CEFRLevel) -> int:
    return int(round(level.target_words * (1 + WORD_COUNT_MAX_TOLERANCE)))


def read_field(value, field_name: str, default=None):
    if isinstance(value, dict):
        return value.get(field_name, default)
    return getattr(value, field_name, default)


def validate_simplified_version(version, level: CEFRLevel) -> list[str]:
    """Return human-readable quality issues for one generated CEFR version."""
    issues: list[str] = []

    title = read_field(version, "title", "")
    body = read_field(version, "body", "")
    vocabulary = read_field(version, "key_vocabulary")

    if not isinstance(title, str) or not title.strip():
        issues.append("missing title")
    elif count_words(title) > 12:
        issues.append("title is longer than 12 words")

    if not isinstance(body, str) or not body.strip():
        issues.append("missing body")
    else:
        words = count_words(body)
        if words < level.min_words:
            issues.append(f"body too short ({words}/{level.min_words} min words)")
        if words > max_allowed_words(level):
            issues.append(
                f"body too long ({words}/{max_allowed_words(level)} max words)"
            )

    if not isinstance(vocabulary, list):
        issues.append("key_vocabulary is not a list")
    else:
        cleaned = [str(word).strip() for word in vocabulary if str(word).strip()]
        unique = {word.lower() for word in cleaned}

        if len(cleaned) != 5:
            issues.append(f"key_vocabulary must contain exactly 5 items ({len(cleaned)} found)")
        if len(unique) != len(cleaned):
            issues.append("key_vocabulary contains duplicates")

        body_lower = body.lower() if isinstance(body, str) else ""
        matches_in_body = sum(1 for word in unique if word in body_lower)
        if cleaned and matches_in_body == 0:
            issues.append("none of the vocabulary words appear in the body")

    return issues


def expected_level_codes() -> set[str]:
    return {level.code for level in CEFR_LEVELS}


def missing_level_codes(versions: dict) -> list[str]:
    return sorted(expected_level_codes() - set(versions.keys()))


def normalized_key(value: str) -> str:
    lowered = (value or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def titles_are_similar(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return SequenceMatcher(None, left, right).ratio() >= TITLE_SIMILARITY_THRESHOLD


def dedupe_articles_by_identity(articles: Iterable, label: str) -> list:
    """Remove duplicate article-like objects by URL and near-identical title."""
    deduped = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []

    for article in articles:
        url = read_field(article, "url") or read_field(article, "original_url", "")
        title = read_field(article, "title") or read_field(article, "original_title", "")
        url_key = normalized_key(url)
        title_key = normalized_key(title)

        if url_key and url_key in seen_urls:
            print(f"  ⚠️  Duplicate {label} skipped by URL: {title[:60]}...")
            continue

        if title_key and any(titles_are_similar(title_key, old) for old in seen_titles):
            print(f"  ⚠️  Duplicate {label} skipped by title: {title[:60]}...")
            continue

        if url_key:
            seen_urls.add(url_key)
        if title_key:
            seen_titles.append(title_key)

        deduped.append(article)

    return deduped


def dedupe_raw_articles(articles: Iterable) -> list:
    return dedupe_articles_by_identity(articles, "raw article")


def dedupe_processed_articles(articles: Iterable) -> list:
    return dedupe_articles_by_identity(articles, "processed article")


def article_to_dict(article) -> dict:
    """Dataclass-safe conversion used by output generation."""
    return asdict(article)
