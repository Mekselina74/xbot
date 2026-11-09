"""
X (Twitter) Canlı Trendler, Kategori Bazlı Viral Tweetler ve Özel Hesap Takipçisi
"""
import random
import logging
from twikit import Client
from config import COOKIES_FILE, SPECIAL_ACCOUNTS
from rss_fetcher import load_history

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TURKEY_WOEID = 23424969  # Türkiye WOEID kodu

# Kategori bazlı gelişmiş X arama filtreleri
CATEGORY_QUERIES = {
    "spor": "(Galatasaray OR Fenerbahce OR Besiktas OR futbol OR hakem OR transfer OR 'Süper Lig' OR maç) min_faves:80 lang:tr",
    "haber": "('son dakika' OR sondakika OR gündem OR haber OR açıklama OR karar) min_faves:80 lang:tr",
    "mizah": "('şaka gibi' OR 'yok artık' OR koptum OR komik OR kahkaha OR ahahah OR 'bu ne abi') min_faves:80 lang:tr",
    "tekno": "('yapay zeka' OR teknoloji OR robot OR openai OR nvidia OR apple OR yazılım OR chatgpt) min_faves:30 lang:tr",
}


async def fetch_user_tweets(screen_name="turkce_dusun", limit=5):
    """
    Belirli bir X kullanıcısının son tweetlerini çeker.
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


async def fetch_viral_turkish_tweets(category=None, limit=15):
    """
    X Türkiye viral tweetlerini çeker.
    Eğer 'category' belirtilmişse (spor, haber, mizah, tekno) o alandaki viralleri arar.
    Belirtilmemişse canlı Trend Topic (TT) listesini tarar.
    """
    client = Client(language="tr-TR", impersonate="chrome124")
    client.load_cookies(str(COOKIES_FILE))

    history = set(load_history())
    candidates = []

    try:
        # 1. Kategori bazlı arama
        if category and category in CATEGORY_QUERIES:
            query = CATEGORY_QUERIES[category]
            logging.info(f"'{category.upper()}' kategorisi için viral tweetler aranıyor: {query}")
            tweets = await client.search_tweet(query, product="Top")

            for tw in tweets[:limit * 2]:
                tweet_url = f"https://x.com/{tw.user.screen_name}/status/{tw.id}"
                if tweet_url in history or str(tw.id) in history:
                    continue

                fav_count = getattr(tw, "favorite_count", 0) or 0
                rt_count = getattr(tw, "retweet_count", 0) or 0
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
                    "topic": f"Viral {category.capitalize()}"
                })
                if len(candidates) >= limit:
                    break

        # 2. Genel canlı Trend Topic taraması
        else:
            logging.info("Türkiye canlı Trend Topic listesi taranıyor...")
            trends_resp = await client.get_place_trends(TURKEY_WOEID)
            trends_list = trends_resp.get("trends", [])

            selected_topics = []
            for t in trends_list:
                name = getattr(t, "name", str(t))
                if len(name) > 30:
                    continue
                selected_topics.append(name)

            random.shuffle(selected_topics)
            topics_to_scan = selected_topics[:8]

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
        logging.error(f"Viral tweetler çekilirken hata: {e}")

    random.shuffle(candidates)
    logging.info(f"Toplam {len(candidates)} adet viral tweet adayı toplandı.")
    return candidates
