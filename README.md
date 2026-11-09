# 🤖 X (Twitter) Otomatik Haber Küratörü

7/24 bulutta (GitHub Actions üzerinde) veya yerel bilgisayarınızda çalışabilen, teknoloji, spor ve popüler dünya haberlerini RSS kaynaklarından toplayıp **Google Gemini AI** ile analiz eden ve dikkat çekici Türkçe tweetler olarak paylaşan otomatik bot.

---

## 🌟 Özellikler

- **%100 Ücretsiz:** X Developer Portal ücretli API paketine ihtiyaç duymaz; oturum çerezleri (`cookies.json`) üzerinden çalışır.
- **7/24 Bulut Desteği:** GitHub Actions sayesinde bilgisayarınız kapalıyken bile belirli aralıklarla (örneğin 3 saatte bir) otomatik tweet atar.
- **Çoklu Kategori & Akıllı Dağılım:**
  - 🚀 **Teknoloji & Yapay Zekâ** (The Verge, TechCrunch, Ars Technica, Engadget)
  - ⚽ **Spor & Küresel Gelişmeler** (BBC Sport, ESPN, Sky Sports)
  - 🌍 **Popüler Gündem & Keşifler** (BBC World, The Guardian)
- **Gemini AI Editörü:** Haberleri tarafsız ve akıcı bir Türkçe ile ilgi çekici sosyal medya metinlerine dönüştürür, uygun hashtagler ve kaynak linki ekler.
- **Tekrar Önleme (`history.json`):** Daha önce paylaşılan haberler kaydedilir ve asla iki kez paylaşılmaz.

---

## 📁 Proje Dosya Yapısı

```
x-news-bot/
├── .github/workflows/
│   └── tweet_scheduler.yml  # GitHub Actions 7/24 zamanlayıcı
├── .env.example             # Örnek ortam değişkenleri
├── .gitignore
├── ai_curator.py            # Gemini AI ile haber seçimi ve tweet yazımı
├── config.py                # RSS kaynakları, modeller ve ayarlar
├── history.json             # Paylaşılmış haberlerin listesi
├── login_helper.py          # Bir defalık X giriş ve cookies.json üretici
├── main.py                  # Ana çalıştırıcı (Haber çek -> Gemini -> Tweet)
├── requirements.txt         # Bağımlılıklar
├── rss_fetcher.py           # RSS toplayıcı ve HTML temizleyici
└── twitter_client.py        # Twikit tabanlı X paylaşım istemcisi
```

---

## 🚀 Kurulum ve İlk Çalıştırma

### 1. Gemini API Anahtarı
1. [Google AI Studio](https://aistudio.google.com/app/apikey) adresinden ücretsiz API anahtarınızı alın.
2. `x-news-bot` klasörü içinde `.env` dosyası oluşturup ekleyin:
   ```env
   GEMINI_API_KEY=AIzaSy...
   ```

### 2. Tek Seferlik X Girişi (cookies.json)
Bilgisayarınızda terminalden şu komutu çalıştırın:
```bash
python login_helper.py
```
Kullanıcı adı, e-posta ve şifrenizi girin. Başarılı girişten sonra klasörde `cookies.json` dosyası oluşacaktır.

### 3. Test Çalıştırması (Dry Run)
Tweet atmadan botun nasıl çalıştığını görmek için:
```bash
python main.py --dry-run
```

Gerçek bir tweet paylaşımı denemek için:
```bash
python main.py
```

---

## ☁️ 7/24 Buluta Taşıma (GitHub Actions)

1. GitHub'da **Private (Gizli)** bir repo oluşturun.
2. Kodları bu depoya yükleyin (Not: `cookies.json` ve `.env` dosyası gitignore'dadır, asla kodla yüklenmez).
3. GitHub reponuzda **Settings > Secrets and variables > Actions** sayfasına gidin.
4. **New repository secret** butonuna tıklayarak şu 2 sırrı ekleyin:
   - **`GEMINI_API_KEY`**: Google AI Studio anahtarınız.
   - **`TWITTER_COOKIES`**: Bilgisayarınızda oluşan `cookies.json` dosyasının tüm metin içeriği (Not Defteri ile açıp kopyalayın).
5. Artık her şey hazır! `.github/workflows/tweet_scheduler.yml` her 3 saatte bir otomatik olarak çalışacak ve bilgisayarınız kapalı olsa bile tweet atacaktır.
