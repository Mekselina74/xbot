"""
Gemini AI Haber Küratörü ve Tweet Üreticisi
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
    Haber adayları arasından en etkili ve ilgi çekici olanı seçer,
    akıcı ve dikkat çekici bir Türkçe tweet metni üretir.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY ortam değişkeni veya .env dosyasında bulunamadı!")

    client = genai.Client(api_key=api_key)

    # Adayları özet bir liste formatına getir
    items_text = ""
    for idx, item in enumerate(candidates[:20]):
        items_text += f"\n[{idx}] Kategori: {item['category']} | Kaynak: {item['source']}\n"
        items_text += f"Başlık: {item['title']}\n"
        items_text += f"Özet: {item['summary'][:250]}\n"
        items_text += f"Link: {item['link']}\n"

    system_instruction = (
        "Sen profesyonel bir sosyal medya editörü ve teknoloji/spor gazetecisisin. "
        "Görevin, sana sunulan haber adayları arasından sosyal medyada (X/Twitter) en çok yankı "
        "uyandıracak, okuyucunun ilgisini en çok çekecek 1 haberi seçmek ve bunu Türkçe olarak "
        "harika bir tweet metnine dönüştürmektir."
    )

    category_note = f"Eğer mümkünse '{preferred_category}' kategorisinden seç." if preferred_category else "En çarpıcı olanı seç."

    prompt = f"""Aşağıdaki güncel haber listesinden sosyal medyada en yüksek etkileşim potansiyeline sahip 1 haberi seç.
{category_note}

Haber Listesi:
{items_text}

Kurallar:
1. Seçtiğin haber için Türkçe, doğal, akıcı ve dikkat çekici bir tweet yaz.
2. Tweet robotik veya yapay çeviri gibi hissettirmemeli. Samimi, merak uyandırıcı ve bilgilendirici olmalı.
3. Varsa önemli bir detay, rakam veya alıntıyı öne çıkar.
4. Metnin sonuna 2-3 adet popüler ve konuyla ilgili hashtag ekle (örneğin #YapayZeka, #Teknoloji, #Spor).
5. Haberin kaynak linkini mutlaka tweetin en sonuna ekle.
6. Yanıtını SADECE geçerli bir JSON formatında döndür.

JSON Formatı:
{{
  "selected_index": 0,
  "reason": "Bu haberi neden seçtiğinin kısa açıklaması",
  "tweet_text": "Türkçe tweet metni, emojiler, hashtagler ve kaynak linki",
  "link": "https://..."
}}
"""

    try:
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

    except Exception as e:
        logging.error(f"Gemini API yanıtı işlenirken hata oluştu: {e}")
        raise
