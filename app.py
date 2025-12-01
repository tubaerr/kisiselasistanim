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
    try:
        dt = datetime.strptime(tarih, "%Y-%m-%d")
        tarih_format = dt.strftime("%Y%m%d")
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
    return f"Etkinlik veritabanına kaydedildi: {olay_adi}"

def gorev_sil_tekli(olay_adi):
    """Tek bir olayı isminden bulup siler."""
    eski_liste = gorev_listesini_yukle()
    yeni_liste = [x for x in eski_liste if x['olay'] != olay_adi]
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
    kritik_gunler = [30, 21, 14, 7, 2] 

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

# --- DETAY PENCERESİ (POP-UP) ---
@st.dialog("📅 Etkinlik Detayları")
def detay_goster(gorev):
    st.header(gorev['olay'])
    st.write(f"**Tarih:** {gorev['tarih']}")
    
    # Kalan Gün Hesabı
    try:
        dt = datetime.strptime(gorev['tarih'], "%Y-%m-%d")
        bugun = datetime.now()
        kalan = (dt - bugun).days + 1
        
        if kalan > 0:
            st.info(f"⏳ Bu etkinliğe **{kalan} gün** kaldı.")
        elif kalan == 0:
            st.warning("🔥 BUGÜN!")
        else:
            st.error("❌ Bu etkinlik geçmiş.")
    except:
        st.write("Tarih hesaplanamadı.")

    # Linkler ve Butonlar
    link = google_calendar_link(gorev['tarih'], gorev['olay'])
    st.markdown(f"👉 [**Google Takvim'de Aç**]({link})")
    
    st.divider()
    
    if st.button("🗑 Bu Etkinliği Sil", type="primary"):
        gorev_sil_tekli(gorev['olay'])
        st.success("Silindi! Kapatıp sayfayı yenileyin.")
        st.rerun()

# --- ARAYÜZ ---

st.title("👑 Tuba'nın Kişisel Asistanı ve Planlayıcısı")

# SİDEBAR
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    
    if st.button("📅 Tarihleri Tara & Mail At", use_container_width=True):
        with st.spinner("Kontrol ediliyor..."):
            sonuclar = alarmlari_kontrol_et()
            for s in sonuclar:
                if "🚨" in s: st.success(s)
                elif "⏳" in s: st.info(s)
                else: st.write(s)
    
    st.divider()
    st.subheader("📌 Etkinliklerin")
    st.caption("Detay görmek için üzerine tıkla 👇")
    
    # LİSTEYİ BUTON OLARAK GÖSTERME
    gorevler = gorev_listesini_yukle()
    if not gorevler:
        st.info("Henüz plan yok.")
    
    for i, g in enumerate(gorevler):
        # Her etkinlik için bir buton oluşturuyoruz
        if st.button(f"🗓 {g['tarih']} \n {g['olay']}", key=f"btn_{i}", use_container_width=True):
            detay_goster(g)

# SOHBET KISMI
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "system", 
        "content": """Sen Tuba'nın profesyonel asistanısın.
        GÖREVİN:
        1. Kullanıcı tarih verirse 'gorev_kaydet' aracını kullan.
        2. Kayıttan sonra DETAYLI CHECKLIST hazırla.
        """
    }]

for msg in st.session_state.messages:
    if msg["role"] != "system" and msg["role"] != "tool":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if prompt := st.chat_input("Yeni bir etkinlik planlayalım..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

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
                    
                    link = google_calendar_link(args["tarih"], args["olay_adi"])
                    st.success(f"✅ Kaydedildi!")
                    st.markdown(f"👉 [**Takvime Ekle**]({link})", unsafe_allow_html=True)

            final = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
            yanit = final.choices[0].message.content
        else:
            yanit = ai_msg.content

        st.session_state.messages.append({"role": "assistant", "content": yanit})
        with st.chat_message("assistant"):
            st.markdown(yanit)

    except Exception as e:
        st.error(str(e))
