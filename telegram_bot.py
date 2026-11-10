"""
X (Twitter) Telegram Onay ve Yönetim Botu
- RSS Haberleri & Gemini Tweet Üretimi
- X Türkiye Canlı Trendleri ve Viral Tweetleri Alıntılama (Quote Tweet)
- Kullanıcının Kendi Yorumunu Yazarak Alıntılama Desteği
"""
import os
import sys
import uuid
import logging
from pathlib import Path
from dotenv import load_dotenv

# Windows terminal UTF-8 desteği
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Windows üzerinde curl_cffi için selector ayarı
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import RSS_SOURCES
from rss_fetcher import fetch_candidate_news, load_history, save_history
from ai_curator import select_and_craft_tweet, generate_viral_quote_comment
from twitter_client import async_post_tweet
from twitter_trends import fetch_viral_turkish_tweets, fetch_user_tweets

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK - X News Bot is Running!")

    def log_message(self, format, *args):
        pass  # Gereksiz HTTP loglarını gizle

def start_health_check_server():
    """Render.com gibi bulut sağlayıcılarının kapanmaması için basit HTTP sağlık portu dinler."""
    port = int(os.getenv("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        logging.info(f"Bulut sağlık kontrolü sunucusu port {port} üzerinde başlatıldı.")
    except Exception as e:
        logging.warning(f"Sağlık kontrolü sunucusu başlatılamadı (yerel ortam olabilir): {e}")

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Bellek nesneleri
PENDING_DRAFTS = {}     # {draft_id: {type: 'news'|'viral', text: ..., url: ..., ...}}
USER_STATES = {}        # {chat_id: {draft_id: ..., mode: 'quote'|'news'}}
CUSTOM_COMMENTS = {}    # {draft_id: user_comment_text}
SEEN_VIRAL_IDS = set()  # Kullanıcıya gösterilen ve "Başka Bul" denilen tweetler
SEEN_NEWS_URLS = set()  # Kullanıcıya gösterilen ve "Başka Bul" denilen haberler


def check_auth(update: Update) -> bool:
    """Yalnızca yetkili kullanıcının erişimine izin verir."""
    if not ALLOWED_CHAT_ID:
        return True
    chat_id = str(update.effective_chat.id)
    return chat_id == str(ALLOWED_CHAT_ID)


async def send_special_account_draft(chat_id: int, context: ContextTypes.DEFAULT_TYPE, screen_name="turkce_dusun"):
    """Özel takip edilen hesabın (@turkce_dusun) son tweetlerini alıp alıntılama taslağı sunar."""
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🌟 @{screen_name} hesabının son paylaşımları taranıyor..."
    )

    try:
        tweets = await fetch_user_tweets(screen_name=screen_name, limit=6)
        available = [tw for tw in tweets if tw["id"] not in SEEN_VIRAL_IDS]
        if not available and tweets:
            SEEN_VIRAL_IDS.clear()
            available = tweets

        if not available:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ @{screen_name} hesabından yeni tweet bulunamadı."
            )
            return

        selected_tw = available[0]
        SEEN_VIRAL_IDS.add(selected_tw["id"])

        curation = generate_viral_quote_comment(selected_tw)
        draft_id = str(uuid.uuid4())[:8]

        PENDING_DRAFTS[draft_id] = {
            "type": "viral",
            "suggested_comment": curation["suggested_comment"],
            "url": selected_tw["url"],
            "author_username": selected_tw["author_username"],
            "author_name": selected_tw["author_name"],
            "text": selected_tw["text"],
            "topic": selected_tw["topic"],
            "likes": selected_tw["likes"],
            "retweets": selected_tw["retweets"],
        }

        message_text = (
            f"🌟 **@{selected_tw['author_username']} ({selected_tw['author_name']}) Paylaşımı:**\n\n"
            f"\"{selected_tw['text']}\"\n\n"
            f"❤️ {selected_tw['likes']} Beğeni | 🔁 {selected_tw['retweets']} Retweet\n"
            f"🔗 {selected_tw['url']}\n\n"
            f"🤖 **Gemini'ın Önerdiği Alıntı Yorumu:**\n"
            f"\"{curation['suggested_comment']}\""
        )

        keyboard = [
            [InlineKeyboardButton("✅ Önerilen Yorumla Alıntıla", callback_data=f"quote_sug_{draft_id}")],
            [InlineKeyboardButton("✍️ Kendi Yorumumu Yazıp Alıntıla", callback_data=f"quote_custom_{draft_id}")],
            [
                InlineKeyboardButton("🔄 Başka Tweetini Getir", callback_data=f"another_friend_{screen_name}"),
                InlineKeyboardButton("❌ Pas Geç", callback_data=f"skip_{draft_id}")
            ]
        ]

        await context.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logging.error(f"Özel hesap taslak hatası: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Hata: {str(e)[:200]}")


async def send_viral_draft(chat_id: int, context: ContextTypes.DEFAULT_TYPE, category=None):
    """X Türkiye canlı trendlerinden veya belirli bir kategoriden (spor, haber, mizah, tekno) viral tweet bulur."""
    cat_label = f"Viral {category.upper()}" if category else "X Türkiye Canlı Gündemi"
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔥 {cat_label} taranıyor, viral içerikler toplanıyor..."
    )

    try:
        virals = await fetch_viral_turkish_tweets(category=category, limit=15)
        # Daha önce kullanıcıya gösterilmiş olanları filtrele
        available = [tw for tw in virals if tw["id"] not in SEEN_VIRAL_IDS]
        if not available and virals:
            SEEN_VIRAL_IDS.clear()
            available = virals

        if not available:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ {cat_label} alanında uygun yeni viral tweet bulunamadı."
            )
            return

        # Listeden yeni olan ilk tweeti seç ve görüldü olarak işaretle
        selected_tw = available[0]
        SEEN_VIRAL_IDS.add(selected_tw["id"])
        curation = generate_viral_quote_comment(selected_tw)
        draft_id = str(uuid.uuid4())[:8]

        PENDING_DRAFTS[draft_id] = {
            "type": "viral",
            "suggested_comment": curation["suggested_comment"],
            "url": selected_tw["url"],
            "author_username": selected_tw["author_username"],
            "author_name": selected_tw["author_name"],
            "text": selected_tw["text"],
            "topic": selected_tw["topic"],
            "likes": selected_tw["likes"],
            "retweets": selected_tw["retweets"],
            "category": category
        }

        message_text = (
            f"🔥 **{selected_tw['topic']}**\n\n"
            f"👤 **@{selected_tw['author_username']} ({selected_tw['author_name']}):**\n"
            f"\"{selected_tw['text']}\"\n\n"
            f"❤️ {selected_tw['likes']} Beğeni | 🔁 {selected_tw['retweets']} Retweet\n"
            f"🔗 {selected_tw['url']}\n\n"
            f"🤖 **Gemini'ın Önerdiği Alıntı Yorumu:**\n"
            f"\"{curation['suggested_comment']}\""
        )

        keyboard = [
            [InlineKeyboardButton("✅ Önerilen Yorumla Alıntıla", callback_data=f"quote_sug_{draft_id}")],
            [InlineKeyboardButton("✍️ Kendi Yorumumu Yazıp Alıntıla", callback_data=f"quote_custom_{draft_id}")],
            [
                InlineKeyboardButton("🔄 Başka Viral Bul", callback_data=f"another_viral_{category or 'all'}"),
                InlineKeyboardButton("❌ Pas Geç", callback_data=f"skip_{draft_id}")
            ]
        ]

        await context.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logging.error(f"Viral taslak hatası: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Hata: {str(e)[:200]}")


async def send_news_draft(chat_id: int, context: ContextTypes.DEFAULT_TYPE, category=None):
    """RSS haberlerinden bir taslak üretir."""
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔍 {'Tüm kategorilerden' if not category else category.upper() + ' kategorisinden'} haberler taranıyor..."
    )

    try:
        candidates = fetch_candidate_news(category=category)
        if not candidates and category:
            candidates = fetch_candidate_news(category=None)

        # Kullanıcıya daha önce gösterilmiş haberleri filtrele
        available = [c for c in candidates if c["link"] not in SEEN_NEWS_URLS]
        if not available and candidates:
            SEEN_NEWS_URLS.clear()
            available = candidates

        if not available:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Paylaşılacak yeni haber bulunamadı.")
            return

        curation = select_and_craft_tweet(available, preferred_category=category)
        SEEN_NEWS_URLS.add(curation["link"])
        draft_id = str(uuid.uuid4())[:8]

        PENDING_DRAFTS[draft_id] = {
            "type": "news",
            "tweet_text": curation["tweet_text"],
            "url": curation["link"],
            "category": curation["original_news"].get("category", "haber"),
            "source": curation["original_news"].get("source", "Kaynak")
        }

        message_text = (
            f"📰 **Yeni Haber Taslağı Hazır!**\n\n"
            f"📌 **Gerekçe:** {curation.get('reason', '')}\n\n"
            f"📝 **Önerilen Tweet:**\n{curation['tweet_text']}\n\n"
            f"🏷️ #{curation['original_news'].get('category', 'haber')} | Kaynak: {curation['original_news'].get('source')}"
        )

        keyboard = [
            [InlineKeyboardButton("✅ Bu Metinle Tweetle", callback_data=f"tweet_sug_{draft_id}")],
            [InlineKeyboardButton("✍️ Kendi Yorumumu Yaz", callback_data=f"news_custom_{draft_id}")],
            [
                InlineKeyboardButton("🔄 Başka Haber", callback_data=f"another_news_{category or 'all'}"),
                InlineKeyboardButton("❌ Pas Geç", callback_data=f"skip_{draft_id}")
            ]
        ]

        await context.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logging.error(f"Haber taslağı hatası: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Hata: {str(e)[:200]}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komutu."""
    if not check_auth(update):
        return

    text = (
        "👋 Merhaba Eray! X (@e_raybs) Asistanınız Tam Kontrolünüzde.\n\n"
        "⚡ Neler Yapabilirsiniz?\n"
        "• /viral veya /trend ➔ X Türkiye'de o an viral olan bir tweeti/videoyu bulur ve alıntılama taslağı sunar\n"
        "• /haber veya /yeni ➔ Güncel küresel teknoloji/spor haberlerinden tweet taslağı üretir\n"
        "• /teknoloji, /spor, /gundem ➔ Kategoriye özel haber getirir\n\n"
        "💡 Kendi Yorumunuzu Katma:\n"
        "Taslağın altındaki [✍️ Kendi Yorumumu Yaz] butonuna basıp istediğiniz cümleyi yazarak doğrudan alıntılayabilirsiniz!"
    )
    await update.message.reply_text(text)


async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buton tıklamalarını yönetir."""
    query = update.callback_query
    await query.answer()

    if not check_auth(update):
        return

    data = query.data
    chat_id = update.effective_chat.id

    # 1. Önerilen Yorumla Alıntıla (Viral)
    if data.startswith("quote_sug_"):
        draft_id = data.replace("quote_sug_", "")
        draft = PENDING_DRAFTS.get(draft_id)
        if not draft:
            await query.edit_message_text("⚠️ Bu taslak artık geçerli değil.")
            return

        await query.edit_message_text("⏳ Viral tweet alıntılanıyor (Quote Tweet)...")
        try:
            await async_post_tweet(
                tweet_text=draft["suggested_comment"],
                attachment_url=draft["url"]
            )
            history = load_history()
            history.append(draft["url"])
            save_history(history)
            del PENDING_DRAFTS[draft_id]

            await query.edit_message_text(
                f"🎉 **TWEET BAŞARIYLA ALINTILANDI!**\n\n"
                f"💬 **Yorumunuz:** {draft['suggested_comment']}\n"
                f"🔗 **Alıntılanan Tweet:** {draft['url']}"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Alıntılama sırasında hata oluştu:\n{e}")

    # 2. Önerilen Metinle Tweetle (Haber)
    elif data.startswith("tweet_sug_"):
        draft_id = data.replace("tweet_sug_", "")
        draft = PENDING_DRAFTS.get(draft_id)
        if not draft:
            await query.edit_message_text("⚠️ Bu taslak artık geçerli değil.")
            return

        await query.edit_message_text("⏳ Tweet gönderiliyor...")
        try:
            await async_post_tweet(tweet_text=draft["tweet_text"])
            history = load_history()
            history.append(draft["url"])
            save_history(history)
            del PENDING_DRAFTS[draft_id]

            await query.edit_message_text(
                f"🎉 **TWEET BAŞARIYLA PAYLAŞILDI!**\n\n"
                f"📝 {draft['tweet_text']}"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Hata: {e}")

    # 3. Kendi Yorumunu Yaz (Viral Alıntılama)
    elif data.startswith("quote_custom_"):
        draft_id = data.replace("quote_custom_", "")
        draft = PENDING_DRAFTS.get(draft_id)
        if not draft:
            await query.edit_message_text("⚠️ Taslak bulunamadı.")
            return

        USER_STATES[chat_id] = {"draft_id": draft_id, "mode": "quote"}
        await query.message.reply_text(
            f"✍️ **@{draft['author_username']}** kullanıcısının bu paylaşımını alıntılarken yazmak istediğiniz yorumu hemen buraya mesaj olarak yazıp gönderin:"
        )

    # 4. Kendi Metnini Yaz (Haber)
    elif data.startswith("news_custom_"):
        draft_id = data.replace("news_custom_", "")
        draft = PENDING_DRAFTS.get(draft_id)
        if not draft:
            await query.edit_message_text("⚠️ Taslak bulunamadı.")
            return

        USER_STATES[chat_id] = {"draft_id": draft_id, "mode": "news"}
        await query.message.reply_text(
            f"✍️ Bu haberle ilgili paylaşmak istediğiniz kendi tweet metninizi buraya yazıp gönderin (link otomatik eklenecektir):"
        )

    # 5. Pas Geç
    elif data.startswith("skip_"):
        draft_id = data.replace("skip_", "")
        draft = PENDING_DRAFTS.get(draft_id)
        if draft:
            history = load_history()
            history.append(draft["url"])
            save_history(history)
            del PENDING_DRAFTS[draft_id]
        await query.edit_message_text("❌ Bu içerik pas geçildi.")

    # 6. Başka Viral / Haber
    elif data.startswith("another_viral"):
        cat = data.replace("another_viral_", "").replace("another_viral", "")
        cat_arg = None if (not cat or cat == "all") else cat
        await query.edit_message_text(f"🔄 {'Viral ' + cat_arg.upper() if cat_arg else 'Viral'} içerik aranıyor...")
        await send_viral_draft(chat_id, context, category=cat_arg)

    elif data.startswith("menu_viral_"):
        cat = data.replace("menu_viral_", "")
        cat_arg = None if cat == "all" else cat
        await query.edit_message_text(f"🎯 {'Viral ' + cat_arg.upper() if cat_arg else 'Genel Gündem'} taranıyor...")
        await send_viral_draft(chat_id, context, category=cat_arg)

    elif data.startswith("another_friend_"):
        sn = data.replace("another_friend_", "")
        await query.edit_message_text(f"🔄 @{sn} hesabından başka tweet aranıyor...")
        await send_special_account_draft(chat_id, context, screen_name=sn)

    elif data.startswith("another_news_"):
        cat = data.replace("another_news_", "")
        cat_arg = None if cat == "all" else cat
        await query.edit_message_text("🔄 Başka bir haber aranıyor...")
        await send_news_draft(chat_id, context, category=cat_arg)

    # 7. Kullanıcının Kendi Yorumunu Onaylaması
    elif data.startswith("confirm_custom_"):
        draft_id = data.replace("confirm_custom_", "")
        draft = PENDING_DRAFTS.get(draft_id)
        user_comment = CUSTOM_COMMENTS.get(draft_id)

        if not draft or not user_comment:
            await query.edit_message_text("⚠️ Taslak veya yorum zaman aşımına uğramış.")
            return

        await query.edit_message_text("⏳ Özel yorumunuzla X'te paylaşılıyor...")
        try:
            if draft["type"] == "viral":
                # Alıntı tweet (Quote Tweet)
                await async_post_tweet(
                    tweet_text=user_comment,
                    attachment_url=draft["url"]
                )
            else:
                # Normal haber tweeti + link
                full_text = f"{user_comment}\n\n{draft['url']}"
                await async_post_tweet(tweet_text=full_text)

            history = load_history()
            history.append(draft["url"])
            save_history(history)

            del PENDING_DRAFTS[draft_id]
            CUSTOM_COMMENTS.pop(draft_id, None)

            await query.edit_message_text(
                f"🎉 **ÖZEL YORUMUNUZLA BAŞARIYLA PAYLAŞILDI!**\n\n"
                f"💬 **Yorumunuz:** {user_comment}\n"
                f"🔗 **Hedef Link:** {draft['url']}"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Paylaşım sırasında hata oluştu:\n{e}")


async def handle_user_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcının Telegram'a yazdığı özel yorumları yakalar."""
    if not check_auth(update):
        return

    chat_id = update.effective_chat.id
    user_state = USER_STATES.get(chat_id)

    if not user_state:
        # Beklenen bir yorum yoksa genel yanıt ver
        await update.message.reply_text(
            "Yeni bir içerik aramak için komutları kullanabilirsiniz:\n"
            "• `/viral` ➔ X Türkiye'de viral olan içerikleri bulur\n"
            "• `/haber` ➔ Güncel haber taslağı üretir"
        )
        return

    draft_id = user_state["draft_id"]
    draft = PENDING_DRAFTS.get(draft_id)

    if not draft:
        USER_STATES.pop(chat_id, None)
        await update.message.reply_text("⚠️ Taslak bulunamadı veya süresi doldu.")
        return

    user_comment = update.message.text.strip()
    CUSTOM_COMMENTS[draft_id] = user_comment
    USER_STATES.pop(chat_id, None)

    preview_text = (
        f"📋 **Alıntı Önizlemesi:**\n\n"
        f"✍️ **Sizin Yorumunuz:**\n\"{user_comment}\"\n\n"
        f"🔗 **Alıntılanacak Paylaşım:**\n{draft['url']}"
    )

    keyboard = [
        [InlineKeyboardButton("🚀 Onayla ve X'te Alıntıla", callback_data=f"confirm_custom_{draft_id}")],
        [InlineKeyboardButton("❌ İptal Et", callback_data=f"skip_{draft_id}")]
    ]

    await update.message.reply_text(
        preview_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def category_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcıya tek tıkla kategori seçebileceği buton menüsü sunar."""
    if not check_auth(update):
        return

    text = (
        "🎯 Hangi alanda içerik/viral aramak istersiniz?\n\n"
        "Aşağıdaki butonlara dokunarak o kategorideki en popüler paylaşımları anında getirebilirsiniz:"
    )

    keyboard = [
        [
            InlineKeyboardButton("⚽ Viral Spor", callback_data="menu_viral_spor"),
            InlineKeyboardButton("📰 Viral Gündem/Haber", callback_data="menu_viral_haber")
        ],
        [
            InlineKeyboardButton("😂 Viral Mizah/Komik", callback_data="menu_viral_mizah"),
            InlineKeyboardButton("🚀 Viral Teknoloji/AI", callback_data="menu_viral_tekno")
        ],
        [
            InlineKeyboardButton("🌟 @turkce_dusun", callback_data="another_friend_turkce_dusun"),
            InlineKeyboardButton("🎲 Canlı Trendler (Genel)", callback_data="menu_viral_all")
        ]
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def router_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı komutlarını yönlendirir."""
    if not check_auth(update):
        return

    cmd = update.message.text.lower()
    chat_id = update.effective_chat.id

    if "menu" in cmd or "kategori" in cmd:
        await category_menu_command(update, context)
    elif "turkce" in cmd or "arkadas" in cmd or "dusun" in cmd:
        await send_special_account_draft(chat_id, context, screen_name="turkce_dusun")
    elif "viral" in cmd or "trend" in cmd:
        # Kategori parametresi kontrolü: /viral spor, /viral haber, /viral mizah, /viral tekno
        cat = None
        if "spor" in cmd:
            cat = "spor"
        elif "haber" in cmd or "gundem" in cmd:
            cat = "haber"
        elif "mizah" in cmd or "komik" in cmd:
            cat = "mizah"
        elif "tekno" in cmd or "ai" in cmd:
            cat = "tekno"
        await send_viral_draft(chat_id, context, category=cat)
    elif "tekno" in cmd:
        await send_news_draft(chat_id, context, category="tech")
    elif "spor" in cmd:
        await send_news_draft(chat_id, context, category="sports")
    elif "gundem" in cmd:
        await send_news_draft(chat_id, context, category="general")
    else:
        # /yeni veya /haber
        await send_news_draft(chat_id, context)


async def scheduled_job(context: ContextTypes.DEFAULT_TYPE):
    """Her 3 saatte bir dönüşümlü olarak viral, haber veya özel hesap paylaşımı gönderir."""
    if ALLOWED_CHAT_ID:
        import random
        r = random.random()
        if r < 0.40:
            await send_viral_draft(int(ALLOWED_CHAT_ID), context)
        elif r < 0.75:
            await send_news_draft(int(ALLOWED_CHAT_ID), context)
        else:
            await send_special_account_draft(int(ALLOWED_CHAT_ID), context, screen_name="turkce_dusun")


def main():
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN bulunamadı!")

    app = Application.builder().token(TOKEN).build()

    # Komutlar
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler(["menu", "kategori"], category_menu_command))
    app.add_handler(CommandHandler(["viral", "trend"], router_command))
    app.add_handler(CommandHandler(["turkcedusun", "arkadas"], router_command))
    app.add_handler(CommandHandler(["yeni", "haber", "teknoloji", "spor", "gundem"], router_command))

    # Buton tıklamaları
    app.add_handler(CallbackQueryHandler(handle_button_click))

    # Kullanıcıdan gelen metin mesajları (Özel yorum yazma)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_text_message))

    # Zamanlayıcı (Her 3 saatte bir)
    if app.job_queue and ALLOWED_CHAT_ID:
        app.job_queue.run_repeating(scheduled_job, interval=10800, first=15)

    # Render.com için HTTP sağlık kontrolü sunucusunu başlat
    start_health_check_server()

    print(">>> Telegram Onay & Alintilama Botu Calisiyor! (Durdurmak icin CTRL+C)")
    app.run_polling()


if __name__ == "__main__":
    main()
