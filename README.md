# LexiNews Content Generator

LexiNews iOS app'inin içerik üretim pipeline'ı. RSS feed'lerinden haberleri çeker,
AI ile 6 farklı CEFR seviyesine (A1-C2) basitleştirir ve JSON olarak yayınlar.

## AI Provider Desteği

İki farklı AI provider destekler, `.env`'deki `AI_PROVIDER` ile seçilir:

| Provider | Model | Maliyet | Limit |
|----------|-------|---------|-------|
| **gemini** (varsayılan) | Gemini 2.0 Flash | **Ücretsiz** | 1500 istek/gün |
| claude | Claude Haiku 4.5 | ~$4/ay | Pratikte yok |

Biz **~60 istek/gün** kullanıyoruz, Gemini ücretsiz tier rahat rahat yetiyor.

## Nasıl Çalışır

1. **GitHub Actions** her gün UTC 06:00'da tetiklenir
2. Script RSS feed'lerinden güncel haberleri çeker
3. Her haberi AI provider'a gönderir, her CEFR seviyesi için ayrı versiyon üretir
4. Sonucu `output/articles.json`'a yazar
5. Workflow dosyayı repo'ya commit'ler
6. iOS app şu URL'den çeker:
   ```
   https://raw.githubusercontent.com/alialtinok/lexinews-content/main/output/articles.json
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
# .env'yi düzenle: GEMINI_API_KEY değerini gir
# https://aistudio.google.com/apikey adresinden ücretsiz al

# Çalıştır
cd scripts
python generate_articles.py
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
lexinews-content/
├── scripts/
│   ├── config.py              # RSS feed'leri, prompt, CEFR tanımları
│   ├── rss_fetcher.py         # feedparser ile haber çekme
│   ├── ai_simplifier.py       # Provider-agnostic AI katmanı (Gemini + Claude)
│   └── generate_articles.py   # Ana orchestration
├── output/
│   └── articles.json          # Üretilen içerik (iOS buradan okur)
└── .github/workflows/
    └── generate.yml           # Günlük cron
```
