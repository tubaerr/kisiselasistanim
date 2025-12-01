import streamlit as st
import os
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from dotenv import load_dotenv
from openai import OpenAI

# --- AYARLAR (HEM PC HEM BULUT UYUMLU) ---
# Önce PC'deki .env dosyasını yüklemeyi dene
load_dotenv()

# Şifreleri alma mantığı:
# Eğer PC'deysek os.environ'dan, Buluttaysak st.secrets'tan al.

try:
    if os.environ.get("OPENAI_API_KEY"):
        # PC Modu
        API_KEY = os.environ.get("OPENAI_API_KEY")
        MAIL_ADRESIM = os.environ.get("MAIL_ADRESIM")
        MAIL_SIFRESI = os.environ.get("MAIL_SIFRESI")
    else:
        # Bulut Modu (Streamlit Cloud)
        API_KEY = st.secrets["OPENAI_API_KEY"]
        MAIL_ADRESIM = st.secrets["MAIL_ADRESIM"]
        MAIL_SIFRESI = st.secrets["MAIL_SIFRESI"]
except:
    st.error("Şifreler bulunamadı! Lütfen Secrets ayarlarını kontrol et.")
    st.stop()

# İstemcileri Başlat
client = OpenAI(api_key=API_KEY)
GONDEREN_MAIL = MAIL_ADRESIM
GONDEREN_SIFRE = MAIL_SIFRESI

st.set_page_config(page_title="Kişisel Asistanım", page_icon="🤖")

# --- FONKSİYONLAR ---

def gorev_kaydet(tarih, olay_adi):
    """Görevi JSON dosyasına kaydeder."""
    dosya_adi = "gorevler.json"
    try:
        with open(dosya_adi, "r", encoding="utf-8") as f:
            liste = json.load(f)
    except:
        liste = []
    
    liste.append({"tarih": tarih, "olay": olay_adi})
    
    with open(dosya_adi, "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=4)
    return "✅ Kaydedildi."

def mail_gonder(kime, konu, icerik):
    """Mail gönderme işlemi."""
    try:
        msg = MIMEText(icerik)
        msg['Subject'] = konu
        msg['From'] = GONDEREN_MAIL
        msg['To'] = kime
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GONDEREN_MAIL, GONDEREN_SIFRE)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Mail hatası: {e}")
        return False

def alarmlari_kontrol_et():
    """Görevi yaklaşanları kontrol eder ve mail atar."""
    loglar = []
    try:
        with open("gorevler.json", "r", encoding="utf-8") as f:
            gorevler = json.load(f)
    except:
        return ["Görev dosyası bulunamadı."]

    bugun = datetime.now()
    mail_gonderildi = False
    
    for gorev in gorevler:
        tarih_str = gorev["tarih"]
        olay = gorev["olay"]
        try:
            etkinlik_tarihi = datetime.strptime(tarih_str, "%Y-%m-%d")
            kalan_gun = (etkinlik_tarihi - bugun).days + 1
            
            if 0 <= kalan_gun <= 30:
                mail_gonder(GONDEREN_MAIL, f"⚠️ HATIRLATMA: {olay}", f"{olay} etkinliğine {kalan_gun} gün kaldı.")
                loglar.append(f"🚨 {olay}: {kalan_gun} gün kaldı (Mail Atıldı!)")
                mail_gonderildi = True
            elif kalan_gun < 0:
                loglar.append(f"❌ {olay}: Geçmiş etkinlik.")
            else:
                loglar.append(f"⏳ {olay}: {kalan_gun} gün var.")
        except:
            pass
            
    if not mail_gonderildi:
        loglar.append("✅ Yaklaşan acil bir durum yok.")
    return loglar

# --- ARAYÜZ (FRONTEND) ---

st.title("🤖 Kişisel Asistan & Planlayıcı")

# Yan Menü (Sidebar)
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    if st.button("📅 Tarihleri Kontrol Et & Mail At"):
        with st.spinner("Takvim taranıyor..."):
            sonuclar = alarmlari_kontrol_et()
            for sonuc in sonuclar:
                st.write(sonuc)
            st.success("Kontrol tamamlandı!")

    st.divider()
    st.write("Kayıtlı Görevler:")
    try:
        with open("gorevler.json", "r", encoding="utf-8") as f:
            veriler = json.load(f)
            for v in veriler:
                st.caption(f"{v['tarih']} - {v['olay']}")
    except:
        st.caption("Henüz görev yok.")

# Sohbet Alanı
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "Sen yardımsever bir asistan ve etkinlik planlayıcısısın. Kullanıcı tarihli bir etkinlik verirse önce 'gorev_kaydet' aracını kullan, sonra checklist hazırla."}
    ]

for message in st.session_state.messages:
    if message["role"] != "system" and message["role"] != "tool":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

if prompt := st.chat_input("Bir etkinlik planlayalım mı?"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    tools = [{
        "type": "function",
        "function": {
            "name": "gorev_kaydet",
            "description": "Etkinlik kaydetmek için",
            "parameters": {
                "type": "object",
                "properties": {
                    "tarih": {"type": "string", "description": "YYYY-AA-GG formatında tarih"},
                    "olay_adi": {"type": "string", "description": "Olay adı"}
                },
                "required": ["tarih", "olay_adi"]
            }
        }
    }]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=st.session_state.messages,
            tools=tools
        )
        
        msg = response.choices[0].message
        
        if msg.tool_calls:
            st.session_state.messages.append(msg)
            for tool_call in msg.tool_calls:
                if tool_call.function.name == "gorev_kaydet":
                    args = json.loads(tool_call.function.arguments)
                    sonuc = gorev_kaydet(args["tarih"], args["olay_adi"])
                    
                    st.session_state.messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": "gorev_kaydet",
                        "content": sonuc
                    })
                    st.toast(f"💾 {args['olay_adi']} başarıyla kaydedildi!", icon="✅")

            final_response = client.chat.completions.create(
                model="gpt-4o",
                messages=st.session_state.messages
            )
            ai_cevap = final_response.choices[0].message.content
        else:
            ai_cevap = msg.content

        with st.chat_message("assistant"):
            st.markdown(ai_cevap)
        
        st.session_state.messages.append({"role": "assistant", "content": ai_cevap})

    except Exception as e:
        st.error(f"Hata: {e}")
