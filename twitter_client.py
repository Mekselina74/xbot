"""
X (Twitter) Paylaşım İstemcisi (Standart Tweet ve Alıntı Tweet Desteği)
"""
import os
import sys
import logging
import asyncio

# Windows üzerinde curl_cffi için selector ayarı
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from twikit import Client
from config import COOKIES_FILE

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def ensure_cookies():
    """Bulut (GitHub Actions) veya yerel ortamda cookies.json dosyasının varlığını kontrol eder."""
    env_cookies = os.getenv("TWITTER_COOKIES")
    if env_cookies and not COOKIES_FILE.exists():
        logging.info("Ortam değişkeninden TWITTER_COOKIES okundu, cookies.json oluşturuluyor...")
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            f.write(env_cookies.strip())


async def async_post_tweet(tweet_text: str, attachment_url: str | None = None):
    """
    Twikit/twifork kullanarak oturum çerezleri üzerinden tweet veya alıntı tweet (Quote Tweet) paylaşır.
    """
    ensure_cookies()

    if not COOKIES_FILE.exists():
        raise FileNotFoundError(
            f"Oturum dosyası bulunamadı: {COOKIES_FILE}\n"
            "Lütfen önce 'python login_helper.py' çalıştırarak çerezleri oluşturun."
        )

    client = Client(language="tr-TR", impersonate="chrome124")

    try:
        logging.info("Oturum çerezleri yükleniyor...")
        client.load_cookies(str(COOKIES_FILE))

        logging.info("Tweet paylaşılıyor...")
        logging.info(f"Tweet metni: {tweet_text}")
        if attachment_url:
            logging.info(f"Alıntılanan Tweet URL: {attachment_url}")

        is_note = len(tweet_text) > 270
        try:
            response = await client.create_tweet(
                text=tweet_text,
                attachment_url=attachment_url,
                is_note_tweet=is_note
            )
        except Exception as e:
            if is_note and "shorter" in str(e).lower():
                logging.warning("Metin 270 karaktere sığdırılıyor...")
                response = await client.create_tweet(
                    text=tweet_text[:260] + "...",
                    attachment_url=attachment_url,
                    is_note_tweet=False
                )
            else:
                raise

        tweet_id = getattr(response, "id", None)
        logging.info(f"Tweet başarıyla paylaşıldı! Tweet ID: {tweet_id}")
        return response

    except Exception as e:
        logging.error(f"Tweet atılırken hata meydana geldi: {e}")
        raise


def post_tweet(tweet_text: str, attachment_url: str | None = None):
    """Senkron çağırma yardımcısı."""
    return asyncio.run(async_post_tweet(tweet_text, attachment_url))
