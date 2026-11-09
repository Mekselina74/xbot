"""
RSS Haber Toplayıcı Modülü
"""
import json
import logging
from datetime import datetime
from bs4 import BeautifulSoup
import feedparser
from config import HISTORY_FILE, MAX_HISTORY_ITEMS, RSS_SOURCES

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def load_history():
    """Daha önce paylaşılan haberlerin linklerini yükler."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Geçmiş dosyası okunamadı, sıfırlanıyor: {e}")
    return []


def save_history(history_list):
    """Paylaşılan linkleri kaydeder, liste şişmesin diye limitler."""
    if len(history_list) > MAX_HISTORY_ITEMS:
        history_list = history_list[-MAX_HISTORY_ITEMS:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=2)


def clean_html(raw_html):
    """HTML etiketlerini temizleyip düz metin bırakır."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def fetch_candidate_news(category=None, limit_per_source=5):
    """
    Belirtilen kategorideki (veya tüm kategorilerdeki) yeni haberleri çeker.
    Daha önce paylaşılmış olanları eler.
    """
    history = set(load_history())
    candidates = []

    categories_to_check = [category] if category and category in RSS_SOURCES else RSS_SOURCES.keys()

    for cat in categories_to_check:
        for source in RSS_SOURCES[cat]:
            try:
                logging.info(f"Haberler çekiliyor: {source['name']} ({cat})")
                feed = feedparser.parse(source["url"])

                for entry in feed.entries[:limit_per_source]:
                    link = entry.get("link", "").strip()
                    if not link or link in history:
                        continue

                    title = entry.get("title", "").strip()
                    summary_raw = entry.get("summary", "") or entry.get("description", "")
                    summary = clean_html(summary_raw)

                    # Boş veya çok kısa içerikleri atla
                    if len(title) < 10:
                        continue

                    candidates.append({
                        "category": cat,
                        "source": source["name"],
                        "title": title,
                        "summary": summary,
                        "link": link,
                        "published": entry.get("published", "")
                    })
            except Exception as e:
                logging.error(f"RSS hatası ({source['name']}): {e}")

    logging.info(f"Toplam {len(candidates)} adet paylaşılmamış yeni haber bulundu.")
    return candidates
