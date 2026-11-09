"""
X Haber Küratörü ve Otomasyon Ana Çalıştırıcı
"""
import os
import sys
import random
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv

from config import RSS_SOURCES
from rss_fetcher import fetch_candidate_news, load_history, save_history
from ai_curator import select_and_craft_tweet
from twitter_client import post_tweet

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def pick_category():
    """
    Günün saatine ve ağırlıklara göre bir kategori seçer:
    %60 Teknoloji, %25 Spor, %15 Popüler/Gündem
    """
    categories = ["tech", "sports", "general"]
    weights = [0.60, 0.25, 0.15]
    chosen = random.choices(categories, weights=weights, k=1)[0]
    return chosen


def run(dry_run=False, category=None):
    logging.info("=" * 50)
    logging.info("X Haber Küratörü Başlatıldı")
    logging.info("=" * 50)

    # 1. Kategori Belirle
    target_category = category if category else pick_category()
    logging.info(f"Hedef Kategori: {target_category}")

    # 2. RSS Kaynaklarından Yeni Haberleri Çek
    candidates = fetch_candidate_news(category=target_category)
    if not candidates:
        logging.info(f"'{target_category}' kategorisinde yeni haber bulunamadı, tüm kategorilere bakılıyor...")
        candidates = fetch_candidate_news(category=None)

    if not candidates:
        logging.warning("Paylaşılacak yeni bir haber bulunamadı. Tüm haberler daha önce paylaşılmış olabilir.")
        return

    # 3. Gemini ile En İyi Haberi Seç ve Tweet Oluştur
    logging.info(f"{len(candidates)} adet aday arasından Gemini ile haber seçiliyor...")
    curation_result = select_and_craft_tweet(candidates, preferred_category=target_category)

    tweet_text = curation_result["tweet_text"]
    news_link = curation_result["link"]
    reason = curation_result["reason"]

    logging.info("-" * 40)
    logging.info(f"Seçim Gerekçesi: {reason}")
    logging.info("Oluşturulan Tweet:\n" + tweet_text)
    logging.info("-" * 40)

    # 4. Paylaşım Aşaması
    if dry_run:
        logging.info("[DRY RUN AKTİF] Tweet gerçekte atılmadı. Test başarıyla tamamlandı.")
        return

    try:
        post_tweet(tweet_text)
        
        # 5. Başarılı olduysa geçmişe ekle
        history = load_history()
        history.append(news_link)
        save_history(history)
        logging.info(f"Haber geçmişe eklendi ({news_link}). Süreç tamamlandı.")

    except Exception as e:
        logging.error(f"Tweet paylaşımı sırasında hata oluştu: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="X Otomatik Haber Paylaşım Botu")
    parser.add_argument("--dry-run", action="store_true", help="Tweet'i atmadan sadece çıktıyı gösterir")
    parser.add_argument("--category", choices=["tech", "sports", "general"], help="Belirli bir kategori seçer")
    args = parser.parse_args()

    run(dry_run=args.dry_run, category=args.category)
