"""
Gemini AI Haber Küratörü ve Tweet/Alıntı Yorum Üreticisi
"""
import os
import json
import logging
from google import genai
from google.genai import types
from config import GEMINI_MODEL

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def select_and_craft_tweet(candidates, preferred_category=None):
    """
    Haber adayları arasından en etkili olanı seçer ve kısa, vurucu Türkçe tweet metni üretir.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY bulunamadı!")

    client = genai.Client(api_key=api_key)

    items_text = ""
    for idx, item in enumerate(candidates[:20]):
        items_text += f"\n[{idx}] Kategori: {item['category']} | Kaynak: {item['source']}\n"
        items_text += f"Başlık: {item['title']}\n"
        items_text += f"Özet: {item['summary'][:200]}\n"
        items_text += f"Link: {item['link']}\n"

    system_instruction = (
        "Sen profesyonel bir sosyal medya editörüsün. X (Twitter) Türkiye kitlesinin dilini çok iyi biliyorsun. "
        "Görevin, okuyucunun ilgisini en çok çekecek 1 haberi seçmek ve bunu kısa, vurucu, samimi bir tweet formatına dönüştürmektir."
    )

    prompt = f"""Aşağıdaki güncel haber listesinden sosyal medyada en yüksek etkileşim potansiyeline sahip 1 haberi seç.
Öncelikli Kategori Tercihi: {preferred_category or 'En çarpıcı olan'}

Haber Listesi:
{items_text}

Kurallar:
1. Seçtiğin haber için Türkçe, doğal ve dikkat çekici bir tweet yaz.
2. ÖNEMLİ: Tweet metni (link ve etiketler DAHİL) TOPLAMDA EN FAZLA 230 karakter olmalıdır.
3. Metnin sonuna 1-2 adet popüler hashtag ekle.
4. Haberin kaynak linkini mutlaka tweetin en sonuna ekle.
5. Yanıtını SADECE geçerli bir JSON formatında döndür.

JSON Formatı:
{{
  "selected_index": 0,
  "reason": "Neden seçtiğinin kısa açıklaması",
  "tweet_text": "Kısa Türkçe tweet metni, emojiler, hashtag ve link",
  "link": "https://..."
}}
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.7,
        )
    )

    result = json.loads(response.text.strip())
    selected_index = result.get("selected_index", 0)
    selected_item = candidates[selected_index] if 0 <= selected_index < len(candidates) else candidates[0]

    return {
        "tweet_text": result["tweet_text"],
        "reason": result.get("reason", ""),
        "original_news": selected_item,
        "link": selected_item["link"]
    }


def generate_viral_quote_comment(tweet_candidate):
    """
    X Türkiye'de viral olan bir tweet için alıntı (Quote Tweet) yorumu üretir.
    Samimi, zekice, esprili veya düşündürücü Twitter TR üslubunu kullanır.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY bulunamadı!")

    client = genai.Client(api_key=api_key)

    system_instruction = (
        "Sen Twitter/X Türkiye gündemini çok iyi takip eden, mizahı kuvvetli, zeki ve samimi bir sosyal medya kullanıcısısın. "
        "Önüne gelen viral bir tweeti alıntılayarak (Quote Tweet) takipçilerinle paylaşacaksın."
    )

    prompt = f"""Aşağıdaki viral tweeti alıntılarken yazmak için kısa, zekice, hafif esprili veya düşündürücü bir Türkçe yorum üret.

Tweet Sahibi: @{tweet_candidate['author_username']} ({tweet_candidate['author_name']})
Gündem / Başlık: {tweet_candidate.get('topic', 'Gündem')}
Tweet Metni:
"{tweet_candidate['text']}"

Kurallar:
1. Yorumun samimi, Twitter Türkiye kültürüne uygun olmalı (robotik veya resmi haber spikeri gibi ASLA olmasın).
2. Yorum EN FAZLA 120-140 karakter olmalı (kısa ve vurucu).
3. Gerekirse uygun 1-2 emoji kullanabilirsin.
4. Yanıtını SADECE geçerli bir JSON olarak döndür.

JSON Formatı:
{{
  "suggested_comment": "Alıntı tweet için önerilen Türkçe yorum",
  "reason": "Neden bu yorumun etkileşim getireceğinin açıklaması"
}}
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.8,
        )
    )

    result = json.loads(response.text.strip())
    return {
        "suggested_comment": result["suggested_comment"],
        "reason": result.get("reason", "")
    }
