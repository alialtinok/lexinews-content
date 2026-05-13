# WislyNews Content Generator

WislyNews iOS app'inin içerik üretim pipeline'ı. NewsData.io'dan haberleri çeker,
AI ile 4 farklı CEFR seviyesine (A2-C1) basitleştirir, kalite kontrolünden geçirir
ve JSON olarak yayınlar.

## AI Provider Desteği

Üç farklı AI provider destekler, `.env`'deki `AI_PROVIDER` ile seçilir:

| Provider | Model | Maliyet | Limit |
|----------|-------|---------|-------|
| **groq** (varsayılan) | Llama 3.3 70B | **Ücretsiz** | Günlük kullanım için yeterli |
| gemini | Gemini 2.0 Flash | **Ücretsiz** | 1500 istek/gün |
| claude | Claude Haiku 4.5 | ~$4/ay | Pratikte yok |

Günlük üretim hacmi düşük olduğu için ücretsiz provider'lar bu iş için yeterli.

## Nasıl Çalışır

1. **GitHub Actions** her gün UTC 06:00'da tetiklenir
2. Script RSS feed'lerinden güncel haberleri çeker
3. Her haberi AI provider'a gönderir, her CEFR seviyesi için ayrı versiyon üretir
4. Her versiyonu kalite kontrolünden geçirir: kelime sayısı, başlık, gövde,
   vocabulary sayısı ve eksik seviye kontrol edilir
5. Sonucu `output/articles.json`'a yazar
6. Workflow dosyayı repo'ya commit'ler
7. iOS app şu URL'den çeker:
   ```
   https://raw.githubusercontent.com/alialtinok/wislynews-content/main/output/articles.json
   ```

## Local Çalıştırma

```bash
# Virtual environment
python -m venv .venv
source .venv/bin/activate

# Bağımlılıklar
pip install -r requirements.txt

# API key
cp .env.example .env
# .env'yi düzenle: AI_PROVIDER, NEWSDATA_API_KEY ve provider key değerlerini gir

# Çalıştır
PYTHONPATH=scripts python scripts/generate_articles.py

# Üretilen JSON'u kontrol et
PYTHONPATH=scripts python scripts/validate_output.py output/articles.json
```

## Claude'a Geçmek (ileride)

Kaliteyi yükseltmek istersen:

1. `.env` dosyasında:
   ```
   AI_PROVIDER=claude
   ANTHROPIC_API_KEY=sk-ant-...
   ```
2. GitHub Actions'da `.github/workflows/generate.yml` dosyasındaki env bloğunu güncelle

Kod değişikliği gerekmez, provider-agnostic mimari.

## GitHub Actions Setup

1. Repo → Settings → Secrets and variables → Actions
2. "New repository secret" → `GEMINI_API_KEY` ekle
3. Actions sekmesinden workflow'u manuel tetikleyerek test et

## Proje Yapısı

```
wislynews-content/
├── scripts/
│   ├── config.py              # prompt, CEFR tanımları, provider ayarları
│   ├── newsdata_fetcher.py    # NewsData.io ile haber çekme
│   ├── rss_fetcher.py         # eski feedparser tabanlı haber çekme
│   ├── ai_simplifier.py       # Provider-agnostic AI katmanı (Groq + Gemini + Claude)
│   ├── quality_check.py       # kelime sayısı, vocabulary ve eksik seviye kontrolleri
│   ├── validate_output.py     # mevcut articles.json kalite kontrolü
│   └── generate_articles.py   # Ana orchestration
├── output/
│   └── articles.json          # Üretilen içerik (iOS buradan okur)
└── .github/workflows/
    └── generate.yml           # Günlük cron
```
