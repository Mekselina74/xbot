"""
X (Twitter) Canlı Trendler, Viral Tweetler ve Özel Hesap Takipçisi
"""
import random
import logging
from twikit import Client
from config import COOKIES_FILE, SPECIAL_ACCOUNTS
from rss_fetcher import load_history

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TURKEY_WOEID = 23424969  # Türkiye WOEID kodu


async def fetch_user_tweets(screen_name="turkce_dusun", limit=5):
    """
    Belirli bir X kullanıcısının (örn: @turkce_dusun) son tweetlerini çeker.
    Daha önce alıntılanmış olanları eler.
    """
    client = Client(language="tr-TR", impersonate="chrome124")
    client.load_cookies(str(COOKIES_FILE))

    history = set(load_history())
    candidates = []

    try:
        logging.info(f"@{screen_name} kullanıcısının son tweetleri alınıyor...")
        user = await client.get_user_by_screen_name(screen_name)
        tweets = await user.get_tweets("Tweets", count=10)

        for tw in tweets:
            tweet_url = f"https://x.com/{tw.user.screen_name}/status/{tw.id}"
            if tweet_url in history or str(tw.id) in history:
                continue

            clean_text = tw.text.strip()
            if len(clean_text) < 15:
                continue

            candidates.append({
                "id": str(tw.id),
                "url": tweet_url,
                "author_name": tw.user.name,
                "author_username": tw.user.screen_name,
                "text": clean_text,
                "likes": getattr(tw, "favorite_count", 0) or 0,
                "retweets": getattr(tw, "retweet_count", 0) or 0,
                "topic": f"@{screen_name} Özel Paylaşım"
            })
            if len(candidates) >= limit:
                break

    except Exception as e:
        logging.error(f"Kullanıcı tweetleri çekilirken hata (@{screen_name}): {e}")

    logging.info(f"@{screen_name} hesabından {len(candidates)} adet yeni tweet bulundu.")
    return candidates


async def fetch_viral_turkish_tweets(limit=15):
    """
    X Türkiye canlı trendlerini tarar ve en çok etkileşim alan viral tweetleri getirir.
    Daha önce alıntılanmış olanları eler ve çeşitlilik için farklı trendleri harmanlar.
    """
    client = Client(language="tr-TR", impersonate="chrome124")
    client.load_cookies(str(COOKIES_FILE))

    history = set(load_history())
    candidates = []

    try:
        logging.info("Türkiye canlı X trendleri taranıyor...")
        trends_resp = await client.get_place_trends(TURKEY_WOEID)
        trends_list = trends_resp.get("trends", [])

        # Reklam veya siyasi bot etiketlerini temizle
        selected_topics = []
        for t in trends_list:
            name = getattr(t, "name", str(t))
            if len(name) > 30:
                continue
            selected_topics.append(name)

        # Çeşitlilik için trend sırasını karıştır
        random.shuffle(selected_topics)
        topics_to_scan = selected_topics[:8]
        logging.info(f"Taranacak Çeşitli Trendler: {topics_to_scan}")

        for topic in topics_to_scan:
            try:
                tweets = await client.search_tweet(topic, product="Top")
                for tw in tweets[:5]:
                    tweet_url = f"https://x.com/{tw.user.screen_name}/status/{tw.id}"
                    if tweet_url in history or str(tw.id) in history:
                        continue

                    fav_count = getattr(tw, "favorite_count", 0) or 0
                    rt_count = getattr(tw, "retweet_count", 0) or 0

                    if fav_count < 30 and rt_count < 5:
                        continue

                    clean_text = tw.text.strip()
                    if len(clean_text) < 15:
                        continue

                    candidates.append({
                        "id": str(tw.id),
                        "url": tweet_url,
                        "author_name": tw.user.name,
                        "author_username": tw.user.screen_name,
                        "text": clean_text,
                        "likes": fav_count,
                        "retweets": rt_count,
                        "topic": topic
                    })
            except Exception as err:
                logging.warning(f"Trend araması hatası ({topic}): {err}")

            if len(candidates) >= limit:
                break

    except Exception as e:
        logging.error(f"X Trendleri çekilirken hata: {e}")

    random.shuffle(candidates)
    logging.info(f"Toplam {len(candidates)} adet benzersiz viral tweet adayı toplandı.")
    return candidates
