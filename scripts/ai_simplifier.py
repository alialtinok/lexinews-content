"""
LexiNews Content Generator - AI Simplifier (Provider-Agnostic)

Makaleleri CEFR seviyelerine basitleştirmek için AI kullanır.
İki provider destekler:
  - gemini (ücretsiz, Google Gemini 2.0 Flash)
  - claude (ücretli, Anthropic Haiku 4.5)

.env'deki AI_PROVIDER değişkeniyle seçilir.

Tasarım kararı - neden iki ayrı sınıf:
Her provider'ın SDK'sı, mesaj formatı ve hata tipleri farklı.
Ortak bir 'Simplifier' interface'i tanımlayıp her provider'ı
kendi sınıfında tutmak, kodu temiz ve test edilebilir kılıyor.
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Optional

from config import (
    CEFRLevel,
    CEFR_LEVELS,
    CLAUDE_MODEL,
    GEMINI_MODEL,
    GROQ_MODEL,
    CLAUDE_MAX_TOKENS,
    GEMINI_MAX_TOKENS,
    GROQ_MAX_TOKENS,
    SIMPLIFICATION_PROMPT,
)
from newsdata_fetcher import RawArticle


# ─────────────────────────────────────────────────────────────
# Ortak veri yapıları
# ─────────────────────────────────────────────────────────────
@dataclass
class SimplifiedVersion:
    """Tek bir CEFR seviyesi için basitleştirilmiş makale."""
    level: str
    title: str
    body: str
    key_vocabulary: list[str]


@dataclass
class ProcessedArticle:
    """Tüm CEFR versiyonlarını içeren final makale."""
    id: str
    original_title: str
    original_url: str
    category: str
    published: Optional[str]
    versions: dict[str, dict]


# ─────────────────────────────────────────────────────────────
# Yardımcı fonksiyonlar (provider'dan bağımsız)
# ─────────────────────────────────────────────────────────────
def clean_json_response(raw_text: str) -> str:
    """
    AI yanıtını JSON parse için temizler.
    Hem Gemini hem Claude bazen ```json ... ``` ile sararlar.
    """
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return text.strip()


def parse_simplification_response(
    raw_text: str, level_code: str
) -> Optional[SimplifiedVersion]:
    """
    AI yanıtını SimplifiedVersion'a parse eder.
    Ortak kod - her iki provider da aynı JSON formatını döndürüyor.
    """
    cleaned = clean_json_response(raw_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"      ❌ JSON parse failed: {e}")
        print(f"         Raw: {cleaned[:200]}...")
        return None

    required = {"title", "body", "key_vocabulary"}
    if not required.issubset(data.keys()):
        print(f"      ❌ Missing fields: got {set(data.keys())}")
        return None

    return SimplifiedVersion(
        level=level_code,
        title=data["title"],
        body=data["body"],
        key_vocabulary=data["key_vocabulary"],
    )


# ─────────────────────────────────────────────────────────────
# Base class - tüm provider'ların uyması gereken interface
# ─────────────────────────────────────────────────────────────
class BaseSimplifier(ABC):
    """Her AI provider'ı bu sınıftan türeyecek."""

    @abstractmethod
    def simplify_one(
        self, article: RawArticle, level: CEFRLevel
    ) -> Optional[SimplifiedVersion]:
        """Bir makaleyi bir CEFR seviyesine basitleştir."""
        pass

    def process_article(self, article: RawArticle) -> Optional[ProcessedArticle]:
        """
        Bir makaleyi tüm CEFR seviyelerinde işler.
        Bu mantık provider'dan bağımsız, base'de tutuyoruz.
        """
        print(f"\n  📝 {article.title[:60]}...")

        versions = {}
        for level in CEFR_LEVELS:
            print(f"      Processing {level.code}...", end=" ", flush=True)
            result = self.simplify_one(article, level)
            if result:
                versions[level.code] = asdict(result)
                print("✓")
            else:
                print("✗")

        if not versions:
            print("      ⚠️  All levels failed, skipping")
            return None

        return ProcessedArticle(
            id=article.id,
            original_title=article.title,
            original_url=article.url,
            category=article.category,
            published=article.published,
            versions=versions,
        )


# ─────────────────────────────────────────────────────────────
# Gemini Provider (Google AI)
# ─────────────────────────────────────────────────────────────
class GeminiSimplifier(BaseSimplifier):
    """
    Google Gemini 2.0 Flash kullanır. Ücretsiz tier: günde 1500 istek.
    Bizim ihtiyacımız günde ~60 istek, rahat rahat sığıyor.
    """

    def __init__(self, api_key: Optional[str] = None):
        # Lazy import - Gemini kullanılmıyorsa paketi yüklemeye gerek yok
        try:
            from google import genai
        except ImportError:
            raise ImportError(
                "google-genai paketi yüklü değil. "
                "requirements.txt'yi kontrol et ve 'pip install -r requirements.txt' çalıştır."
            )

        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError(
                "GEMINI_API_KEY bulunamadı. "
                "https://aistudio.google.com/apikey adresinden ücretsiz key al."
            )

        self.client = genai.Client(api_key=key)
        self._genai = genai  # Tiplendirme için saklıyoruz

    def simplify_one(
        self, article: RawArticle, level: CEFRLevel
    ) -> Optional[SimplifiedVersion]:
        prompt = SIMPLIFICATION_PROMPT.format(
            level_code=level.code,
            min_words=level.min_words,
            level_name=level.name,
            level_description=level.description,
            target_words=level.target_words,
            original_title=article.title,
            original_content=article.summary,
        )

        try:
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "max_output_tokens": GEMINI_MAX_TOKENS,
                },
            )
        except Exception as e:
            print(f"      ❌ Gemini API error: {e}")
            return None

        if not response.text:
            print("      ❌ Empty response from Gemini")
            return None

        return parse_simplification_response(response.text, level.code)


# ─────────────────────────────────────────────────────────────
# Claude Provider (Anthropic)
# ─────────────────────────────────────────────────────────────
class ClaudeSimplifier(BaseSimplifier):
    """
    Anthropic Claude Haiku 4.5 kullanır. Ücretli ($1/$5 per 1M tokens).
    Günlük maliyet tahmini: ~$0.14 (60 çağrı için).
    """

    def __init__(self, api_key: Optional[str] = None):
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic paketi yüklü değil. "
                "requirements.txt'yi kontrol et ve 'pip install -r requirements.txt' çalıştır."
            )

        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY bulunamadı. "
                "https://console.anthropic.com/ adresinden key al."
            )

        self.client = Anthropic(api_key=key)

    def simplify_one(
        self, article: RawArticle, level: CEFRLevel
    ) -> Optional[SimplifiedVersion]:
        prompt = SIMPLIFICATION_PROMPT.format(
            level_code=level.code,
            min_words=level.min_words,
            level_name=level.name,
            level_description=level.description,
            target_words=level.target_words,
            original_title=article.title,
            original_content=article.summary,
        )

        try:
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=CLAUDE_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            print(f"      ❌ Claude API error: {e}")
            return None

        raw_text = response.content[0].text
        return parse_simplification_response(raw_text, level.code)


# ─────────────────────────────────────────────────────────────
# Groq Provider (ücretsiz, hızlı)
# ─────────────────────────────────────────────────────────────
class GroqSimplifier(BaseSimplifier):
    """
    Groq üzerinde Llama 3.3 70B kullanır. Tamamen ücretsiz.
    Groq'un API'si OpenAI uyumlu, çok hızlı yanıt verir.
    Limit: dakikada 30 istek, günde ~14,400 istek.
    """

    def __init__(self, api_key: Optional[str] = None):
        try:
            from groq import Groq
        except ImportError:
            raise ImportError(
                "groq paketi yüklü değil. "
                "'pip install groq' çalıştır."
            )

        key = api_key or os.environ.get("GROQ_API_KEY")
        if not key:
            raise ValueError(
                "GROQ_API_KEY bulunamadı. "
                "https://console.groq.com/keys adresinden ücretsiz key al."
            )

        self.client = Groq(api_key=key)

    def simplify_one(
        self, article: RawArticle, level: CEFRLevel
    ) -> Optional[SimplifiedVersion]:
        prompt = SIMPLIFICATION_PROMPT.format(
            level_code=level.code,
            min_words=level.min_words,
            level_name=level.name,
            level_description=level.description,
            target_words=level.target_words,
            original_title=article.title,
            original_content=article.summary,
        )

        try:
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                max_tokens=GROQ_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            print(f"      ❌ Groq API error: {e}")
            return None

        raw_text = response.choices[0].message.content
        if not raw_text:
            print("      ❌ Empty response from Groq")
            return None

        return parse_simplification_response(raw_text, level.code)


# ─────────────────────────────────────────────────────────────
# Factory - AI_PROVIDER'a göre doğru simplifier'ı döndürür
# ─────────────────────────────────────────────────────────────
def create_simplifier() -> BaseSimplifier:
    """
    .env'deki AI_PROVIDER değişkenine göre doğru provider'ı döndürür.
    Varsayılan: groq (ücretsiz).
    """
    provider = os.environ.get("AI_PROVIDER", "groq").lower()

    if provider == "groq":
        print("🤖 Using Groq Llama 3.3 70B (free)")
        return GroqSimplifier()
    elif provider == "gemini":
        print("🤖 Using Gemini 2.0 Flash (free tier)")
        return GeminiSimplifier()
    elif provider == "claude":
        print("🤖 Using Claude Haiku 4.5 (paid)")
        return ClaudeSimplifier()
    else:
        raise ValueError(
            f"Bilinmeyen AI_PROVIDER: '{provider}'. "
            f"'groq', 'gemini' veya 'claude' olmalı."
        )
