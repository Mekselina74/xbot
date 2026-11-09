"""
X (Twitter) Oturum ve Çerez (Cookie) Oluşturucu

İki farklı yöntem sunar:
1. (En Kolay & En Güvenli): Zaten giriş yaptığınız tarayıcınızdan (Chrome/Edge)
   'auth_token' ve 'ct0' değerlerini yapıştırarak tek tıkla cookies.json oluşturmak.
2. Kullanıcı adı ve şifre ile doğrudan otomatik giriş yapmak (twifork).
"""
import os
import json
import asyncio
import getpass
from twikit import Client
from dotenv import load_dotenv
from config import COOKIES_FILE

load_dotenv()


def save_manual_cookies():
    print("\n--- YÖNTEM 1: Tarayıcı Çerezleri ile Hızlı Kurulum ---")
    print("X hesabınız tarayıcınızda (Chrome, Edge vb.) zaten açıksa:")
    print("1. x.com sayfasına gidin.")
    print("2. F12 tuşuna basın (Geliştirici Araçları).")
    print("3. 'Application' (Uygulama) sekmesine tıklayın.")
    print("4. Sol menüde 'Cookies' -> 'https://x.com' yolunu seçin.")
    print("5. Listeden 'auth_token' ve 'ct0' değerlerini bulun.\n")

    auth_token = input("auth_token değerini yapıştırın: ").strip()
    ct0 = input("ct0 değerini yapıştırın: ").strip()

    if not auth_token or not ct0:
        print("Hata: Değerler boş bırakılamaz.")
        return False

    cookies = {
        "auth_token": auth_token,
        "ct0": ct0
    }

    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2)

    print("\n" + "=" * 60)
    print("TEBRİKLER! cookies.json başarıyla oluşturuldu:")
    print(f"-> {COOKIES_FILE}")
    print("=" * 60)
    return True


async def login_with_credentials():
    print("\n--- YÖNTEM 2: Şifre ile Otomatik Giriş ---")
    username = os.getenv("TWITTER_USERNAME") or input("X Kullanıcı Adı (@ olmadan): ").strip()
    email = os.getenv("TWITTER_EMAIL") or input("X Kayıtlı E-posta Adresi: ").strip()
    password = os.getenv("TWITTER_PASSWORD")

    if not password:
        password = getpass.getpass("X Şifresi: ").strip()

    client = Client(language="tr-TR")

    print("\nX'e bağlanılıyor, lütfen bekleyin...")
    try:
        totp_code = input("2FA/TOTP kodu (varsa girin, yoksa Enter'a basın): ").strip()
        totp_arg = totp_code if totp_code else None

        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password,
            totp_secret=totp_arg,
            cookies_file=str(COOKIES_FILE)
        )
        print("\n" + "=" * 60)
        print("TEBRİKLER! Başarıyla giriş yapıldı ve oturum çerezi kaydedildi:")
        print(f"-> {COOKIES_FILE}")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"\nGiriş sırasında hata oluştu: {e}")
        return False


async def main():
    print("=" * 60)
    print(" X (Twitter) Çerez (Cookie) Kurulum Sihirbazı")
    print("=" * 60)
    print("1) Tarayıcımdan çerezleri kopyalayacağım (TAVSİYE EDİLEN - Hızlı & Sorunsuz)")
    print("2) Kullanıcı adı ve şifre ile giriş yapmayı dene")
    
    choice = input("\nSeçiminiz (1 veya 2): ").strip()

    if choice == "2":
        success = await login_with_credentials()
        if not success:
            print("\nŞifre ile giriş başarısız olduysa 1. yöntemi (Tarayıcı Çerezleri) deneyebilirsiniz.")
    else:
        save_manual_cookies()


if __name__ == "__main__":
    asyncio.run(main())
