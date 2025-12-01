import streamlit as st
import os
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from dotenv import load_dotenv
from openai import OpenAI

# --- AYARLAR (HEM PC HEM BULUT UYUMLU) ---
load_dotenv()

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

client = OpenAI(api_key=API_KEY)
GONDEREN_MAIL = MAIL_ADRESIM
GONDEREN_SIFRE = MAIL_SIFRESI

# Sayfa Başlığı ve İkonu
st.set_page_config(page_title="Tuba'nın Asistanı", page_icon="👑")

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
    """Belirli günlerde mail atar (30, 21, 14, 7, 2 gün kala)."""
    loglar = []
    try:
        with open("gorevler.json", "r", encoding="utf-8") as f:
            gorevler = json.load(f)
    except:
        return ["Görev dosyası bulunamadı."]

    bugun = datetime.now()
    mail_gonderildi = False
    
    # Mail atılacak kritik gün sayıları
    kritik_gunler = [30, 21, 14, 7, 2]

    for gorev in gorevler:
        tarih_str = gorev["tarih"]
        olay = gorev["olay"]
        try:
            etkinlik_tarihi = datetime.strptime(tarih_str, "%Y-%m-%d")
            kalan_gun = (etkinlik_tarihi - bugun).days + 1
            
            # Kalan gün, listemizdeki kritik günlerden biri mi?
            if kalan_gun in kritik_gunler:
                konu = f"⚠️ HATIRLATMA: {olay} ({kalan_gun} Gün Kaldı!)"
                icerik = f"Merhaba Tuba,\n\n'{olay}' etkinliğine tam {kalan_gun} gün kaldı.\nChecklist'ini kontrol etmeyi unutma!\n\nTarih: {tarih_str}\n\nSevgiler,\nDijital Asistanın."
                
                mail_gonder(GONDEREN_MAIL, konu, icerik)
                loglar.append(f"🚨 {olay}: {kalan_gun} gün kaldı -> MAIL ATILDI ✅")
                mail_gonderildi = True
                
            elif kalan_gun == 0:
                mail_gonder(GONDEREN_MAIL, f"BUGÜN BÜYÜK GÜN: {olay}", f"İyi şanslar! Bugün {olay} günü.")
                loglar.append(f"🏁 {olay}: BUGÜN!")
                mail_gonderildi = True
                
            elif kalan_gun < 0:
                loglar.append(f"❌ {olay}: Geçmiş etkinlik.")
            else:
                # Mail atılmayan günler
                loglar.append(f"⏳ {olay}: {kalan_gun} gün var. (Mail günü değil)")
        except:
            pass
            
    if not mail_gonderildi:
        loglar.append("✅ Bugün mail atılacak kritik bir tarih yok.")
    return loglar

# --- ARAYÜZ (FRONTEND) ---

st.title("👑 Tuba'nın Kişisel Asistanı ve Planlayıcısı")

# Yan Menü (Sidebar)
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    
    if st.button("📅 Takvimi Kontrol Et"):
        with st.spinner("Tarihler hesaplanıyor..."):
            sonuclar = alarmlari_kontrol_et()
            for sonuc in sonuclar:
                if "MAIL ATILDI" in sonuc:
                    st.success(sonuc)
                elif "BUGÜN" in sonuc:
                    st.warning(sonuc)
                else:
                    st.info(sonuc)

    st.divider()
    st.write("📌 Kayıtlı Etkinlikler:")
    try:
        with open("gorevler.json", "r", encoding="utf-8") as f:
            veriler = json.load(f)
            for v in veriler:
                st.caption(f"🗓 {v['tarih']} - {v['olay']}")
    except:
        st.caption("Liste boş.")

# Sohbet Alanı
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "Sen Tuba'nın kişisel asistanısın. Kullanıcı tarihli bir etkinlik verirse 'gorev_kaydet' ile kaydet ve checklist hazırla."}
    ]

for message in st.session_state.messages:
    if message["role"] != "system" and message["role"] != "tool":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

if prompt := st.chat_input("Yeni bir planın mı var Tuba?"):
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
                    st.toast(f"💾 {args['olay_adi']} listeye eklendi!", icon="✅")

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
