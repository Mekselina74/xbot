"""
X News Curator - Yapılandırma ve Çerez Yönetimi
"""
import os
import json
import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
HISTORY_FILE = BASE_DIR / "history.json"
COOKIES_FILE = BASE_DIR / "cookies.json"


def load_client_cookies(client):
    """
    Çerezleri hem bulutta (TWITTER_COOKIES ortam değişkeni) hem yerelde (cookies.json)
    dosya bağımlılığı olmadan doğrudan belleğe yükler.
    """
    env_cookies = os.getenv("TWITTER_COOKIES")
    if env_cookies:
        try:
            raw = env_cookies.strip()
            # Eğer tırnaklarla sarmalanmışsa temizle
            if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
                raw = raw[1:-1]
            data = json.loads(raw)
            client.set_cookies(data)
            logging.info("Çerezler TWITTER_COOKIES ortam değişkeninden başarıyla yüklendi.")
            return True
        except Exception as e:
            logging.error(f"TWITTER_COOKIES JSON ayrıştırma hatası: {e}")

    # Ortam değişkeni yoksa yerel dosyadan dene
    if COOKIES_FILE.exists():
        client.load_cookies(str(COOKIES_FILE))
        logging.info("Çerezler yerel cookies.json dosyasından yüklendi.")
        return True

    raise FileNotFoundError(
        "X çerezleri bulunamadı! Lütfen Render panelinde Environment Variables altına "
        "TWITTER_COOKIES değişkenini eklediğinizden emin olun."
    )


# Takip edilecek RSS kaynakları (Kategorilere ayrılmış)
RSS_SOURCES = {
    "tech": [
        {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
        {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
        {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
        {"name": "Engadget", "url": "https://www.engadget.com/rss.xml"},
    ],
    "sports": [
        {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/rss.xml"},
        {"name": "ESPN Top News", "url": "https://www.espn.com/espn/rss/news"},
        {"name": "Sky Sports", "url": "https://www.skysports.com/rss/12040"},
    ],
    "general": [
        {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
        {"name": "The Guardian World", "url": "https://www.theguardian.com/world/rss"},
    ]
}

# Takip Edilecek Özel Hesaplar
SPECIAL_ACCOUNTS = [
    "turkce_dusun"
]

# Varsayılan Gemini Modeli
GEMINI_MODEL = "gemini-3.5-flash-lite"

# Geçmişte paylaşılan kaç link saklansın
MAX_HISTORY_ITEMS = 500
