import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Ayarları yükle
load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- 1. HAFIZA FONKSİYONU ---
def gorev_kaydet(tarih, olay_adi):
    print(f"\n[SİSTEM] 💾 Kayıt İşlemi Başlatıldı: {olay_adi} -> {tarih}")
    
    dosya_adi = "gorevler.json"
    
    try:
        with open(dosya_adi, "r", encoding="utf-8") as f:
            liste = json.load(f)
    except:
        liste = []
        
    liste.append({"tarih": tarih, "olay": olay_adi})
    
    with open(dosya_adi, "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=4)
        
    return "KAYIT BAŞARILI. Şimdi kullanıcıya checklist sunabilirsin."

# --- 2. ARAÇ TANIMI ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "gorev_kaydet",
            "description": "Tarih ve etkinlik adı verildiğinde veritabanına kaydetmek için kullanılır.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tarih": {"type": "string", "description": "Tarih (Yıl-Ay-Gün formatında, örn: 2025-04-15)"},
                    "olay_adi": {"type": "string", "description": "Etkinliğin adı"}
                },
                "required": ["tarih", "olay_adi"]
            }
        }
    }
]

# --- 3. SERT TALİMATLAR ---
SISTEM_TALIMATI = """
Sen bir Deadline Takip Asistanısın.
KURAL 1: Kullanıcı sana bir tarih ve etkinlik söylediğinde, SADECE konuşmak yasak!
KURAL 2: ÖNCE mutlaka 'gorev_kaydet' fonksiyonunu çalıştırarak etkinliği kaydet.
KURAL 3: Kayıt işlemi bittikten sonra kullanıcıya güzel bir checklist sun.
"""

def asistan_baslat():
    print("\n--- ASİSTAN V2.1 (Disiplinli Mod) HAZIR ---")
    print("Çıkmak için 'q' yazabilirsin.\n")
    
    sohbet_gecmisi = [{"role": "system", "content": SISTEM_TALIMATI}]

    while True:
        soru = input("Sen: ")
        if soru.lower() == 'q': break
        
        sohbet_gecmisi.append({"role": "user", "content": soru})
        
        # Tool kullanımı için 'tool_choice' parametresini 'auto' bırakıyoruz ama prompt ile zorluyoruz
        cevap = client.chat.completions.create(
            model="gpt-4o",
            messages=sohbet_gecmisi,
            tools=tools
        )
        
        gpt_mesaji = cevap.choices[0].message
        
        # Eğer GPT fonksiyon çağırmaya karar verdiyse (Ki artık vermeli!)
        if gpt_mesaji.tool_calls:
            tool_call = gpt_mesaji.tool_calls[0]
            fonksiyon_adi = tool_call.function.name
            argumanlar = json.loads(tool_call.function.arguments)
            
            if fonksiyon_adi == "gorev_kaydet":
                # Python fonksiyonunu çalıştır
                sonuc = gorev_kaydet(argumanlar["tarih"], argumanlar["olay_adi"])
                
                # GPT'ye "Tamam kaydettim" bilgisini ver
                sohbet_gecmisi.append(gpt_mesaji)
                sohbet_gecmisi.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": sonuc
                })
                
                # Şimdi asıl konuşmayı yapsın (Checklist'i versin)
                ikinci_cevap = client.chat.completions.create(
                    model="gpt-4o",
                    messages=sohbet_gecmisi
                )
                print(f"\nAsistan:\n{ikinci_cevap.choices[0].message.content}\n")
        
        else:
            print(f"\nAsistan:\n{gpt_mesaji.content}\n")
            sohbet_gecmisi.append(gpt_mesaji)

if __name__ == "__main__":
    asistan_baslat()