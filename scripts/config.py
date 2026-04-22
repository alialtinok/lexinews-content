"""
LexiNews Content Generator - Configuration

Tüm sabitler, feed listeleri, CEFR seviye tanımları ve prompt şablonları
burada tutulur. Kod mantığından ayrıdır, böylece ayarları değiştirmek için
script'i düzenlemen gerekmez.
"""

from dataclasses import dataclass


# ─────────────────────────────────────────────────────────────
# CEFR Seviye Tanımları
# ─────────────────────────────────────────────────────────────
@dataclass
class CEFRLevel:
    code: str           # "A2", "B1" vb.
    name: str           # Açıklayıcı isim
    min_words: int      # Minimum kelime sayısı
    target_words: int   # Hedef (maksimum) kelime sayısı
    description: str    # AI'a gönderilecek açıklama


CEFR_LEVELS = [
    CEFRLevel(
        code="A2",
        name="Elementary",
        min_words=200,
        target_words=280,
        description="simple English, common 1000 words, short sentences (8-12 words), basic past and future tenses only. Cover the full story with enough detail — write 5-6 paragraphs minimum so the reader understands what happened, who was involved, and why it matters",
    ),
    CEFRLevel(
        code="B1",
        name="Intermediate",
        min_words=150,
        target_words=220,
        description="clear English, 2000 most common words, moderate sentence length (10-15 words), all basic tenses",
    ),
    CEFRLevel(
        code="B2",
        name="Upper-Intermediate",
        min_words=180,
        target_words=260,
        description="natural English, 3500 common words, varied sentence structure, some idiomatic expressions allowed",
    ),
    CEFRLevel(
        code="C1",
        name="Advanced",
        min_words=220,
        target_words=320,
        description="advanced English, 5000+ words, complex sentences, nuanced vocabulary, figurative language, formal register",
    ),
]


# ─────────────────────────────────────────────────────────────
# RSS Feed'leri - Kategorilere göre
# ─────────────────────────────────────────────────────────────
# Sadece güvenilir, halka açık RSS feed'leri kullanıyoruz.
# Her gün her kategoriden 2 haber alacağız = günde 10 haber toplam.
# Her haber 6 CEFR seviyesinde üretilecek = 60 makale/gün.
RSS_FEEDS = {
    "world": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
    "technology": [
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://www.theverge.com/rss/index.xml",
    ],
    "science": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    ],
    "sports": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
    ],
    "culture": [
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    ],
}

# Her kategoriden kaç haber alınacak
ARTICLES_PER_CATEGORY = 2


# ─────────────────────────────────────────────────────────────
# AI Provider Ayarları
# ─────────────────────────────────────────────────────────────
# Claude (Anthropic)
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
CLAUDE_MAX_TOKENS = 1024

# Gemini (Google) - ücretsiz tier: günde 1500 istek
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_MAX_TOKENS = 1024

# Groq - ücretsiz, bölge kısıtlaması yok, çok hızlı
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MAX_TOKENS = 1024


# ─────────────────────────────────────────────────────────────
# Prompt Template
# ─────────────────────────────────────────────────────────────
# Bu prompt Claude'a gönderilir. {placeholder}'lar runtime'da doldurulur.
# Claude'dan STRICT JSON döndürmesini istiyoruz, böylece parse etmek kolay.
SIMPLIFICATION_PROMPT = """You are an English teacher creating reading material for language learners.

Rewrite the following news article for a CEFR {level_code} ({level_name}) English learner.

CRITICAL REQUIREMENTS:
- Use {level_description}
- Your text MUST be between {min_words} and {target_words} words. This is mandatory. Count your words.
- Keep all facts accurate - do not invent or hallucinate information
- Write a clear, engaging title (max 10 words)
- Identify 5 key vocabulary words from your rewritten text that a {level_code} learner should study
- The 5 vocabulary words must be appropriate for {level_code} level - not too easy, not too hard
- Return ONLY valid JSON, no markdown, no explanation

Required JSON format:
{{
  "title": "Your rewritten title",
  "body": "Your rewritten article body",
  "key_vocabulary": ["word1", "word2", "word3", "word4", "word5"]
}}

Original article:
Title: {original_title}
Content: {original_content}
"""


# ─────────────────────────────────────────────────────────────
# Output Ayarları
# ─────────────────────────────────────────────────────────────
OUTPUT_PATH = "output/articles.json"
