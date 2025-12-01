import json
import smtplib
import os
from datetime import datetime
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Ayarları yükle
load_dotenv()

GONDEREN_MAIL = os.environ.get("MAIL_ADRESIM")
GONDEREN_SIFRE = os.environ.get("MAIL_SIFRESI")

def mail_gonder(kime, konu, icerik):
    try:
        print(f"📧 Mail sunucusuna bağlanılıyor... ({kime})")
        
        msg = MIMEText(icerik)
        msg['Subject'] = konu
        msg['From'] = GONDEREN_MAIL
        msg['To'] = kime

        # Gmail Sunucusuna Bağlan (Port 465)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GONDEREN_MAIL, GONDEREN_SIFRE)
            smtp.send_message(msg)
            
        print("✅ BAŞARILI: Mail gerçekten gönderildi! Gelen kutunu kontrol et.")
    except Exception as e:
        print(f"❌ HATA: Mail gönderilemedi. Sebebi:\n{e}")

def tarihleri_kontrol_et():
    print("--- 🕵️‍♂️ ZAMAN BEKÇİSİ ÇALIŞIYOR (GERÇEK MOD) ---")
    bugun = datetime.now()
    alici_mail = GONDEREN_MAIL 

    try:
        with open("gorevler.json", "r", encoding="utf-8") as f:
            gorevler = json.load(f)
    except FileNotFoundError:
        print("Dosya yok.")
        return

    for gorev in gorevler:
        tarih_str = gorev["tarih"]
        olay = gorev["olay"]
        
        try:
            etkinlik_tarihi = datetime.strptime(tarih_str, "%Y-%m-%d")
            kalan_sure = etkinlik_tarihi - bugun
            kalan_gun = kalan_sure.days + 1
            
            print(f"📌 {olay} -> {kalan_gun} gün kaldı.")
            
            # 30 günden az kaldıysa mail at
            if 0 <= kalan_gun <= 30:
                print(f"   🚨 KRİTİK: {olay} için mail gönderiliyor...")
                
                konu = f"⚠️ HATIRLATMA: {olay} Yaklaşıyor!"
                icerik = f"Merhaba,\n\n'{olay}' etkinliğine sadece {kalan_gun} gün kaldı ({tarih_str}).\n\nHazırlıklarını kontrol etmeyi unutma!\n\nSenin Dijital Asistanın."
                
                mail_gonder(alici_mail, konu, icerik)
                
        except ValueError:
            pass

if __name__ == "__main__":
    tarihleri_kontrol_et()