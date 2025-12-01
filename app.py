import streamlit as st
import os
import json
import smtplib
import urllib.parse
from datetime import datetime
from email.mime.text import MIMEText
from dotenv import load_dotenv
from openai import OpenAI

# --- AYARLAR ---
load_dotenv()

try:
    if os.environ.get("OPENAI_API_KEY"):
        API_KEY = os.environ.get("OPENAI_API_KEY")
        MAIL_ADRESIM = os.environ.get("MAIL_ADRESIM")
        MAIL_SIFRESI = os.environ.get("MAIL_SIFRESI")
    else:
        API_KEY = st.secrets["OPENAI_API_KEY"]
        MAIL_ADRESIM = st.secrets["MAIL_ADRESIM"]
        MAIL_SIFRESI = st.secrets["MAIL_SIFRESI"]
except:
    st.error("Şifreler eksik! Secrets ayarlarını kontrol et.")
    st.stop()

client = OpenAI(api_key=API_KEY)
GONDEREN_MAIL = MAIL_ADRESIM
GONDEREN_SIFRE = MAIL_SIFRESI

st.set_page_config(page_title="Tuba'nın Asistanı", page_icon="👑")

# --- YARDIMCI FONKSİYONLAR ---

def google_calendar_link(tarih, olay):
    """Google Takvim için özel link oluşturur."""
    # Tarihi YYYYMMDD formatına çevir
    try:
        dt = datetime.strptime(tarih, "%Y-%m-%d")
        tarih_format = dt.strftime("%Y%m%d")
        # Bitiş tarihi olarak ertesi günü verelim (Tam gün etkinliği)
        ertesi_gun = dt.strftime("%Y%m%d") 
        
        base_url = "https://www.google.com/calendar/render?action=TEMPLATE"
        params = {
            "text": f"👑 {olay}",
            "details": "Asistanın tarafından oluşturuldu.",
            "dates": f"{tarih_format}/{tarih_format}"
        }
        return base_url + "&" + urllib.parse.urlencode(params)
    except:
        return "https://calendar.google.com"

def gorev_listesini_yukle():
    try:
        with open("gorevler.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def gorev_kaydet(tarih, olay_adi):
    liste = gorev_listesini_yukle()
    liste.append({"tarih": tarih, "olay": olay_adi})
    with open("gorevler.json", "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=4)
    return f"✅ Kaydedildi: {olay_adi}"

def gorev_sil(silinecek_olaylar):
    """Seçilen olayları listeden siler."""
    eski_liste = gorev_listesini_yukle()
    # Silinecekler listesinde OLMAYANLARI yeni listeye al (Filtreleme)
    yeni_liste = [x for x in eski_liste if x['olay'] not in silinecek_olaylar]
    
    with open("gorevler.json", "w", encoding="utf-8") as f:
        json.dump(yeni_liste, f, ensure_ascii=False, indent=4)

def mail_gonder(kime, konu, icerik):
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
        return False

def alarmlari_kontrol_et():
    liste = gorev_listesini_yukle()
    if not liste: return ["Görev dosyası boş."]
    
    bugun = datetime.now()
    loglar = []
    kritik_gunler = [30, 21, 14, 7, 2] # Mail atılacak günler

    for gorev in liste:
        try:
            dt = datetime.strptime(gorev["tarih"], "%Y-%m-%d")
            kalan = (dt - bugun).days + 1
            
            if kalan in kritik_gunler:
                mail_gonder(GONDEREN_MAIL, f"⚠️ {gorev['olay']} ({kalan} Gün Kaldı!)", f"{gorev['olay']} yaklaşıyor.")
                loglar.append(f"🚨 {gorev['olay']}: Mail atıldı ({kalan} gün).")
            elif kalan == 0:
                mail_gonder(GONDEREN_MAIL, f"BUGÜN: {gorev['olay']}", "Bugün büyük gün!")
                loglar.append(f"🏁 {gorev['olay']}: BUGÜN!")
            elif kalan < 0:
                loglar.append(f"❌ {gorev['olay']}: Geçmiş.")
            else:
                loglar.append(f"⏳ {gorev['olay']}: {kalan} gün var.")
        except:
            pass
    return loglar

# --- ARAYÜZ ---

st.title("👑 Tuba'nın Kişisel Asistanı ve Planlayıcısı")

# SİDEBAR (Yan Menü)
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    
    # 1. Kontrol Butonu
    if st.button("📅 Takvimi Tara & Mail At"):
        with st.spinner("Kontrol ediliyor..."):
            sonuclar = alarmlari_kontrol_et()
            for s in sonuclar:
                if "🚨" in s: st.success(s)
                elif "⏳" in s: st.info(s)
                else: st.write(s)
    
    st.divider()
    
    # 2. Silme İşlemi (YENİ)
    st.subheader("🗑 Görev Sil")
    mevcut_gorevler = gorev_listesini_yukle()
    if mevcut_gorevler:
        # Sadece olay adlarını listeye çek
        olay_listesi = [x['olay'] for x in mevcut_gorevler]
        silinecekler = st.multiselect("Silinecekleri Seç:", olay_listesi)
        
        if st.button("Seçilenleri Sil"):
            if silinecekler:
                gorev_sil(silinecekler)
                st.success("Silindi! Sayfa yenileniyor...")
                st.rerun() # Sayfayı yenile
    else:
        st.caption("Silinecek görev yok.")

    st.divider()
    st.subheader("📌 Kayıtlı Listesi")
    for g in gorev_listesini_yukle():
        st.caption(f"{g['tarih']} - {g['olay']}")

# SOHBET
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "Tuba'nın asistanısın. Tarihli işleri kaydet ve checklist hazırla."}]

for msg in st.session_state.messages:
    if msg["role"] != "system" and msg["role"] != "tool":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if prompt := st.chat_input("Yeni bir etkinlik ekle..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    # Tool Tanımı
    tools = [{
        "type": "function",
        "function": {
            "name": "gorev_kaydet",
            "description": "Etkinlik kaydet",
            "parameters": {
                "type": "object",
                "properties": {
                    "tarih": {"type": "string", "description": "YYYY-AA-GG"},
                    "olay_adi": {"type": "string", "description": "Olay adı"}
                }, "required": ["tarih", "olay_adi"]
            }
        }
    }]

    try:
        resp = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages, tools=tools)
        ai_msg = resp.choices[0].message

        if ai_msg.tool_calls:
            st.session_state.messages.append(ai_msg)
            for tool in ai_msg.tool_calls:
                if tool.function.name == "gorev_kaydet":
                    args = json.loads(tool.function.arguments)
                    res = gorev_kaydet(args["tarih"], args["olay_adi"])
                    
                    st.session_state.messages.append({
                        "tool_call_id": tool.id, "role": "tool", "name": "gorev_kaydet", "content": res
                    })
                    
                    # --- GOOGLE TAKVİM LİNKİ OLUŞTURMA (YENİ) ---
                    link = google_calendar_link(args["tarih"], args["olay_adi"])
                    st.success(f"Etkinlik Kaydedildi! 👇")
                    st.markdown(f"[📅 **Google Takvime Eklemek İçin Tıkla**]({link})", unsafe_allow_html=True)

            final = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
            yanit = final.choices[0].message.content
        else:
            yanit = ai_msg.content

        st.session_state.messages.append({"role": "assistant", "content": yanit})
        with st.chat_message("assistant"):
            st.markdown(yanit)

    except Exception as e:
        st.error(str(e))
