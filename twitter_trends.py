"""
X (Twitter) Canlı Trendler ve Viral Tweet Toplayıcı
"""
import logging
from twikit import Client
from config import COOKIES_FILE
from rss_fetcher import load_history

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TURKEY_WOEID = 23424969  # Türkiye WOEID kodu


async def fetch_viral_turkish_tweets(limit=5):
    """
    X Türkiye canlı trendlerini tarar ve en çok etkileşim alan viral tweetleri getirir.
    Daha önce alıntılanmış olanları eler.
    """
    client = Client(language="tr-TR", impersonate="chrome124")
    client.load_cookies(str(COOKIES_FILE))

    history = set(load_history())
    candidates = []

    try:
        logging.info("Türkiye canlı X trendleri alınıyor...")
        trends_resp = await client.get_place_trends(TURKEY_WOEID)
        trends_list = trends_resp.get("trends", [])

        # Reklam veya siyasi spam etiketleri temizlemek için basit filtre
        selected_topics = []
        for t in trends_list:
            name = getattr(t, "name", str(t))
            # Çok uzun veya şüpheli bot etiketlerini atla
            if len(name) > 30:
                continue
            selected_topics.append(name)
            if len(selected_topics) >= 6:
                break

        logging.info(f"Taranacak Trendler: {selected_topics}")

        for topic in selected_topics:
            try:
                # En popüler (Top) tweetleri ara
                tweets = await client.search_tweet(topic, product="Top")
                for tw in tweets[:4]:
                    tweet_url = f"https://x.com/{tw.user.screen_name}/status/{tw.id}"
                    if tweet_url in history or str(tw.id) in history:
                        continue

                    # Sadece etkileşim almış (en az 50 beğeni) organik tweetleri seç
                    fav_count = getattr(tw, "favorite_count", 0) or 0
                    rt_count = getattr(tw, "retweet_count", 0) or 0

                    if fav_count < 30 and rt_count < 5:
                        continue

                    # Tweet metninin temizliği
                    clean_text = tw.text.strip()
                    if len(clean_text) < 20:
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

                    if len(candidates) >= limit:
                        break
            except Exception as err:
                logging.warning(f"Trend araması hatası ({topic}): {err}")

            if len(candidates) >= limit:
                break

    except Exception as e:
        logging.error(f"X Trendleri çekilirken hata: {e}")

    logging.info(f"Toplam {len(candidates)} adet viral tweet adayı bulundu.")
    return candidates
