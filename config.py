"""
X News Curator - Yapılandırma ve Kaynak Listesi
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
HISTORY_FILE = BASE_DIR / "history.json"
COOKIES_FILE = BASE_DIR / "cookies.json"

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

# Takip Edilecek Özel Hesaplar (Arkadaş / Kaliteli İçerik Üretenler)
SPECIAL_ACCOUNTS = [
    "turkce_dusun"
]

# Gemini Model Ayarları
GEMINI_MODEL = "gemini-3.1-flash-lite"

# Geçmişte paylaşılan kaç link saklansın
MAX_HISTORY_ITEMS = 500
